# JobSys — Modern Agentic Architectures Beyond RAG

> [!NOTE]
> RAG (Retrieval-Augmented Generation) was the dominant paradigm in 2023. By 2025-26, several architectures have superseded it for specific use cases — especially for document-heavy, multi-step reasoning tasks like yours.

---

## The Problem With Basic RAG for JobSys

Before exploring alternatives, here's why vanilla RAG has real limitations for this use case:

| RAG Limitation | Impact on JobSys |
|----------------|-----------------|
| Retrieval is passive (keyword/vector similarity) | Can miss semantically equivalent skills (e.g., "data wrangling" ≠ "ETL pipeline") without fine-tuning |
| No memory of past jobs/resumes | Can't learn from which resume style worked well for a "fintech ML Engineer" role |
| Single-pass generation | Produces a resume in one shot — no self-correction or ATS validation loop |
| No planning step | Doesn't reason about *what* to prioritize before generating |
| Chunk fragmentation | Splitting a resume into chunks loses coherence (skills + experience must be read together) |

---

## 🏆 Modern Architectures That Supersede RAG

### Architecture 1 — Long-Context "Whole Document" Strategy ⭐ Best for Resume Matching

**The insight:** Gemini 1.5 Pro has a **1,000,000 token context window**. GPT-4o has 128K. Instead of chunking and retrieving, you can just **load all base resumes + the JD directly into one LLM call** and let the model decide what's relevant.

```
JD (full text) + ALL base resumes + System prompt
        ↓
Gemini 1.5 Pro (1M context)
        ↓
"Resume_B is the best match. Here's why: ..."
```

**Why this beats RAG for your use case:**
- Your base resumes are small (typically 5-15KB each). Even 20 resumes = ~200KB — tiny vs 1M token limit.
- No chunking = no coherence loss. The model reads each resume holistically.
- No vector DB infrastructure needed for the matching step.
- The LLM can do richer reasoning (tone match, seniority match, industry alignment) that pure vector similarity misses.

> [!TIP]
> For JobSys specifically, this is the single highest-ROI change you can make. Eliminate the cosine similarity + vector matching complexity entirely. Just feed everything to Gemini 1.5 Pro.

**Cost estimate:** A Gemini 1.5 Pro call with 5 resumes + 1 JD (≈ 10,000 tokens) costs ~$0.0375. Highly affordable even at scale.

---

### Architecture 2 — Multi-Agent System (Specialist Agents) ⭐ Best for Document Generation

Instead of one monolithic LLM call that does everything, assign **specialized agents** to each sub-task. Each agent has its own prompt, tools, and responsibility.

```
                    ┌─────────────────────────┐
                    │   ORCHESTRATOR AGENT     │
                    │   (LangGraph / CrewAI)   │
                    └──────────┬──────────────┘
                               │ delegates to
          ┌────────────────────┼────────────────────┐
          ▼                    ▼                    ▼
  ┌──────────────┐   ┌──────────────────┐   ┌─────────────────┐
  │ JD ANALYST   │   │ RESUME WRITER    │   │ COVER LETTER    │
  │ Agent        │   │ Agent            │   │ Agent           │
  │              │   │                  │   │                 │
  │ Extracts:    │   │ Reads JD brief   │   │ Reads JD brief  │
  │ - Skills     │   │ + base resume    │   │ + company info  │
  │ - Tone       │   │ → draft resume   │   │ → personalized  │
  │ - Seniority  │   │                  │   │ cover letter    │
  │ - Culture    │   └──────┬───────────┘   └─────────────────┘
  └──────┬───────┘          │
         │                  ▼
         │         ┌──────────────────┐
         └────────►│ ATS CRITIC       │
                   │ Agent            │
                   │                  │
                   │ Scores the draft │
                   │ against JD.      │
                   │ Returns pass/    │
                   │ fail + feedback  │
                   └──────┬───────────┘
                          │ if fail → send back to Writer (max 2 loops)
                          │ if pass → finalize DOCX
                          ▼
                   ┌──────────────────┐
                   │  DOCX GENERATOR  │
                   │  Tool            │
                   └──────────────────┘
```

**Why Multi-Agent beats single-LLM:**
- Each agent has a **focused, narrower prompt** → better accuracy
- ATS Critic agent provides **structured feedback** (not just "improve it")
- Resume Writer and Cover Letter run **in parallel** (no sequential wait)
- Easy to **replace or upgrade** individual agents independently

---

### Architecture 3 — Memory-Augmented Agents ⭐ Long-term Learning

This is the most powerful long-term capability: **the system remembers what worked**.

```
                    ┌──────────────────────────────────────┐
                    │            MEMORY STORE              │
                    │ (DynamoDB + Embeddings + Pinecone)   │
                    │                                      │
                    │  Episodic Memory:                    │
                    │  - "For 'Senior ML Engineer' jobs    │
                    │     at fintech companies, Resume_A   │
                    │     scored 92% and got an interview" │
                    │                                      │
                    │  Semantic Memory:                    │
                    │  - Skills taxonomy                   │
                    │  - Industry keyword mappings         │
                    │                                      │
                    │  Procedural Memory:                  │
                    │  - Best prompt templates per role    │
                    └──────────────────┬───────────────────┘
                                       │ retrieved before each generation
                                       ▼
                    ┌──────────────────────────────────────┐
                    │       GENERATION AGENTS              │
                    │  (informed by past successes)        │
                    └──────────────────────────────────────┘
```

**Three types of memory to implement:**

| Memory Type | What to Store | Where to Store |
|-------------|--------------|----------------|
| **Episodic** | "Resume_A used for role X on date Y, got invited to interview" | DynamoDB (already have it) |
| **Semantic** | Skills taxonomy, industry terms, keyword equivalences | Pinecone vector store |
| **Procedural** | Which writing styles/tones worked for which company types | SSM Parameter Store or DynamoDB |

**Practical first step:** Add a `feedback` field to your DynamoDB job record. When you update the status to `interview-scheduled` or `rejected`, the system learns. Over time, the Resume Writer agent queries: *"For similar jobs in the past, what approach scored highest?"*

---

### Architecture 4 — Self-RAG & Corrective RAG (CRAG)

These are upgrades **within** the RAG paradigm. Relevant if you keep a vector store.

**Self-RAG** asks the LLM to decide: *"Do I even need to retrieve anything, or do I already know enough?"*

```
Query → LLM Decision Gate:
  ├─ "I need retrieval" → Retrieve chunks → Generate with context
  └─ "I don't need retrieval" → Generate directly (faster, cheaper)
```

**CRAG (Corrective RAG)** evaluates retrieved chunks before using them:

```
Query → Retrieve chunks → LLM Evaluates chunks:
  ├─ "Relevant" → Use them
  ├─ "Partially relevant" → Filter + web search to fill gaps
  └─ "Irrelevant" → Discard, use web search only
```

**For JobSys:** CRAG is useful in Phase 1 (job ingestion) if you scrape job pages and the content is noisy or incomplete — the agent can self-correct by searching for more company/role context.

---

### Architecture 5 — GraphRAG (Microsoft) for Knowledge Relationships

**GraphRAG** builds a **knowledge graph** over your documents rather than just embedding chunks. It understands *relationships*, not just similarity.

```
Resume chunks + JD chunks
         ↓
   Knowledge Graph:
   [Python] ─── required_by ──► [ML Engineer Role]
   [PyTorch] ─── subset_of ──► [Python ML Skills]
   [Resume_A] ── contains ──► [PyTorch, 5 years exp]
   [Resume_A] ── matches ──► [ML Engineer Role] (score: 0.93)
```

**For JobSys specifically:** GraphRAG would let you answer queries like:
- *"Which of my resumes is best for a role requiring Kubernetes + MLOps?"* (multi-hop graph traversal)
- *"What skills am I missing for this role?"* (gap analysis via graph)
- *"Which companies have I applied to that are similar to this one?"*

**Toolstack:** Microsoft GraphRAG (open source), Neo4j for graph storage, or Amazon Neptune.

> [!WARNING]
> GraphRAG has higher infrastructure complexity. Only worth it when you have 10+ resumes and hundreds of jobs. **Not recommended for the current scale** — but excellent for a v2 roadmap.

---

## 🏗️ Recommended Architecture for JobSys (2026 Best Practice)

Combining the above, here is the **optimal hybrid architecture** ranked by implementation priority:

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1: INGESTION                                             │
│  Firecrawl (web) / LlamaParse (PDF) → Structured Job Record     │
│  → DynamoDB + S3                                                │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│  LAYER 2: MATCHING  (Long-Context Strategy)                     │
│  ALL base resumes + JD → Gemini 1.5 Pro (1M ctx)               │
│  → Best resume selected + structured match analysis             │
│  NO vector DB needed at this layer                              │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│  LAYER 3: GENERATION  (Multi-Agent + Reflection)                │
│                                                                 │
│  LangGraph Workflow:                                            │
│  [JD Analyst] ──► [Resume Writer] ──► [ATS Critic]             │
│                         ▲                    │                  │
│                         └──── revise ────────┘ (max 2 loops)   │
│                                              │ pass             │
│                              [Cover Letter Writer] (parallel)   │
│                                              │                  │
│                              [python-docx Generator]            │
│                                              │                  │
│                                           → S3                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│  LAYER 4: MEMORY  (Learn from outcomes)                         │
│  DynamoDB feedback field → embeddings → Pinecone                │
│  Future calls informed by past successful resume styles         │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│  LAYER 5: API + DASHBOARD                                       │
│  API Gateway → Lambda → React (keep current)                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Toolstack Recommendation (2026)

### Tier 1 — Core (Essential now)

| Component | Tool | Reason |
|-----------|------|--------|
| LLM (Long-context) | **Gemini 1.5 Pro / 2.0 Flash** | 1M token ctx, excellent at document tasks, already in stack |
| Structured Output | **Pydantic + `instructor` lib** | Force LLM to return type-safe JSON — no more parsing headaches |
| Agent Framework | **LangGraph** | Best for stateful multi-step agents with loops, branching |
| PDF/DOCX Parsing | **LlamaParse** | Best-in-class multimodal document parsing, handles tables/layouts |
| Web Scraping | **Firecrawl** | LLM-native scraping, returns clean markdown |

### Tier 2 — Enhanced Capabilities (Add in v2)

| Component | Tool | Reason |
|-----------|------|--------|
| Memory Store | **Pinecone Serverless** | Managed, free tier, fast vector search for semantic memory |
| Agent Monitoring | **LangSmith** | Trace every LLM call, debug agent failures, measure latency |
| Multi-agent | **CrewAI** | Higher-level abstraction for multi-agent role definitions (simpler than raw LangGraph) |
| Evaluation | **RAGAS** | Evaluate resume quality automatically (faithfulness, relevance) |

### Tier 3 — Future Scale

| Component | Tool | Reason |
|-----------|------|--------|
| Knowledge Graph | **Microsoft GraphRAG + Neo4j** | Relationship-aware retrieval at scale |
| Fine-tuning | **OpenAI fine-tuning / LoRA** | Domain-specific models for ATS scoring |
| Workflow Orchestration | **AWS Step Functions** | Replace Lambda chains for production-grade agent state |

---

## 📦 Key Libraries to Add to `requirements.txt`

```txt
# Core Agentic Stack
langgraph>=0.2.0
langchain>=0.3.0
langchain-google-genai>=2.0.0
langchain-openai>=0.2.0

# Structured LLM Output (game changer)
instructor>=1.6.0
pydantic>=2.0.0

# Document Parsing
llama-parse>=0.5.0      # or docx2txt for simple cases

# Web Scraping (optional upgrade)
firecrawl-py>=1.0.0

# Evaluation & Monitoring
langsmith>=0.1.0
```

---

## 💡 The Single Most Impactful Change You Can Make Right Now

> **Replace your `resume_matcher` Lambda with a single Gemini 1.5 Pro call that receives all base resumes + the JD in one prompt, with structured output via `instructor` + Pydantic.**

This eliminates:
- Cosine similarity code
- Chunk management
- Vector DB (for matching — you don't need it)
- Multiple sequential LLM calls

And gives you:
- Better semantic matching
- Holistic resume comparison (the model sees the whole resume)
- Structured, type-safe match results
- Explanations for *why* a resume was chosen

Sample output schema:
```python
class ResumeMatchResult(BaseModel):
    best_resume_id: str
    match_score: float  # 0.0 - 1.0
    matched_skills: list[str]
    missing_skills: list[str]
    reasoning: str
    recommended_sections_to_expand: list[str]
```
