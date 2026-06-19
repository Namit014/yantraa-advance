import os
import sys
import json
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import datetime

# Ensure the src/ directory is always on the path
_src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from scraper.search import search_web
from scraper.scraper import scrape_url
from llm import invoke_yantra_ai

_PROJECT_ROOT = os.path.dirname(_src_dir)
KB_DIR = os.path.join(_PROJECT_ROOT, "knowledgebase")
CAD_SCRAPED_DIR = os.path.join(KB_DIR, "CAD_Models", "Scraped")
SCRAPED_JSON_PATH = os.path.join(KB_DIR, "Robots_MetaData", "scraped_components.json")

# Ensure directories exist
os.makedirs(CAD_SCRAPED_DIR, exist_ok=True)
os.makedirs(os.path.dirname(SCRAPED_JSON_PATH), exist_ok=True)


def _download_file(url: str, dest_path: str) -> bool:
    try:
        response = requests.get(url, stream=True, timeout=15, headers={"User-Agent": "Mozilla/5.0 (compatible; YantraBot/1.0)"})
        response.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"[CAD Scraper] Failed to download {url}: {e}")
        return False


def scrape_missing_component(component_name: str):
    print(f"[CAD Scraper] Background task started for missing component: {component_name}")
    
    # Check if already scraped
    if os.path.exists(SCRAPED_JSON_PATH):
        try:
            with open(SCRAPED_JSON_PATH, "r", encoding="utf-8") as f:
                scraped_data = json.load(f)
                for comp in scraped_data.get("components", []):
                    if comp.get("name", "").lower() == component_name.lower():
                        print(f"[CAD Scraper] Component '{component_name}' already exists in scraped_components.json. Skipping.")
                        return
        except Exception:
            pass

    query = f"{component_name} 3D CAD step stp file download"
    urls = search_web(query, max_results=5)
    
    cad_downloaded = False
    cad_filename = None
    extracted_text = ""
    source_url = ""

    for url in urls:
        print(f"[CAD Scraper] Checking {url} for CAD files...")
        try:
            resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0 (compatible; YantraBot/1.0)"})
            resp.raise_for_status()
            html = resp.text
            soup = BeautifulSoup(html, "html.parser")
            
            # Find any link ending with .step or .stp
            cad_link = None
            for a in soup.find_all("a", href=True):
                href = a["href"].lower()
                if href.endswith(".step") or href.endswith(".stp"):
                    cad_link = urljoin(url, a["href"])
                    break
                    
            if cad_link:
                print(f"[CAD Scraper] Found CAD link: {cad_link}")
                clean_name = re.sub(r"[^a-z0-9]+", "_", component_name.lower()).strip("_")
                ext = ".step" if cad_link.lower().endswith(".step") else ".stp"
                cad_filename = f"{clean_name}{ext}"
                dest_path = os.path.join(CAD_SCRAPED_DIR, cad_filename)
                
                if _download_file(cad_link, dest_path):
                    print(f"[CAD Scraper] Successfully downloaded {cad_filename}")
                    cad_downloaded = True
                    source_url = url
                    # Extract text from the page for LLM metadata extraction
                    extracted_text = soup.get_text(separator=" ", strip=True)
                    break
        except Exception as e:
            print(f"[CAD Scraper] Error checking {url}: {e}")
            continue

    if not cad_downloaded and urls:
        # Best effort: Scrape the first URL for text metadata anyway
        print(f"[CAD Scraper] Could not find direct CAD link for {component_name}. Will scrape text metadata only.")
        extracted_text = scrape_url(urls[0]) or ""
        source_url = urls[0]

    if not extracted_text:
        print(f"[CAD Scraper] No textual metadata could be scraped for {component_name}.")
        return

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
        
    except Exception as e:
        print(f"[CAD Scraper] Failed to extract or save metadata: {e}")
