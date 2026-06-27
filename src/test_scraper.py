import asyncio
import sys
import os

# Add src directory to path
_src_dir = os.path.dirname(os.path.abspath(__file__))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from scraper.cad_scraper import scrape_missing_component

async def main():
    print("Testing CAD Scraper for 'NEMA 17 Stepper Motor'...")
    # Force remodel to bypass cache
    result = await scrape_missing_component("NEMA 17 Stepper Motor", force_remodel=True)
    print(f"Scraper returned: {result}")

if __name__ == "__main__":
    asyncio.run(main())
