# PROJECT: HR AI Assistant (RAG + Evaluation)

## OBJECTIVE

Build a minimal but complete AI system that allows employees to query internal HR documentation and receive grounded, structured answers.

The system must include:

* RAG (retrieval-augmented generation)
* Guardrails
* Evaluation layer (grading + groundedness)

This must be a structured, modular system ready for deployment.

---

## SCOPE (STRICT)

INCLUDED:

* Chat interface (simple)
* HR document ingestion (local files)
* Embeddings + vector search (Neon)
* LLM response generation (Gemini)
* Guardrails (basic)
* Evaluation (grading + groundedness)

EXCLUDED:

* Authentication
* Role-based access control
* Multi-agent systems
* Graph databases
* Complex frontend

---

## USER STORY

An employee asks questions about HR processes (vacations, evaluations, benefits).

The system:

1. retrieves relevant documents
2. generates a response using context
3. validates response (guardrails)
4. evaluates quality (grading + groundedness)
5. returns answer + metadata

---

## SYSTEM BEHAVIOR RULES

* NEVER invent information
* If context is insufficient → respond:
  "No encontré información suficiente en la base de conocimiento"
* Always respond in structured format
* Prefer step-by-step answers
* Always reference source documents
* If question requires human intervention → suggest contact

---

## TECH STACK (FIXED)

* Python
* FastAPI (backend)
* Streamlit (UI)
* Neon (PostgreSQL + pgvector)
* HuggingFace embeddings (sentence-transformers)
* Gemini 1.5 Flash (LLM - Default for speed/free tier)

DO NOT CHANGE STACK.

---

## DATA STRATEGY (NEW)

### Chunking Strategy
* **Method:** Recursive Character Text Splitting.
* **Separators:** `["\n\n", "\n", ".", " ", ""]` (Prioritize paragraphs and headers).
* **Chunk Size:** ~500-800 characters.
* **Overlap:** 10-15% (To maintain context between chunks).
* **Goal:** Avoid breaking semantic units (like a specific HR rule or benefit).

---

## ARCHITECTURE

Pipeline:

User Input
→ Embedding (HuggingFace)
→ Vector Search (Neon pgvector)
→ Context Assembly
→ LLM Generation (Gemini)
→ Guardrails Validation
→ Evaluation Layer (Auditor Mode)
→ Final Response (JSON)

---

## DATABASE (STRICT)

Use Neon with pgvector.

Table: documents

Fields:

* id (uuid)
* content (text)
* embedding (vector)
* source (text)
* chunk_id (int)

DO NOT use:

* FAISS
* local vector storage
* graph databases

---

## DATA

Documents are stored in:
data/raw/hr_docs/

They must be:

* plain text
* 5–10 documents max

---

## REQUIRED MODULES

1. RAG pipeline
2. Embedding handler
3. Neon retriever
4. Gemini LLM interface
5. Guardrails
6. Evaluation (Grading & Groundedness)

---

## OUTPUT FORMAT (STRICT)

Return JSON (via Pydantic):

{
"answer": "...",
"sources": ["doc_name"],
"grading": {
"relevance": int,
"clarity": int,
"usefulness": int
},
"groundedness": true/false
}

---

## EVALUATION LOGIC

### Grading:
* relevance (1–5)
* clarity (1–5)
* usefulness (1–5)

### Groundedness (Auditor Mode):
* **Model:** Gemini 1.5 Flash (Temp 0).
* **Role:** Strict Auditor.
* **Logic:** Verify if EVERY claim in the answer is explicitly supported by the retrieved context. Return `false` if any hallucination is detected.

---

## DEVELOPMENT STRATEGY

Build in this order:

1. Data ingestion + Chunking
2. Embeddings + Neon storage
3. Retrieval (vector search)
4. LLM response (Gemini)
5. Guardrails
6. Evaluation (The "Auditor")
7. API (FastAPI)
8. UI (Streamlit)

Do NOT skip steps.

---

## CONSTRAINTS

* Keep code modular
* Avoid overengineering
* Prefer clarity over optimization
* No unnecessary abstractions
* No unused features

---

## SUCCESS CRITERIA

The system is complete when:

* it answers HR questions correctly
* it refuses when context is missing
* it provides evaluation scores
* it is deployable

---

## IMPORTANT

Do NOT:

* add features outside scope
* redesign architecture
* introduce complexity

Only implement what is defined here.
