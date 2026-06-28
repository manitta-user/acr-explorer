# -*- coding: utf-8 -*-
"""
Importador del catálogo ACR Appropriateness Criteria(R).

Qué hace
--------
1) `indice`   : baja la lista oficial de tópicos (panel + título + ID + URL)
                y la guarda en acr_cache/topicos_acr.json
2) `docs`     : descarga los documentos 'Narrative' de tópicos elegidos
                (HTML) a acr_cache/docs/ para CONSULTA PERSONAL.

==========================  USO RESPONSABLE  ==========================
- Contenido propiedad de la American College of Radiology (copyright).
- Este caché es para CONSULTA PERSONAL del profesional. NO redistribuir
  ni empaquetar en la app compartible. Por eso vive en acr_cache/ que
  se ignora en .gitignore.
- Se usa un User-Agent identificable y un retardo entre descargas para
  no sobrecargar el servidor.
======================================================================

Uso:
    python tools/importar_acr.py indice
    python tools/importar_acr.py docs --panel Neurologic
    python tools/importar_acr.py docs --buscar "stroke,headache,appendicitis"
"""

import os, re, ssl, json, time, html as ihtml, argparse, urllib.request

BASE = "https://acsearch.acr.org"
LIST_URL = BASE + "/list"
UA = "validador-acr-educativo/1.0 (uso personal; contacto: medico)"
DELAY_SEG = 1.5  # cortesía entre requests

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(RAIZ, "acr_cache")
DOCS = os.path.join(CACHE, "docs")
INDICE_JSON = os.path.join(CACHE, "topicos_acr.json")

_CTX = ssl._create_unverified_context()


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=40, context=_CTX) as r:
        return r.read().decode("utf-8", "ignore")


def _limpiar(texto):
    texto = re.sub(r"<[^>]+>", " ", texto)
    texto = ihtml.unescape(texto)
    return re.sub(r"\s+", " ", texto).strip()


# Marca de inicio de panel y de fila de tópico
_RE_PANEL = re.compile(r'divPanelName.*?<h2[^>]*>(.*?)</h2>', re.S)
_RE_TITULO = re.compile(r'col-lg-4"?\s*>(.*?)</div>', re.S)
_RE_DOC = re.compile(r'/docs/(\d+)/Narrative/?')


def parsear_indice(html):
    """Devuelve lista de dicts: {panel, titulo, narrative_id, url}."""
    # Cortar el HTML en segmentos por panel
    paneles = list(_RE_PANEL.finditer(html))
    topicos = []
    for i, m in enumerate(paneles):
        panel = _limpiar(m.group(1))
        ini = m.end()
        fin = paneles[i + 1].start() if i + 1 < len(paneles) else len(html)
        segmento = html[ini:fin]
        # Cada fila tiene un título (col-lg-4) y uno o más /docs/ID/Narrative
        for fila in re.split(r'row div(?:Even|Odd)', segmento)[1:]:
            mt = _RE_TITULO.search(fila)
            md = _RE_DOC.search(fila)
            if not mt or not md:
                continue
            titulo = _limpiar(mt.group(1))
            if not titulo:
                continue
            nid = md.group(1)
            topicos.append({
                "panel": panel,
                "titulo": titulo,
                "narrative_id": nid,
                "url": f"{BASE}/docs/{nid}/Narrative/",
            })
    return topicos


def cmd_indice():
    os.makedirs(CACHE, exist_ok=True)
    print(f"Descargando índice de {LIST_URL} ...")
    html = _get(LIST_URL)
    topicos = parsear_indice(html)
    # Quitar duplicados por (titulo, narrative_id)
    vistos, unicos = set(), []
    for t in topicos:
        k = (t["titulo"], t["narrative_id"])
        if k not in vistos:
            vistos.add(k)
            unicos.append(t)
    with open(INDICE_JSON, "w", encoding="utf-8") as f:
        json.dump(unicos, f, ensure_ascii=False, indent=2)
    paneles = sorted({t["panel"] for t in unicos})
    print(f"OK: {len(unicos)} tópicos en {len(paneles)} paneles.")
    print("Paneles:", ", ".join(paneles))
    print(f"Guardado en: {INDICE_JSON}")


def _cargar_indice():
    if not os.path.exists(INDICE_JSON):
        raise SystemExit("Falta el índice. Corré primero: python tools/importar_acr.py indice")
    with open(INDICE_JSON, encoding="utf-8") as f:
        return json.load(f)


def cmd_docs(panel=None, buscar=None, limite=None, ids=None):
    indice = _cargar_indice()
    sel = indice
    if ids:
        pedidos = {i.strip() for i in ids.split(",") if i.strip()}
        sel = [t for t in sel if t["narrative_id"] in pedidos]
    if panel:
        sel = [t for t in sel if t["panel"].lower() == panel.lower()]
    if buscar:
        claves = [b.strip().lower() for b in buscar.split(",") if b.strip()]
        sel = [t for t in sel if any(c in t["titulo"].lower() for c in claves)]
    if limite:
        sel = sel[:limite]
    if not sel:
        print("No hay tópicos que coincidan con el filtro.")
        return
    os.makedirs(DOCS, exist_ok=True)
    print(f"Descargando {len(sel)} documentos a {DOCS} (delay {DELAY_SEG}s) ...")
    for i, t in enumerate(sel, 1):
        destino = os.path.join(DOCS, f"{t['narrative_id']}.html")
        if os.path.exists(destino):
            print(f"  [{i}/{len(sel)}] (ya existe) {t['titulo']}")
            continue
        try:
            contenido = _get(t["url"])
            with open(destino, "w", encoding="utf-8") as f:
                f.write(contenido)
            print(f"  [{i}/{len(sel)}] OK  {t['titulo']}")
        except Exception as e:
            print(f"  [{i}/{len(sel)}] ERROR {t['titulo']}: {e}")
        time.sleep(DELAY_SEG)
    print("Listo. Caché de consulta personal en acr_cache/docs/")


def main():
    ap = argparse.ArgumentParser(description="Importador catálogo ACR (uso personal).")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("indice", help="Baja la lista de tópicos a JSON")
    pd = sub.add_parser("docs", help="Descarga documentos Narrative")
    pd.add_argument("--panel", help="Filtrar por panel (ej. Neurologic)")
    pd.add_argument("--buscar", help="Palabras clave separadas por coma")
    pd.add_argument("--ids", help="narrative_id exactos separados por coma")
    pd.add_argument("--limite", type=int, help="Máximo de documentos a bajar")
    args = ap.parse_args()

    if args.cmd == "indice":
        cmd_indice()
    elif args.cmd == "docs":
        cmd_docs(panel=args.panel, buscar=args.buscar, limite=args.limite, ids=args.ids)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
