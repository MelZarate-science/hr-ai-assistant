"""Corre el golden set contra el pipeline real y mide calidad end-to-end.

A diferencia de validate_golden_set.py (que solo chequea que el set este bien
formado offline), esto ejecuta orchestrator.process_query() para cada
pregunta: llama a Gemini y a la base Neon real. Tiene costo de API y tiempo.

Uso:
    python evaluation/run_golden_eval.py [--limit N] [--categoria factual]
"""
import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.constants import STATUS_ANSWERED, STATUS_BLOCKED, STATUS_REFUSED, is_refusal
from core.orchestrator import orchestrator

GOLDEN_SET_PATH = Path(__file__).resolve().parent / "golden_set.jsonl"


def cargar_golden_set(path, categoria_filtro=None, limit=None, ids_filtro=None):
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea:
                continue
            item = json.loads(linea)
            if categoria_filtro and item["categoria"] != categoria_filtro:
                continue
            if ids_filtro and item["id"] not in ids_filtro:
                continue
            items.append(item)
    if limit:
        items = items[:limit]
    return items


def actual_status(answer: str) -> str:
    if answer.strip() == "Fuera de ámbito.":
        return STATUS_BLOCKED
    if is_refusal(answer):
        return STATUS_REFUSED
    return STATUS_ANSWERED


async def evaluar_item(item):
    historial = item.get("historial", [])
    t0 = time.perf_counter()
    answer, sources, is_grounded, score, is_repaired, grading, telemetry, reasoning = \
        await orchestrator.process_query(item["pregunta"], historial)
    dt = time.perf_counter() - t0

    status_ok = actual_status(answer) == item["status_esperado"]

    fuentes_esperadas = set(item["fuentes_esperadas"])
    fuentes_obtenidas = set(sources)
    # Recall a nivel documento: cuantas fuentes esperadas aparecieron.
    if fuentes_esperadas:
        source_recall = len(fuentes_esperadas & fuentes_obtenidas) / len(fuentes_esperadas)
    else:
        source_recall = None  # No aplica (incontestable / fuera_de_ambito)

    hechos_ok = [h for h in item["hechos_clave"] if h.lower() in answer.lower()]
    hechos_recall = (len(hechos_ok) / len(item["hechos_clave"])) if item["hechos_clave"] else None

    return {
        "id": item["id"],
        "categoria": item["categoria"],
        "pregunta": item["pregunta"],
        "answer": answer,
        "status_esperado": item["status_esperado"],
        "status_real": actual_status(answer),
        "status_ok": status_ok,
        "fuentes_esperadas": sorted(fuentes_esperadas),
        "fuentes_obtenidas": sorted(fuentes_obtenidas),
        "source_recall": source_recall,
        "hechos_clave": item["hechos_clave"],
        "hechos_encontrados": hechos_ok,
        "hechos_recall": hechos_recall,
        "is_grounded": is_grounded,
        "groundedness_score": score,
        "is_repaired": is_repaired,
        "grading": grading,
        "tokens": telemetry["total_tokens"],
        "duration_s": round(dt, 2),
    }


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--categoria", type=str, default=None)
    parser.add_argument("--ids", type=str, default=None, help="Lista separada por comas, ej: I01,I02,C02")
    parser.add_argument("--out", type=str, default=str(Path(__file__).resolve().parent / "golden_eval_results.json"))
    args = parser.parse_args()

    ids_filtro = set(args.ids.split(",")) if args.ids else None
    items = cargar_golden_set(GOLDEN_SET_PATH, args.categoria, args.limit, ids_filtro)
    print(f"Corriendo {len(items)} preguntas contra el pipeline real...\n")

    resultados = []
    for i, item in enumerate(items, start=1):
        print(f"[{i}/{len(items)}] {item['id']} ({item['categoria']}): {item['pregunta'][:70]}")
        try:
            r = await evaluar_item(item)
        except Exception as e:
            print(f"  ERROR: {e}")
            r = {"id": item["id"], "categoria": item["categoria"], "error": str(e)}
        resultados.append(r)
        estado = "OK" if r.get("status_ok") else "MISMATCH" if "error" not in r else "ERROR"
        print(f"  -> status_real={r.get('status_real')} ({estado}) | source_recall={r.get('source_recall')} | hechos_recall={r.get('hechos_recall')} | grounded={r.get('is_grounded')}")

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)

    validos = [r for r in resultados if "error" not in r]
    errores = [r for r in resultados if "error" in r]

    status_ok_n = sum(1 for r in validos if r["status_ok"])
    recalls = [r["source_recall"] for r in validos if r["source_recall"] is not None]
    hechos_recalls = [r["hechos_recall"] for r in validos if r["hechos_recall"] is not None]
    grounded_n = sum(1 for r in validos if r["is_grounded"])
    total_tokens = sum(r["tokens"] for r in validos)
    total_time = sum(r["duration_s"] for r in validos)

    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    print(f"Preguntas evaluadas: {len(items)} | Errores de ejecucion: {len(errores)}")
    print(f"Status correcto (answered/blocked/refused): {status_ok_n}/{len(validos)} ({100*status_ok_n/len(validos):.0f}%)")
    if recalls:
        print(f"Source recall promedio: {100*sum(recalls)/len(recalls):.0f}% (sobre {len(recalls)} preguntas con fuente esperada)")
    if hechos_recalls:
        print(f"Hechos clave recall promedio: {100*sum(hechos_recalls)/len(hechos_recalls):.0f}% (sobre {len(hechos_recalls)} preguntas con hechos clave)")
    print(f"Groundedness (auditoria interna) PASS: {grounded_n}/{len(validos)} ({100*grounded_n/len(validos):.0f}%)")
    print(f"Tokens totales estimados: {total_tokens}")
    print(f"Tiempo total: {total_time:.1f}s (avg {total_time/len(validos):.2f}s/pregunta)")

    if errores:
        print(f"\nErrores de ejecucion en: {', '.join(r['id'] for r in errores)}")

    fallos_status = [r for r in validos if not r["status_ok"]]
    if fallos_status:
        print(f"\nMismatches de status ({len(fallos_status)}):")
        for r in fallos_status:
            print(f"  {r['id']} ({r['categoria']}): esperado={r['status_esperado']} real={r['status_real']}")

    print(f"\nDetalle completo guardado en: {args.out}")


if __name__ == "__main__":
    asyncio.run(main())
