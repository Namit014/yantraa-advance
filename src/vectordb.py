import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct
)


class VectorDB:

    def __init__(
        self,
        collection_name="yantra_knowledgebase",
        vector_size=1024,
        client=None
    ):

        self.collection_name = collection_name

        if client:
            self.client = client
        else:
            self.client = QdrantClient(
                path="./qdrant_data"
            )

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

            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=chunk["embedding"],
                    payload={
                        "text": chunk["text"],
                        **chunk["metadata"]
                    }
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
        self.client.close()


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