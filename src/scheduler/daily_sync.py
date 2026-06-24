import os
import sys
import logging
import asyncio

_src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from scraper.selenium_downloader import discover_new_models
from storage.s3_client import upload_to_s3
from cad_registry import get_known_cads, _save_cad_registry
from api.step_analyzer import analyze_step_file
import json

# Configure persistent logging for the daily sync
log_file_path = os.path.abspath(os.path.join(_src_dir, "..", "sync.log"))
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Broad search scope to capture all types of robots as requested
SEARCH_KEYWORDS = [
    "robotic arm", "quadruped", "hexapod", "drone frame", "rover chassis", 
    "humanoid", "AGV", "scara robot", "delta robot", "bipedal robot",
    "mobile base", "robot gripper", "robotic hand", "welding robot", "AMR"
]

async def run_daily_cad_sync():
    """
    The background synchronization job.
    1. Discovers new models on GrabCAD.
    2. Downloads them.
    3. Uploads to S3 (mocked).
    4. Updates CAD registry and extracts metadata.
    """
    logger.info("[Background Sync] Starting daily CAD synchronization pipeline...")
    
    # We will loop through the keywords and discover new models
    # Note: In a production environment with an active GrabCAD scraper, this would 
    # iterate and download. For this demo, we'll invoke the discover function.
    
    known_cads = get_known_cads()
    newly_added = 0
    
    try:
        # Step 1 & 2: Discover and download
        # Note: selenium_downloader currently has a scrape_missing_component function.
        # We will wrap it or call discover_new_models which we will implement.
        downloaded_files = await discover_new_models(SEARCH_KEYWORDS, known_cads)
        
        if not downloaded_files:
            logger.info("[Background Sync] No new models downloaded today.")
            return
            
        for file_path in downloaded_files:
            filename = os.path.basename(file_path)
            
            # Step 3: Upload to S3
            upload_success = upload_to_s3(file_path, filename)
            
            if upload_success:
                # Step 4: Extract Metadata & Update Registry
                try:
                    meta_res = analyze_step_file(file_path)
                    
                    # Determine a logical name from filename or metadata
                    clean_name = filename.lower().replace(".step", "").replace(".stp", "").replace("_", " ")
                    
                    known_cads[clean_name] = filename
                    
                    # Extract subcomponents for broader matching
                    for comp in meta_res.get("components", []):
                        if isinstance(comp, str) and len(comp) > 3:
                            known_cads[comp.lower()] = filename
                            
                    _save_cad_registry(known_cads)
                    newly_added += 1
                    logger.info(f"[Background Sync] Successfully synced and registered: {filename}")
                except Exception as e:
                    logger.error(f"[Background Sync] Failed to process metadata for {filename}: {e}")
                    
    except Exception as e:
        logger.error(f"[Background Sync] Critical error in sync pipeline: {e}")
        
    logger.info(f"[Background Sync] Pipeline complete. {newly_added} new models added to registry.")

def trigger_sync_sync():
    """Synchronous wrapper for the scheduler"""
    asyncio.run(run_daily_cad_sync())

