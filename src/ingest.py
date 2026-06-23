import sys
import io
import logging

# Force UTF-8 encoding for standard output/error to avoid charmap crashes on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Local module imports
# ---------------------------------------------------------------------------
from loader import (
    load_files,
    read_docx,
    read_pdf,
    read_image,
    read_text,
)

from chunker import (
    Chunker,
    create_metadata,
    chunk_cad_by_component,
    chunk_excel_by_row,
)

from embedder import Embedder
from vectordb import VectorDB, get_all_content_hashes, compute_content_hash, get_qdrant_client


def ingest():
    # ── Step 1: List all eligible files from S3 ──────────────────────────────
    files = load_files()
    print(f"\nFound {len(files)} files\n")

    chunker  = Chunker()
    embedder = Embedder()
    vectordb = VectorDB()

    # ── Step 2: Retrieve existing content hashes from Qdrant ─────────────────
    # This lets us skip chunks that are already stored, enabling incremental
    # ingestion without re-embedding files that haven't changed.
    existing_hashes = get_all_content_hashes(
        get_qdrant_client(), collection_name=vectordb.collection_name
    )
    print(f"Retrieved {len(existing_hashes)} existing chunk hashes from Qdrant.")

    total_chunks = 0

    # ── Step 3: Process each file, streaming content in-memory from S3 ───────
    for file_info in files:
        try:
            file_type = file_info["file_type"]

            # ── CAD / STEP files ───────────────────────────────────────────
            if file_type in [".stp", ".step"]:
                # chunk_cad_by_component internally fetches the S3 object
                chunks = chunk_cad_by_component(file_info)
                if not chunks:
                    continue

                # Deduplicate against Qdrant
                filtered_chunks = [
                    c for c in chunks
                    if compute_content_hash(c["text"]) not in existing_hashes
                ]
                if not filtered_chunks:
                    print(f"Skipping already-ingested CAD: {file_info['file_name']}")
                    continue

                embedded_chunks = embedder.embed_chunks(filtered_chunks)
                vectordb.store_chunks(embedded_chunks)
                total_chunks += len(filtered_chunks)
                print(
                    f"CAD Processed: {file_info['file_name']} "
                    f"→ {len(filtered_chunks)} components"
                )
                continue

            # ── Excel files ────────────────────────────────────────────────
            if file_type == ".xlsx":
                # chunk_excel_by_row internally fetches the S3 object
                chunks = chunk_excel_by_row(file_info)
                if not chunks:
                    continue

                filtered_chunks = [
                    c for c in chunks
                    if compute_content_hash(c["text"]) not in existing_hashes
                ]
                if not filtered_chunks:
                    print(f"Skipping already-ingested Excel: {file_info['file_name']}")
                    continue

                embedded_chunks = embedder.embed_chunks(filtered_chunks)
                vectordb.store_chunks(embedded_chunks)
                total_chunks += len(filtered_chunks)
                print(
                    f"Excel Processed: {file_info['file_name']} "
                    f"→ {len(filtered_chunks)} row chunks"
                )
                continue

            # ── Text-based documents ───────────────────────────────────────
            # Only process the formats we can chunk meaningfully
            if file_type not in [".docx", ".pdf", ".md", ".txt"]:
                continue

            # Stream the file from S3 in-memory — no local path needed
            if file_type == ".docx":
                text = read_docx(file_info)

            elif file_type == ".pdf":
                text = read_pdf(file_info)

            elif file_type in [".md", ".txt"]:
                text = read_text(file_info)

            else:
                continue

            # Skip empty documents
            if not text or not text.strip():
                continue

            # Build metadata, chunk, deduplicate, embed, and store
            metadata = create_metadata(file_info)
            chunks   = chunker.chunk_document(text, metadata)

            filtered_chunks = [
                c for c in chunks
                if compute_content_hash(c["text"]) not in existing_hashes
            ]

            if not filtered_chunks:
                print(f"Skipping already-ingested file: {file_info['file_name']}")
                continue

            embedded_chunks = embedder.embed_chunks(filtered_chunks)
            vectordb.store_chunks(embedded_chunks)
            total_chunks += len(filtered_chunks)

            print(f"Processing: {file_info['file_name']}")

        except Exception as exc:
            # Log but do NOT abort — keep processing remaining files
            logger.error(
                "Failed to process %s: %s",
                file_info.get("file_name", "unknown"),
                exc,
                exc_info=True,
            )

    # ── Step 4: Clean up ─────────────────────────────────────────────────────
    vectordb.close()

    print(f"\nFinished!")
    print(f"Total Chunks: {total_chunks}")


if __name__ == "__main__":
    ingest()