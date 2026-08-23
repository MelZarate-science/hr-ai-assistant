"""Mide la Capa 1 (chunking + retrieval + reranking) de forma aislada.

A diferencia de run_golden_eval.py, esto NO llama a rewriting, guardrails,
generacion ni auditoria: solo embeddings + busqueda vectorial + reranker.
Mucho mas barato y rapido, pensado para iterar sobre CHUNK_SIZE, el umbral
de similitud o el prompt del reranker sin gastar en la capa de generacion
cada vez. Ver EVALUATION_METHODOLOGY.md.

Usa la pregunta cruda del golden set (no la reescrita): el rewriting
pertenece a la Capa 2 (usa el LLM y el historial de chat), asi que se
excluye a proposito para aislar la medicion de retrieval puro.

Uso:
    python evaluation/run_retrieval_eval.py [--top-k 40] [--top-n-rerank 10]
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.database import db_manager
from core.embeddings import EmbeddingManager
from core.reranker import reranker

GOLDEN_SET_PATH = Path(__file__).resolve().parent / "golden_set.jsonl"


def cargar_golden_set(path):
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea:
                continue
            items.append(json.loads(linea))
    return items


def buscar_con_chunk_id(embed_manager, query_text, top_k):
    """Replica core/retriever.py pero exponiendo chunk_id, solo para eval.

    No se reusa HRRetriever a proposito: su SELECT no trae chunk_id (ver
    hallazgo de la auditoria), y agregarlo ahi tocaria el contrato que usa
    produccion. Esta consulta vive solo en el script de evaluacion.
    """
    query_embedding = embed_manager.generate_single_embedding(query_text)
    conn = db_manager.get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT content, source, chunk_id, (embedding <#> %s::vector) * -1 AS similarity
            FROM documents
            ORDER BY embedding <#> %s::vector
            LIMIT %s;
            """,
            (query_embedding, query_embedding, top_k)
        )
        resultados = cur.fetchall()
        cur.close()
        return resultados
    finally:
        db_manager.release_connection(conn)


def recall_at_k(recuperados, relevantes):
    if not relevantes:
        return None
    return len(set(recuperados) & set(relevantes)) / len(set(relevantes))


def precision_at_k(recuperados, relevantes):
    if not recuperados or not relevantes:
        return None
    return len(set(recuperados) & set(relevantes)) / len(set(recuperados))


def mrr(recuperados_ordenados, relevantes):
    relevantes_set = set(relevantes)
    for i, item in enumerate(recuperados_ordenados):
        if item in relevantes_set:
            return 1.0 / (i + 1)
    return 0.0


async def evaluar_item(item, embed_manager, top_k, top_n_rerank):
    relevantes = [(c["source"], c["chunk_id"]) for c in item["chunks_relevantes"]]

    filas = buscar_con_chunk_id(embed_manager, item["pregunta"], top_k)
    recuperados_ids = [(source, chunk_id) for _, source, chunk_id, _ in filas]

    r_recall = recall_at_k(recuperados_ids, relevantes)
    r_precision = precision_at_k(recuperados_ids, relevantes)
    r_mrr = mrr(recuperados_ids, relevantes)

    chunks_texto = [content for content, _, _, _ in filas]
    # rerank() devuelve indices sobre `chunks_texto`, no texto: se mapea por
    # posicion, no por igualdad de contenido (fix aplicado tambien en
    # core/orchestrator.py para el mismo problema de atribucion de fuente).
    reranked_positions, _ = await reranker.rerank(item["pregunta"], chunks_texto, top_n=top_n_rerank)
    reranked_ids = [(filas[i][1], filas[i][2]) for i in reranked_positions]

    return {
        "id": item["id"],
        "categoria": item["categoria"],
        "pregunta": item["pregunta"],
        "n_relevantes": len(relevantes),
        "n_recuperados_raw": len(recuperados_ids),
        "recall_at_k_raw": r_recall,
        "precision_at_k_raw": r_precision,
        "mrr_raw": r_mrr,
        "n_post_rerank": len(reranked_ids),
        "recall_post_rerank": recall_at_k(reranked_ids, relevantes),
        "precision_post_rerank": precision_at_k(reranked_ids, relevantes),
    }


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-k", type=int, default=40)
    parser.add_argument("--top-n-rerank", type=int, default=10)
    parser.add_argument("--out", type=str, default=str(Path(__file__).resolve().parent / "retrieval_eval_results.json"))
    args = parser.parse_args()

    items = cargar_golden_set(GOLDEN_SET_PATH)
    items_con_chunks = [i for i in items if i["chunks_relevantes"]]
    print(f"Evaluando Capa 1 (retrieval + reranking) sobre {len(items_con_chunks)} preguntas "
          f"con chunks etiquetados (de {len(items)} totales; el resto son incontestables/fuera de ambito/conversacionales).\n")

    embed_manager = EmbeddingManager()
    resultados = []
    for i, item in enumerate(items_con_chunks, start=1):
        print(f"[{i}/{len(items_con_chunks)}] {item['id']} ({item['categoria']}): {item['pregunta'][:70]}")
        r = await evaluar_item(item, embed_manager, args.top_k, args.top_n_rerank)
        resultados.append(r)
        print(f"  raw: recall={r['recall_at_k_raw']:.2f} precision={r['precision_at_k_raw']:.2f} mrr={r['mrr_raw']:.2f} "
              f"| post-rerank: recall={r['recall_post_rerank']} precision={r['precision_post_rerank']}")

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)

    def promedio(campo):
        valores = [r[campo] for r in resultados if r[campo] is not None]
        return sum(valores) / len(valores) if valores else None

    print("\n" + "=" * 60)
    print("RESUMEN - Capa 1 (retrieval + reranking)")
    print("=" * 60)
    print(f"Preguntas evaluadas: {len(resultados)}")
    print(f"Recall@{args.top_k} (raw retrieval):    {promedio('recall_at_k_raw'):.1%}")
    print(f"Precision@{args.top_k} (raw retrieval): {promedio('precision_at_k_raw'):.1%}")
    print(f"MRR (raw retrieval):                    {promedio('mrr_raw'):.2f}")
    print(f"Recall post-rerank (top {args.top_n_rerank}):        {promedio('recall_post_rerank'):.1%}")
    print(f"Precision post-rerank (top {args.top_n_rerank}):     {promedio('precision_post_rerank'):.1%}")
    print(f"\nDetalle completo guardado en: {args.out}")


if __name__ == "__main__":
    asyncio.run(main())
