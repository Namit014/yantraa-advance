import sys
import os
import re
import datetime

# Ensure the src/ directory is always on the path so sibling modules are importable
_src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from .search import search_web
from .scraper import fetch_clean_text
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


def get_embedder():
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder


# ── URL Cache Persistence (Fix 5) ────────────────────────────────────
import json
from pathlib import Path

CACHE_FILE = Path(__file__).parent / ".scraped_url_cache.json"


def _load_url_cache() -> set:
    if CACHE_FILE.exists():
        try:
            return set(json.loads(CACHE_FILE.read_text(encoding="utf-8")))
        except Exception:
            return set()
    return set()


def _save_url_cache(cache: set):
    try:
        CACHE_FILE.write_text(json.dumps(list(cache)), encoding="utf-8")
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Could not save URL cache: {e}")


# Initialize at module load
_url_cache = _load_url_cache()


# ── Garbage Text Heuristic (Fix 2) ──────────────────────────────────
def is_garbage_text(text: str) -> bool:
    """Heuristic: if text is too short or has very low word density, discard it."""
    if not text:
        return True
    words = text.split()
    if len(words) < 50:
        return True
    # Check for encoding garbage (high ratio of non-ASCII in a short window)
    sample = text[:500]
    non_ascii = sum(1 for c in sample if ord(c) > 127)
    if non_ascii / max(len(sample), 1) > 0.3:
        return True
    return False


# ── Domain Prioritization (Fix 4) ───────────────────────────────────
PRIORITY_DOMAINS = [
    "arduino.cc", "sparkfun.com", "adafruit.com", "robotshop.com",
    "ros.org", "wiki.ros.org", "docs.ros.org",
    "pololu.com", "dfrobot.com", "seeedstudio.com",
    "electronics.stackexchange.com", "robotics.stackexchange.com",
    "microchip.com", "st.com", "ti.com", "nxp.com",
    "instructables.com", "hackaday.io", "hackster.io",
    "github.com", "arxiv.org",
]

LOW_QUALITY_DOMAINS = [
    "medium.com", "quora.com", "yahoo.com", "pinterest.com",
    "facebook.com", "twitter.com", "x.com", "tiktok.com",
    "amazon.com", "ebay.com", "alibaba.com",
]


def rank_urls(urls: list[str]) -> list[str]:
    from urllib.parse import urlparse
    import logging
    logger = logging.getLogger(__name__)
    priority, neutral, skip = [], [], []
    for url in urls:
        domain = urlparse(url).netloc.replace("www.", "")
        if any(d in domain for d in LOW_QUALITY_DOMAINS):
            skip.append(url)
        elif any(d in domain for d in PRIORITY_DOMAINS):
            priority.append(url)
        else:
            neutral.append(url)
    logger.debug(f"Skipped low-quality domains: {skip}")
    return priority + neutral


# ── Langchain Chunker (Fix 6) ───────────────────────────────────────
def chunk_scraped_text(text: str, source_url: str) -> list[dict]:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=512,
        chunk_overlap=100,
        separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " "],
    )
    chunks = splitter.split_text(text)
    return [
        {
            "text": chunk,
            "metadata": {
                "source": "web_scraped",  # web_scraped is key to match Qdrant filter
                "url": source_url,
                "categories": ["Web"],
            }
        }
        for chunk in chunks
        if len(chunk.strip()) > 50
    ]


async def web_ingest(query, qdrant_client=None, original_query=None):
    """
    Full web ingestion pipeline (Asynchronous):
      DuckDuckGo search (15 results)
      → rank and limit to top 5 URLs
      → fetch via Jina Reader (with BeautifulSoup fallback)
      → skip garbage and cached URLs
      → save .txt to web_scraped/<category>/
      → chunk → embed → upsert into Qdrant with rich metadata
    """
    # Derive topic slug from the original human query for KB folder naming.
    category_query = original_query or query
    topic_slug = _query_to_slug(category_query)
    category = _detect_category(category_query)
    print(f"[WebIngest] Topic folder: 'web_scraped/{topic_slug}/' | Qdrant category: '{category}'")

    print(f"[WebIngest] Searching the web for: '{query}'")
    urls = search_web(query)

    if not urls:
        print("[WebIngest] No URLs returned by search.")
        return

    print(f"[WebIngest] Found {len(urls)} URL(s)")
    ranked_urls = rank_urls(urls)[:5]
    print(f"[WebIngest] Ranked top URLs: {ranked_urls}")

    embedder = get_embedder()
    vectordb = VectorDB(client=qdrant_client)

    # Retrieve all existing content hashes to skip duplicate chunks
    from vectordb import get_all_content_hashes, compute_content_hash
    existing_hashes = get_all_content_hashes(vectordb.client, collection_name=vectordb.collection_name)

    total_stored = 0
    timestamp = datetime.datetime.now().isoformat()

    for url in ranked_urls:
        if url in _url_cache:
            print(f"[WebIngest] Already scraped (in cache), skipping: {url}")
            continue

        print(f"[WebIngest] Scraping: {url}")
        clean_text = await fetch_clean_text(url)

        if not clean_text:
            continue

        if is_garbage_text(clean_text):
            print(f"[WebIngest] Text from {url} is garbage, skipping.")
            continue

        # Add to cache and persist
        _url_cache.add(url)
        _save_url_cache(_url_cache)

        # ── Step 2: Persist to knowledgebase on disk ──────────────────────────
        try:
            saved_path = _save_to_kb(topic_slug, url, clean_text)
            print(f"[WebIngest] Saved to KB: {saved_path}")
        except Exception as e:
            print(f"[WebIngest] Warning — could not save to KB disk: {e}")
            saved_path = None

        # ── Step 3: Chunk ──────────────────────────────────────────────────────
        chunks_data = chunk_scraped_text(clean_text, url)
        print(f"[WebIngest] {len(chunks_data)} chunk(s) from {url}")

        # Format chunks for Yantra's Embedder with rich metadata
        formatted_chunks = []
        for i, chunk_item in enumerate(chunks_data):
            c_text = chunk_item["text"]
            c_hash = compute_content_hash(c_text)
            if c_hash in existing_hashes:
                continue

            formatted_chunks.append({
                "chunk_id": i,
                "text": c_text,
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
            print(f"[WebIngest] All chunks were duplicates or too short for {url}, skipping.")
            continue

        # ── Step 4: Embed and upsert into Qdrant ──────────────────────────────
        embedded_chunks = embedder.embed_chunks(formatted_chunks)
        vectordb.store_chunks(embedded_chunks)
        total_stored += len(embedded_chunks)

    print(f"[WebIngest] Done. Total chunks stored: {total_stored}")
