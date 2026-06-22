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
            # Use chromium, headless mode
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                accept_downloads=True,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            # Navigate and wait for network to idle to ensure dynamic scripts have loaded
            try:
                await page.goto(url, wait_until="networkidle", timeout=20000)
            except PlaywrightTimeoutError:
                print(f"[Playwright Downloader] Warning: network did not fully idle, proceeding anyway.")
            
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
                # Use suggested filename from the browser, or fallback to our clean name
                suggested_name = download_obj.suggested_filename
                
                # Check if it's actually a step file if we can infer from filename
                final_filename = suggested_name
                if not (suggested_name.lower().endswith(".step") or suggested_name.lower().endswith(".stp")):
                    print(f"[Playwright Downloader] Warning: downloaded file '{suggested_name}' doesn't look like a .step file. Saving as {fallback_filename}")
                    final_filename = fallback_filename
                else:
                    # Replace characters that might be invalid in paths
                    import re
                    final_filename = re.sub(r"[^a-zA-Z0-9_.-]", "_", suggested_name)
                
                final_path = os.path.join(dest_dir, final_filename)
                
                print(f"[Playwright Downloader] Saving downloaded file to {final_path}")
                await download_obj.save_as(final_path)
                
                await browser.close()
                return final_filename
            
            print("[Playwright Downloader] Could not find any working download buttons.")
            await browser.close()
            return None
            
    except Exception as e:
        print(f"[Playwright Downloader] Fatal error during download attempt: {e}")
        return None
