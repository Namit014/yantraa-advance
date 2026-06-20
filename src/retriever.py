import sys
import os
import re
import atexit

# Ensure src/ is on the path for all sub-imports
_src_dir = os.path.dirname(os.path.abspath(__file__))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from vectordb import _client
from qdrant_client.models import Distance, VectorParams
from embedder import Embedder, EMBEDDING_DIMENSION

# ── Thresholds ────────────────────────────────────────────────────────────────
# Hard floor: if the top result is below this, skip LLM validation and go web.
SCORE_HARD_FLOOR = 0.50
# Relevance floor: a chunk must exceed this to count as "relevant"
SCORE_RELEVANCE_FLOOR = 0.45
# Minimum number of relevant chunks required before trusting Qdrant context
MIN_RELEVANT_CHUNKS = 1
# ─────────────────────────────────────────────────────────────────────────────


def _parse_yes_no(llm_response: str) -> str:
    """
    Robustly extract YES or NO from an LLM response.
    - Looks for the first occurrence of the word YES or NO (whole word, case-insensitive)
    - Defaults to "NO" if neither is found (fail-safe: prefer web fallback over wrong answer)
    """
    text = llm_response.strip().upper()
    # Match whole word YES or NO at start or anywhere
    match = re.search(r'\b(YES|NO)\b', text)
    if match:
        return match.group(1)
    # If response is ambiguous, fail safe to NO
    print(f"[Yantra AI] Ambiguous validation response: '{llm_response[:80]}' — defaulting to NO")
    return "NO"


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


def _run_async(coro):
    import asyncio
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    else:
        return asyncio.run(coro)


class Retriever:

    def __init__(self):

        self.embedder = Embedder()

        self.client = _client

        # Explicitly close the Qdrant client on exit to avoid
        # "sys.meta_path is None" warning during Python shutdown
        atexit.register(self._close_qdrant)

        self.collection_name = (
            "yantra_knowledgebase"
        )
        
        # Ensure collection exists so query_points doesn't crash on an empty database
        collections = self.client.get_collections()
        existing = [c.name for c in collections.collections]
        if self.collection_name not in existing:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=EMBEDDING_DIMENSION, distance=Distance.COSINE)
            )
            print(f"[Yantra AI] Initialized new empty Qdrant collection: {self.collection_name}")

    def _close_qdrant(self):
        """Gracefully close the Qdrant client before Python shuts down."""
        try:
            self.client.close()
        except Exception:
            pass

    def _embed_query(self, query):
        """Embed a query string using the OpenRouter API."""
        return self.embedder.embed_text(query)

    def search(
        self,
        query,
        top_k=5
    ):

        query_vector = self._embed_query(query)

        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=top_k
        )

        if not results.points or results.points[0].score < SCORE_HARD_FLOOR:
            print("Score too low. Searching the web...")
            from scraper.pipeline import web_ingest
            optimized_query = optimize_for_web_search(query)
            _run_async(web_ingest(optimized_query, qdrant_client=self.client, original_query=query))
            results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                limit=top_k
            )

        return results.points

    async def _web_fallback(self, query: str) -> dict:
        """
        Fires only when Qdrant score is below SCORE_HARD_FLOOR.
        Returns structured context with source attribution.
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[RAG FALLBACK] Qdrant score too low. Triggering web fallback for: {query}")

        from scraper.search import search_web
        from scraper.pipeline import rank_urls, is_garbage_text, chunk_scraped_text, _url_cache, _save_url_cache
        from scraper.scraper import fetch_clean_text

        # DDG search
        urls = search_web(query)

        if not urls:
            logger.warning("[RAG FALLBACK] DDG returned no URLs.")
            return {"context": "", "source": "none", "fallback_used": True, "source_urls": []}

        # Rank and limit
        ranked_urls = rank_urls(urls)[:5]

        # Fetch via Jina with fallback
        texts = []
        for url in ranked_urls:
            if url in _url_cache:
                logger.info(f"[RAG FALLBACK] URL already in cache, skipping fetch: {url}")
                continue
            text = await fetch_clean_text(url)
            if text and not is_garbage_text(text):
                texts.append({"url": url, "text": text})
                # Add to cache and save
                _url_cache.add(url)
                _save_url_cache(_url_cache)
            if len(texts) >= 3:  # stop after 3 good pages
                break

        if not texts:
            logger.warning("[RAG FALLBACK] All fetched pages were garbage or already cached. Returning empty context.")
            return {"context": "", "source": "none", "fallback_used": True, "source_urls": []}

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

    def ask(self, query, top_k=15):
        """
        Agentic Workflow:
          Query Planning → Qdrant search → Sufficiency gate → (YES) Answer
                                                             → (NO) Web fallback → Re-query → Answer
        """
        try:
            from llm import invoke_yantra_ai
        except ImportError:
            try:
                from .llm import invoke_yantra_ai
            except ImportError:
                from src.llm import invoke_yantra_ai

        # ── Step 1: Query Planning ─────────────────────────────────────────
        # OPTIMIZATION: Skip LLM-based intent extraction to save 6-10 seconds!

        optimized_query = query
        logical_intent = query
        query_vector = self._embed_query(optimized_query)

        from qdrant_client.models import Filter, FieldCondition, MatchValue

        # ── Step 2: Search Local Knowledgebase ─────────────────────────────
        print("[Yantra AI] Searching local knowledgebase...")
        local_filter = Filter(
            must_not=[
                FieldCondition(
                    key="source",
                    match=MatchValue(value="web_scraped")
                )
            ]
        )
        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=local_filter,
            limit=top_k
        )

        context_texts = [p.payload.get("text", "") for p in results.points] if results.points else []
        context_block = "\n\n".join(context_texts)

        top_score = results.points[0].score if results.points else 0.0
        relevant_count = sum(1 for p in results.points if p.score >= SCORE_RELEVANCE_FLOOR)

        print(f"[Yantra AI] Local Top score: {top_score:.3f} | Relevant chunks (>={SCORE_RELEVANCE_FLOOR}): {relevant_count}/{len(results.points)}")

        is_enough = "NO"
        if context_texts and top_score >= SCORE_HARD_FLOOR and relevant_count >= MIN_RELEVANT_CHUNKS:
            # OPTIMIZATION: Trust the high vector score instead of asking LLM to validate.
            print("[Yantra AI] Data exceeds relevance threshold. Bypassing LLM validation for speed.")
            is_enough = "YES"
            print(f"[Yantra AI] Enough Local Data? {is_enough}")
        else:
            reason = (
                f"top score {top_score:.3f} < {SCORE_HARD_FLOOR}"
                if top_score < SCORE_HARD_FLOOR
                else f"only {relevant_count} relevant chunk(s) (need >={MIN_RELEVANT_CHUNKS})"
            )
            print(f"[Yantra AI] Enough Local Data? NO ({reason})")

        # ── Step 3: Search Web Scraped Data ────────────────────────────────
        if is_enough == "NO":
            print("[Yantra AI] Not enough local data. Searching web_scraped data...")
            web_filter = Filter(
                must=[
                    FieldCondition(
                        key="source",
                        match=MatchValue(value="web_scraped")
                    )
                ]
            )
            results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                query_filter=web_filter,
                limit=top_k
            )

            context_texts = [p.payload.get("text", "") for p in results.points] if results.points else []
            context_block = "\n\n".join(context_texts)

            top_score = results.points[0].score if results.points else 0.0
            relevant_count = sum(1 for p in results.points if p.score >= SCORE_RELEVANCE_FLOOR)

            print(f"[Yantra AI] Web_scraped Top score: {top_score:.3f} | Relevant chunks (>={SCORE_RELEVANCE_FLOOR}): {relevant_count}/{len(results.points)}")

            if context_texts and top_score >= SCORE_HARD_FLOOR and relevant_count >= MIN_RELEVANT_CHUNKS:
                # OPTIMIZATION: Trust the high vector score instead of asking LLM to validate.
                print("[Yantra AI] Web data exceeds relevance threshold. Bypassing LLM validation.")
                is_enough = "YES"
                print(f"[Yantra AI] Enough Web_scraped Data? {is_enough}")
            else:
                reason = (
                    f"top score {top_score:.3f} < {SCORE_HARD_FLOOR}"
                    if top_score < SCORE_HARD_FLOOR
                    else f"only {relevant_count} relevant chunk(s) (need >={MIN_RELEVANT_CHUNKS})"
                )
                print(f"[Yantra AI] Enough Web_scraped Data? NO ({reason})")

        # ── Step 4: Web Fallback (if needed) ──────────────────────────────
        fallback_used = False
        source_urls = []
        source_type = "kb"

        if is_enough == "NO":
            print("[Yantra AI] Triggering Web Fallback Pipeline to search internet...")
            opt_query = optimize_for_web_search(query)
            fallback_res = _run_async(self._web_fallback(opt_query))
            context_block = fallback_res["context"]
            fallback_used = fallback_res["fallback_used"]
            source_urls = fallback_res.get("source_urls", [])
            source_type = fallback_res.get("source", "none")

        # ── Step 5: Final Synthesis ────────────────────────────────────────
        print("[Yantra AI] Generating final synthesis...")
        context_note = ""
        if source_type == "web":
            context_note = "\n\n[Note: This context was retrieved from the web, not the internal knowledgebase.]"

        final_prompt = (
            f"Context from Knowledge Base:\n{context_block}{context_note}\n\n"
            f"User Query: {query}\n\n"
            f"You are an expert robotics and manufacturing AI engineer. "
            f"Answer the query in extreme detail. "
            f"If the user is asking how to build, create, or design something, provide a highly detailed, "
            f"step-by-step 'from scratch' guide. Use the provided context as your foundation, but "
            f"you are fully encouraged to use your own expert knowledge to expand on the topic, fill in any missing gaps, "
            f"and provide a complete, robust tutorial."
        )
        final_answer = invoke_yantra_ai(final_prompt)

        # ── Step 6: CAD Availability Check ─────────────────────────────────
        cad_available = False
        cad_url = None
        
        from cad_registry import get_known_cads
        known_cads = get_known_cads()
        
        query_lower = query.lower()
        for key, filename in known_cads.items():
            if key in query_lower:
                cad_available = True
                cad_url = f"/api/cad/{filename}"
                break
                
        if not cad_available and results and results.points:
            for pt in results.points:
                payload = pt.payload or {}
                robot_val = payload.get("robot") or payload.get("robot_name") or payload.get("category")
                if robot_val and isinstance(robot_val, str):
                    r_lower = robot_val.lower()
                    for key, filename in known_cads.items():
                        if key.replace(" ", "_") in r_lower or key in r_lower:
                            cad_available = True
                            cad_url = f"/api/cad/{filename}"
                            break
                if cad_available:
                    break

        return final_answer, cad_available, cad_url, fallback_used, source_urls


if __name__ == "__main__":

    retriever = Retriever()

    results = retriever.search(
        "What sensors are used in articulated robots?"
    )

    for result in results:

        print("\nScore:", result.score)

        print(
            "Robot:",
            result.payload.get("robot")
        )

        print(
            "Category:",
            result.payload.get("category")
        )

        print(
            "Text:",
            result.payload.get("text")[:300]
        )