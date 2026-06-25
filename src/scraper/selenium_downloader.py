import os
import asyncio
import logging
import time
import re
import zipfile
import shutil
from typing import Optional

logger = logging.getLogger(__name__)

def sync_selenium_download(url: str, dest_dir: str, fallback_filename: str) -> Optional[str]:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    print(f"[Selenium Downloader] Attempting advanced fallback download for {url}")
    
    # Track existing files in dest_dir to detect new downloads
    existing_files = set(os.listdir(dest_dir)) if os.path.exists(dest_dir) else set()
    
    options = uc.ChromeOptions()
    prefs = {
        "download.default_directory": os.path.abspath(dest_dir),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
        "profile.default_content_settings.popups": 0
    }
    options.add_experimental_option("prefs", prefs)
    
    # Use headless=False for maximum Cloudflare bypass success, force version_main=149 to match local Chrome
    driver = uc.Chrome(options=options, headless=False, version_main=149)
    
    try:
        # GrabCAD Login Flow
        if "grabcad.com" in url:
            print("[Selenium Downloader] Detected GrabCAD URL. Attempting authentication...")
            email = os.environ.get("GRABCAD_EMAIL")
            password = os.environ.get("GRABCAD_PASSWORD")
            
            if email and password:
                try:
                    driver.get("https://grabcad.com/login")
                    # Wait for Cloudflare Turnstile if present, or email field
                    email_field = WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='member[email]']"))
                    )
                    email_field.send_keys(email)
                    driver.find_element(By.CSS_SELECTOR, "input[type='password'], input[name='member[password]']").send_keys(password)
                    driver.find_element(By.CSS_SELECTOR, "input[type='submit'], button[type='submit']").click()
                    print("[Selenium Downloader] Login form submitted. Waiting...")
                    time.sleep(5)
                except Exception as e:
                    print(f"[Selenium Downloader] GrabCAD login failed: {e}")
            else:
                print("[Selenium Downloader] GrabCAD credentials not found in .env, skipping login.")
                
        # Navigate to target URL
        try:
            driver.get(url)
            # Wait for cloudflare/load
            time.sleep(8) 
        except Exception as e:
            print(f"[Selenium Downloader] Warning during page navigation: {e}")
            
        # Collect candidate elements
        candidates = []
        
        # 1. Elements with explicit .step/.stp in text (prioritized)
        for el in driver.find_elements(By.XPATH, "//a[contains(translate(., 'STEP', 'step'), '.step') or contains(translate(., 'STP', 'stp'), '.stp')]"):
            try:
                if el.is_displayed() and el not in candidates:
                    candidates.append(el)
            except Exception:
                continue
                
        # 2. Elements with .step/.stp in href (prioritized)
        for el in driver.find_elements(By.XPATH, "//a[contains(translate(@href, 'STEP', 'step'), '.step') or contains(translate(@href, 'STP', 'stp'), '.stp')]"):
            try:
                if el.is_displayed() and el not in candidates:
                    candidates.append(el)
            except Exception:
                continue

        # 3. Main/general download buttons or links
        for xpath in [
            "//a[contains(translate(., 'DOWNLOAD', 'download'), 'download files')]",
            "//button[contains(translate(., 'DOWNLOAD', 'download'), 'download')]",
            "//a[contains(translate(., 'DOWNLOAD', 'download'), 'download')]",
            "//a[contains(@href, '/download')]"
        ]:
            for el in driver.find_elements(By.XPATH, xpath):
                try:
                    if el.is_displayed() and el not in candidates:
                        candidates.append(el)
                except Exception:
                    continue

        if not candidates:
            print("[Selenium Downloader] Could not find any potential download links/buttons on the page.")
            return None

        print(f"[Selenium Downloader] Found {len(candidates)} potential download candidates.")
        
        success_file = None
        for idx, el in enumerate(candidates):
            print(f"[Selenium Downloader] Trying download candidate {idx+1}/{len(candidates)}...")
            
            # Record existing files before clicking to detect the new download
            existing_files = set(os.listdir(dest_dir)) if os.path.exists(dest_dir) else set()
            
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
                time.sleep(1)
                el.click()
            except Exception as e:
                print(f"[Selenium Downloader] Failed to click candidate {idx+1}: {e}")
                continue

            # Phase 1: Wait for a new file to start downloading (either regular or temp file)
            download_started = False
            for _ in range(15):
                time.sleep(1)
                current_files = set(os.listdir(dest_dir)) if os.path.exists(dest_dir) else set()
                new_files = current_files - existing_files
                if new_files:
                    download_started = True
                    break
            
            if not download_started:
                print(f"[Selenium Downloader] Candidate {idx+1} did not trigger a download. Trying next.")
                continue

            # Phase 2: Wait for temporary files (.crdownload, .tmp, .part) to disappear (download completion)
            print(f"[Selenium Downloader] Download started. Waiting for completion...")
            downloaded_file = None
            for _ in range(60): # Allow up to 60 seconds for large files
                current_files = set(os.listdir(dest_dir)) if os.path.exists(dest_dir) else set()
                new_files = current_files - existing_files
                
                temp_files = [f for f in new_files if f.endswith('.crdownload') or f.endswith('.tmp') or f.endswith('.part')]
                if not temp_files:
                    if new_files:
                        downloaded_file = list(new_files)[0]
                    break
                time.sleep(1)

            if not downloaded_file:
                print(f"[Selenium Downloader] Candidate {idx+1} download timed out or failed.")
                continue

            full_path = os.path.join(dest_dir, downloaded_file)
            print(f"[Selenium Downloader] File completed: {downloaded_file}")

            # Phase 3: Process the downloaded file
            final_filename = None
            if downloaded_file.lower().endswith(".zip"):
                print(f"[Selenium Downloader] Extracting ZIP to look for .step/.stp...")
                extract_dir = os.path.join(dest_dir, "temp_extracted_selenium")
                os.makedirs(extract_dir, exist_ok=True)
                try:
                    with zipfile.ZipFile(full_path, 'r') as zip_ref:
                        zip_ref.extractall(extract_dir)
                        
                    step_files = []
                    for root, dirs, files in os.walk(extract_dir):
                        for file in files:
                            if file.lower().endswith(".step") or file.lower().endswith(".stp"):
                                step_files.append(os.path.join(root, file))
                                
                    if step_files:
                        best_file = max(step_files, key=os.path.getsize)
                        final_filename = os.path.basename(best_file)
                        final_filename = re.sub(r"[^a-zA-Z0-9_.-]", "_", final_filename)
                        shutil.copy(best_file, os.path.join(dest_dir, final_filename))
                        print(f"[Selenium Downloader] Extracted CAD: {final_filename}")
                        success_file = final_filename
                        break
                    else:
                        print("[Selenium Downloader] No .step/.stp files inside the downloaded ZIP.")
                except Exception as e:
                    print(f"[Selenium Downloader] ZIP extraction error: {e}")
                finally:
                    if os.path.exists(full_path):
                        os.remove(full_path)
                    shutil.rmtree(extract_dir, ignore_errors=True)
            elif downloaded_file.lower().endswith((".step", ".stp")):
                final_filename = re.sub(r"[^a-zA-Z0-9_.-]", "_", downloaded_file)
                shutil.move(full_path, os.path.join(dest_dir, final_filename))
                print(f"[Selenium Downloader] Successfully downloaded direct CAD: {final_filename}")
                success_file = final_filename
                break
            else:
                print(f"[Selenium Downloader] Downloaded file '{downloaded_file}' is not a .step, .stp, or .zip. Deleting it and trying next candidate.")
                if os.path.exists(full_path):
                    os.remove(full_path)

        if success_file:
            return success_file
        else:
            print("[Selenium Downloader] Failed to retrieve any valid .step/.stp file after trying all candidates.")
            return None
        
    except Exception as e:
        print(f"[Selenium Downloader] Fatal error: {e}")
        return None
    finally:
        try:
            driver.quit()
        except:
            pass

async def selenium_download_cad(url: str, dest_dir: str, fallback_filename: str) -> Optional[str]:
    """Async wrapper for the synchronous selenium downloader."""
    return await asyncio.to_thread(sync_selenium_download, url, dest_dir, fallback_filename)

async def discover_new_models(keywords: list, known_cads: dict) -> list[str]:
    """
    Background discovery job. Searches DuckDuckGo for GrabCAD links matching the keywords.
    Downloads the .step files if they aren't already known in `known_cads`.
    Returns a list of downloaded absolute file paths.
    """
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        logger.error("[Selenium Downloader] duckduckgo-search not installed. Cannot run background sync.")
        return []

    discovered_urls = set()
    downloaded_paths = []
    
    # GrabCAD base search query
    base_query = "site:grabcad.com/library step OR stp"
    
    with DDGS() as ddgs:
        for kw in keywords:
            query = f"{base_query} {kw}"
            logger.info(f"[Selenium Downloader] Discovering models for: {kw}")
            try:
                results = ddgs.text(query, max_results=3)
                for r in results:
                    url = r.get("href")
                    if url and "grabcad.com/library" in url:
                        # Quick check to see if the name already exists in known_cads
                        # Grabcad URLs end in -1 or similar, parse it out
                        slug = url.split("/")[-1].lower().replace("-1", "").replace("-", " ")
                        if slug not in known_cads:
                            discovered_urls.add(url)
            except Exception as e:
                logger.error(f"[Selenium Downloader] DDGS search failed for {kw}: {e}")
                
    if not discovered_urls:
        logger.info("[Selenium Downloader] No new URLs discovered today.")
        return []
        
    logger.info(f"[Selenium Downloader] Discovered {len(discovered_urls)} potential new GrabCAD models. Downloading...")
    
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    dest_dir = os.path.join(root_dir, "frontend", "public", "cad")
    os.makedirs(dest_dir, exist_ok=True)
    
    # We download sequentially to avoid hammering GrabCAD and getting blocked
    for url in discovered_urls:
        slug = url.split("/")[-1]
        fallback_filename = f"{slug}.step"
        logger.info(f"[Selenium Downloader] Initiating background download for {url}")
        
        filename = await selenium_download_cad(url, dest_dir, fallback_filename)
        if filename:
            downloaded_paths.append(os.path.join(dest_dir, filename))
            
        # Jitter to avoid bot detection
        await asyncio.sleep(5)
        
    return downloaded_paths

