import sys
import os

# Ensure src/ is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from embedder import Embedder
from vectordb import VectorDB

class FAQRetriever:
    def __init__(self):
        self.embedder = Embedder()
        self.vectordb = VectorDB(collection_name="yantra_faq", vector_size=2048)

    def retrieve_clarification_faqs(self, prompt: str, scores: dict, top_k: int = 3) -> list:
        # Embed the prompt
        query_embedding = self.embedder.embed_text(prompt)
        
        # Search Qdrant for similar FAQs
        results = self.vectordb.client.query_points(
            collection_name=self.vectordb.collection_name,
            query=query_embedding,
            limit=top_k * 2  # fetch more to filter/boost
        )
        
        faqs = []
        for res in results.points:
            faqs.append({
                "id": res.payload.get("chunk_id", res.id),
                "question": res.payload.get("text"),
                "dimension": res.payload.get("dimension"),
                "hint": res.payload.get("hint"),
                "parameter": res.payload.get("parameter"),
                "similarity": res.score
            })
            
        # Boost FAQs that correspond to low-scoring dimensions
        dimensions = scores.get("dimensions", {})
        low_dimensions = [dim_name for dim_name, score in dimensions.items() if score <= 3]
        
        # Sort so that FAQs matching low dimensions appear first
        def get_boost(faq):
            # FAQ dimension matches a low-scoring dimension
            faq_dim = str(faq.get("dimension")).lower()
            if faq_dim in [d.replace('_', ' ') for d in low_dimensions] or faq_dim in [d.replace('_', '') for d in low_dimensions]:
                return faq["similarity"] + 1.0 # arbitrary boost
            return faq["similarity"]
            
        faqs.sort(key=get_boost, reverse=True)
        
        return faqs[:top_k]

if __name__ == "__main__":
    retriever = FAQRetriever()
    faqs = retriever.retrieve_clarification_faqs("scara robot", {"dimensions": {"completeness": 2, "specificity": 2}})
    for faq in faqs:
        print(faq)
