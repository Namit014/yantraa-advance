import base64
from pathlib import Path
from docx import Document
from pypdf import PdfReader


import os

BASE_DIR = Path(__file__).parent.parent
KNOWLEDGEBASE_PATH = BASE_DIR / "knowledgebase"


def read_docx(file_path):

    doc = Document(file_path)

    text = []

    for para in doc.paragraphs:

        if para.text.strip():
            text.append(para.text)

    return "\n".join(text)


def read_pdf(file_path):

    reader = PdfReader(file_path)

    text = []

    for page in reader.pages:

        page_text = page.extract_text()

        if page_text:
            text.append(page_text)

    return "\n".join(text)


def read_text(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()



def read_image(file_path):
    """
    Read image as base64 string for vision model processing.
    """
    with open(file_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")
    return image_data


def load_files():

    files = []

    for file_path in KNOWLEDGEBASE_PATH.rglob("*"):

        if file_path.is_file():
            
            # Skip hidden files/folders like .git
            if any(part.startswith('.') for part in file_path.parts):
                continue
                
            # Skip boilerplate files
            name_lower = file_path.name.lower()
            if name_lower in ["readme.md", "license", "license.txt", "contributing.md"]:
                continue

            relative_path = file_path.relative_to(
                KNOWLEDGEBASE_PATH
            )

            metadata = {
                "robot_name": relative_path.parts[0],
                "file_name": file_path.name,
                "file_type": file_path.suffix.lower(),
                "file_path": str(file_path)
            }

            files.append(metadata)

    return files


if __name__ == "__main__":

    files = load_files()

    print(f"\nTotal Files: {len(files)}\n")

    for file in files[:10]:
        print(file)