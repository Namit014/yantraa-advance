import os
import requests
from dotenv import load_dotenv

# Always load .env from the project root (two levels up from src/embedder.py)
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(_project_root, ".env"), override=True)

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
EMBEDDING_MODEL = "baai/bge-large-en-v1.5"
EMBEDDING_DIMENSION = 1024


class Embedder:

    def __init__(self):

        print(f"Using OpenRouter Embedding API: {EMBEDDING_MODEL}")

        if not OPENROUTER_API_KEY:
            raise ValueError(
                "OPENROUTER_API_KEY not found in environment. "
                "Set it in your .env file."
            )

        self.model = EMBEDDING_MODEL
        self.api_key = OPENROUTER_API_KEY
        self.api_url = "https://openrouter.ai/api/v1/embeddings"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "Yantra RAG"
        }

        print("OpenRouter Embedder ready.")

    def embed_text(self, text):

        payload = {
            "model": self.model,
            "input": text
        }

        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]
        except Exception as e:
            print(f"Error calling OpenRouter Embedding API: {e}")
            if 'response' in locals():
                print(f"Response: {response.text}")
            raise Exception(f"Embedding failed: {e}")

    def embed_batch(self, texts):
        """Embed multiple texts in a single API call for efficiency."""

        payload = {
            "model": self.model,
            "input": texts
        }

        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            data = response.json()
            # Sort by index to maintain order
            sorted_data = sorted(data["data"], key=lambda x: x["index"])
            return [item["embedding"] for item in sorted_data]
        except Exception as e:
            print(f"Error calling OpenRouter Embedding API (batch): {e}")
            if 'response' in locals():
                print(f"Response: {response.text}")
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