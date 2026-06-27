"""
loader.py — S3-backed knowledge base loader.

All file reading is done entirely in-memory using io.BytesIO / boto3.get_object().
No files are written to disk.  The rest of the ingestion pipeline (ingest.py,
chunker.py, embedder.py, vectordb.py) requires minimal or no changes.

Environment variables consumed:
    AWS_ACCESS_KEY_ID      – IAM key with s3:GetObject / s3:ListBucket
    AWS_SECRET_ACCESS_KEY  – matching secret
    AWS_REGION             – bucket region, e.g. "ap-south-1"
    S3_BUCKET_NAME         – bucket that stores the knowledge-base files
"""

import io
import os
import base64
import logging

import boto3
from botocore.exceptions import ClientError, BotoCoreError
from docx import Document
from pypdf import PdfReader
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

# ---------------------------------------------------------------------------
# Load credentials from .env (silently ignored if already in environment)
# ---------------------------------------------------------------------------
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(_project_root, ".env"), override=False)

AWS_ACCESS_KEY_ID     = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_REGION            = os.environ.get("AWS_REGION", "ap-south-1")
S3_BUCKET_NAME        = os.environ.get("S3_BUCKET_NAME")

# ---------------------------------------------------------------------------
# File-type filters (unchanged from original)
# ---------------------------------------------------------------------------
# Extensions the ingestion pipeline can actually process
SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx", ".stp", ".step", ".xlsx", ".jpg", ".jpeg", ".png", ".webp"}

# Boilerplate filenames to skip (case-insensitive)
SKIP_FILENAMES = {"readme.md", "license", "license.txt", "contributing.md"}


# ---------------------------------------------------------------------------
# S3 client factory (lazy singleton per process)
# ---------------------------------------------------------------------------
_s3_client = None

def _get_s3_client():
    """Return a cached boto3 S3 client, creating it on first call."""
    global _s3_client
    if _s3_client is None:
        if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET_NAME]):
            raise EnvironmentError(
                "Missing required environment variables: "
                "AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET_NAME"
            )
        _s3_client = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION,
        )
    return _s3_client


# ---------------------------------------------------------------------------
# Core: fetch raw bytes from S3 into memory
# ---------------------------------------------------------------------------
def _fetch_s3_bytes(s3_key: str) -> bytes:
    """
    Stream an S3 object into memory and return its raw bytes.
    Raises ClientError on access/not-found errors.
    """
    client = _get_s3_client()
    response = client.get_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
    # read() buffers the streaming body fully in-memory (BytesIO-compatible)
    return response["Body"].read()


# ---------------------------------------------------------------------------
# File readers — each works from in-memory bytes when source is S3
# ---------------------------------------------------------------------------

def read_text(file_info: dict) -> str:
    """Read a plain-text / Markdown file from S3 in-memory."""
    raw = _fetch_s3_bytes(file_info["s3_key"])
    # Decode with UTF-8 and fall back to latin-1 for robustness
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1", errors="replace")


def read_pdf(file_info: dict) -> str:
    """Stream a PDF from S3 into PdfReader via BytesIO."""
    raw = _fetch_s3_bytes(file_info["s3_key"])
    reader = PdfReader(io.BytesIO(raw))
    pages = [page.extract_text() for page in reader.pages if page.extract_text()]
    return "\n".join(pages)


def read_docx(file_info: dict) -> str:
    """Stream a DOCX from S3 into python-docx via BytesIO."""
    raw = _fetch_s3_bytes(file_info["s3_key"])
    doc = Document(io.BytesIO(raw))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def read_image(file_info: dict) -> str:
    """
    Fetch an image from S3 and return it as a base64-encoded string
    suitable for vision model processing.
    """
    raw = _fetch_s3_bytes(file_info["s3_key"])
    return base64.b64encode(raw).decode("utf-8")


def read_step_content(file_info: dict) -> str:
    """
    Fetch a STEP/STP file from S3 and return its raw text content.
    Used by chunker.parse_step_components() which expects a string.
    """
    raw = _fetch_s3_bytes(file_info["s3_key"])
    try:
        return raw.decode("utf-8", errors="ignore")
    except Exception:
        return raw.decode("latin-1", errors="ignore")


def read_excel_bytes(file_info: dict) -> io.BytesIO:
    """
    Fetch an Excel file from S3 and return a BytesIO buffer.
    pandas.read_excel() natively accepts a BytesIO object.
    """
    raw = _fetch_s3_bytes(file_info["s3_key"])
    return io.BytesIO(raw)


# ---------------------------------------------------------------------------
# Main entry point: list all objects in S3 and return file metadata
# ---------------------------------------------------------------------------

def load_files() -> list[dict]:
    """
    Paginate through the entire S3 bucket and return a list of file-info
    dicts that the ingestion pipeline understands.

    Each dict has the shape:
        {
            "robot_name": str,   # top-level folder in the S3 key
            "file_name":  str,   # basename of the object
            "file_type":  str,   # lowercase extension, e.g. ".pdf"
            "file_path":  str,   # logical s3://bucket/key URI (informational)
            "s3_key":     str,   # raw S3 object key used for get_object()
            "source":     "s3",
        }

    Objects that are directory markers, hidden, boilerplate, or unsupported
    are silently skipped — matching the original filesystem filter logic.
    """
    client = _get_s3_client()
    paginator = client.get_paginator("list_objects_v2")

    files = []
    total_seen = 0

    logger.info("Scanning S3 bucket: %s", S3_BUCKET_NAME)

    for page in paginator.paginate(Bucket=S3_BUCKET_NAME):
        for obj in page.get("Contents", []):
            key: str = obj["Key"]
            total_seen += 1

            # ── Skip S3 "directory" markers (keys ending with /) ──────────
            if key.endswith("/"):
                continue

            # Split the key into path segments for filtering
            parts = key.split("/")
            filename = parts[-1]

            # ── Skip hidden files or files inside hidden folders ──────────
            # (any segment starting with "." is considered hidden)
            if any(part.startswith(".") for part in parts):
                continue

            # ── Skip well-known boilerplate filenames ─────────────────────
            if filename.lower() in SKIP_FILENAMES:
                continue

            # ── Derive file extension ─────────────────────────────────────
            _, ext = os.path.splitext(filename)
            file_type = ext.lower()

            # ── Skip unsupported formats early ────────────────────────────
            if file_type not in SUPPORTED_EXTENSIONS:
                continue

            # ── Derive robot_name from the top-level folder ───────────────
            # key format expected: <robot_name>/.../<filename>
            # If the file sits at the bucket root, use "general"
            robot_name = parts[0] if len(parts) > 1 else "general"

            files.append({
                "robot_name": robot_name,
                "file_name":  filename,
                "file_type":  file_type,
                "file_path":  f"s3://{S3_BUCKET_NAME}/{key}",
                "s3_key":     key,
                "source":     "s3",
            })

    logger.info("S3 scan complete. Objects seen: %d | Eligible files: %d", total_seen, len(files))
    return files


# ---------------------------------------------------------------------------
# CLI helper (python src/loader.py for a quick sanity check)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    items = load_files()
    print(f"\nTotal Files: {len(items)}\n")
    for f in items[:20]:
        print(f)