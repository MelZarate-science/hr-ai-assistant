import time
import asyncio
from core.llm import LLMManager
from core.guardrails import GuardrailManager
from core.retriever import retriever
from core.reranker import reranker
from core.repair import RepairManager
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
        rewritten_query, t0 = await self.llm.rewrite_query(query, history)
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
                return "Fuera de ámbito.", [], False, 0.0, False, \
                       {"relevance": 0, "clarity": 0, "usefulness": 0, "total_score": 0}, telemetry, "Consulta bloqueada por política de seguridad.", "Consulta bloqueada por política de seguridad."

        # 3. Vector Retrieval (Subimos a 40 para máxima cobertura)
        s2 = time.perf_counter()
        raw_chunks, all_sources = retriever.get_relevant_context(rewritten_query, top_k=40)
        d2 = time.perf_counter() - s2
        telemetry["durations"]["retrieval"] = f"{d2:.2f}s"
        telemetry["steps"].append(f"3. Retrieval: {len(raw_chunks)} candidates | {d2:.2f}s")

        # 4. Neural Reranking (Optimizado a Top-10 para balance velocidad/precisión)
        s3 = time.perf_counter()
        best_chunks, t_rerank = await reranker.rerank(rewritten_query, raw_chunks, top_n=10)
        d3 = time.perf_counter() - s3
        telemetry["durations"]["reranking"] = f"{d3:.2f}s"
        telemetry["steps"].append(f"4. Reranking: {t_rerank} tokens | {d3:.2f}s")
        telemetry["total_tokens"] += t_rerank

        # TOON Serialization (Fidelidad absoluta al formato tabular)
        context = f"HR_Knowledge[{len(best_chunks)}]{{source,content}}:\n"
        for chunk in best_chunks:
            clean_chunk = chunk.replace("\n", " ").strip()
            if "]\n" in chunk:
                parts = chunk.split("]\n", 1)
                source_name = parts[0].replace("[CONTEXTO: ", "").split(">")[0].strip()
                # Resolvemos el reemplazo de saltos de línea fuera de la f-string para evitar SyntaxError
                content_part = parts[1].replace("\n", " ").strip()
                context += f"{source_name}|{content_part}\n---\n"
            else:
                context += f"Doc|{clean_chunk}\n---\n"
        
        sources = list(set([str(all_sources[raw_chunks.index(c)]) for c in best_chunks if c in raw_chunks]))

        # 5. Answer Generation
        s4 = time.perf_counter()
        answer, t2 = await self.llm.generate_answer(query, context, history)
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
            
            if eval_res["status"] != "PASS":
                answer, t4 = await self.repair_manager.repair_answer(answer, context)
                is_repaired = True
                eval_res, t5 = await self.evaluator.check_groundedness(answer, context)
                telemetry["total_tokens"] += t4 + t5
            
            is_grounded = eval_res["status"] == "PASS"
            score = eval_res["groundedness_score"]
            reasoning = eval_res.get("reasoning", "No se detectaron inconsistencias.")
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
        
        return answer, sources, is_grounded, score, is_repaired, grading, telemetry, reasoning

orchestrator = RAGOrchestrator()
