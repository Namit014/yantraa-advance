import httpx
import asyncio
import logging

logger = logging.getLogger(__name__)

JINA_BASE = "https://r.jina.ai/"

async def fetch_clean_text(url: str, timeout: int = 20) -> str:
    """
    Fetch a URL via Jina Reader which returns clean, LLM-ready markdown.
    Falls back to direct BeautifulSoup extraction if Jina fails.
    """
    jina_url = f"{JINA_BASE}{url}"
    headers = {
        "Accept": "text/plain",
        "X-Timeout": str(timeout),
        "X-Return-Format": "text",   # plain text, not markdown with image tags
    }
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(jina_url, headers=headers)
            response.raise_for_status()
            text = response.text.strip()
            if len(text) > 200:
                return text
            # Jina returned too little — fall through to direct fetch
    except Exception as e:
        logger.warning(f"Jina fetch failed for {url}: {e}. Falling back to direct fetch.")

    return await _direct_fetch_fallback(url, timeout)


async def _direct_fetch_fallback(url: str, timeout: int) -> str:
    """BeautifulSoup fallback when Jina is unavailable."""
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
            html = response.text
    except Exception as e:
        logger.error(f"Direct fetch also failed for {url}: {e}")
        return ""

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    for tag in ("nav", "footer", "header", "script", "style", "aside", "form", "noscript"):
        for el in soup.find_all(tag):
            el.decompose()
    article = soup.find("article") or soup.find("main") or soup.body or soup
    text = article.get_text(separator="\n", strip=True)
    lines = [line.strip() for line in text.splitlines() if len(line.strip()) > 30]
    return "\n".join(lines)
