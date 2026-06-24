import asyncio
import os
import sys

# Ensure src/ is on sys.path
_src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "src"))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from scraper.cad_scraper import scrape_missing_component

async def test():
    print("Testing GrabCAD Scraper directly for 'detailed hexapod walking robot'...")
    res = await scrape_missing_component("detailed hexapod walking robot")
    print(f"Scraper returned: {res}")

if __name__ == "__main__":
    asyncio.run(test())
