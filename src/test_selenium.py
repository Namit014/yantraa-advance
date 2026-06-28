import asyncio
import sys
import os

_src_dir = os.path.dirname(os.path.abspath(__file__))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from scraper.search import search_web
from scraper.selenium_downloader import selenium_download_cad

async def main():
    print("Testing DuckDuckGo Search...")
    urls = search_web("site:grabcad.com NEMA 17 Stepper Motor step stp model", max_results=3)
    print(f"Found URLs: {urls}")
    
    if not urls:
        print("No URLs found. Exiting.")
        return

    test_url = urls[0]
    print(f"Testing Selenium Downloader with URL: {test_url}")
    dest_dir = os.path.join(_src_dir, "..", "frontend", "public", "cad")
    os.makedirs(dest_dir, exist_ok=True)
    
    result = await selenium_download_cad(test_url, dest_dir, "test_nema_17.step")
    print(f"Selenium downloader returned: {result}")

if __name__ == "__main__":
    asyncio.run(main())
