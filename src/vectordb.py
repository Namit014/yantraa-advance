import os
import uuid
import hashlib
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct
)

# Allow configuring Qdrant storage path via env var (important for production/AWS deployments)
# Default: ./qdrant_data (relative, works for local dev)
# On AWS set: QDRANT_DATA_PATH=/home/ubuntu/yantraa-advance/qdrant_data
QDRANT_DATA_PATH = os.getenv("QDRANT_DATA_PATH", "./qdrant_data")
_client_instance = None

def get_qdrant_client():
    global _client_instance
    if _client_instance is None:
        try:
            _client_instance = QdrantClient(path=QDRANT_DATA_PATH)
        except Exception as e:
            if "already accessed by another instance" in str(e):
                print(f"[Yantra AI] WARNING: Qdrant Database is locked by another process. Returning existing instance or running without Qdrant.")
                raise RuntimeError("Storage folder is locked. Please ensure only one backend instance is running.") from e
            raise e
    return _client_instance

def compute_content_hash(text: str) -> str:
    """Compute SHA-256 hash of a string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def get_all_content_hashes(client, collection_name="yantra_knowledgebase") -> set:
    """Scroll through Qdrant collection to retrieve all existing content hashes."""
    hashes = set()
    try:
        collections = client.get_collections()
        existing = [c.name for c in collections.collections]
        if collection_name not in existing:
            return hashes
            
        offset = None
        while True:
            results, next_page_offset = client.scroll(
                collection_name=collection_name,
                limit=100,
                with_payload=["content_hash"],
                with_vectors=False,
                offset=offset
            )
            for record in results:
                if record.payload and "content_hash" in record.payload:
                    hashes.add(record.payload["content_hash"])
            if not next_page_offset:
                break
            offset = next_page_offset
    except Exception as e:
        print(f"Error retrieving content hashes: {e}")
    return hashes

class VectorDB:

    def __init__(
        self,
        collection_name="yantra_knowledgebase",
        vector_size=2048,
        client=None
    ):

        self.collection_name = collection_name

        if client:
            self.client = client
        else:
            self.client = get_qdrant_client()

        self._create_collection(
            vector_size
        )

    def _create_collection(
        self,
        vector_size
    ):

        collections = self.client.get_collections()

        existing = [
            c.name
            for c in collections.collections
        ]

        if self.collection_name not in existing:

            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE
                )
            )

            print(
                f"Created collection: {self.collection_name}"
            )

    def store_chunks(
        self,
        embedded_chunks
    ):

        points = []

        for idx, chunk in enumerate(
            embedded_chunks
        ):
            # Compute content hash and store it in payload
            c_hash = compute_content_hash(chunk["text"])
            payload = {
                "text": chunk["text"],
                "content_hash": c_hash,
                **chunk["metadata"]
            }

            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=chunk["embedding"],
                    payload=payload
                )
            )

        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )

        print(
            f"Stored {len(points)} chunks."
        )
        
    def close(self):
        # We don't close the shared client here to keep the singleton open,
        # but keep the interface for compatibility.
        pass


if __name__ == "__main__":

    sample_chunks = [
        {
            "text": "Servo motors are used for position control.",
            "metadata": {
                "robot": "Articulated_Robot",
                "category": "Motors"
            },
            "embedding": [0.1] * 1024
        }
    ]

    vectordb = VectorDB()

    vectordb.store_chunks(
        sample_chunks
    )