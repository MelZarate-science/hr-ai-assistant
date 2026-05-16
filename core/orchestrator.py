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
        telemetry = {"steps": [], "total_tokens": 0}
        
        # 0. Rewriting
        rewritten_query, t0 = self.llm.rewrite_query(query, history)
        telemetry["steps"].append(f"1. Rewriting: {t0} tokens | Query: {rewritten_query}")
        telemetry["total_tokens"] += t0

        # 1. Guardrail
        if settings.ENABLE_GUARDRAILS:
            is_safe, t1 = self.guardrail.validate_query(rewritten_query)
            telemetry["steps"].append(f"2. Guardrail: {t1} tokens ({'PASS' if is_safe else 'FAIL'})")
            telemetry["total_tokens"] += t1
            if not is_safe:
                return "Fuera de ámbito.", [], False, 0.0, False, \
                       {"relevance": 0, "clarity": 0, "usefulness": 0, "total_score": 0}, telemetry

        # 2. Retrieval (Top-20 candidates)
        raw_chunks, all_sources = retriever.get_relevant_context(rewritten_query, top_k=20)
        telemetry["steps"].append(f"3. Retrieval: {len(raw_chunks)} candidates")

        # 3. Reranking (Select Top-15 best to avoid missing secondary info)
        best_chunks, t_rerank = reranker.rerank(rewritten_query, raw_chunks, top_n=15)
        telemetry["steps"].append(f"4. Reranking: {t_rerank} tokens (Top-15 selected)")
        telemetry["total_tokens"] += t_rerank

        # Serialización TOON del contexto final (solo los 10 mejores)
        # Formato estricto: fuente|contenido (preservando saltos de línea para estructura)
        context = f"HR_Knowledge[{len(best_chunks)}]{{source,content}}:\n"
        for chunk in best_chunks:
            try:
                # Extraemos la fuente y el contenido preservando la estructura interna
                parts = chunk.split("]\n", 1)
                source_part = parts[0].replace("[CONTEXTO: ", "").split(">")[0].strip()
                content_part = parts[1].strip()
                context += f"{source_part}|{content_part}\n---\n"
            except:
                context += f"Documento|{chunk.strip()}\n---\n"
        
        # Filtramos fuentes únicas para la respuesta del API
        sources = list(set([all_sources[raw_chunks.index(c)] for c in best_chunks if c in raw_chunks]))

        # 4. Generation
        answer, t2 = self.llm.generate_answer(query, context, history)
        telemetry["steps"].append(f"5. Generation: {t2} tokens")
        telemetry["total_tokens"] += t2

        # 5. Evaluation & Repair
        is_grounded = True
        score = 1.0
        is_repaired = False
        if settings.ENABLE_EVALUATION:
            eval_res, t3 = self.evaluator.check_groundedness(answer, context)
            telemetry["total_tokens"] += t3
            
            if eval_res["status"] != "PASS":
                answer, t4 = self.repair_manager.repair_answer(answer, context)
                is_repaired = True
                eval_res, t5 = self.evaluator.check_groundedness(answer, context)
                telemetry["steps"].append(f"6. Eval/Repair: {t3+t4+t5} tokens")
                telemetry["total_tokens"] += t4 + t5
            else:
                telemetry["steps"].append(f"6. Eval: {t3} tokens (PASS)")
            
            is_grounded = eval_res["status"] == "PASS"
            score = eval_res["groundedness_score"]

        # 6. Grading
        grading = {"relevance": 5, "clarity": 5, "usefulness": 5, "total_score": 5.0}
        if settings.ENABLE_EVALUATION:
            grading, t6 = self.evaluator.get_grading(query, answer)
            telemetry["total_tokens"] += t6

        return answer, sources, is_grounded, score, is_repaired, grading, telemetry

# Instancia única del orquestador
orchestrator = RAGOrchestrator()
