import re
import io
import base64
import logging

import pandas as pd
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


class Chunker:

    def __init__(
        self,
        chunk_size=512,
        chunk_overlap=100
    ):

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=[
                "\n\n",
                "\n",
                ". ",
                " ",
                ""
            ]
        )

    def chunk_document(self, text, metadata):

        chunks = self.splitter.split_text(text)

        chunked_documents = []

        for idx, chunk in enumerate(chunks):

            chunked_documents.append({
                "chunk_id": idx,
                "text": chunk,
                "metadata": metadata
            })

        return chunked_documents




def create_metadata(file_info):

    filename = file_info["file_name"].lower()

    KEYWORD_MAP = {
        "sensor": "Sensors", "motor": "Motors", "driver": "Motor Drivers",
        "bldc": "Motors", "servo": "Motors", "stepper": "Motors",
        "control": "Control System", "power": "Power System", "psu": "Power System",
        "software": "Software", "firmware": "Software",
        "comm": "Communication", "uart": "Communication", "can": "Communication",
        "cad": "CAD", "step": "CAD", "stp": "CAD",
        "gripper": "End Effectors", "effector": "End Effectors",
        "frame": "Structural", "chassis": "Structural",
        "bom": "Bill of Materials", "schematic": "Schematics",
        "lidar": "Sensors", "imu": "Sensors", "encoder": "Sensors",
    }
    categories = [cat for kw, cat in KEYWORD_MAP.items() if kw in filename]
    if not categories:
        categories = ["General"]

    metadata = {
        "robot": file_info["robot_name"],
        "source_file": file_info["file_name"],
        "file_type": file_info["file_type"],
        "categories": categories  # multi-label list, not a single string
    }

    return metadata

def parse_step_components(content: str) -> list:
    """
    Parse a STEP (.stp/.step) file and extract named components.

    Args:
        content: The full text content of the STEP file as a Python string.
                 The caller is responsible for fetching the bytes (from S3 or
                 local disk) and decoding them before calling this function.

    Returns:
        List of dicts with keys: entity_id, name, description.
    """
    components = []

    # Extract all PRODUCT entities — each represents a named CAD component.
    # PRODUCT entity format: PRODUCT('name','description','',(#ref))
    product_pattern = re.compile(
        r"#(\d+)\s*=\s*PRODUCT\s*\(\s*'([^']*)'\s*,\s*'([^']*)'\s*,",
        re.IGNORECASE,
    )

    for match in product_pattern.finditer(content):
        entity_id = match.group(1)
        name      = match.group(2).strip()
        desc      = match.group(3).strip()

        if not name:
            continue

        components.append({
            "entity_id":   entity_id,
            "name":        name,
            "description": desc if desc else name,
        })

    return components


def chunk_cad_by_component(file_info: dict) -> list:
    """
    Component-based chunking for STEP/STP files.
    Returns one chunk per named PRODUCT component.

    When file_info["source"] == "s3" the function fetches the file content
    in-memory via loader.read_step_content(); otherwise it falls back to
    opening the local file_path on disk (backward-compat for local runs).
    """
    robot_name = file_info["robot_name"]
    file_name  = file_info["file_name"]

    # ── Fetch STEP content ─────────────────────────────────────────────────
    if file_info.get("source") == "s3":
        # Import here to avoid a circular import at module level
        from loader import read_step_content  # noqa: PLC0415
        content = read_step_content(file_info)
    else:
        # Legacy local-file path (kept for backward compatibility)
        with open(file_info["file_path"], "r", encoding="utf-8", errors="ignore") as fh:
            content = fh.read()

    components = parse_step_components(content)

    chunks = []
    for idx, comp in enumerate(components):
        # Build a human-readable text representation of the component
        text = (
            f"Robot: {robot_name}\n"
            f"CAD Component: {comp['name']}\n"
            f"Description: {comp['description']}\n"
            f"Entity ID: #{comp['entity_id']}\n"
            f"Source File: {file_name}"
        )
        chunks.append({
            "chunk_id": idx,
            "text":     text,
            "metadata": {
                "robot":       robot_name,
                "source_file": file_name,
                "file_type":   ".step",
                "category":    "CAD",
                "component":   comp["name"],
                "entity_id":   comp["entity_id"],
                "chunk_type":  "cad_component",
            },
        })

    return chunks


if __name__ == "__main__":

    sample_text = """
    Articulated Robot Overview

    An articulated robot is a robotic arm with multiple rotary joints.

    Components:
    Servo Motors
    Controllers
    Sensors

    Applications:
    Welding
    Painting
    Material Handling
    """

    sample_file = {
        "robot_name": "Articulated_Robot",
        "file_name": "04_Articulated_Robot_Sensors.docx",
        "file_type": ".docx"
    }

    metadata = create_metadata(sample_file)

    chunker = Chunker()

    chunks = chunker.chunk_document(
        sample_text,
        metadata
    )

    print(f"Total Chunks: {len(chunks)}\n")

    for chunk in chunks:
        print(chunk)


def chunk_excel_by_row(file_info: dict) -> list:
    """
    Row-based chunking for Excel (.xlsx) files.

    When file_info["source"] == "s3", the spreadsheet is fetched in-memory
    via loader.read_excel_bytes() and passed directly to pandas — no temp
    files are created.  For local files the original file_path is used.
    """
    robot_name = file_info["robot_name"]
    file_name  = file_info["file_name"]

    # ── Fetch Excel content ────────────────────────────────────────────────
    if file_info.get("source") == "s3":
        from loader import read_excel_bytes  # noqa: PLC0415
        excel_source = read_excel_bytes(file_info)   # io.BytesIO
    else:
        excel_source = file_info["file_path"]        # local path string

    df = pd.read_excel(excel_source)

    chunks = []
    for idx, row in df.iterrows():
        # Build a readable text representation of each row
        row_text = "\n".join(
            f"{col}: {val}" for col, val in row.items() if pd.notna(val)
        )
        text = (
            f"Robot: {robot_name}\n"
            f"Source File: {file_name}\n"
            f"Data Row {idx + 1}:\n{row_text}"
        )

        metadata = create_metadata(file_info)
        metadata["chunk_type"] = "excel_row"
        metadata["row_index"]  = idx

        chunks.append({
            "chunk_id": idx,
            "text":     text,
            "metadata": metadata,
        })

    return chunks