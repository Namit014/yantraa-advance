# Yantraa — Surgical Fix Prompt (Main Branch)

> **Context:** This is the existing `yantraa-advance` main branch — NOT a rebuild. Make targeted, surgical changes only. Do not restructure the project or rename files unless explicitly told to. Preserve all existing functionality; only fix what is broken or degraded.

---

## PART 1 — PIPELINE FIXES

### 1.1 — Unified Chunking Strategy

**Problem:** `src/chunker.py` uses `RecursiveCharacterTextSplitter` with `chunk_size=350`, but `src/scraper/chunker.py` uses raw character slicing (`text[i:i+chunk_size]`) which cuts mid-word and mid-sentence. Both feed the same Qdrant collection, producing inconsistent embedding quality.

**Fix:**
- In `src/scraper/chunker.py`, replace the raw character slicing with `RecursiveCharacterTextSplitter` using the exact same parameters as `src/chunker.py`.
- Change `chunk_size` in both files to `512` and `chunk_overlap` to `100`.
- The scraper chunker should use these separators in order: `["\n## ", "\n### ", "\n\n", "\n", ". ", " "]`.
- Skip any chunk shorter than 50 characters after stripping.
- Do not change anything else in either file.

---

### 1.2 — Fix Double-Chunking in the Embedder

**Problem:** `src/embedder.py` has a `MAX_CHARS = 1200` guard that re-splits chunks the chunker already produced, using raw character slicing with no overlap. This silently destroys semantic boundaries for the second time.

**Fix:**
- Remove the inner re-chunking loop in `embedder.py` entirely.
- Replace it with a `logger.warning(...)` if any chunk exceeds `MAX_CHARS`.
- The embedder's job is only to embed — never to split. The chunker owns that.

---

### 1.3 — Fix the Embedding Query Being Called Multiple Times

**Problem:** Inside `src/retriever.py` → `ask()`, `self._embed_query(optimized_query)` is called 2-3 times for different Qdrant searches within the same request. Each call takes 50-200ms on the local model.

**Fix:**
- At the top of `ask()`, embed once: `query_vector = self._embed_query(optimized_query)`.
- Replace every subsequent `self._embed_query(...)` call inside the same `ask()` function with `query_vector`.
- Do not change any other logic in the retriever.

---

### 1.4 — Fix Qdrant Client Fragmentation

**Problem:** Separate `QdrantClient` instances are created independently in `src/retriever.py`, `src/vectordb.py`, and `src/api/connections/generate.py`. With file-based Qdrant this causes locking conflicts.

**Fix:**
- In `src/vectordb.py`, expose the already-created `QdrantClient` instance as a module-level singleton: `_client = QdrantClient(path=...)`. Other modules should import this instead of creating their own.
- In `src/api/connections/generate.py`, import the singleton from `vectordb.py` instead of instantiating a new `QdrantClient` locally in `_rag_search`.
- In `src/retriever.py`, do the same — import the singleton from `vectordb.py`.
- The `path="./qdrant_data"` string must be defined in exactly one place (in `vectordb.py`) and imported everywhere else. Remove all other hardcoded `qdrant_data` path strings.

---

### 1.5 — Fix the "openrouter/free" Model Default

**Problem:** `src/llm.py` uses `DEFAULT_MODEL = "openrouter/free"` which rotates between random models with inconsistent JSON compliance, causing the design pipeline to return invalid JSON and fall back to the empty/generic "Monolithic Robot System" response.

**Fix:**
- Change `DEFAULT_MODEL` in `src/llm.py` to `"google/gemini-2.5-flash"`.
- If the model name is already coming from `.env` via `OPENROUTER_MODEL`, make sure the `.env.example` default is `google/gemini-2.5-flash`.
- Do not change anything else in `llm.py`.

---

### 1.6 — Fix Synchronous Scraper Blocking the Event Loop

**Problem:** `src/scraper/scraper.py` uses `requests.get()` (synchronous). When called from inside a FastAPI async endpoint via the retriever's web fallback, it blocks the entire event loop.

**Fix:**
- Replace `import requests` with `import httpx`.
- Replace `requests.get(url, timeout=10)` with `httpx.get(url, timeout=15, follow_redirects=True)`.
- In `main.py`, wrap any synchronous call to `retriever.ask()` inside `await asyncio.get_event_loop().run_in_executor(None, retriever.ask, request.query)` to move it off the event loop.
- Add `import asyncio` to `main.py` if not already present.

---

### 1.7 — Fix LLM Cleaning Call Per Scraped Page

**Problem:** `src/scraper/pipeline.py` calls the LLM for every scraped page to clean HTML noise. At 15 pages this adds 45-150 seconds of latency and occasionally hallucinates content.

**Fix:**
- Replace the LLM cleaning call with a BeautifulSoup extraction function:
```python
def extract_clean_text(html: str) -> str:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    for tag in ("nav", "footer", "header", "script", "style", "aside", "form"):
        for el in soup.find_all(tag):
            el.decompose()
    article = soup.find("article") or soup.find("main") or soup.body or soup
    text = article.get_text(separator="\n", strip=True)
    lines = [line for line in text.splitlines() if line.strip()]
    return "\n".join(lines)
```
- Call this function instead of the LLM cleaning prompt in `pipeline.py`.
- Keep the LLM call only if the cleaned text is still clearly garbage (less than 100 characters).

---

### 1.8 — Fix Ingestion Deduplication

**Problem:** Running `ingest.py` multiple times creates duplicate chunks in Qdrant because there is no check for already-ingested content.

**Fix:**
- Add a `compute_content_hash(text: str) -> str` function using `hashlib.sha256`.
- Before upserting any chunk in `vectordb.py`, store the hash in the chunk's payload as `"content_hash"`.
- At the start of an ingestion run, query Qdrant to retrieve all existing `content_hash` values into a set.
- Skip any chunk whose hash is already in that set.
- Do not change the Qdrant collection schema — just add `content_hash` as an extra payload field.

---

### 1.9 — Fix Metadata Categorization

**Problem:** `src/chunker.py` → `create_metadata()` uses naive single-keyword filename matching. `motor_sensor_assembly.docx` becomes "Motors" only. `BLDC_guide.pdf` becomes "General".

**Fix:**
- Replace the `if/elif` chain with a multi-label keyword map:
```python
KEYWORD_MAP = {
    "sensor": "Sensors", "motor": "Motors", "driver": "Motor Drivers",
    "bldc": "Motors", "servo": "Motors", "stepper": "Motors",
    "control": "Control System", "power": "Power System", "psu": "Power System",
    "software": "Software", "firmware": "Software",
    "comm": "Communication", "uart": "Communication", "can": "Communication",
    "cad": "CAD", "step": "CAD", "stp": "CAD",
    "gripper": "End Effectors", "effector": "End Effectors",
    "frame": "Structural", "chassis": "Structural",
    "bom": "Bill of Materials", "schematic": "Schematics",
    "lidar": "Sensors", "imu": "Sensors", "encoder": "Sensors",
}
categories = [cat for kw, cat in KEYWORD_MAP.items() if kw in filename.lower()]
if not categories:
    categories = ["General"]
metadata["categories"] = categories  # multi-label list, not a single string
```
- Keep the rest of `create_metadata()` unchanged.

---

### 1.10 — Fix the CAD Filename Mismatch Between retriever.py and design.py

**Problem:** `src/retriever.py` and `src/api/design.py` each have their own hardcoded `known_cads` dict. The filenames don't match between them (e.g., `"painting_robot_cad.stp"` vs `"Painting_Robot.step"`).

**Fix:**
- Create a new file `src/cad_registry.py` with a single `KNOWN_CADS` dict that maps keyword aliases to the actual correct filename (verify each filename against the real files in `knowledgebase/`).
- Import `KNOWN_CADS` from `cad_registry.py` in both `retriever.py` and `design.py`.
- Delete the local hardcoded dicts from both files.
- The dict keys should be lowercase normalized aliases; values should be the exact filename with correct extension and casing.

---

### 1.11 — Fix the CAD File Endpoint Path Traversal

**Problem:** `/api/cad/{filename}` in `main.py` accepts any string and runs `glob` on it. A malformed filename like `../../.env` could expose secrets.

**Fix:**
- Before the glob call, validate the filename:
```python
import re
if not re.match(r'^[a-zA-Z0-9_\-]+\.(step|stp|STEP|STP)$', filename):
    raise HTTPException(status_code=400, detail="Invalid filename")
```
- Add this validation as the very first line inside the endpoint handler.

---

### 1.12 — Fix the Void Fallback ("Monolithic Robot System")

**Problem:** When the LLM returns invalid JSON (common on free-tier models), the design pipeline catches the exception and returns a hardcoded fallback dict with a single "Monolithic Robot System" subsystem. The user sees an empty or broken design every time JSON parsing fails.

**Fix in `src/api/design.py` (or wherever the LLM JSON is parsed):**

1. **Add a repair step before giving up.** After catching a JSON parse error, extract the JSON substring from the LLM response using regex before raising:
```python
import re, json

def extract_json(text: str) -> dict:
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try extracting from markdown code block
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    # Try finding the outermost { } block
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    raise ValueError(f"Could not extract JSON from LLM response: {text[:300]}")
```

2. **Strengthen the LLM prompt** for the design pipeline. In the system prompt that asks for robot design JSON, add explicitly at the end:
```
CRITICAL: Your response must be valid JSON only. No markdown, no backticks, no explanation text before or after the JSON object. Start your response with { and end with }.
```

3. **If JSON extraction still fails after the repair step**, do NOT return the "Monolithic Robot System" fallback. Instead return an error response to the frontend:
```python
{"error": "Design generation failed — LLM returned unparseable output. Try rephrasing your request or try again."}
```
And surface this as a visible error message in the UI instead of a broken design.

---

## PART 2 — CONNECTION TAB FIXES

### 2.1 — Fix Empty Connection Generation

**Problem:** The connection generator in `src/api/connections/generate.py` returns empty `connections: []` for vague queries like "build me an arm robot" because the RAG search finds nothing relevant and the fallback logic does not synthesize components from the design step.

**Fix:**
- In `generate.py`, before calling the LLM to generate connections, check if the RAG-retrieved context is empty or below a relevance threshold.
- If the context is insufficient, use the subsystems and components from the already-generated design (passed in the request payload) as the grounding context instead of relying solely on Qdrant results.
- The LLM prompt for connection generation should receive:
  - The list of subsystems and their components from the design step.
  - The connection KB rules from `connection_kb.py`.
  - Any RAG context if available (append it, don't replace the above).
- This ensures connection generation always has structural grounding even when RAG returns nothing.

---

### 2.2 — Fix Connection KB Not Being Applied

**Problem:** `connection_kb.py` defines connection patterns and validation rules, but they may not be actively enforced when the LLM generates the `connections` array — the LLM ignores or contradicts them.

**Fix:**
- In the LLM system prompt for connection generation, serialize the relevant rules from `connection_kb.py` as a numbered list and inject them directly:
```
CONNECTION RULES (you must follow these exactly):
1. Microcontrollers connect to motor drivers via PWM or UART.
2. Motor drivers connect to motors via power lines.
3. Power supply connects to all components requiring Vin.
... (expand from connection_kb.py)
```
- After the LLM returns the connections array, run the existing validation logic from `connection_kb.py` against the output.
- For any connection that fails validation, either auto-repair it (fix the signal type or swap source/target) or remove it and log it.
- Do not silently swallow validation failures.

---

### 2.3 — Fix Connection Nodes Not Rendering in React Flow

**Problem:** If the `connections` array arrives correctly but nodes are not appearing in the React Flow canvas, the likely cause is that node IDs in the connections array do not match the component IDs used to build the React Flow node objects.

**Fix in `frontend/src/components/connection/` (or wherever the React Flow graph is built):**
- When building React Flow nodes, use a normalized ID: `component.id.toString().toLowerCase().replace(/\s+/g, '_')`.
- When building edges from the connections array, normalize the `source` and `target` IDs the same way before lookup.
- Add a console warning if any edge references a source or target ID that does not exist in the nodes array — this immediately surfaces the mismatch during development.

---

### 2.4 — Fix Orthogonal Wire Routing Breaking on Dense Graphs

**Problem:** With many components, the orthogonal edge routing collides and produces overlapping wires.

**Fix:**
- In the React Flow configuration, set `connectionLineType="smoothstep"` and add `edgesFocusable={false}` to reduce visual noise.
- On each edge object, add `{ type: 'smoothstep', animated: false, style: { strokeWidth: 1.5 } }`.
- Do not attempt to implement custom orthogonal routing — use React Flow's built-in smoothstep which handles dense graphs well.

---

## PART 3 — MAPPING TAB FIXES

### 3.1 — Fix Empty Mapping When Design Returns No Subsystems

**Problem:** If the LLM returns a design with 0 or 1 subsystems, the mapping tab renders nothing or a single block with no components visible.

**Fix in the mapping tab component:**
- Add a guard: if `design.subsystems` is empty or undefined, show a visible error message inside the tab: `"No subsystems were generated. Try a more specific robot description."` — not a blank canvas.
- If `subsystems` exists but `components` inside any subsystem is an empty array, show a placeholder card: `"No components mapped for this subsystem."` instead of nothing.

---

### 3.2 — Fix BOM Table Not Populating

**Problem:** The BOM table in the mapping tab may not render if `design.bom` is undefined or arrives as a different key name from the backend.

**Fix:**
- In the backend design response, ensure the BOM is always returned under the key `"bom"` as a flat array. If the LLM returns it under a different key (e.g., `"bill_of_materials"`), normalize it before sending the response.
- In the frontend, add a fallback: if `design.bom` is undefined or empty, derive a minimal BOM from `design.subsystems[*].components` — use component name, subsystem as category, and `"1"` as quantity.
- Display "N/A" for any missing fields rather than crashing or rendering `undefined`.

---

### 3.3 — Fix Validation Issues List Not Showing

**Problem:** The validation section in the mapping tab is blank even when the backend detects issues.

**Fix:**
- In the backend, ensure `validation` key is always present in the response, even if it's an empty array `[]`.
- In `design.py`, after generating the design JSON from the LLM, run a basic local validation pass before sending:
  - Flag any subsystem with 0 components.
  - Flag any component that appears in the connections array but is missing from all subsystems.
  - Flag if no power subsystem is present.
- Include results as `[{ "level": "warning"|"error", "message": "..." }]`.
- In the frontend mapping tab, if `validation` is an empty array, show: `"✓ No issues detected."` — not a blank section.

---

## PART 4 — CAD TAB FIXES

### 4.1 — Fix CAD Viewer Controls (Pan/Zoom/Rotate Not Working)

**Problem:** The Three.js/React Three Fiber CAD viewer's orbit controls are not responding or only partially working.

**Fix in `cad-tab.tsx` (or the CAD viewer component):**
- Ensure `OrbitControls` is imported from `@react-three-fiber/drei` (not from `three` directly, which requires manual setup).
- Set `makeDefault` on `<OrbitControls>` so it registers as the default control.
- The `<Canvas>` element must not have `pointer-events: none` in its CSS — check for this in the tab wrapper.
- Add `domElement` event listener cleanup on unmount to prevent stale listeners causing broken controls after tab switching.

---

### 4.2 — Fix CAD File Not Loading for Certain Robot Types

**Problem:** Some robot type keywords from the design step do not match any entry in the `known_cads` lookup, returning 404 from the CAD endpoint.

**Fix:**
- After fixing `cad_registry.py` in 1.10, expand the alias keys with common variations:
  - `"arm"`, `"robotic arm"`, `"6dof arm"`, `"manipulator"` → same STEP file
  - `"agv"`, `"autonomous mobile"`, `"amr"`, `"mobile robot"` → same STEP file
  - `"delta"`, `"delta robot"`, `"parallel"` → same STEP file
- In `design.py` (or `retriever.py`) where `cad_url` is resolved, normalize the robot description to lowercase and check against all aliases before declaring `cad_available: false`.
- If no CAD match is found, set `cad_available: false` and `cad_url: null` cleanly — do not pass a broken URL to the frontend.

---

### 4.3 — Fix CAD Tab Showing Blank on Tab Switch

**Problem:** Navigating away from the CAD tab and back causes the Three.js canvas to go blank.

**Fix:**
- Wrap the CAD viewer in a `key` prop tied to the selected CAD URL. When the URL changes, React remounts the viewer: `<CADViewer key={cadUrl} url={cadUrl} />`.
- This forces a clean Three.js context on each load and prevents stale WebGL state.

---

## PART 5 — SECURITY QUICK FIXES (Non-Breaking)

### 5.1 — Restrict CORS
In `src/api/main.py`, replace `allow_origins=["*"]` with:
```python
ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, ...)
```
Add `CORS_ORIGINS=http://localhost:3000` to `.env.example`.

### 5.2 — Rotate the Exposed API Key
The OpenRouter key `sk-or-v1-45ba5a8...` is in Git history. Even if `.env` is gitignored, the key is already committed. Revoke it on the OpenRouter dashboard and generate a new one. Run BFG Repo-Cleaner or `git filter-repo --path .env --invert-paths` to scrub the history.

### 5.3 — Add `.env` to `.gitignore` if not already present
```
.env
.env.local
*.bak
debug_*.txt
api_response.json
.temp_*/
scratch/
qdrant_data/
```

---

## EXECUTION ORDER

Apply fixes in this sequence to minimize breakage:

```
1. Fix llm.py model default (1.5) — immediate impact on JSON quality
2. Fix void fallback + JSON repair (1.12) — stops the empty design problem
3. Fix embed query calls (1.3) — quick win, no logic change
4. Fix Qdrant client singleton (1.4) — required before running ingest + api together
5. Fix chunking unification (1.1) and double-chunking in embedder (1.2)
6. Fix CAD registry (1.10) + path traversal guard (1.11)
7. Fix connection grounding (2.1) + KB enforcement (2.2)
8. Fix mapping tab guards (3.1, 3.2, 3.3)
9. Fix CAD viewer controls (4.1, 4.2, 4.3)
10. Fix scraper sync blocking (1.6) + LLM cleaning (1.7)
11. Apply security quick fixes (Part 5)
12. Fix ingestion dedup (1.8) — run a fresh ingest after this
```

---

> **Scope reminder:** Do not restructure folders, rename modules, or introduce new dependencies beyond `httpx` (replacing `requests`) and `beautifulsoup4` (already likely installed). Every fix targets the existing file at its existing path.
