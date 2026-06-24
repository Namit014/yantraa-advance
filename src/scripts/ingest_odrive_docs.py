import os
import sys
import requests

# Add src to path so we can import RAG modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from chunker import Chunker
from embedder import Embedder
from vectordb import VectorDB, get_all_content_hashes, compute_content_hash, get_qdrant_client

ODRIVE_DOCS_URLS = [
    "https://raw.githubusercontent.com/odriverobotics/ODrive/master/README.md",
    "https://raw.githubusercontent.com/odriverobotics/ODrive/master/docs/getting-started.md",
    "https://raw.githubusercontent.com/odriverobotics/ODrive/master/docs/pinout.md"
]

def ingest_odrive():
    print("Fetching ODrive Documentation...")
    
    chunker = Chunker()
    embedder = Embedder()
    vectordb = VectorDB()
    
    existing_hashes = get_all_content_hashes(get_qdrant_client(), collection_name=vectordb.collection_name)
    total_chunks = 0

    for url in ODRIVE_DOCS_URLS:
        try:
            print(f"Downloading {url}...")
            response = requests.get(url)
            if response.status_code != 200:
                print(f"Failed to download {url}")
                continue
                
            text = response.text
            if not text.strip():
                continue
                
            filename = url.split('/')[-1]
            metadata = {
                "source": "odrive_docs",
                "url": url,
                "file_name": filename,
                "title": f"ODrive Documentation: {filename}"
            }
            
            chunks = chunker.chunk_document(text, metadata)
            filtered_chunks = []
            
            for chunk in chunks:
                c_hash = compute_content_hash(chunk["text"])
                if c_hash not in existing_hashes:
                    filtered_chunks.append(chunk)
                    
            if not filtered_chunks:
                print(f"Skipping already-ingested docs: {filename}")
                continue
                
            embedded_chunks = embedder.embed_chunks(filtered_chunks)
            vectordb.store_chunks(embedded_chunks)
            total_chunks += len(filtered_chunks)
            
            print(f"Processed: {filename} ({len(filtered_chunks)} chunks)")
            
        except Exception as e:
            print(f"Failed processing {url}: {e}")
            
    vectordb.close()
    print(f"\nFinished ingesting ODrive docs! Total new chunks: {total_chunks}")

if __name__ == "__main__":
    ingest_odrive()
