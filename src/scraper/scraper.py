import requests
from bs4 import BeautifulSoup

# Tags whose content is pure navigation/boilerplate — strip them before extracting text
_BOILERPLATE_TAGS = [
    "nav", "footer", "header", "script", "style",
    "noscript", "aside", "form", "button", "iframe"
]

def scrape_url(url):
    """
    Fetch `url` and return clean visible text.
    Returns None on network/parse errors or if the page yields no useful content.
    """
    try:
        resp = requests.get(
            url,
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0 (compatible; YantraBot/1.0)"}
        )
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        print(f"[Scraper] Failed to fetch {url}: {e}")
        return None

    try:
        soup = BeautifulSoup(html, "html.parser")

        # Remove boilerplate sections
        for tag in _BOILERPLATE_TAGS:
            for el in soup.find_all(tag):
                el.decompose()

        text = soup.get_text(separator=" ", strip=True)
    except Exception as e:
        print(f"[Scraper] Failed to parse HTML from {url}: {e}")
        return None

    # Require at least 150 meaningful characters
    if len(text) < 150:
        print(f"[Scraper] Page too short or empty, skipping: {url}")
        return None

    return text
