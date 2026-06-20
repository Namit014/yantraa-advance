import sys
import os

# Configure UTF-8 encoding for standard output/error to avoid charmap crashes on Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Ensure src/ is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from retriever import Retriever

def main():
    print("Initializing retriever...")
    retriever = Retriever()
    
    # Query completely unrelated to robotics to guarantee local database returns low scores
    query = "Who is the current Prime Minister of Japan in June 2026?"
    print(f"\nAsking: '{query}'")
    
    answer, cad_available, cad_url, fallback_used, source_urls = retriever.ask(query)
    
    print("\n" + "="*50)
    print("RESULTS:")
    print("="*50)
    print(f"Fallback Used: {fallback_used}")
    print(f"Source URLs: {source_urls}")
    print(f"CAD Available: {cad_available}")
    print(f"CAD URL: {cad_url}")
    print(f"Answer:\n{answer}")
    print("="*50)

if __name__ == "__main__":
    main()
