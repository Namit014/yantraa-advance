import sys
import os
import re
import datetime

# Ensure the src/ directory is always on the path so sibling modules are importable
_src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from .search import search_web
from .scraper import scrape_url
from .chunker import chunk_text
from embedder import Embedder
from vectordb import VectorDB

# ── Project root (two levels up from src/scraper/) ─────────────────────
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Category mapping: keywords → existing KB folder names ────────────────────
# Keys are lowercase trigger words; values are exact folder names under KB_ROOT.
_CATEGORY_MAP = {
    # Articulated
    "articulated": "Articulated_Robot",
    "6-axis": "Articulated_Robot",
    "six axis": "Articulated_Robot",
    # AGV
    "agv": "Automated_Guided_Vehicle",
    "automated guided": "Automated_Guided_Vehicle",
    "guided vehicle": "Automated_Guided_Vehicle",
    # AMR
    "amr": "Autonomous_Mobile_Robot",
    "autonomous mobile": "Autonomous_Mobile_Robot",
    "mobile robot": "Autonomous_Mobile_Robot",
    # Cartesian / Gantry
    "cartesian": "Cartesian_Robot",
    "gantry": "Cartesian_Robot",
    "linear robot": "Cartesian_Robot",
    "coordinate robot": "Cartesian_Robot",
    # Machine Tending
    "machine tending": "Machine_Tending_Robot",
    "machine tend": "Machine_Tending_Robot",
    "tending robot": "Machine_Tending_Robot",
    "cnc": "Machine_Tending_Robot",
    # Painting
    "painting": "Painting_Robot",
    "spray": "Painting_Robot",
    "coating robot": "Painting_Robot",
    # Palletizing / Sorting
    "palletiz": "Palletizing_Robot",
    "depalletiz": "Palletizing_Robot",
    "sorting robot": "Palletizing_Robot",
    "sorting": "Palletizing_Robot",
    "pallet": "Palletizing_Robot",
    # Cobot
    "cobot": "cobot_robot",
    "collaborative": "cobot_robot",
    # Delta
    "delta": "delta_robot",
    "parallel robot": "delta_robot",
    # Inspection
    "inspection": "inspection_robot",
    "quality control": "inspection_robot",
    "vision robot": "inspection_robot",
    # SCARA
    "scara": "scara_robot",
    "selective compliance": "scara_robot",
    # Welding
    "welding": "welding_robot",
    "weld robot": "welding_robot",
    "arc weld": "welding_robot",
}


def _detect_category(query: str) -> str:
    """
    Map a free-text query to an existing KB folder name.
    Returns the matched folder name, or a sanitised slug of the query if no match.
    """
    q = query.lower()
    for keyword, folder in _CATEGORY_MAP.items():
        if keyword in q:
            return folder
    # No match → derive a new folder slug from the query
    slug = re.sub(r"[^a-z0-9]+", "_", q).strip("_")
    return slug or "general_web"


def _url_to_slug(url: str) -> str:
    """Convert a URL to a short filesystem-safe slug (max 60 chars)."""
    # Strip scheme
    slug = re.sub(r"^https?://", "", url)
    slug = re.sub(r"[^a-z0-9]+", "_", slug.lower()).strip("_")
    return slug[:60]


def _query_to_slug(query: str) -> str:
    """Convert a query string to a filesystem-safe slug.
    e.g. 'sorting robot' → 'sorting_robot'
    """
    slug = re.sub(r"[^a-z0-9]+", "_", query.lower()).strip("_")
    return slug[:80] or "general_web"


def _save_to_kb(topic_slug: str, url: str, text: str) -> str:
    """
    Persist `text` as a .txt file inside:
        web_scraped/<topic_slug>/

    This folder is SEPARATE from all curated KB subfolders.
    Returns the absolute path of the saved file.
    """
    web_dir = os.path.join(_PROJECT_ROOT, "web_scraped", topic_slug)
    os.makedirs(web_dir, exist_ok=True)

    date_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = _url_to_slug(url)
    filename = f"{slug}_{date_str}.txt"
    filepath = os.path.join(web_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"Source URL: {url}\n")
        f.write(f"Scraped: {datetime.datetime.now().isoformat()}\n")
        f.write("=" * 60 + "\n\n")
        f.write(text)

    return filepath


# Global embedder instance (reused across calls — uses OpenRouter API)
_embedder = None

# To prevent duplicate scraping within a session
scraped_urls = set()


def get_embedder():
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder


def web_ingest(query, qdrant_client=None, original_query=None):
    """
    Full web ingestion pipeline:
      DuckDuckGo search (15 results)
      → scrape
      → Yantra AI clean
      → save .txt to web_scraped/<category>/
      → chunk → embed → upsert into Qdrant with rich metadata
    """
    from llm import invoke_yantra_ai

    # Derive topic slug from the original human query for KB folder naming.
    # Never use the category map for the save path — curated folders stay untouched.
    category_query = original_query or query
    topic_slug = _query_to_slug(category_query)
    # _detect_category is still used for Qdrant metadata only
    category = _detect_category(category_query)
    print(f"[WebIngest] Topic folder: 'web_scraped/{topic_slug}/' | Qdrant category: '{category}'")

    print(f"[WebIngest] Searching the web for: '{query}'")
    urls = search_web(query)

    if not urls:
        print("[WebIngest] No URLs returned by search.")
        return

    print(f"[WebIngest] Found {len(urls)} URL(s):")
    for u in urls:
        print(f"  • {u}")

    embedder = get_embedder()

    # Construct VectorDB fresh each call with the caller's qdrant_client.
    vectordb = VectorDB(client=qdrant_client)

    total_stored = 0
    timestamp = datetime.datetime.now().isoformat()

    for url in urls:
        if url in scraped_urls:
            print(f"[WebIngest] Already scraped, skipping: {url}")
            continue

        scraped_urls.add(url)
        print(f"[WebIngest] Scraping: {url}")
        text = scrape_url(url)

        if not text:
            # scrape_url already logged the reason
            continue

        # ── Yantra AI: extract clean technical text from raw scraped content ──
        extraction_system_prompt = (
            "You are Yantra AI, a technical data extraction agent. "
            "Given raw scraped web text, extract and return ONLY the relevant technical "
            "specifications, facts, numbers, and descriptions. "
            "Remove all navigation menus, ads, and boilerplate. "
            "Write in clean prose. Do NOT invent information not in the source text."
        )
        clean_text = invoke_yantra_ai(
            text[:8000],
            system_prompt=extraction_system_prompt
        )

        if not clean_text or len(clean_text.strip()) < 80:
            print(f"[WebIngest] Yantra AI returned empty/short extraction for {url}, using raw text fallback.")
            clean_text = text  # fallback to raw scraped text

        # ── Step 1: Persist to knowledgebase on disk ──────────────────────────
        try:
            saved_path = _save_to_kb(topic_slug, url, clean_text)
            print(f"[WebIngest] Saved to KB: {saved_path}")
        except Exception as e:
            print(f"[WebIngest] Warning — could not save to KB disk: {e}")
            saved_path = None

        # ── Step 2: Chunk ──────────────────────────────────────────────────────
        raw_chunks = chunk_text(clean_text)
        print(f"[WebIngest] {len(raw_chunks)} chunk(s) from {url}")

        # Format chunks for Yantra's Embedder with rich metadata
        formatted_chunks = []
        for i, c in enumerate(raw_chunks):
            if len(c.strip()) < 30:
                continue
            formatted_chunks.append({
                "chunk_id": i,
                "text": c,
                "metadata": {
                    "source": "web_scraped",
                    "category": category,
                    "url": url,
                    "timestamp": timestamp,
                    "query": query,
                    "kb_file": saved_path or "",
                }
            })

        if not formatted_chunks:
            print(f"[WebIngest] All chunks were too short for {url}, skipping.")
            continue

        # ── Step 3: Embed and upsert into Qdrant ──────────────────────────────
        embedded_chunks = embedder.embed_chunks(formatted_chunks)
        vectordb.store_chunks(embedded_chunks)
        total_stored += len(embedded_chunks)

    print(f"[WebIngest] Done. Total chunks stored: {total_stored}")
