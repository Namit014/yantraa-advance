from loader import (
    load_files,
    read_docx,
    read_pdf,
    read_image,
    read_text
)

from chunker import (
    Chunker,
    create_metadata,
    chunk_cad_by_component,
    chunk_excel_by_row
)

from embedder import Embedder
from vectordb import VectorDB


def ingest():

    files = load_files()

    print(f"\nFound {len(files)} files\n")

    chunker = Chunker()
    embedder = Embedder()
    vectordb = VectorDB()

    total_chunks = 0

    for file_info in files:

        try:

            file_type = file_info["file_type"]

            if file_type in [".stp", ".step"]:
                chunks = chunk_cad_by_component(file_info)
                if not chunks:
                    continue
                embedded_chunks = embedder.embed_chunks(chunks)
                vectordb.store_chunks(embedded_chunks)
                total_chunks += len(chunks)
                print(f"CAD Processed: {file_info['file_name']} → {len(chunks)} components")
                continue

            if file_type == ".xlsx":
                chunks = chunk_excel_by_row(file_info)
                if not chunks:
                    continue
                embedded_chunks = embedder.embed_chunks(chunks)
                vectordb.store_chunks(embedded_chunks)
                total_chunks += len(chunks)
                print(f"Excel Processed: {file_info['file_name']} → {len(chunks)} row chunks")
                continue


            if file_type not in [
                ".docx",
                ".pdf",
                ".md",
                ".txt"
            ]:
                continue

            file_path = file_info["file_path"]

            if file_type == ".docx":

                text = read_docx(
                    file_path
                )

            elif file_type == ".pdf":

                text = read_pdf(
                    file_path
                )
                
            elif file_type in [".md", ".txt"]:

                text = read_text(
                    file_path
                )

            if not text.strip():
                continue

            metadata = create_metadata(
                file_info
            )

            chunks = (
                chunker.chunk_document(
                    text,
                    metadata
                )
            )

            embedded_chunks = (
                embedder.embed_chunks(
                    chunks
                )
            )

            vectordb.store_chunks(
                embedded_chunks
            )

            total_chunks += len(chunks)

            print(
                f"Processed: "
                f"{file_info['file_name']}"
            )

        except Exception as e:

            print(
                f"Failed: "
                f"{file_info['file_name']}"
            )

            print(e)

    vectordb.close()

    print(
        f"\nFinished!"
    )

    print(
        f"Total Chunks: "
        f"{total_chunks}"
    )


if __name__ == "__main__":
    ingest()