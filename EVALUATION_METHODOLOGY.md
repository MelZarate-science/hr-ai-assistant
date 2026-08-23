# Metodología de evaluación y calibración

Este documento define cómo se calibra y mide el pipeline, separado en las dos
capas que tienen naturaleza distinta y se calibran en orden: primero la capa
dura (determinística, medible con métricas de recuperación de información),
después la capa blanda (generativa, medida con LLM-como-juez). Corresponde al
"RAG Triad" (Context Relevance / Groundedness / Answer Relevance), adaptado a
este proyecto.

Cada corrida de cualquiera de las dos capas se registra en
[EXPERIMENTS.md](EXPERIMENTS.md), sea cual sea el resultado (incluidas las
regresiones). Ese archivo es la bitácora; este documento es el procedimiento.

---

## Capa 1 — Retrieval (chunking + retrieval + ranking)

**Qué mide**: Context Relevance — si lo que trae el pipeline hasta el momento
de generar es lo correcto, independientemente de qué tan bien lo redacte
después el LLM.

**Componentes que pertenecen a esta capa**:
- `scripts/ingest_data.py` (chunking: `CHUNK_SIZE`, `CHUNK_OVERLAP`, split por headers)
- `core/embeddings.py` (modelo de embeddings)
- `core/retriever.py` (búsqueda vectorial, `top_k`, umbral de similitud)
- `core/reranker.py` (el reranker usa un LLM, pero su *función* es de recuperación:
  decide qué contexto llega a generación, no genera la respuesta final. Por eso
  vive en esta capa aunque técnicamente llame a Gemini)

**Métricas**: Recall@K, Precision@K, MRR — calculados contra el campo
`chunks_relevantes` de cada pregunta en `evaluation/golden_set.jsonl`.

**Cuándo correr esta capa (y solo esta, sin gastar en generación completa)**:
- Cambios a `CHUNK_SIZE` / `CHUNK_OVERLAP` en `config/settings.py`
- Cambios al umbral de similitud o `top_k` en `core/retriever.py`
- Cambios al prompt o `top_n` del reranker en `core/reranker.py`
- Cambios al modelo de embeddings

**Cómo correr**: `python evaluation/run_retrieval_eval.py`
(no llama al LLM de generación ni a la auditoría — solo embeddings + búsqueda +
reranker. Mucho más barato y rápido que la corrida end-to-end.)

**Prerequisito ya resuelto**: el retriever no exponía `chunk_id`, lo que
impedía medir recall a nivel de chunk (solo se podía medir a nivel de
documento-fuente, como se hizo en la corrida del 2026-08-22). El script de
retrieval-only lo resuelve con una consulta propia que expone `chunk_id`, sin
tocar el contrato de `core/retriever.py` que usa producción.

---

## Capa 2 — Generación e interpretación (LLM + controles)

**Qué mide**: Groundedness (¿la respuesta está respaldada por el contexto?) y
Answer Relevance (¿la respuesta contesta lo que se preguntó?), más el
comportamiento de los controles de seguridad/negocio.

**Componentes que pertenecen a esta capa**:
- `core/llm.py` (rewriting, generación)
- `core/guardrails.py` (dentro/fuera de ámbito)
- `evaluation/eval_runner.py` (groundedness + grading, LLM-juez)
- `core/repair.py` (reparación de respuestas no fundamentadas)
- Los prompts en `prompts/` (`system_prompt`, `groundedness_prompt`,
  `repair_prompt`, `guardrail_prompt`, `rewriter_prompt`)

**Cuándo correr esta capa**: cualquier cambio a los prompts o lógica de esta
lista, **y también** después de cualquier cambio a la Capa 1 — un cambio de
reranker puede arreglar la Capa 1 y aun así cambiar el comportamiento final
visible (como pasó el 2026-08-22: el fix del reranker solo se confirmó como
seguro después de correr las 35 preguntas completas, no con el subset).

**Cómo correr**: `python evaluation/run_golden_eval.py` (end-to-end, el que
ya existe). Para iterar rápido sobre pocos casos: `--ids ID1,ID2,...`. Para
confirmar que no hay regresión general antes de dar un cambio por bueno,
correr las 35 completas al menos una vez.

---

## Procedimiento de calibración (orden)

1. Cambiaste algo de la Capa 1 → corré `run_retrieval_eval.py` primero
   (barato). Si Recall@K/Precision@K empeoraron, no sigas: ajustá ahí antes de
   gastar en la Capa 2.
2. Recall/Precision de la Capa 1 se mantienen o mejoran → corré
   `run_golden_eval.py` completo (35 preguntas) para confirmar que la Capa 2
   sigue bien con el nuevo contexto que le llega.
3. Cualquier resultado (mejora, regresión, o sin cambio) se registra en
   `EXPERIMENTS.md` con: fecha, commit, qué cambió, métricas antes/después,
   y el porqué si hay una regresión.
4. Si hay una regresión y no es obvio por qué, diagnosticar antes de seguir
   iterando prompts a ciegas (ver el caso del 2026-08-22: dos intentos de
   fix por wording no funcionaron porque la causa real estaba en otra capa).

## Qué NO forma parte de esta metodología (por ahora)

- CI/regresión automática: se evaluó y se decidió no implementarla mientras
  el proyecto sea de un solo desarrollador — la disciplina manual + este
  documento + `EXPERIMENTS.md` ya cubre el mismo objetivo sin la
  infraestructura extra. Reconsiderar si se suma otro colaborador.
- Langfuse/OpenTelemetry/DeepEval/RAGAS como frameworks completos: se
  evaluó adoptar piezas sueltas (ver Run log), no la plataforma completa,
  por costo/beneficio en un proyecto de este tamaño.
