# JobSys — Architecture Analysis & Recommendations

---

## 1. 📄 Where Are the Business & Product Requirements?

Your project has **three layered requirement documents**, each serving a slightly different purpose:

| File | Role | Best For |
|------|------|----------|
| [`Requirement Doc.pdf` / `.docx`](file:///c:/Projects/JobSys/Requirement%20Doc.pdf) | **Original Business Requirements** — the raw, unstructured first-pass written description of what the system should do. Contains open questions (e.g. "How do we know a job is already there in database?"). | Stakeholder/origin reference |
| [`requirements_text.txt`](file:///c:/Projects/JobSys/requirements_text.txt) | **Intermediate transcription** of the .docx — plain text version of the original document. Same open questions remain. | LLM ingestion / raw input |
| [`requirements.md`](file:///c:/Projects/JobSys/requirements.md) | ✅ **The authoritative Product Requirements Document (PRD)** — structured, phased, with a tech decision table and status flow. This is the refined engineering-ready version. | Day-to-day development reference |
| [`README.md`](file:///c:/Projects/JobSys/README.md) | **Technical Overview / Quick-start Guide** — not a requirements doc, but gives a compact system architecture diagram. | Onboarding new developers |
| [`DOCS.md`](file:///c:/Projects/JobSys/DOCS.md) | **Documentation index** — links to all docs. | Navigation |

> [!IMPORTANT]
> **`requirements.md`** is your canonical PRD. It is the most complete, structured, and engineering-ready document. The `.docx`/`.txt` files are the original business input that `requirements.md` was derived from.

---

## 2. 🤔 Is This Project RAG Architecture?

**Short answer: Not currently — but it's RAG-adjacent, and it _should_ be RAG-based.**

### What You Currently Have

The current architecture is a **sequential LLM-augmented pipeline**:

```
EventBridge (Cron) → Job Scanner → Resume Matcher → Document Generator
                                        ↑
                              LLM called with full text
                              (JD + Resume as prompt context)
```

The LLM (`Gemini`, `OpenAI`, or `HuggingFace`) is called **with full text passed directly in the prompt** — this is **prompt stuffing**, not RAG. There is no:
- Vector database or embedding store
- Semantic retrieval step
- Chunked document indexing

### Why It's RAG-Adjacent

The core idea — *"retrieve the most relevant base resume for a job description"* — **is exactly what RAG was designed for**. You are manually approximating RAG with:
- Keyword extraction + cosine similarity (a primitive retrieval step)
- LLM-based semantic matching (the generation step)

This means you've **built a poor-man's RAG** by hand, without the infrastructure benefits (vector search, chunking, re-ranking, etc.).

---

## 3. 🏗️ Recommended Architecture — RAG + Agentic Workflow

This is the architecture that would make JobSys significantly more powerful, accurate, and scalable.

### High-Level Agentic Flow

```
┌─────────────────────────────────────────────────────────────┐
│                      ORCHESTRATOR AGENT                     │
│                   (LangGraph / LangChain)                   │
└───────────────────────┬─────────────────────────────────────┘
                        │ routes to specialized tools/agents
          ┌─────────────┼──────────────────┐
          ▼             ▼                  ▼
  [Job Scraper]  [Resume Matcher]  [Document Generator]
   Tool/Agent     Tool/Agent        Tool/Agent
          │             │                  │
          ▼             ▼                  ▼
    DynamoDB +    Vector Store +      LLM (Gemini)
    S3 (JDs)     Embeddings          + DOCX Writer
                 (Pinecone/pgvector)
```

### Phase-by-Phase Recommendations

#### Phase 1 & 2 — Job Ingestion (Keep, improve scraping)
- **Current approach is fine** — DynamoDB + S3 storage works well.
- Add: Use an LLM to **extract structured fields** (title, company, skills required) from raw HTML/PDF job postings instead of regex parsing.
- Tool: `Firecrawl` or `BeautifulSoup` → LLM extraction → DynamoDB.

#### Phase 3 — Resume Matching → **Replace with RAG**

> [!TIP]
> This is the highest-value improvement you can make.

**Current (Primitive):**
1. Load all base resumes as full text
2. Score each against JD using cosine similarity manually
3. Pass best resume + JD to LLM

**RAG-Based Replacement:**
1. **Chunk** each base resume into semantic sections (Skills, Experience, Education, Projects)
2. **Embed** each chunk using an embedding model (e.g., `text-embedding-3-small` from OpenAI or `BAAI/bge-small-en` from HuggingFace — free)
3. **Store** embeddings in a vector DB (Pinecone Serverless free tier, or `pgvector` on RDS)
4. At match time: **embed the JD** and run a **similarity search** to retrieve the top-K most relevant resume sections
5. Pass **only the retrieved chunks** (not the full resume) to the LLM for generation

**Why this is better:**
- Handles long resumes without exceeding LLM context windows
- Finds semantically similar content even if keywords differ (e.g., "ML Engineer" ↔ "Machine Learning Developer")
- Much faster than loading all resumes for each job

#### Phase 4 — Document Generation → **Add Agentic Loop**

Replace a single LLM call with a **multi-step agent**:

```
Step 1: Analyze JD → extract required skills, tone, industry keywords
Step 2: Retrieve relevant resume sections (RAG)
Step 3: Draft optimized resume sections
Step 4: Self-critique: "Does this resume pass an ATS scan for the JD?"
Step 5: Revise if needed (reflection loop, max 2 iterations)
Step 6: Generate final DOCX
```

**Tools:** LangGraph (for stateful multi-step agents), LangChain document loaders.

---

## 4. 🛠️ Recommended Toolstack

### Core Orchestration
| Component | Recommended Tool | Why |
|-----------|-----------------|-----|
| Agent Framework | **LangGraph** | Best for stateful, multi-step agents with conditional edges; great for your pipeline |
| Orchestration Glue | **LangChain** | Document loaders, LLM wrappers, tool definitions |
| LLM (Primary) | **Google Gemini 1.5 Pro** | Long context window (1M tokens), great for document tasks, already in your stack |
| LLM (Fallback) | **OpenAI GPT-4o-mini** | Cost-effective, fast, excellent at structured output |
| Embeddings | **OpenAI `text-embedding-3-small`** | Cheap, fast, high quality; or use HuggingFace `BAAI/bge-small-en` for free |

### RAG Infrastructure
| Component | Recommended Tool | Why |
|-----------|-----------------|-----|
| Vector DB | **Pinecone Serverless** | Zero infra, generous free tier, AWS integrable |
| Alternative Vector DB | **pgvector on RDS** | If you want everything in AWS; more complex but unified |
| Document Parsing | **LangChain `Docx2txtLoader`** | Already parse DOCX resumes |
| Web Scraping | **Firecrawl** or **Playwright** | Firecrawl is LLM-native; Playwright for complex JS sites |

### AWS Infrastructure (Keep What You Have + Add)
| Component | Current | Recommended Addition |
|-----------|---------|---------------------|
| Compute | Lambda | Keep for API/triggers; add **Step Functions** for agent orchestration |
| Storage | S3 + DynamoDB | Keep |
| Scheduler | EventBridge | Keep |
| Secrets | SSM + Secrets Manager | Keep |
| Vector Search | ❌ None | Add **Pinecone** (external) or **OpenSearch Serverless** (AWS-native) |

### Frontend (Keep Current)
| Component | Current | Status |
|-----------|---------|--------|
| Framework | React + Vite | ✅ Good |
| Styling | Vanilla CSS | ✅ Good |
| Animations | Framer Motion | ✅ Good |

---

## 5. 📐 Revised Architecture Diagram

```
┌──────────────────────────────────────────────────────────┐
│  INGESTION LAYER                                         │
│  Firecrawl/Playwright → LLM Extractor → DynamoDB + S3   │
└──────────────────────────────┬───────────────────────────┘
                               │ new job registered
┌──────────────────────────────▼───────────────────────────┐
│  RAG INDEXING (one-time / on resume update)              │
│  Base Resumes → Chunk → Embed → Pinecone Vector Store    │
└──────────────────────────────┬───────────────────────────┘
                               │ embeddings ready
┌──────────────────────────────▼───────────────────────────┐
│  AGENTIC DOCUMENT PIPELINE  (LangGraph)                  │
│                                                          │
│  [Analyze JD] → [RAG Retrieval] → [Draft Resume]        │
│       ↑               ↓                   ↓             │
│  [Revise]  ←── [Self-Critique] ←── [ATS Score Check]    │
│                                           ↓             │
│                              [Generate DOCX] → S3       │
└──────────────────────────────┬───────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────┐
│  API LAYER  (API Gateway → Lambda → DynamoDB)            │
│  React Dashboard ← REST API                             │
└──────────────────────────────────────────────────────────┘
```

---

## 6. 🚀 Suggested Migration Path

Since you already have a working pipeline, migrate incrementally:

1. **Phase A** *(Low effort, high impact)*: Add embedding + Pinecone to the resume matching step. Replace cosine similarity with vector search. Keep everything else the same.
2. **Phase B** *(Medium effort)*: Wrap document generator in a LangGraph agent with a self-critique / reflection loop.
3. **Phase C** *(Higher effort)*: Replace Lambda-chain with **AWS Step Functions** to manage the agentic state machine properly (retries, branching, human-in-the-loop pauses).
4. **Phase D** *(Future)*: Add a **human-in-the-loop** node where you can review and approve the optimized resume before final DOCX generation via the React dashboard.

> [!NOTE]
> Your existing multi-provider LLM abstraction (`llm_client.py`, `llm_provider.py`, `providers/`) is excellent infrastructure. LangChain integrates with it or you can wrap it as a custom LangChain `BaseChatModel`.
