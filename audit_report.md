# AI SYSTEM AUDIT REPORT

## 1. Executive Summary
This project is an HR AI Assistant built on a RAG (Retrieval-Augmented Generation) architecture. It aims to answer employee queries strictly based on ingested corporate documents. The system relies on a stack featuring FastAPI, Streamlit, Neon (pgvector), HuggingFace embeddings (`all-MiniLM-L6-v2`), and an LLM engine (Groq/Gemini). It includes a basic guardrail layer and a custom LLM-as-a-judge evaluation suite for grading and groundedness.

**What it does well:** 
The system establishes a clean, understandable pipeline from document ingestion to UI. The separation of concerns between embedding, retrieval, LLM generation, and evaluation is structurally sound. The recent shift to Markdown-aware document ingestion and the explicit instructions against cross-pollinating constraints across hierarchical sections represent a strong architectural defense against hallucinations caused by text proximity. The query-rewriting mechanism (Mini-cerebro) is a smart touch to decouple conversational nuances from semantic search vectors.

**Main risks:**
The system is brittle under load and edge cases. Error handling is rudimentary, often masking critical failures by falling back to default behaviors (e.g., returning "PASS" on guardrail failure or default grading scores if the evaluation fails). The retrieval threshold strategy is hardcoded and fragile, risking empty contexts for slightly out-of-distribution wording. The evaluation suite adds significant latency by relying on sequential LLM calls in the critical path of the user request.

---

## 2. Architecture Audit
**RAG Pipeline Correctness:** The pipeline generally follows best practices: Rewriting -> Guardrails -> Retrieval -> Generation -> Evaluation. However, the evaluation layer runs synchronously *before* returning the response, creating a severe UX bottleneck. 

**Separation of Concerns:** Good. Modules like `core/embeddings.py`, `core/llm.py`, and `evaluation/eval_runner.py` are distinct. The routing layer is somewhat bypassed by the UI directly calling logic (as seen in `ui.py`), which breaks the clean API-client contract.

**Missing Components:** 
- **Caching:** No semantic caching for frequent queries (e.g., "vacaciones").
- **Asynchronous Execution:** The evaluation and guardrail LLM calls are synchronous, compounding latency.
- **Observability:** `print()` statements are used instead of a robust logging framework. Tracing LLM calls is impossible.

**Overengineering vs Underengineering:** 
- *Overengineered:* Running LLM-as-a-judge (Groundedness + Grading) inline for *every single user query* in a production environment is computationally expensive and slow. This should be an asynchronous background task or limited to a sample.
- *Underengineered:* Database connection pooling is absent; `psycopg2.connect()` is called per request in `get_context`, which will collapse under concurrent load.

---

## 3. Retrieval System Analysis
**Chunking Strategy Evaluation:** The strategy (RecursiveCharacterTextSplitter) combined with the recent Markdown structure injection during PDF extraction is solid. However, relying purely on text splitters without semantic boundaries can still occasionally truncate context.

**Embedding Model Usage:** `sentence-transformers/all-MiniLM-L6-v2` is fast and lightweight, suitable for English but suboptimal for Spanish HR documents. A multilingual model (e.g., `paraphrase-multilingual-MiniLM-L12-v2`) would significantly improve retrieval accuracy for queries in Spanish.

**Vector Search Correctness:** Using Neon with pgvector (`<=>` cosine distance) is correct. 

**Top-k Strategy Risks:** The system uses `LIMIT 5` and a hardcoded threshold of `0.45`.
- *Risk:* Cosine distance values from `all-MiniLM-L6-v2` can cluster tightly. A hard threshold of 0.45 is arbitrary. If documents are slightly different semantically, the threshold blocks them, returning empty results instead of falling back to best-effort matches. 
- *Risk:* `LIMIT 5` on 1500-character chunks injects up to 7500 characters into the prompt. This is fine for Gemini 1.5 Flash, but can drown out relevance in noise.

**Failure Modes:** Database connection timeouts are not gracefully handled; they crash the request.

---

## 4. LLM Integration Audit
**Prompt Design Quality:** The prompts are explicit and focus correctly on structure and constraints. The recent shift to "Reasoning over Rules" (instructing the model on *how* to read Markdown hierarchies rather than hardcoding HR rules) is a highly professional approach.

**Context Injection Correctness:** Injecting context with source metadata is handled well. Injecting the history is done via string formatting rather than native message arrays (system, user, assistant), which is prone to formatting leakage or prompt injection attacks if user input is not sanitized.

**Hallucination Risk:** Reduced significantly by the structural prompt and groundedness checks. However, Groq/Llama models can sometimes struggle with strict adherence to "don't know" instructions compared to larger models like GPT-4 or Claude 3.5 Sonnet.

**Response Consistency:** Good, enforced by the prompt instructions.

---

## 5. Groundedness Evaluation
**Is grounding actually verified?** It is evaluated by an LLM prompt (`groundedness_prompt.txt`), not deterministically. 

**Is it superficial?** Yes. LLM-as-a-judge is subjective. While recently refined to ignore courtesy phrases, relying on an LLM to police another LLM on the exact same context often results in the judge being swayed by the same ambiguities that confused the generator.

**Failure Cases:** If the evaluation LLM API fails or times out, the code (`eval_runner.py`) silently catches the exception and prints an error, but the main flow forces a default value (`is_grounded = True` in `main.py`). This is a critical security failure: failing open on an audit check.

---

## 6. Grading System Evaluation
**Are metrics meaningful?** Relevance, clarity, and usefulness are standard, but without a golden dataset (ground truth), these scores are arbitrary self-assessments by the LLM. 

**Are they reliable?** No. LLMs suffer from positive bias when grading themselves. 

**Are they actionable?** Barely. A score of 4/5 in "usefulness" doesn't tell an engineer what to fix in the retrieval pipeline.

---

## 7. Error Handling & Edge Cases
- **No context:** Handled gracefully via the `get_context` check, returning a canned refusal response.
- **Ambiguous queries:** The `rewrite_query` function attempts to resolve ambiguity using chat history. If it fails, it returns the original query. Acceptable fallback.
- **Irrelevant queries:** Blocked by `GuardrailManager`. However, if the LLM call in the guardrail fails, it returns `True` (fails open), allowing irrelevant queries through.
- **Conflicting information:** Not explicitly handled in retrieval. The generation LLM is left to resolve conflicts, which is risky.

---

## 8. UX & Product Logic
**Clarity of System Behavior:** High. The UI explicitly states what documents are indexed and provides quick-start questions.
**Output Structure Quality:** High. The prompt forces structured, readable outputs (lists, bold text) and explicit source citations.
**User Guidance:** The side-panel showing real-time audit scores is a great tool for building trust with recruiters, demystifying the "black box" of AI.

---

## 9. Engineering Quality
**Code Structure:** Logical file separation (`core/`, `app/`, `config/`). 
**Modularity:** High. Changing the LLM provider from Gemini to Groq is seamless due to the `LLMManager` abstraction.
**Maintainability:** Medium. Using raw string manipulation for chat histories and prompt formatting is harder to maintain than using frameworks like LangChain's prompt templates or native API message structures.
**Dependency Management:** The reliance on `asyncio.set_event_loop()` inside a Streamlit render loop (`ui.py`) is a major anti-pattern and a sign of forcing asynchronous backend code into a synchronous frontend framework.

---

## 10. Critical Issues (MUST FIX)

1. **Synchronous DB Connections per Request**
   - *Why it matters:* `psycopg2.connect()` in `get_context` creates a new connection for every query. This will exhaust Neon's connection limits instantly under load.
   - *Fix:* Implement a connection pool (e.g., `psycopg2.pool.SimpleConnectionPool` or an async equivalent like `asyncpg`).

2. **Failing Open on Security/Audit Checks**
   - *Why it matters:* If the Guardrail API fails, it returns `True`. If Evaluation fails, it defaults to `is_grounded=True`. This creates a false sense of security.
   - *Fix:* Fail closed. If the guardrail errors out, return a standard "System unavailable" error.

3. **Async Event Loop Hijacking in Streamlit**
   - *Why it matters:* `loop.run_until_complete(ask_hr(request_data))` inside Streamlit is dangerous and unstable.
   - *Fix:* Streamlit should make an HTTP request to the FastAPI backend via `requests` or `httpx`, completely decoupling the UI from the backend logic.

---

## 11. Weaknesses (SHOULD IMPROVE)

- **Inline Evaluation Latency:** Running Groundedness and Grading inline blocks the UI response. Move evaluation to a background task (`BackgroundTasks` in FastAPI) and store results in a database.
- **Embedding Model Language:** Switch to a multilingual embedding model for Spanish documents.
- **Prompt Injection Vulnerability:** Raw string injection (`{query}`) in `llm.call` is risky if users input prompt-override commands.

---

## 12. Strengths
- **Markdown Ingestion Strategy:** Transforming unstructured PDFs into Markdown for hierarchical context injection is a highly sophisticated approach to solving proximity hallucinations.
- **Memory Management:** The "Mini-cerebro" for query rewriting and the explicit "User Profile Memory" instruction show an advanced understanding of conversational UX.
- **Agnostic LLM Architecture:** The factory-like `LLMManager` handling both Groq and Gemini demonstrates mature architectural foresight.

---

## 13. Final Technical Assessment
- **Level:** Solid / Transitioning to Strong.
- **Assessment:** The project demonstrates strong conceptual understanding of RAG architectures, prompt engineering, and UX. However, it lacks production-grade backend engineering rigor (connection pooling, async boundary enforcement, fail-closed security). 
- **Role Qualification:** Qualifies for a Mid-to-Senior AI Engineer role or an AI Solutions Architect role, pending demonstration of backend hardening skills.

---

## 14. Strategic Recommendations
To stand out professionally:
1. **Implement RAG Metrics (RAGAS):** Replace arbitrary LLM grading with established metrics like Context Precision and Context Recall.
2. **Add Semantic Caching:** Integrate Redis or GPTCache to serve repeated queries (e.g., "vacaciones") without hitting the LLM.
3. **Decouple the Architecture:** Deploy FastAPI and Streamlit as separate services in Docker containers. This proves you understand modern deployment topologies, not just script writing.
