# Yantra - Product Context

## Overview
Yantra is an AI-powered Robotics Knowledge System and Physical Product Intelligence Platform. It functions as a specialized Retrieval-Augmented Generation (RAG) system for robotics, automation, industrial systems, CAD assemblies, and component-level engineering.

The long-term vision is to serve as a **Physical Product Operating System** that assists engineers throughout the entire hardware lifecycle:
`Idea → Research → Component Selection → CAD Design → Assembly → Manufacturing`

## Architecture & Directory Structure
The repository is split into a Next.js frontend and a Python backend.

### 1. Backend (`/src/`)
- **Core Engine**: Python-based data ingestion, processing, and retrieval engine.
  - `api/` - FastAPI backend application handling frontend requests.
  - `scraper/` - Web scraping agents for dynamic knowledge acquisition.
  - **RAG Pipeline**: `ingest.py`, `retriever.py`, `embedder.py`, `vectordb.py`, `chunker.py`, `loader.py`.
  - **CAD & Assembly**: `assembly_engine.py`, `bom_extractor.py`, `cad_registry.py`, `connection_kb.py` (responsible for understanding physical structure, extracting Bill of Materials, and mapping component connections).

### 2. Frontend (`/frontend/`)
- **Web App**: Next.js 16 (React 19) application using TypeScript.
- **Styling**: Tailwind CSS v4, shadcn, and base-ui.
- **3D / CAD Viewer**: Three.js, `@react-three/fiber`, `@react-three/drei`, and `occt-import-js` for rendering and interacting with physical models (STEP files).
- **Mapping / Graphs**: React Flow (`@xyflow/react`) for visualizing component connectivity and knowledge graphs (e.g., Motor → Driver → Power Supply).

### 3. Data Storage (`/knowledgebase/` & `/qdrant_data/`)
- **Knowledge Base**: Curated local directory of technical documents categorized by robot type (e.g., `Articulated_Robot`, `Autonomous_Mobile_Robot`, `cobot_robot`).
- **Supported Formats**: Technical Manuals (`.pdf`, `.docx`), Engineering CAD (`.step`, `.prt`, `.sldasm`), Images.
- **Vector Store**: Qdrant running locally to store and query 1024-dimensional document embeddings.

## Tech Stack
* **Language/Frameworks**: Python, Next.js, React, FastAPI
* **Embedding Model**: `BAAI/bge-large-en-v1.5` (via OpenRouter API)
* **Vector Database**: Qdrant (Cosine Similarity)
* **Document Processing**: `PyPDF`, `python-docx`, LangChain `RecursiveCharacterTextSplitter` (1000 chars, 150 overlap)
* **3D Engine**: Three.js / OpenCASCADE (occt)

## Key Features & Pipelines
1. **Document Ingestion & RAG**: Extracts text/metadata from robotics manuals, chunks it, embeds it via the OpenRouter API, and stores it in Qdrant. At query time, it uses semantic search to fetch the top-k relevant technical snippets.
2. **CAD Intelligence & BOM Extraction**: Parses engineering CAD files (STEP) to extract components, assemblies, and connections.
3. **Component Mapping Graph**: Visually maps how physical components relate and connect to one another to build functional systems.
4. **Agentic Knowledge Fetching**: When local knowledge falls short, web scraping agents use DuckDuckGo and Playwright to find, extract, chunk, and embed information dynamically from the web.

## Current State & Next Steps
- **Completed**: Baseline RAG pipeline, offline document ingestion, Qdrant integration, basic frontend/CLI chat interfaces.
- **In Progress**: Full Next.js + FastAPI integration, robust CAD processing, 3D visualization, and dynamic web scraping RAG agents.
- **Future Goals**: Multi-modal RAG (understanding images and schematics natively), agentic reasoning (Owl Alpha integration), and deep engineering component-level design assistance.
