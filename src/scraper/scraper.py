import httpx

def scrape_url(url):
    """
    Fetch `url` using httpx and return the raw HTML text.
    Returns None on network errors.
    """
    try:
        resp = httpx.get(
            url,
            timeout=15,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; YantraBot/1.0)"}
        )
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"[Scraper] Failed to fetch {url}: {e}")
        return None
