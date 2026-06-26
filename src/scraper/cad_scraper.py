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

from .search import search_web
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
        zoo_key = os.getenv("ZOO_API_KEY", "api-8aa07608-c02f-4297-b167-7f71f03deeab")
        client = Client(token=zoo_key)
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
    
    grabcad_queries = [
        f"site:grabcad.com {component_name} step stp model",
        f"site:grabcad.com {component_name} step download",
        f"site:grabcad.com {component_name} 3d cad step stp",
        f"site:grabcad.com {component_name} stp file",
        f"site:grabcad.com {component_name} step cad"
    ]
    
    urls_tried = set()
    
    async with AsyncWebCrawler(verbose=False) as crawler:
        # Phase 1: 5 attempts on GrabCAD
        for attempt, g_query in enumerate(grabcad_queries):
            print(f"[CAD Scraper] GrabCAD Attempt {attempt + 1}/5 for {component_name}...")
            raw_urls = search_web(g_query, max_results=10)
            
            # Filter URLs
            urls = []
            for url in raw_urls:
                if "/library?" in url or "/tag/" in url or "/software/" in url:
                    continue
                if url not in urls_tried:
                    urls.append(url)
                    urls_tried.add(url)
                    
            if force_remodel:
                random.shuffle(urls)
            
            if not urls:
                print(f"[CAD Scraper] No new GrabCAD links found on attempt {attempt + 1}.")
                continue
                
            # Try URLs with Crawl4AI
            for url in urls:
                print(f"[CAD Scraper] Checking {url} for CAD files using Crawl4AI...")
                try:
                    result = await crawler.arun(url=url, config=config)
                    if not result.success:
                        continue

                    cad_link = None
                    if result.links:
                        all_links = result.links.get("internal", []) + result.links.get("external", [])
                        for link_data in all_links:
                            href = link_data.get("href", "").lower()
                            if href.endswith(".step") or href.endswith(".stp"):
                                cad_link = urljoin(url, link_data.get("href", ""))
                                break
                            
                    if cad_link:
                        print(f"[CAD Scraper] Found CAD link: {cad_link}")
                        clean_name = re.sub(r"[^a-z0-9]+", "_", component_name.lower()).strip("_")
                        ext = ".step" if cad_link.lower().endswith(".step") else ".stp"
                        cad_filename = f"{clean_name}{ext}"
                        dest_path = os.path.join(CAD_SCRAPED_DIR, cad_filename)
                        
                        if await _download_file(cad_link, dest_path):
                            print(f"[CAD Scraper] Successfully downloaded {cad_filename}")
                            cad_downloaded = True
                            source_url = url
                            extracted_text = result.markdown
                            break
                except Exception as e:
                    print(f"[CAD Scraper] Error checking {url}: {e}")
                    continue

            if cad_downloaded:
                break
                
            # Try URLs with Selenium if Crawl4AI missed
            if not cad_downloaded:
                from .selenium_downloader import selenium_download_cad
                for url in urls:
                    print(f"[CAD Scraper] Standard crawl missed CAD for {url}, attempting Playwright fallback...")
                    clean_name = re.sub(r"[^a-z0-9]+", "_", component_name.lower()).strip("_")
                    fallback_filename = f"{clean_name}.step"
                    
                    final_file = await selenium_download_cad(url, CAD_SCRAPED_DIR, fallback_filename)
                    if final_file:
                        print(f"[CAD Scraper] Selenium fallback succeeded: {final_file}")
                        cad_downloaded = True
                        cad_filename = final_file
                        source_url = url
                        # Best effort to get text metadata
                        result = await crawler.arun(url=url, config=config)
                        if result.success:
                            extracted_text = result.markdown
                        break
                        
            if cad_downloaded:
                break
                
        # Phase 2: Fallback to another website if GrabCAD fails entirely
        if not cad_downloaded:
            print(f"[CAD Scraper] All 5 GrabCAD attempts failed for {component_name}. Falling back to general search...")
            query = f"{component_name} 3D CAD step stp file download"
            raw_urls = search_web(query, max_results=10)
            urls = [u for u in raw_urls if u not in urls_tried]
            
            if force_remodel:
                random.shuffle(urls)
            
            for url in urls:
                print(f"[CAD Scraper] Checking {url} for CAD files using Crawl4AI...")
                try:
                    result = await crawler.arun(url=url, config=config)
                    if not result.success:
                        continue

                    cad_link = None
                    if result.links:
                        all_links = result.links.get("internal", []) + result.links.get("external", [])
                        for link_data in all_links:
                            href = link_data.get("href", "").lower()
                            if href.endswith(".step") or href.endswith(".stp"):
                                cad_link = urljoin(url, link_data.get("href", ""))
                                break
                            
                    if cad_link:
                        print(f"[CAD Scraper] Found CAD link: {cad_link}")
                        clean_name = re.sub(r"[^a-z0-9]+", "_", component_name.lower()).strip("_")
                        ext = ".step" if cad_link.lower().endswith(".step") else ".stp"
                        cad_filename = f"{clean_name}{ext}"
                        dest_path = os.path.join(CAD_SCRAPED_DIR, cad_filename)
                        
                        if await _download_file(cad_link, dest_path):
                            print(f"[CAD Scraper] Successfully downloaded {cad_filename}")
                            cad_downloaded = True
                            source_url = url
                            extracted_text = result.markdown
                            break
                except Exception as e:
                    print(f"[CAD Scraper] Error checking {url}: {e}")
                    continue
                    
            if not cad_downloaded:
                from .selenium_downloader import selenium_download_cad
                for url in urls:
                    print(f"[CAD Scraper] Standard crawl missed CAD for {url}, attempting Playwright fallback...")
                    clean_name = re.sub(r"[^a-z0-9]+", "_", component_name.lower()).strip("_")
                    fallback_filename = f"{clean_name}.step"
                    
                    final_file = await selenium_download_cad(url, CAD_SCRAPED_DIR, fallback_filename)
                    if final_file:
                        print(f"[CAD Scraper] Selenium fallback succeeded: {final_file}")
                        cad_downloaded = True
                        cad_filename = final_file
                        source_url = url
                        result = await crawler.arun(url=url, config=config)
                        if result.success:
                            extracted_text = result.markdown
                        break

        # Best effort text fallback if absolutely no CAD is found
        if not cad_downloaded and urls_tried:
            print(f"[CAD Scraper] Could not find direct CAD link for {component_name} via any method. Will scrape text metadata only from first GrabCAD link.")
            first_url = list(urls_tried)[0]
            result = await crawler.arun(url=first_url, config=config)
            if result.success:
                extracted_text = result.markdown
            source_url = first_url

    # Fallback to Zoo.dev AI CAD Generation if still no CAD
    if not cad_downloaded:
        zoo_filename = await generate_cad_via_zoo(component_name, CAD_SCRAPED_DIR)
        if zoo_filename:
            cad_downloaded = True
            cad_filename = zoo_filename
            source_url = "https://zoo.dev"
            extracted_text = f"AI Generated mechanical component for {component_name} using Zoo Text-to-CAD API."
            print(f"[CAD Scraper] Successfully generated fallback CAD with Zoo: {zoo_filename}")

    if not extracted_text:
        print(f"[CAD Scraper] No textual metadata could be scraped or generated for {component_name}.")
        return cad_filename if cad_downloaded else None

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
