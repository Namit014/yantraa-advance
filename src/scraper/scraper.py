import logging
import asyncio
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

async def fetch_clean_text(url: str, timeout: int = 20) -> str:
    """
    Fetch a URL using requests and BeautifulSoup to prevent Windows asyncio hangs
    that occur when using Playwright in subthreads.
    """
    try:
        def do_fetch():
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            # Remove scripts and styles
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            text = soup.get_text(separator="\n")
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = "\n".join(chunk for chunk in chunks if chunk)
            return text

        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(None, do_fetch)
        
        if len(text) > 50:
            return text
            
        logger.warning(f"Requests returned empty result for {url}")
        return ""
            
    except Exception as e:
        logger.error(f"Requests fetch failed for {url}: {e}")
        return ""
