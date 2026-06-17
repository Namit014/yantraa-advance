from ddgs import DDGS

def search_web(query, max_results=15):
    """Search DuckDuckGo and return a list of result URLs."""
    urls = []
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=max_results)
            for result in results:
                href = result.get("href") or result.get("url", "")
                if href:
                    urls.append(href)
    except Exception as e:
        print(f"[Search] DuckDuckGo search failed: {e}")
    return urls

if __name__ == "__main__":
    print(search_web("delta robot specifications"))
