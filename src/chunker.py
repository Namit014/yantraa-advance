import re
from langchain_text_splitters import RecursiveCharacterTextSplitter
import io
import base64
import pandas as pd



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

def parse_step_components(file_path):
    """
    Parse a STEP (.stp/.step) file and extract components
    by reading PRODUCT and SHAPE_DEFINITION entities.
    No external library needed — pure text parsing.
    """
    components = []

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    # Extract all PRODUCT entities — each is a named component
    # PRODUCT('name','description','',(#ref))
    product_pattern = re.compile(
        r"#(\d+)\s*=\s*PRODUCT\s*\(\s*'([^']*)'\s*,\s*'([^']*)'\s*,",
        re.IGNORECASE
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


def chunk_cad_by_component(file_info):
    """
    Component-based chunking for STEP/STP files.
    Returns one chunk per named PRODUCT component.
    """
    file_path  = file_info["file_path"]
    robot_name = file_info["robot_name"]
    file_name  = file_info["file_name"]

    components = parse_step_components(file_path)

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
                "robot":        robot_name,
                "source_file":  file_name,
                "file_type":    ".step",
                "category":     "CAD",
                "component":    comp["name"],
                "entity_id":    comp["entity_id"],
                "chunk_type":   "cad_component"
            }
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


def chunk_excel_by_row(file_info):
    file_path  = file_info["file_path"]
    robot_name = file_info["robot_name"]
    file_name  = file_info["file_name"]

    df = pd.read_excel(file_path)

    chunks = []
    for idx, row in df.iterrows():
        # Build text representation of the row
        row_text = "\n".join([f"{col}: {val}" for col, val in row.items() if pd.notna(val)])
        text = (
            f"Robot: {robot_name}\n"
            f"Source File: {file_name}\n"
            f"Data Row {idx + 1}:\n{row_text}"
        )

        metadata = create_metadata(file_info)
        metadata["chunk_type"] = "excel_row"
        metadata["row_index"] = idx

        chunks.append({
            "chunk_id": idx,
            "text": text,
            "metadata": metadata
        })

    return chunks