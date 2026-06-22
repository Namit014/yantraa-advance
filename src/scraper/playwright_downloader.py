import os
import asyncio
import logging
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)

async def playwright_download_cad(url: str, dest_dir: str, fallback_filename: str) -> str | None:
    """
    Attempts to download a CAD file (.step, .stp) using Playwright.
    This acts as a fallback when standard HTTP requests or Crawl4AI link extraction fails,
    for example when the download is hidden behind a button or a Javascript API blob.
    
    Args:
        url: The page URL containing the download button.
        dest_dir: Directory where the file should be saved.
        fallback_filename: The name to use if the downloaded file doesn't have an explicit name.
        
    Returns:
        The filename of the downloaded file, or None if failed.
    """
    print(f"[Playwright Downloader] Attempting advanced fallback download for {url}")
    
    # Common text that appears on CAD download buttons
    download_selectors = [
        "text=Download CAD",
        "text=Download STEP",
        "text=Download 3D Model",
        "text=Download .STEP",
        "button:has-text('Download')",
        "a:has-text('.step')",
        "a:has-text('.stp')",
        "[title*='Download']",
        "[aria-label*='Download']"
    ]
    
    try:
        async with async_playwright() as p:
            # Use chromium, headed mode to bypass Cloudflare bot protection
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                accept_downloads=True,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            # Navigate and wait for network to idle to ensure dynamic scripts have loaded
            try:
                # GrabCAD Login Flow
                if "grabcad.com" in url:
                    print("[Playwright Downloader] Detected GrabCAD URL. Attempting authentication...")
                    email = os.environ.get("GRABCAD_EMAIL")
                    password = os.environ.get("GRABCAD_PASSWORD")
                    
                    if email and password:
                        try:
                            await page.goto("https://grabcad.com/login", wait_until="domcontentloaded", timeout=20000)
                            # GrabCAD specific selectors
                            await page.fill("input[type='email'], input[name='member[email]']", email)
                            await page.fill("input[type='password'], input[name='member[password]']", password)
                            await page.click("input[type='submit'], button[type='submit']")
                            # Wait for login to complete by waiting for navigation or a logged-in element
                            await page.wait_for_load_state("domcontentloaded", timeout=15000)
                            print("[Playwright Downloader] GrabCAD authentication successful.")
                        except Exception as e:
                            print(f"[Playwright Downloader] GrabCAD login failed: {e}")
                    else:
                        print("[Playwright Downloader] GrabCAD credentials not found in .env, skipping login.")
                
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                except Exception as e:
                    print(f"[Playwright Downloader] Warning during page navigation: {e}. Proceeding anyway to check for buttons.")
            except Exception as e:
                print(f"[Playwright Downloader] Error during navigation block: {e}")
            
            # Give it a couple seconds for lazy-loaded UI to appear
            await asyncio.sleep(2)
            
            download_triggered = False
            download_obj = None
            
            # Iterate through potential download buttons and attempt to click them
            for selector in download_selectors:
                elements = await page.locator(selector).all()
                for el in elements:
                    if await el.is_visible():
                        print(f"[Playwright Downloader] Found potential download button: '{selector}'. Clicking...")
                        try:
                            # Start waiting for the download BEFORE clicking
                            async with page.expect_download(timeout=10000) as download_info:
                                await el.click()
                            
                            download_obj = await download_info.value
                            download_triggered = True
                            break
                        except Exception as e:
                            print(f"[Playwright Downloader] Clicked but no download triggered: {e}")
                            continue
                
                if download_triggered:
                    break
            
            if download_triggered and download_obj:
                suggested_name = download_obj.suggested_filename
                import re
                import zipfile
                import shutil
                
                temp_path = os.path.join(dest_dir, "temp_download_" + suggested_name)
                print(f"[Playwright Downloader] Saving downloaded file to {temp_path}")
                await download_obj.save_as(temp_path)
                
                final_filename = None
                
                if suggested_name.lower().endswith(".zip"):
                    print(f"[Playwright Downloader] Downloaded a ZIP file '{suggested_name}'. Extracting to find detailed CAD...")
                    extract_dir = os.path.join(dest_dir, "temp_extracted")
                    os.makedirs(extract_dir, exist_ok=True)
                    try:
                        with zipfile.ZipFile(temp_path, 'r') as zip_ref:
                            zip_ref.extractall(extract_dir)
                            
                        # Find all step/stp files
                        step_files = []
                        for root, dirs, files in os.walk(extract_dir):
                            for file in files:
                                if file.lower().endswith(".step") or file.lower().endswith(".stp"):
                                    step_files.append(os.path.join(root, file))
                                    
                        if step_files:
                            # Select the largest one (assuming most detailed)
                            best_file = max(step_files, key=os.path.getsize)
                            final_filename = os.path.basename(best_file)
                            final_filename = re.sub(r"[^a-zA-Z0-9_.-]", "_", final_filename)
                            
                            shutil.copy(best_file, os.path.join(dest_dir, final_filename))
                            print(f"[Playwright Downloader] Successfully extracted detailed CAD: {final_filename}")
                        else:
                            print(f"[Playwright Downloader] No .step or .stp files found inside the ZIP.")
                    except Exception as e:
                        print(f"[Playwright Downloader] Failed to process ZIP file: {e}")
                    finally:
                        # Cleanup
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                        shutil.rmtree(extract_dir, ignore_errors=True)
                else:
                    # Not a zip, check if it's a step
                    if suggested_name.lower().endswith(".step") or suggested_name.lower().endswith(".stp"):
                        final_filename = re.sub(r"[^a-zA-Z0-9_.-]", "_", suggested_name)
                        shutil.move(temp_path, os.path.join(dest_dir, final_filename))
                        print(f"[Playwright Downloader] Saved CAD as {final_filename}")
                    else:
                        print(f"[Playwright Downloader] Warning: downloaded file '{suggested_name}' doesn't look like a .step or .zip. Renaming to fallback.")
                        final_filename = fallback_filename
                        shutil.move(temp_path, os.path.join(dest_dir, final_filename))
                        
                await browser.close()
                return final_filename
            
            print("[Playwright Downloader] Could not find any working download buttons.")
            await browser.close()
            return None
            
    except Exception as e:
        print(f"[Playwright Downloader] Fatal error during download attempt: {e}")
        return None
