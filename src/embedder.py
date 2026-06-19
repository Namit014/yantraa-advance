import os
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

# Always load .env from the project root (two levels up from src/embedder.py)
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(_project_root, ".env"), override=True)

# Using local model to bypass OpenRouter 402 Payment Required errors
EMBEDDING_MODEL = "BAAI/bge-large-en-v1.5"
EMBEDDING_DIMENSION = 1024


class Embedder:

    def __init__(self):
        print(f"Loading Local Embedding Model: {EMBEDDING_MODEL}")
        # Initialize local sentence-transformers model
        self.model = SentenceTransformer(EMBEDDING_MODEL)
        print("Local Embedder ready.")

    def embed_text(self, text):
        try:
            # sentence-transformers outputs a numpy array, convert to list
            embedding = self.model.encode(text).tolist()
            return embedding
        except Exception as e:
            print(f"Error calling Local Embedding Model: {e}")
            raise Exception(f"Embedding failed: {e}")

    def embed_batch(self, texts):
        """Embed multiple texts in a single batch locally."""
        try:
            # encode() naturally handles lists of texts efficiently
            embeddings = self.model.encode(texts).tolist()
            return embeddings
        except Exception as e:
            print(f"Error calling Local Embedding Model (batch): {e}")
            raise Exception(f"Batch embedding failed: {e}")

    def embed_chunks(self, chunks):

        embedded_chunks = []
        MAX_CHARS = 1200

        # Safety check: split any oversized chunks before embedding
        safe_chunks = []
        for chunk in chunks:
            text = chunk["text"]
            if len(text) > MAX_CHARS:
                # Split into smaller pieces
                for j in range(0, len(text), MAX_CHARS):
                    piece = text[j:j + MAX_CHARS]
                    # Create a new chunk object for the piece
                    new_chunk = chunk.copy()
                    new_chunk["text"] = piece
                    # Optionally append something to chunk_id to make it unique
                    new_chunk["chunk_id"] = f"{chunk['chunk_id']}_p{j//MAX_CHARS}"
                    safe_chunks.append(new_chunk)
            else:
                safe_chunks.append(chunk)

        # Process in batches of 20 for efficiency
        batch_size = 20
        for i in range(0, len(safe_chunks), batch_size):
            batch = safe_chunks[i:i + batch_size]
            texts = [chunk["text"] for chunk in batch]

            embeddings = self.embed_batch(texts)

            for chunk, embedding in zip(batch, embeddings):
                embedded_chunks.append({
                    "chunk_id": chunk["chunk_id"],
                    "text": chunk["text"],
                    "metadata": chunk["metadata"],
                    "embedding": embedding
                })

        return embedded_chunks


if __name__ == "__main__":

    sample_chunks = [
        {
            "chunk_id": 0,
            "text": "Servo motors are used for precise position control.",
            "metadata": {
                "robot": "Articulated_Robot"
            }
        }
    ]

    embedder = Embedder()

    embedded = embedder.embed_chunks(
        sample_chunks
    )

    print("\nEmbedding Dimension:")
    print(len(embedded[0]["embedding"]))

    print("\nFirst 10 Values:")
    print(embedded[0]["embedding"][:10])