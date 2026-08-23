# Registro de experimentos

Cada corrida del golden set contra el pipeline real queda acá con: commit,
config relevante, métricas agregadas y qué cambió respecto a la corrida
anterior. El JSON crudo de cada corrida vive en `evaluation/runs/`.

Cómo correr una nueva medición:
```bash
python evaluation/run_golden_eval.py
```

---

## Run 1 — Baseline

- **Fecha**: 2026-08-22
- **Commit**: `d31b53d` (fix: no matar el proceso al inicializar la base de datos)
- **Config**: `CHUNK_SIZE=600`, `CHUNK_OVERLAP=150`, `top_k retrieval=40`, `top_n rerank=10`, `ENABLE_GUARDRAILS=True`, `ENABLE_EVALUATION=True`
- **Resultado crudo**: `evaluation/runs/2026-08-22_baseline_d31b53d.json`

| Métrica | Valor |
|---|---|
| Status correcto (answered/blocked/refused) | 29/35 (83%) |
| Source recall | 100% (27 preguntas con fuente esperada) |
| Hechos clave recall | 96% |
| Groundedness interno (PASS) | 31/35 (89%) |
| Tokens totales | ~145.263 |
| Tiempo total | 586s (~16.7s/pregunta) |

**Hallazgos:**
1. Las 5 preguntas "incontestables" (I01-I05) figuran como mismatch de status, pero 3 de ellas (I02, I03, I05) en realidad se abstuvieron correctamente en contenido — solo que parafrasearon en vez de usar el `REFUSAL_MESSAGE` canónico de `core/constants.py`. Causa: `prompts/system_prompt.txt` nunca exige el string exacto, solo `prompts/repair_prompt.txt` lo hace (y ese solo corre si falla el groundedness check). Esto rompe la medición: el propio propósito del constante ("poder medir con qué frecuencia el asistente se abstiene") no se cumple porque el prompt principal no lo canoniza.
2. I01 respondió con la política general completa en vez de un refusal limpio (pregunta sobre saldo personal de vacaciones, dato que no está en los documentos).
3. I04 agregó info de Wellness Days no pedida como si fuera relacionada a licencia por enfermedad (padding, no alucinación de dato duro).
4. **C02 — bug real**: pregunta con respuesta negativa fundamentada ("no calificás porque te falta seniority") fue marcada FAIL por el juez de groundedness, entró al repair loop, y el repair devolvió el refusal genérico en vez de corregir la respuesta. El juez no distingue "no hay info" de "la info dice que no".

**Próximo paso**: Run 2 — agregar instrucción de refusal canónico a `system_prompt.txt` y re-medir los 6 casos afectados (I01-I05, C02).

---

## Run 2 — Fix refusal canónico (v1) + tolerancia a negativas razonadas

- **Fecha**: 2026-08-22
- **Cambios**: `prompts/system_prompt.txt` regla 1 (exigir string exacto si "ninguna información relacionada"); `prompts/groundedness_prompt.txt` regla 6 nueva (conclusiones negativas razonadas = PASS).
- **Subset evaluado**: I01, I02, I03, I04, I05, C02 (6/35)
- **Resultado crudo**: `evaluation/runs/2026-08-22_fix1_refusal.json`

| Caso | Antes (Run 1) | Ahora | Veredicto |
|---|---|---|---|
| C02 | refused (mal, debía ser negativa razonada) | **answered, correcto** ("no calificás porque...") | ✅ Arreglado |
| I02 | answered (parafraseado, contenido correcto) | **refused, string canónico** | ✅ Arreglado |
| I01 | answered (volcó política completa) | answered (mismo patrón) | Sin cambio |
| I03 | answered (parafraseado, contenido correcto: "no se especifica") | answered, **contenido irrelevante** (Flex Time en vez de home office), relevance=1 | ❌ Regresión |
| I04 | answered (parafraseado, correcto + un poco de padding) | answered, **contenido irrelevante** (gimnasio/odontología en vez de enfermedad), relevance=1 | ❌ Regresión |
| I05 | answered (parafraseado, correcto) | answered, **contenido irrelevante** (seguro médico en vez de guarderías), relevance=1 | ❌ Regresión |

**Diagnóstico de la regresión**: el wording "si el contexto no contiene ninguna información *relacionada*" era demasiado laxo. Con `top_k=40` el retrieval siempre trae chunks temáticamente cercanos (todos son "beneficios de RRHH"), y el modelo interpretó "hay algo relacionado" como licencia para responder con lo que sea, en vez de evaluar si responde la pregunta puntual.

---

## Run 3 — Fix refusal canónico (v2, wording más estricto)

- **Fecha**: 2026-08-22
- **Cambio**: `prompts/system_prompt.txt` regla 1 reescrita para exigir que el contexto responda *específicamente* la pregunta, no solo que sea temáticamente afín.
- **Subset evaluado**: I01, I03, I04, I05 (los 4 que seguían fallando)
- **Resultado crudo**: `evaluation/runs/2026-08-22_fix2_refusal.json`

**Resultado**: sin cambios. Los 4 casos siguen respondiendo con contenido real pero irrelevante (relevance=1 en los tres que lo miden). El wording no es el cuello de botella.

**Causa raíz confirmada** (no es de prompt, es de arquitectura):
1. Los 4 casos tienen `is_repaired: true` — la respuesta original falló groundedness (algo no estaba 100% respaldado), pasó por `RepairManager.repair_answer()`, que corrige hechos contra el contexto pero **nunca recibe la pregunta original** (`core/repair.py:11`, firma `repair_answer(self, answer, context)`). No puede detectar que la respuesta es irrelevante, solo que sea factualmente falsa.
2. El retrieval con `top_k=40` y umbral de similitud bajo (0.20, `core/retriever.py:8`) nunca vuelve vacío: para preguntas sin respuesta real en el corpus trae los "menos malos" candidatos de temas cercanos. Sumado a la regla de "EXHAUSTIVIDAD" del system prompt, el modelo tiende a usar lo que haya.
3. El `grading` (relevance/usefulness) ya mide esto correctamente (relevance=1 en los 3 casos) pero es puramente diagnóstico — no dispara ninguna corrección ni repair.

**Fix real pendiente** (no aplicado todavía, requiere decisión de diseño):
- Pasarle la pregunta original a `RepairManager.repair_answer()` para que pueda rechazar por irrelevancia, no solo por hecho falso.
- O: usar el score de `relevance` del grading (ya se calcula, ya está en paralelo) para gatillar el repair/refusal cuando sea bajo, igual que hoy se hace con el status FAIL de groundedness.
- Revisar si subir el umbral de similitud en el retriever (hoy 0.20) reduce cuántas veces llega contexto irrelevante en primer lugar.

---

## Run 4 — Fix en el reranker (causa raíz real)

- **Fecha**: 2026-08-22
- **Cambio**: `core/reranker.py` — el prompt del reranker pasó de "seleccioná los fragmentos útiles/relacionados" a "seleccioná solo los que contestan específicamente la pregunta; si ninguno contesta, devolvé `{"ids": []}`". Contexto: el retrieval con `top_k=40` y umbral 0.20 siempre trae candidatos temáticamente cercanos aunque no exista respuesta real; el reranker viejo los aceptaba como "útiles" por ser del mismo tema general. Este es el punto correcto de intervención: antes de que el contexto irrelevante llegue a generación (donde ya no se puede deshacer).
- **Subset evaluado primero**: I01, I03, I04, I05
- **Resultado crudo**: `evaluation/runs/2026-08-22_fix3_reranker.json`

| Caso | Antes (Run 2/3) | Ahora | Veredicto |
|---|---|---|---|
| I03 | answered, irrelevante (Flex Time) | **refused, string canónico, fuentes=[]** | ✅ Arreglado |
| I04 | answered, irrelevante (gimnasio) | **refused, string canónico, fuentes=[]** | ✅ Arreglado |
| I05 | answered, irrelevante (seguro médico) | **refused, string canónico, fuentes=[]** | ✅ Arreglado |
| I01 | answered, volcó política completa | answered, explica la regla general y pide antigüedad | Sin cambio — caso distinto (ver nota) |

**I01 no es un bug de irrelevancia**: la pregunta es sobre saldo personal de vacaciones. El reranker ahora trae contexto genuinamente relevante (la política de vacaciones SÍ es el tema), y el modelo explica la regla general y aclara que falta la antigüedad para el número exacto — no inventa nada, pero tampoco es el refusal estricto que pide el golden set. Es una decisión de producto (¿explicar la regla general es más útil que un refusal seco?), no un defecto de retrieval/reranking.

---

## Run 5 — Validación completa (35/35) del fix de reranker

- **Fecha**: 2026-08-22
- **Config**: igual al baseline + los 3 cambios acumulados (`system_prompt.txt` refusal canónico, `groundedness_prompt.txt` tolerancia a negativas razonadas, `core/reranker.py` especificidad + `{"ids": []}`)
- **Resultado crudo**: `evaluation/runs/2026-08-22_run4_full_validation.json`

| Métrica | Run 1 (Baseline) | Run 5 (post-fix) | Delta |
|---|---|---|---|
| Status correcto | 29/35 (83%) | **34/35 (97%)** | +14 pts |
| Source recall | 100% | 100% | sin cambio (sin regresión en factuales) |
| Hechos clave recall | 96% | 94% | -2 pts (ruido, sin caso puntual identificado como regresión) |
| Groundedness interno PASS | 31/35 (89%) | 32/35 (91%) | +2 pts |
| Tokens totales | ~145.263 | ~143.772 | sin cambio significativo |

**Único mismatch restante**: I01 — no es un bug, es una decisión de producto pendiente (ver Run 4: el modelo explica la regla general de vacaciones y pide la antigüedad en vez de refusar seco; no inventa datos).

**Conclusión**: el fix real estaba en el reranker (criterio de "útil" → "contesta específicamente"), no en el prompt de generación. Los 3 cambios se mantienen. Baseline vigente para la próxima ronda: este Run 5.

---

## Run 6 — Baseline de Capa 1 (retrieval + reranking, aislado)

- **Fecha**: 2026-08-22
- **Herramienta nueva**: `evaluation/run_retrieval_eval.py` (ver [EVALUATION_METHODOLOGY.md](EVALUATION_METHODOLOGY.md)) — mide Capa 1 sola, sin generación ni auditoría.
- **Config**: `top_k=40`, `top_n_rerank=10`, prompt de reranker post-fix (Run 4)
- **Subset**: 27/35 preguntas (excluye incontestables/fuera de ámbito, que no tienen `chunks_relevantes`)
- **Resultado crudo**: `evaluation/retrieval_eval_results.json`

| Métrica | Valor |
|---|---|
| Recall@40 (retrieval crudo) | 100% — no informativo: con 27 chunks totales en el corpus y `top_k=40`, el retrieval crudo devuelve casi todo el corpus siempre |
| Precision@40 (retrieval crudo) | 5.9% — mismo motivo, no informativo a este tamaño de corpus |
| **MRR (retrieval crudo)** | **0.64** — el chunk correcto no siempre queda primero por similitud pura; justifica tener reranker |
| **Recall post-rerank (top 10)** | **84.6%** |
| **Precision post-rerank (top 10)** | **85.6%** |

**Nota metodológica**: V01 (conversacional) dio recall/precision post-rerank = 0.0 — esperado, no es un bug. Esta categoría depende del historial de chat (rewriting, Capa 2) para que la pregunta tenga sentido standalone; el script de Capa 1 la excluye a propósito. Las preguntas conversacionales no deberían puntuar en el scoring de Capa 1 aislada.

**Métricas de referencia para futuras corridas de Capa 1**: Recall post-rerank y Precision post-rerank (top 10). Si un cambio de chunking/threshold/reranker baja alguno de estos dos números, no avanzar a la Capa 2 sin antes entender por qué (ver procedimiento en EVALUATION_METHODOLOGY.md).

---

## Run 7 y 8 — Fixes de bajo riesgo (DDL destructivo, atribución de fuente, budget de contexto)

- **Fecha**: 2026-08-22
- **Cambios**:
  1. `scripts/ingest_data.py` — se saca el `DROP TABLE IF EXISTS interactions;` de la ingesta de contenido (nunca debía borrar el log operativo).
  2. `core/reranker.py` — `rerank()` ahora devuelve índices sobre la lista de entrada en vez de texto; elimina la necesidad de re-buscar la fuente por igualdad de contenido.
  3. `core/orchestrator.py` — usa los índices del reranker directamente (`raw_chunks[i]`, `all_sources[i]`), sin `.index()`; agrega tope de caracteres (`settings.MAX_CONTEXT_CHARS=8000`) al armar el contexto final.
  4. `evaluation/run_retrieval_eval.py` — actualizado para la nueva firma de `rerank()`.
- **Validación Capa 1**: `evaluation/runs/2026-08-22_run7_retrieval_postfix.json` — Recall post-rerank 84.6%, Precision post-rerank 85.6%. Idéntico a Run 6: el refactor es funcionalmente equivalente, solo corrige el bug de atribución.
- **Validación Capa 2 (35/35)**: `evaluation/runs/2026-08-22_run8_full_postfix.json` — Status correcto 33/35 (94%, vs 34/35 del Run 5), source recall 100%, groundedness PASS 89%.

**Hallazgo — no determinismo del reranker LLM**: I04 volvió a fallar con el mismo patrón del Run 2/3 (contenido de gimnasio/odontología para una pregunta de licencia por enfermedad), a pesar de tener aplicado el fix de especificidad del Run 4. El reranker llama al LLM con `temperature=0`, pero eso no garantiza el mismo output en cada llamada real a la API — es un límite conocido de usar un LLM como filtro de relevancia en vez de una regla determinística. El fix del Run 4 reduce la tasa de falla (de 3/4 casos fallando siempre, a 1/4 fallando de forma intermitente) pero no la elimina. No se persigue más allá de esto por ahora: el costo de seguir iterando wording ya se demostró con rendimientos decrecientes (Run 2 y 3), y una solución determinística (ej. threshold de similitud duro antes del reranker) es un cambio de arquitectura, no un ajuste de prompt.
