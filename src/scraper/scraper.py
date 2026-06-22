import asyncio
import logging
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

logger = logging.getLogger(__name__)

async def fetch_clean_text(url: str, timeout: int = 20) -> str:
    """
    Fetch a URL via Crawl4AI which returns clean, LLM-ready markdown.
    """
    try:
        config = CrawlerRunConfig(page_timeout=timeout * 1000) # crawl4ai expects milliseconds
        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun(url=url, config=config)
            
            if result.success:
                text = result.markdown.strip() if result.markdown else ""
                if len(text) > 50:
                    return text
            logger.warning(f"Crawl4AI returned empty or failed result for {url}")
            return ""
            
    except Exception as e:
        logger.error(f"Crawl4AI fetch failed for {url}: {e}")
        return ""

