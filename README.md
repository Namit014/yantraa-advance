# Yantraa

## AI-Powered Robotics Knowledge System & Physical Product Intelligence Platform

---

# Overview

Yantra is a robotics-focused Retrieval-Augmented Generation (RAG) system designed to transform technical robotics knowledge into an intelligent searchable knowledge platform.

The project aims to become a Physical Product Operating System where users can move from:

```text
Idea
 ↓
Research
 ↓
Component Selection
 ↓
Knowledge Retrieval
 ↓
CAD Understanding
 ↓
Component Mapping
 ↓
Assembly Understanding
 ↓
Manufacturing
```

Unlike traditional document chatbots, Yantra is being built specifically for robotics, automation, industrial systems, CAD assemblies, and component-level intelligence.

---

# Current System Statistics

| Metric               | Value               |
| -------------------- | ------------------- |
| Knowledge Base Files | 156                 |
| Total Chunks         | 939                 |
| Embedding Model      | BAAI/bge-large-en-v1.5 (via OpenRouter API) |
| Embedding Dimension  | 1024                |
| Vector Database      | Qdrant              |
| Chunk Size           | 1000 Characters     |
| Chunk Overlap        | 150 Characters      |
| Retrieval Method     | Dense Vector Search |
| Similarity Metric    | Cosine Similarity   |
| Top-K Retrieval      | 5                   |

---

# Vision

Yantra is designed to become a unified intelligence layer for robotics and physical product development.

Future capabilities include:

* Robotics Knowledge Intelligence
* CAD Understanding
* Component Mapping
* Connection Mapping
* Multi-Modal RAG
* Manufacturing Intelligence
* Engineering Research
* Product Design Assistance
* Physical Product Operating System

---

# Knowledge Base Structure

```text
knowledgebase/

├── Articulated_Robot/
├── Automated_Guided_Vehicle/
├── Autonomous_Mobile_Robot/
├── Cartesian_Robot/
├── Machine_Tending_Robot/
├── Painting_Robot/
├── cobot_robot/
├── delta_robot/
├── inspection_robot/
├── scara_robot/
├── welding_robot/
│
└── web_scraped/
```

---

# Supported Robot Categories

## Industrial Robots

* Articulated Robot
* Cartesian Robot
* SCARA Robot
* Delta Robot
* Welding Robot
* Painting Robot
* Inspection Robot
* Machine Tending Robot

## Mobile Robots

* AGV (Automated Guided Vehicle)
* AMR (Autonomous Mobile Robot)

## Collaborative Robots

* Cobot

---

# Knowledge Sources

The knowledge base contains:

## Technical Documentation

* Technical Manuals
* Reference Documents
* System Guides
* Operating Procedures

## Datasheets

* Component Specifications
* Robot Specifications
* Performance Metrics

## Research Material

* Research Papers
* Industrial Studies
* Technical References

## Engineering Documents

* Schematics
* Component Mapping Documents
* System Architecture Documents
* Manufacturing Documents

## CAD References

* STEP Files
* STP Files
* SLDASM Files
* PRT Files

## Images

* Robot Images
* Component Images
* Reference Visuals

---

# Supported File Types

## Documents

```text
.pdf
.docx
.txt
```

## CAD

```text
.step
.stp
.sldasm
.prt
```

## Images

```text
.jpg
.jpeg
.png
```

---

# Current Architecture

## Offline Ingestion Pipeline

```text
Knowledge Base
      ↓
Loader
      ↓
Text Extraction
      ↓
Chunking
      ↓
Embedding
      ↓
Qdrant Storage
```

### Workflow

```text
Documents
      ↓
loader.py
      ↓
chunker.py
      ↓
embedder.py
      ↓
vectordb.py
```

---

# Document Chunking

Current chunking strategy:

```python
chunk_size = 1000
chunk_overlap = 150
```

Implementation:

```text
RecursiveCharacterTextSplitter
```

Benefits:

* Context Preservation
* Reduced Information Loss
* Better Retrieval Accuracy
* Efficient Embedding Generation

---

# Embedding Layer

Model:

```text
BAAI/bge-large-en-v1.5 (via OpenRouter API)
```

Features:

* 1024-Dimensional Embeddings
* Semantic Search
* API-Based (No Local GPU Required)
* Optimized for RAG Systems

---

# Vector Database

Database:

```text
Qdrant
```

Configuration:

```text
Collection:
yantra_knowledgebase

Distance Metric:
Cosine Similarity

Vector Size:
1024
```

Responsibilities:

* Store Embeddings
* Similarity Search
* Metadata Storage
* Retrieval Operations

---

# Metadata Structure

Every chunk stores metadata:

```json
{
  "robot": "Articulated_Robot",
  "source_file": "04_Sensors.docx",
  "file_type": ".docx",
  "category": "Sensors"
}
```

---

# Retrieval Pipeline

Current Retrieval Flow:

```text
User Query
      ↓
BGE-M3 Embedding
      ↓
Qdrant Search
      ↓
Top-K Results
      ↓
Return Chunks
```

Current Configuration:

```text
Top K = 5
```

---

# Chat System

Current interface:

```text
chat.py
```

Features:

* Interactive CLI
* Semantic Search
* Source Display
* Retrieval Score Display
* Knowledge Retrieval

---

# Current Source Code Structure

```text
src/

├── chat.py
├── ingest.py
├── loader.py
├── chunker.py
├── embedder.py
├── vectordb.py
├── retriever.py
├── test_rag.py
│
└── scraper/
```

---

# Agentic RAG Architecture (Planned)

Future architecture:

```text
User
 ↓
Retriever
 ↓
Qdrant Search

Enough Data?
│
├─ YES
│     ↓
│   Owl Alpha
│
└─ NO
      ↓
   DuckDuckGo Search
      ↓
   Web Scraper
      ↓
   Content Extraction
      ↓
   Chunking
      ↓
   Embedding
      ↓
   Qdrant
      ↓
   Owl Alpha
```

---

# Web Knowledge Acquisition (Planned)

Purpose:

Acquire missing knowledge when information does not exist inside the curated knowledge base.

Pipeline:

```text
Search
 ↓
Scrape
 ↓
Extract
 ↓
Chunk
 ↓
Embed
 ↓
Store
```

Future Technologies:

* DuckDuckGo
* Playwright
* BeautifulSoup
* Owl Alpha

---

# Image Intelligence (Planned)

Future Workflow:

```text
Robot Image
      ↓
Vision Model
      ↓
Image Captioning
      ↓
Chunking
      ↓
Embedding
      ↓
Qdrant
```

Goals:

* Visual Search
* Robot Identification
* Component Recognition

---

# CAD Intelligence (Planned)

Future Workflow:

```text
CAD File
      ↓
CAD Parser
      ↓
Component Extraction
      ↓
Component Chunks
      ↓
Embedding
      ↓
Qdrant
```

Goals:

* CAD Search
* Assembly Understanding
* Component Retrieval
* Design Intelligence

---

# Component Intelligence (Planned)

Future Architecture:

```text
Servo Motor
      ↓
connected_to
      ↓
Motor Driver
      ↓
powered_by
      ↓
Power Supply
```

Purpose:

* Component Mapping
* Connection Mapping
* Assembly Reasoning
* Engineering Intelligence

---

# API Layer (Planned)

Backend:

```text
FastAPI
```

Architecture:

```text
Frontend
      ↓
FastAPI
      ↓
Retriever
      ↓
Qdrant
      ↓
Owl Alpha
```

Planned Endpoints:

```text
POST /chat
POST /search
POST /upload
POST /ingest
GET  /robots
GET  /components
```

---

# Technology Stack

## Core

* Python

## RAG

* Qdrant
* OpenRouter Embedding API
* BAAI/bge-large-en-v1.5
* LangChain Text Splitters

## Documents

* PyPDF
* python-docx

## Planned

* FastAPI
* Owl Alpha
* Playwright
* Vision Models
* CAD Parsers

---

# Project Status

## Completed

* Knowledge Base Setup
* File Discovery
* PDF Processing
* DOCX Processing
* Metadata Generation
* Chunking Pipeline
* Embedding Pipeline
* Qdrant Integration
* Ingestion Pipeline
* Retrieval Pipeline
* CLI Chat System
* RAG Prototype

## In Progress

* Owl Alpha Integration
* FastAPI Backend
* Image Processing
* CAD Processing

## Future

* Component Graph
* Connection Graph
* Multi-Modal RAG
* Agentic Retrieval
* Web Knowledge Acquisition
* Engineering Intelligence
* Physical Product Operating System

---

# Long-Term Goal

Yantra aims to become an intelligent operating system for physical products capable of understanding:

* Technical Documentation
* CAD Assemblies
* Components
* Connections
* Manufacturing Processes
* Robotics Systems

and eventually assist users throughout the complete product development lifecycle.

```text
Idea
 ↓
Research
 ↓
Design
 ↓
Components
 ↓
CAD
 ↓
Manufacturing
 ↓
Deployment
```
Added 3 new Folders 
.







Hii