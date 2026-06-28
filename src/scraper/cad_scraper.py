import os
import sys
import json
import re
import httpx
import asyncio
import random
from urllib.parse import urljoin
import datetime

# Ensure the src/ directory is always on the path
_src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from scraper.search import search_web
from llm import invoke_yantra_ai
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

_PROJECT_ROOT = os.path.dirname(_src_dir)
KB_DIR = os.path.join(_PROJECT_ROOT, "knowledgebase")
CAD_SCRAPED_DIR = os.path.join(_PROJECT_ROOT, "frontend", "public", "cad")
SCRAPED_JSON_PATH = os.path.join(KB_DIR, "Robots_MetaData", "scraped_components.json")

# Ensure directories exist
os.makedirs(CAD_SCRAPED_DIR, exist_ok=True)
os.makedirs(os.path.dirname(SCRAPED_JSON_PATH), exist_ok=True)


async def _download_file(url: str, dest_path: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (compatible; YantraBot/1.0)"})
            response.raise_for_status()
            with open(dest_path, "wb") as f:
                f.write(response.content)
            return True
    except Exception as e:
        print(f"[CAD Scraper] Failed to download {url}: {e}")
        return False

async def generate_cad_via_zoo(component_name: str, dest_dir: str) -> str:
    print(f"[Zoo API] Generating CAD for {component_name} using Zoo Text-to-CAD...")
    try:
        import kittycad
        from kittycad.client import Client
        import asyncio
        import random
        
        zoo_keys_raw = os.getenv("ZOO_API_KEY", "api-8aa07608-c02f-4297-b167-7f71f03deeab")
        zoo_keys = [k.strip() for k in zoo_keys_raw.split(",") if k.strip()]
        selected_key = random.choice(zoo_keys)
        
        print(f"[Zoo API] Using API Key: {selected_key[:8]}... for generation")
        client = Client(token=selected_key)
        ml_api = kittycad.MlAPI(client)
        
        result = ml_api.create_text_to_cad(
            output_format=kittycad.models.FileExportFormat.STEP,
            body=kittycad.models.TextToCadCreateBody(prompt=f"A highly detailed mechanical industrial part for a {component_name}")
        )
        op_id = result.root.id if hasattr(result, 'root') else result.id
        print(f"[Zoo API] Generation started. Operation ID: {op_id}")
        
        for _ in range(30):
            status = ml_api.get_text_to_cad_part_for_user(id=op_id)
            s_root = status.root if hasattr(status, 'root') else status
            if s_root.status == "completed":
                clean_name = re.sub(r"[^a-z0-9]+", "_", component_name.lower()).strip("_")
                cad_filename = f"zoo_{clean_name}.step"
                dest_path = os.path.join(dest_dir, cad_filename)
                
                # Get first output
                for output_name, output_data in s_root.outputs.items():
                    with open(dest_path, "wb") as f:
                        f.write(output_data)
                    print(f"[Zoo API] Generated successfully: {cad_filename}")
                    return cad_filename
            elif s_root.status == "failed":
                print(f"[Zoo API] Failed: {s_root.error}")
                return None
            print(f"[Zoo API] Status: {s_root.status}...")
            await asyncio.sleep(4)
    except Exception as e:
        print(f"[Zoo API] Error during generation: {e}")
    return None


async def scrape_missing_component(component_name: str, force_remodel: bool = False):
    print(f"[CAD Scraper] Task started for missing component: {component_name}")
    
    # Check if already scraped
    if os.path.exists(SCRAPED_JSON_PATH):
        try:
            with open(SCRAPED_JSON_PATH, "r", encoding="utf-8") as f:
                scraped_data = json.load(f)
            
            if force_remodel:
                # Delete existing entry from cache
                original_len = len(scraped_data.get("components", []))
                scraped_data["components"] = [c for c in scraped_data.get("components", []) if c.get("name", "").lower() != component_name.lower()]
                if len(scraped_data["components"]) < original_len:
                    with open(SCRAPED_JSON_PATH, "w", encoding="utf-8") as f:
                        json.dump(scraped_data, f, indent=4)
                    print(f"[CAD Scraper] force_remodel is True. Removed '{component_name}' from local JSON cache.")
            else:
                for comp in scraped_data.get("components", []):
                    if comp.get("name", "").lower() == component_name.lower():
                        print(f"[CAD Scraper] Component '{component_name}' already exists in scraped_components.json. Skipping.")
                        return comp.get("cad_file")
        except Exception:
            pass

    cad_downloaded = False
    cad_filename = None
    extracted_text = ""
    source_url = ""

    config = CrawlerRunConfig(page_timeout=15000)
    query = f"{component_name} robotic component datasheet specs"
    
    async with AsyncWebCrawler(verbose=False) as crawler:
        print(f"[CAD Scraper] Searching web for textual metadata: {query}")
        raw_urls = search_web(query, max_results=5)
        
        for url in raw_urls:
            print(f"[CAD Scraper] Scraping metadata from {url}...")
            try:
                result = await crawler.arun(url=url, config=config)
                if result.success and result.markdown:
                    text_str = str(result.markdown).strip()
                    if len(text_str) > 50:
                        extracted_text = text_str
                        source_url = url
                        print(f"[CAD Scraper] Successfully extracted text from {url}")
                        break
            except Exception as e:
                print(f"[CAD Scraper] Error scraping {url}: {e}")

    # Normalize extracted text and handle Crawl4Ai empty/blocked results
    extracted_str = str(extracted_text).strip() if extracted_text else ""
    
    if not extracted_str or len(extracted_str) < 5:
        print(f"[CAD Scraper] No textual metadata could be scraped or generated for {component_name}.")
        extracted_text = f"Mechanical component '{component_name}' metadata unavailable."

    # Use LLM to extract JSON assembly info
    print(f"[CAD Scraper] Extracting assembly metadata using Yantra AI...")
    extraction_prompt = f"""You are a data extraction bot. We need to categorize a robotic component named '{component_name}'.
Read the following scraped web text and extract the technical metadata.

OUTPUT EXACTLY IN THIS JSON FORMAT:
{{
  "name": "{component_name}",
  "category": "Actuators | Sensors | Structure | Power | Electronics | EndEffectors | Other",
  "voltage": "e.g., 24V or N/A",
  "interface": "e.g., CAN, EtherCAT, USB, None",
  "description": "Brief 1 sentence description of what it does",
  "cad_file": "{cad_filename if cad_downloaded else ''}"
}}

Scraped Text:
{extracted_text[:6000]}"""

    system_msg = "You extract strictly formatted JSON."
    
    try:
        raw_response = invoke_yantra_ai(extraction_prompt, system_prompt=system_msg, response_format="json_object")
        # Strip markdown if present
        clean_json = raw_response.strip()
        if clean_json.startswith("```json"):
            clean_json = clean_json[7:-3]
        elif clean_json.startswith("```"):
            clean_json = clean_json[3:-3]
            
        metadata = json.loads(clean_json.strip())
        metadata["cad_file"] = cad_filename if cad_downloaded else ""
        metadata["scraped_at"] = datetime.datetime.now().isoformat()
        metadata["source_url"] = source_url
        
        # Load and update scraped_components.json
        scraped_data = {"components": []}
        if os.path.exists(SCRAPED_JSON_PATH):
            with open(SCRAPED_JSON_PATH, "r", encoding="utf-8") as f:
                scraped_data = json.load(f)
                
        scraped_data["components"].append(metadata)
        
        with open(SCRAPED_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(scraped_data, f, indent=4)
            
        print(f"[CAD Scraper] Successfully added {component_name} to scraped_components.json")
        return cad_filename if cad_downloaded else None
        
    except Exception as e:
        print(f"[CAD Scraper] Failed to extract or save metadata: {e}")
        return cad_filename if cad_downloaded else None
