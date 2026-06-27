# Yantraa AI Prompt Quality Scoring & Routing System

This document outlines the proposed implementation plan for the Yantraa AI Prompt Scoring system based on the provided specification.

## Goal

Build a system that intercepts user prompts, scores them across five quality dimensions (Specificity, Completeness, Domain alignment, Actionability, Scope control), and routes them either directly to an AI model (if score = 5) or into a clarification loop (if score <= 4) by retrieving relevant FAQ questions using vector similarity.

## User Review Required

> [!IMPORTANT]
> The specification outlines a full-stack architecture with a backend API and a frontend chat interface. I need your confirmation on the technology stack and the integration of actual AI models versus mock implementations for the initial prototype.

## Open Questions

> [!WARNING]
> Please review and provide feedback on these critical architectural decisions:
> 1. **Tech Stack**: Do you prefer a **Python FastAPI** backend (best for AI and vector math) with a **React (Vite)** frontend, or a unified full-stack framework like **Next.js**?
> 2. **AI APIs**: Should I integrate real OpenAI APIs (e.g., `text-embedding-3-small` for embeddings and `gpt-4o` for the model) or build it with mocked API responses first to validate the routing logic? If real, I will need you to configure an API key.
> 3. **Vector Database**: For the FAQ vector search, should I use an in-memory implementation (e.g., `faiss` or basic cosine similarity in numpy) for prototyping, or connect to a dedicated vector database like ChromaDB/Pinecone?

## Proposed Changes

We will build this as a local web application. Assuming the **Python FastAPI + React** stack for now:

### Backend API (Python / FastAPI)

*   **Core Scoring Engine**: Implements the tokenization, lexicon matching, and rule-based scoring across the 5 dimensions.
*   **Vector FAQ Retrieval**: Implements embedding of the incoming prompt and cosine similarity search against the FAQ database, heavily penalizing dimensions that scored low to target the right questions.
*   **API Endpoints**:
    *   `POST /api/chat/score`
    *   `POST /api/chat/clarify`
    *   `POST /api/chat/route`
    *   `GET /api/faq/search`

### Frontend Application (React / Vite)

*   **Chat Interface**: A sleek, modern chat UI reflecting Yantraa's brand.
*   **Clarification UI**: When a score is <= 4, renders the custom clarification response with the score badge, dimension summary, and inline input fields for the user to answer the targeted FAQ hints.
*   **State Management**: Maintains the 3-round limit state and rebuilds the prompt coherently by concatenating the original prompt with the user's answers before re-scoring.

### Data Layer

*   **FAQ Store**: A JSON-based configuration of predefined FAQ items with pre-computed embeddings for the core Yantraa parameters (Payload, Reach, DOF, Environment, etc.).
*   **Lexicon**: The Yantraa term lexicon for the Domain Alignment scorer.

## Verification Plan

### Automated Tests
*   **Unit Tests (Backend)**: Test the `Composite scoring` math to ensure raw scores correctly map to integer scores (1-5).
*   **Routing Tests**: Verify that score 5 routes to the model and score <= 4 routes to clarification.

### Manual Verification
*   Launch the web app and test various prompts:
    *   *Score 1*: "scara robot" -> Should return 3 high-level FAQs.
    *   *Score 5*: "Generate a BOM for a 4-DOF SCARA robot with 600 mm reach, 5 kg payload, ±0.05 mm repeatability, targeting a tabletop pick-and-place cell running at 60 cycles/minute." -> Should route to AI.
*   Verify the re-scoring logic correctly aggregates answers to clarification questions.
