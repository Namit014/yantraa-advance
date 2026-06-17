from loader import load_files, read_docx
from chunker import Chunker

print("Loading files...")

files = load_files()

print(f"Found {len(files)} files")

doc_path = r"C:\yantra\knowledgebase\Articulated_Robot\articulated_robot_datasheet\04_Articulated_Robot_Sensors.docx"

text = read_docx(doc_path)

chunker = Chunker()

metadata = {
    "robot": "Articulated_Robot",
    "category": "Sensors",
    "source_file": "04_Articulated_Robot_Sensors.docx"
}

chunks = chunker.chunk_document(
    text,
    metadata
)

print(f"\nTotal Chunks: {len(chunks)}")

for i, chunk in enumerate(chunks):
    print(f"\n===== CHUNK {i+1} =====")
    print(chunk["text"][:500])
    
    
from embedder import Embedder
from vectordb import VectorDB

print("\nLoading Embedder...")

embedder = Embedder()

embedded_chunks = embedder.embed_chunks(chunks)

print(f"\nEmbedded Chunks: {len(embedded_chunks)}")

print(
    f"Embedding Dimension: "
    f"{len(embedded_chunks[0]['embedding'])}"
)

print("\nConnecting to Qdrant...")

vectordb = VectorDB()

vectordb.store_chunks(
    embedded_chunks
)

vectordb.close()

print("\nStored Successfully!")


from retriever import Retriever

print("\nTesting Retrieval...")

retriever = Retriever()

results = retriever.search(
    "What sensors are used in articulated robots?"
)

print(f"\nRetrieved {len(results)} results")

for i, result in enumerate(results):

    print(f"\n===== RESULT {i+1} =====")

    print("Score:", result.score)

    print("Robot:",
          result.payload.get("robot"))

    print("Category:",
          result.payload.get("category"))

    print("\nText:\n")

    print(result.payload.get("text"))