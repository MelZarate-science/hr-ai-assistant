import time
import asyncio
from core.llm import LLMManager, LLMError
from core.guardrails import GuardrailManager
from core.retriever import retriever
from core.reranker import reranker
from core.repair import RepairManager
from core.database import db_manager
from evaluation.eval_runner import EvalRunner
from config.settings import settings

class RAGOrchestrator:
    def __init__(self):
        self.llm = LLMManager()
        self.guardrail = GuardrailManager()
        self.repair_manager = RepairManager()
        self.evaluator = EvalRunner()

    async def process_query(self, query: str, history: list):
        telemetry = {"steps": [], "total_tokens": 0, "durations": {}}
        overall_start = time.perf_counter()
        
        # 1. Query Rewriting
        s0 = time.perf_counter()
        try:
            rewritten_query, t0 = await self.llm.rewrite_query(query, history)
        except LLMError as e:
            # Etapa no critica: si falla, seguimos con la consulta original en
            # vez de tirar abajo el pipeline completo.
            print(f"⚠️ Rewriting no disponible, uso la consulta original: {e}")
            rewritten_query, t0 = query, 0
        d0 = time.perf_counter() - s0
        telemetry["durations"]["rewriting"] = f"{d0:.2f}s"
        telemetry["steps"].append(f"1. Rewriting: {t0} tokens | {d0:.2f}s")
        telemetry["total_tokens"] += t0

        # 2. Safety Guardrails
        if settings.ENABLE_GUARDRAILS:
            s1 = time.perf_counter()
            is_safe, t1 = await self.guardrail.validate_query(rewritten_query)
            d1 = time.perf_counter() - s1
            telemetry["durations"]["guardrail"] = f"{d1:.2f}s"
            telemetry["steps"].append(f"2. Guardrail: {t1} tokens | {d1:.2f}s")
            telemetry["total_tokens"] += t1
            if not is_safe:
                blocked_answer = "Fuera de ámbito."
                db_manager.log_interaction(query, rewritten_query, blocked_answer, False, 0.0, [])
                return blocked_answer, [], False, 0.0, False, \
                       {"relevance": 0, "clarity": 0, "usefulness": 0, "total_score": 0}, telemetry, "Consulta bloqueada por política de seguridad."

        # 3. Vector Retrieval (Subimos a 40 para máxima cobertura)
        s2 = time.perf_counter()
        raw_chunks, all_sources = retriever.get_relevant_context(rewritten_query, top_k=40)
        d2 = time.perf_counter() - s2
        telemetry["durations"]["retrieval"] = f"{d2:.2f}s"
        telemetry["steps"].append(f"3. Retrieval: {len(raw_chunks)} candidates | {d2:.2f}s")

        # 4. Neural Reranking (Optimizado a Top-10 para balance velocidad/precisión)
        s3 = time.perf_counter()
        best_ids, t_rerank = await reranker.rerank(rewritten_query, raw_chunks, top_n=10)
        # Se indexa por posicion, no por igualdad de texto: si dos chunks
        # tuvieran contenido identico, buscar la fuente por .index() sobre el
        # texto atribuia siempre la primera coincidencia, no necesariamente la
        # correcta.
        best_chunks = [raw_chunks[i] for i in best_ids]
        best_sources = [all_sources[i] for i in best_ids]
        d3 = time.perf_counter() - s3
        telemetry["durations"]["reranking"] = f"{d3:.2f}s"
        telemetry["steps"].append(f"4. Reranking: {t_rerank} tokens | {d3:.2f}s")
        telemetry["total_tokens"] += t_rerank

        # TOON Serialization (Fidelidad absoluta al formato tabular), con tope
        # de caracteres para no desbordar la ventana de contexto si top_n o
        # CHUNK_SIZE crecen mas adelante.
        rows = []
        used_sources = []
        current_chars = 0
        for chunk, source in zip(best_chunks, best_sources):
            clean_chunk = chunk.replace("\n", " ").strip()
            if "]\n" in chunk:
                parts = chunk.split("]\n", 1)
                source_name = parts[0].replace("[CONTEXTO: ", "").split(">")[0].strip()
                # Resolvemos el reemplazo de saltos de línea fuera de la f-string para evitar SyntaxError
                content_part = parts[1].replace("\n", " ").strip()
                row = f"{source_name}|{content_part}\n---\n"
            else:
                row = f"Doc|{clean_chunk}\n---\n"

            if current_chars + len(row) > settings.MAX_CONTEXT_CHARS:
                break
            rows.append(row)
            used_sources.append(source)
            current_chars += len(row)

        context = f"HR_Knowledge[{len(rows)}]{{source,content}}:\n" + "".join(rows)
        sources = list(dict.fromkeys(used_sources))

        # 5. Answer Generation
        s4 = time.perf_counter()
        try:
            answer, t2 = await self.llm.generate_answer(query, context, history)
        except LLMError as e:
            # Sin respuesta generada no hay nada que auditar ni calificar.
            # Antes, "ERROR_CONEXION" se mostraba al usuario como si fuera
            # una respuesta valida y entraba a la auditoria como alucinacion.
            print(f"❌ Generacion no disponible: {e}")
            telemetry["steps"].append(f"5. Generation: ERROR ({e})")
            telemetry["total_time"] = f"{time.perf_counter() - overall_start:.2f}s"
            unavailable_answer = "El asistente no está disponible en este momento. Por favor, intentá de nuevo en unos minutos."
            db_manager.log_interaction(query, rewritten_query, unavailable_answer, False, 0.0, [])
            return (
                unavailable_answer,
                [], False, 0.0, False,
                {"relevance": 0, "clarity": 0, "usefulness": 0, "total_score": 0},
                telemetry,
                f"Error de generación: {e}"
            )
        d4 = time.perf_counter() - s4
        telemetry["durations"]["generation"] = f"{d4:.2f}s"
        telemetry["steps"].append(f"5. Generation: {t2} tokens | {d4:.2f}s")
        telemetry["total_tokens"] += t2

        # 6. Audit & Quality Control (Async Parallel)
        is_grounded, score, is_repaired = True, 1.0, False
        reasoning = "Respuesta generada y validada correctamente."
        grading = {"relevance": 5, "clarity": 5, "usefulness": 5, "total_score": 5.0}

        if settings.ENABLE_EVALUATION:
            s5 = time.perf_counter()
            (eval_res, t3), (grading_res, t6) = await asyncio.gather(
                self.evaluator.check_groundedness(answer, context),
                self.evaluator.get_grading(query, answer)
            )
            # Estas dos llamadas se imprimian en el paso 6 pero nunca entraban
            # en el acumulador: el total reportado subestimaba la auditoria.
            telemetry["total_tokens"] += t3 + t6

            # Solo un FAIL real dispara reparacion. UNMEASURED significa que la
            # auditoria no pudo correr (fallo de API o de parseo del juez), y
            # reparar a ciegas sobre eso seria peor que no hacerlo.
            if eval_res["status"] == "FAIL":
                try:
                    answer, t4 = await self.repair_manager.repair_answer(answer, context)
                    is_repaired = True
                    # La respuesta cambio, asi que hay que auditarla Y calificarla
                    # de nuevo. El grading que corrio en paralelo describe el
                    # texto anterior, que el usuario ya no va a ver.
                    (eval_res, t5), (grading_res, t7) = await asyncio.gather(
                        self.evaluator.check_groundedness(answer, context),
                        self.evaluator.get_grading(query, answer)
                    )
                    telemetry["total_tokens"] += t4 + t5 + t7
                except LLMError as e:
                    # Sin reparacion no cambio nada: is_repaired queda en False
                    # para no afirmar una correccion que no ocurrio, y el eval
                    # original (FAIL) se conserva tal cual.
                    print(f"❌ Repair no disponible: {e}")
                    telemetry["steps"].append(f"6c. Repair: no disponible ({e})")

            if eval_res["status"] == "UNMEASURED":
                # No se puede afirmar ni negar veracidad: no hay schema Optional
                # para esto todavia, asi que se marca explicitamente en el texto
                # en vez de reportar False (parece alucinacion) o True (parece
                # que se valido, que es el bug que se esta corrigiendo aca).
                is_grounded = False
                score = 0.0
                reasoning = f"No se pudo auditar la respuesta: {eval_res.get('reasoning', '')}"
            else:
                is_grounded = eval_res["status"] == "PASS"
                score = eval_res["groundedness_score"]
                reasoning = eval_res.get("reasoning", "No se detectaron inconsistencias.")

            if grading_res is None:
                # get_grading fallo (API o parseo). Se deja en cero y trazable,
                # en vez de reusar el default 5/5/5 que afirmaria una calidad
                # que nunca se midio.
                grading = {"relevance": 0, "clarity": 0, "usefulness": 0, "total_score": 0.0}
                telemetry["steps"].append("6b. Grading: no disponible")
            else:
                grading = grading_res
            d5 = time.perf_counter() - s5
            telemetry["durations"]["evaluation"] = f"{d5:.2f}s"
            telemetry["steps"].append(f"6. Audit: {t3+t6} tokens | {d5:.2f}s")

        telemetry["total_time"] = f"{time.perf_counter() - overall_start:.2f}s"
        
        # Log final trazable en consola
        print(f"\n--- 📊 RAG TELEMETRY (Refactored) ---")
        print(f"Query: {query}")
        for step in telemetry["steps"]:
            print(step)
        print(f"💰 TOTAL ESTIMATED TOKENS: {telemetry['total_tokens']}")
        print(f"⏱️ TOTAL TIME: {telemetry['total_time']}")
        print(f"-------------------------------------\n")

        db_manager.log_interaction(query, rewritten_query, answer, is_grounded, score, sources)

        return answer, sources, is_grounded, score, is_repaired, grading, telemetry, reasoning

orchestrator = RAGOrchestrator()
