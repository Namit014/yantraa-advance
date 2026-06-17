from src.retriever import Retriever

def test_web_fallback():
    print("Initializing Retriever...")
    retriever = Retriever()

    # Give it a query that is definitely NOT in your local documentation
    query = "What are the exact technical specifications of the Figure 02 humanoid robot released in 2024?"
    
    print(f"\nUser Query: '{query}'\n")
    
    # This will trigger the full Owl Alpha pipeline (Plan -> Qdrant -> Validate -> DuckDuckGo -> Scrape -> Extract JSON -> Embed -> Synthesize)
    final_answer = retriever.ask(query)

    print(f"\n============================================\nFINAL OWL ALPHA ANSWER:\n============================================\n{final_answer}\n")

if __name__ == "__main__":
    test_web_fallback()
