# Yantraa — Web Scraper Fix Prompt (Main Branch)

> **Context:** This targets the existing `yantraa-advance` main branch. The scraper is used as a **RAG fallback only** — it fires when Qdrant finds nothing relevant. DuckDuckGo for URL discovery is working fine and should be kept. The problem is what happens after: pages are fetched but the extracted text is garbage. Fix only the extraction and pipeline layers. Do not touch URL discovery or restructure the module.

---

## Why DuckDuckGo Is Fine (and Kimi/Vercel Aren't Worth It)

Before the fixes — quick answer on the tools you asked about:

**Kimi K1.5 WebBridge** — It's a browsing-augmented LLM, not a scraping API. It's designed to answer questions by browsing, not to return clean text for your own RAG pipeline. You'd be paying to call an LLM just to clean another LLM's context. Overkill and closed.

**Vercel AI SDK Browsing Agent** — Same category. It's an agent pattern for building browsing workflows inside Vercel's stack, not a standalone extraction tool. Doesn't plug cleanly into a FastAPI backend.

**What you actually need** is just a clean URL-to-text extractor that handles JS-heavy pages and nav/footer noise without you writing the parsing logic. That's **Jina Reader** (`r.jina.ai`). It's free, requires no API key for basic use, returns clean markdown directly, handles JS rendering, respects robots.txt, and is explicitly built for RAG pipelines. It replaces only the broken extraction step — DDG still finds the URLs.

---

## SCRAPER FIX 1 — Replace httpx Direct Fetch with Jina Reader

**File:** `src/scraper/scraper.py`

**Problem:** `httpx.get(url)` (or `requests.get(url)`) fetches raw HTML which is then parsed by BeautifulSoup. For most robotics pages (component datasheets, forum threads, JS-rendered sites like RobotShop or Arduino docs), the raw HTML is full of nav bars, cookie banners, sidebars, and script tags. BeautifulSoup strips some of it but still leaves junk that degrades chunk quality.

**Fix:** Replace the direct fetch with a Jina Reader fetch. Jina preprocesses the page server-side and returns clean markdown.

```python
import httpx
import asyncio

JINA_BASE = "https://r.jina.ai/"

async def fetch_clean_text(url: str, timeout: int = 20) -> str:
    """
    Fetch a URL via Jina Reader which returns clean, LLM-ready markdown.
    Falls back to direct BeautifulSoup extraction if Jina fails.
    """
    jina_url = f"{JINA_BASE}{url}"
    headers = {
        "Accept": "text/plain",
        "X-Timeout": str(timeout),
        "X-Return-Format": "text",   # plain text, not markdown with image tags
    }
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(jina_url, headers=headers)
            response.raise_for_status()
            text = response.text.strip()
            if len(text) > 200:
                return text
            # Jina returned too little — fall through to direct fetch
    except Exception as e:
        logger.warning(f"Jina fetch failed for {url}: {e}. Falling back to direct fetch.")

    return await _direct_fetch_fallback(url, timeout)


async def _direct_fetch_fallback(url: str, timeout: int) -> str:
    """BeautifulSoup fallback when Jina is unavailable."""
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
            html = response.text
    except Exception as e:
        logger.error(f"Direct fetch also failed for {url}: {e}")
        return ""

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    for tag in ("nav", "footer", "header", "script", "style", "aside", "form", "noscript"):
        for el in soup.find_all(tag):
            el.decompose()
    article = soup.find("article") or soup.find("main") or soup.body or soup
    text = article.get_text(separator="\n", strip=True)
    lines = [line.strip() for line in text.splitlines() if len(line.strip()) > 30]
    return "\n".join(lines)
```

- Replace every call to `requests.get(url)` or `httpx.get(url)` in the scraper with `await fetch_clean_text(url)`.
- Remove any existing BeautifulSoup HTML-cleaning logic that was doing `soup.get_text()` directly on the raw response — that logic now only lives inside `_direct_fetch_fallback`.
- Remove `import requests` entirely from the scraper if present.

---

## SCRAPER FIX 2 — Remove the LLM Cleaning Call Per Page

**File:** `src/scraper/pipeline.py`

**Problem:** Every scraped page is sent to the LLM to "clean" the extracted text. At 5-15 pages per fallback call, this adds 30-150 seconds of latency and burns tokens for a task BeautifulSoup (and now Jina) already handles.

**Fix:**
- Remove the LLM cleaning call entirely from the per-page scraping step.
- Keep the LLM only for the **final synthesis step** — summarizing/condensing the scraped context before injecting it into the RAG response. That's where LLM reasoning adds real value.
- If you want a sanity check, add this guard instead of an LLM call:

```python
def is_garbage_text(text: str) -> bool:
    """Heuristic: if text is too short or has very low word density, discard it."""
    words = text.split()
    if len(words) < 50:
        return True
    # Check for encoding garbage (high ratio of non-ASCII in a short window)
    sample = text[:500]
    non_ascii = sum(1 for c in sample if ord(c) > 127)
    if non_ascii / max(len(sample), 1) > 0.3:
        return True
    return False
```

- Call `is_garbage_text(extracted_text)` after `fetch_clean_text()`. If it returns `True`, skip this URL and move to the next result — do not add it to the context.

---

## SCRAPER FIX 3 — Fix Synchronous Blocking on the Event Loop

**File:** `src/scraper/scraper.py` and wherever the fallback is invoked from `src/retriever.py`

**Problem:** The scraper may be running synchronous `requests.get()` or blocking `httpx` calls inside an `async def` FastAPI endpoint, blocking the entire event loop for the duration of the scrape.

**Fix:**
- All scraper fetch functions must be `async def` using `httpx.AsyncClient` (as shown in Fix 1 above).
- In `src/retriever.py`, the web fallback call must be awaited properly. If `retriever.ask()` is still a synchronous function, wrap the scraper call using `asyncio.run_in_executor`:

```python
import asyncio

# Inside retriever.ask() — the scraper call:
loop = asyncio.get_event_loop()
scraped_context = loop.run_until_complete(fetch_clean_text(url))
```

Or, if you're refactoring `ask()` to be async (recommended), just `await fetch_clean_text(url)` directly.

- Do not call any synchronous HTTP library (`requests`, `urllib`) anywhere in the scraper code path.

---

## SCRAPER FIX 4 — Add Robotics-Focused Domain Prioritization

**File:** `src/scraper/pipeline.py` (wherever DDG results are ranked/filtered before fetching)

**Problem:** DuckDuckGo returns a mix of random blogs, forums, and spec pages. You've never checked which, so some of that garbage text is from low-signal domains (Medium think pieces, random tutorials with no specs).

**Fix:** After getting DDG search results and before fetching pages, sort URLs by domain quality:

```python
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
    priority, neutral, skip = [], [], []
    for url in urls:
        domain = urlparse(url).netloc.replace("www.", "")
        if any(d in domain for d in LOW_QUALITY_DOMAINS):
            skip.append(url)
        elif any(d in domain for d in PRIORITY_DOMAINS):
            priority.append(url)
        else:
            neutral.append(url)
    return priority + neutral  # skip low quality entirely
```

- Call `rank_urls(ddg_results)` before the fetch loop.
- Only fetch the top 5 URLs after ranking — do not fetch all DDG results.
- Log which domains were skipped: `logger.debug(f"Skipped low-quality domains: {skip}")`.

---

## SCRAPER FIX 5 — Fix URL Deduplication Persisting Across Restarts

**File:** `src/scraper/pipeline.py` or `src/scraper/scraper.py`

**Problem:** `scraped_urls = set()` at module level resets every server restart, so the same pages get re-scraped on every cold start. In a RAG fallback context this means re-fetching the same URLs for common queries repeatedly.

**Fix:** Persist a simple URL cache to disk:

```python
import json
from pathlib import Path

CACHE_FILE = Path(__file__).parent / ".scraped_url_cache.json"

def _load_url_cache() -> set:
    if CACHE_FILE.exists():
        try:
            return set(json.loads(CACHE_FILE.read_text()))
        except Exception:
            return set()
    return set()

def _save_url_cache(cache: set):
    try:
        CACHE_FILE.write_text(json.dumps(list(cache)))
    except Exception as e:
        logger.warning(f"Could not save URL cache: {e}")

# Initialize at module load
_url_cache = _load_url_cache()
```

- Before fetching any URL in the pipeline: `if url in _url_cache: continue`.
- After successfully fetching and processing a URL: `_url_cache.add(url); _save_url_cache(_url_cache)`.
- Add `.scraped_url_cache.json` to `.gitignore`.
- This cache is for deduplication only — it does not cache the extracted text. Jina's own caching handles repeated fetches of the same page efficiently.

---

## SCRAPER FIX 6 — Fix Chunking After Scrape

**File:** `src/scraper/pipeline.py` — the step that chunks the scraped text before embedding

**Problem:** Scraped text chunking uses raw character slicing (same issue as the ingestion chunker). Now that Jina returns clean markdown, the text has natural structure (headings, paragraphs) that `RecursiveCharacterTextSplitter` can use properly.

**Fix:** Use the same unified chunker from the ingestion pipeline:

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

def chunk_scraped_text(text: str, source_url: str) -> list[dict]:
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
                "source": "web_scrape",
                "url": source_url,
                "categories": ["Web"],
            }
        }
        for chunk in chunks
        if len(chunk.strip()) > 50
    ]
```

- Replace any existing character-slice chunking in the scraper pipeline with this function.
- The `source_url` should be stored in chunk metadata so you can trace which web page contributed which context.

---

## SCRAPER FIX 7 — Fix the Fallback Flow in retriever.py

**File:** `src/retriever.py`

**Problem:** The web fallback likely either (a) silently returns nothing when scraping fails, or (b) returns garbage text that the LLM then hallucinates over. There's no clear signal to the caller that the response is web-sourced vs Qdrant-sourced.

**Fix:** Restructure the fallback clearly:

```python
async def _web_fallback(self, query: str) -> dict:
    """
    Fires only when Qdrant score is below SCORE_HARD_FLOOR.
    Returns structured context with source attribution.
    """
    logger.info(f"[RAG FALLBACK] Qdrant score too low. Triggering web fallback for: {query}")

    # DDG search — keep as-is
    urls = self._ddg_search(query + " robotics components specifications")

    if not urls:
        logger.warning("[RAG FALLBACK] DDG returned no URLs.")
        return {"context": "", "source": "none", "fallback_used": True}

    # Rank and limit
    ranked_urls = rank_urls(urls)[:5]

    # Fetch via Jina with fallback
    texts = []
    for url in ranked_urls:
        text = await fetch_clean_text(url)
        if not is_garbage_text(text):
            texts.append({"url": url, "text": text})
        if len(texts) >= 3:  # stop after 3 good pages
            break

    if not texts:
        logger.warning("[RAG FALLBACK] All fetched pages were garbage. Returning empty context.")
        return {"context": "", "source": "none", "fallback_used": True}

    # Chunk and combine
    combined_chunks = []
    for item in texts:
        chunks = chunk_scraped_text(item["text"], item["url"])
        combined_chunks.extend(chunks)

    # Take top chunks by length as a rough relevance proxy
    top_chunks = sorted(combined_chunks, key=lambda c: len(c["text"]), reverse=True)[:6]
    context = "\n\n---\n\n".join(c["text"] for c in top_chunks)

    logger.info(f"[RAG FALLBACK] Returning {len(top_chunks)} chunks from {len(texts)} pages.")
    return {
        "context": context,
        "source": "web",
        "fallback_used": True,
        "source_urls": [item["url"] for item in texts],
    }
```

- Replace the existing `_web_fallback` (or equivalent) logic in `retriever.py` with this.
- In the LLM prompt that uses this context, append: `"[Note: This context was retrieved from the web, not the internal knowledgebase.]"` when `source == "web"` — so the LLM knows to be more conservative.
- In the API response to the frontend, include `"fallback_used": true` and `"source_urls": [...]` so the UI can optionally show the user where the info came from.

---

## SCRAPER FIX 8 — Add Robotics Query Optimization Before DDG Search

**File:** `src/retriever.py` — the part that builds the DDG query string

**Problem:** If the user query is `"build me an arm robot"`, the DDG search is probably `"build me an arm robot"` verbatim — which returns tutorials and YouTube videos, not component specs.

**Fix:** Before passing to DDG, rewrite the query to be spec-focused:

```python
def optimize_for_web_search(query: str) -> str:
    """
    Transform a natural language design query into a spec-focused search query
    for robotics component retrieval.
    """
    # Strip common instruction verbs
    import re
    query = re.sub(
        r'^(build|create|make|design|generate|give me|show me|i want)\s+(me\s+)?(a|an|the)?\s*',
        '',
        query.strip(),
        flags=re.IGNORECASE
    ).strip()

    # Append spec-focused terms
    spec_suffix = "specifications components datasheet pinout"
    return f"{query} {spec_suffix}"
```

- Call `optimized = optimize_for_web_search(query)` before `self._ddg_search(optimized)`.
- Keep the original `query` (unmodified) for the LLM prompt context — only the DDG call uses the optimized version.

---

## Dependencies to Add

Add to `requirements.txt` if not already present:

```
httpx>=0.27.0
beautifulsoup4>=4.12.0
```

Remove `requests` from `requirements.txt` if the only usage was in the scraper (the rest of the codebase should use `httpx`). Check for any other `import requests` before removing.

Jina Reader requires **no additional dependency and no API key** — it's just an HTTPS GET to `https://r.jina.ai/{url}`.

---

## Execution Order

```
1. Add fetch_clean_text() + _direct_fetch_fallback() to scraper.py (Fix 1)
2. Remove LLM cleaning call, add is_garbage_text() guard (Fix 2)
3. Make all scraper calls async (Fix 3)
4. Add rank_urls() and apply before fetch loop (Fix 4)
5. Add URL cache persistence (Fix 5)
6. Replace chunking with RecursiveCharacterTextSplitter (Fix 6)
7. Rewrite _web_fallback() in retriever.py (Fix 7)
8. Add optimize_for_web_search() before DDG call (Fix 8)
9. Update requirements.txt (remove requests, add httpx + bs4)
```

---

## On Kimi WebBridge vs Jina — Final Verdict

| Tool | Free | No Key | RAG-Ready Output | Fits Your Stack |
|---|---|---|---|---|
| **Jina Reader** | ✅ 1M free tokens | ✅ No key needed | ✅ Clean markdown | ✅ Just an HTTPS GET |
| Kimi K1.5 WebBridge | ❌ Paid | ❌ Needs key | ⚠️ LLM response, not raw text | ❌ Overkill |
| Vercel Browsing Agent | ❌ Tied to Vercel | ❌ Needs setup | ⚠️ Agent pattern, not extraction | ❌ Wrong stack |
| Direct httpx + BS4 | ✅ Free | ✅ No key | ⚠️ Garbage on JS sites | ⚠️ Already failing |

**Use Jina Reader as primary, direct httpx+BS4 as fallback. Skip Kimi and Vercel entirely for now.**

> **Scope reminder:** DDG URL discovery is untouched. Qdrant collection schema is untouched. Only the fetch-extract-chunk pipeline is modified.
