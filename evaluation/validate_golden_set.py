"""Valida la integridad del golden set contra el corpus real.

Comprueba que cada pregunta este bien formada y, sobre todo, que los chunks
etiquetados como relevantes existan de verdad en el corpus que produce la
ingesta actual. Sin esta validacion el golden set se degrada en silencio:
basta recalibrar CHUNK_SIZE para que los chunk_id apunten a otra cosa y las
metricas de recall queden midiendo cualquier cosa.

Uso:
    python evaluation/validate_golden_set.py

No toca la base de datos: solo lee los PDF y aplica el mismo chunking que
scripts/ingest_data.py.
"""
import json
import os
import sys
from collections import Counter
from pathlib import Path

# La ingesta importa la configuracion, que exige DATABASE_URL. Este validador
# nunca abre una conexion, asi que basta un valor de relleno para poder correr
# sin infraestructura.
os.environ.setdefault("DATABASE_URL", "postgresql://validador-offline")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import settings
from core.constants import REFUSAL_MESSAGE, STATUS_ANSWERED, STATUS_BLOCKED, STATUS_REFUSED
from scripts.ingest_data import chunk_text, extract_text_from_pdf

CAMPOS_OBLIGATORIOS = {
    "id", "categoria", "pregunta", "respuesta_esperada", "hechos_clave",
    "fuentes_esperadas", "chunks_relevantes", "status_esperado", "revisado_por_humano",
}

CATEGORIAS = {
    "factual", "agregacion", "condicional",
    "incontestable", "fuera_de_ambito", "conversacional",
}

ESTADOS = {STATUS_ANSWERED, STATUS_BLOCKED, STATUS_REFUSED}

# Categorias en las que el sistema no debe recuperar contexto ni responder.
SIN_CONTEXTO = {"incontestable", "fuera_de_ambito"}


def cargar_corpus():
    """Devuelve el conjunto de (source, chunk_id) que produce la ingesta actual."""
    docs_dir = Path(settings.BASE_DIR) / "data/raw/hr_docs"
    corpus = set()
    for pdf_path in sorted(docs_dir.glob("*.pdf")):
        chunks = chunk_text(extract_text_from_pdf(pdf_path))
        for i in range(len(chunks)):
            corpus.add((pdf_path.name, i))
    return corpus


def cargar_golden_set(path):
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for n, linea in enumerate(f, start=1):
            linea = linea.strip()
            if not linea:
                continue
            try:
                items.append((n, json.loads(linea)))
            except json.JSONDecodeError as e:
                raise SystemExit(f"Linea {n}: JSON invalido ({e})")
    return items


def validar(items, corpus):
    errores = []
    vistos = set()

    for n, item in items:
        ref = f"Linea {n} ({item.get('id', 'sin id')})"

        faltantes = CAMPOS_OBLIGATORIOS - set(item)
        if faltantes:
            errores.append(f"{ref}: faltan campos {sorted(faltantes)}")
            continue

        if item["id"] in vistos:
            errores.append(f"{ref}: id duplicado")
        vistos.add(item["id"])

        if item["categoria"] not in CATEGORIAS:
            errores.append(f"{ref}: categoria desconocida '{item['categoria']}'")

        if item["status_esperado"] not in ESTADOS:
            errores.append(f"{ref}: status_esperado desconocido '{item['status_esperado']}'")

        if not item["pregunta"].strip():
            errores.append(f"{ref}: pregunta vacia")

        # Los chunks etiquetados tienen que existir en el corpus real.
        for c in item["chunks_relevantes"]:
            clave = (c.get("source"), c.get("chunk_id"))
            if clave not in corpus:
                errores.append(f"{ref}: el chunk {clave} no existe en el corpus actual")

        fuentes_declaradas = set(item["fuentes_esperadas"])
        fuentes_reales = {c["source"] for c in item["chunks_relevantes"]}
        if fuentes_declaradas != fuentes_reales:
            errores.append(
                f"{ref}: fuentes_esperadas {sorted(fuentes_declaradas)} "
                f"no coincide con las fuentes de los chunks {sorted(fuentes_reales)}"
            )

        if item["categoria"] in SIN_CONTEXTO:
            if item["chunks_relevantes"]:
                errores.append(f"{ref}: una pregunta {item['categoria']} no deberia tener chunks relevantes")
            if item["hechos_clave"]:
                errores.append(f"{ref}: una pregunta {item['categoria']} no deberia tener hechos clave")
        else:
            if not item["chunks_relevantes"]:
                errores.append(f"{ref}: falta etiquetar chunks relevantes (sin ellos no hay recall@k)")
            if not item["hechos_clave"]:
                errores.append(f"{ref}: falta al menos un hecho clave verificable")

        if item["categoria"] == "incontestable":
            if item["status_esperado"] != STATUS_REFUSED:
                errores.append(f"{ref}: una pregunta incontestable debe esperar status '{STATUS_REFUSED}'")
            if item["respuesta_esperada"] != REFUSAL_MESSAGE:
                errores.append(f"{ref}: la respuesta esperada debe ser exactamente REFUSAL_MESSAGE")

        if item["categoria"] == "fuera_de_ambito" and item["status_esperado"] != STATUS_BLOCKED:
            errores.append(f"{ref}: una pregunta fuera de ambito debe esperar status '{STATUS_BLOCKED}'")

        if item["categoria"] == "conversacional" and not item.get("historial"):
            errores.append(f"{ref}: una pregunta conversacional necesita historial")

        # Los hechos clave se verifican por contencion, asi que tienen que estar
        # literalmente en la respuesta esperada.
        for hecho in item["hechos_clave"]:
            if hecho.lower() not in item["respuesta_esperada"].lower():
                errores.append(f"{ref}: el hecho clave '{hecho}' no aparece en la respuesta esperada")

    return errores


def main():
    path = Path(__file__).resolve().parent / "golden_set.jsonl"
    if not path.exists():
        raise SystemExit(f"No existe {path}")

    items = cargar_golden_set(path)
    corpus = cargar_corpus()
    errores = validar(items, corpus)

    print(f"Corpus: {len(corpus)} chunks (CHUNK_SIZE={settings.CHUNK_SIZE})")
    print(f"Golden set: {len(items)} preguntas")
    for categoria, n in Counter(i["categoria"] for _, i in items).most_common():
        print(f"  {categoria:18} {n}")

    cubiertos = {(c["source"], c["chunk_id"]) for _, i in items for c in i["chunks_relevantes"]}
    print(f"\nCobertura del corpus: {len(cubiertos)}/{len(corpus)} chunks referenciados")

    pendientes = [i["id"] for _, i in items if not i["revisado_por_humano"]]
    if pendientes:
        print(f"Pendientes de revision humana: {len(pendientes)} ({', '.join(pendientes)})")

    if errores:
        print(f"\n{len(errores)} error(es):")
        for e in errores:
            print(f"  - {e}")
        raise SystemExit(1)

    print("\nGolden set valido.")


if __name__ == "__main__":
    main()
