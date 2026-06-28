# -*- coding: utf-8 -*-
"""
Importador del NUEVO portal ACR AC (gravitas.acr.org/ACPortal).

A diferencia de las narrativas (HTML largo), este portal expone los datos
ESTRUCTURADOS por escenario: procedimiento + dosis (RRL adulto/peds) +
categoría de adecuación. Hay ~4446 escenarios.

Comandos
--------
  lista                       Baja el índice de escenarios -> acr_cache/portal_index.json
  extraer [--all] [--panel P] [--ids a,b] [--limite N]
                              Baja y parsea el detalle de cada escenario ->
                              acr_cache/portal_data.json (incremental/reanudable)

==========================  USO RESPONSABLE  ==========================
Contenido propiedad de la American College of Radiology. Caché para
CONSULTA PERSONAL, no redistribuir. Delay de cortesía entre requests.
======================================================================
"""

import os, re, ssl, json, time, html as ihtml, argparse, urllib.request

BASE = "https://gravitas.acr.org"
PORTAL = BASE + "/ACPortal"
DETALLE = BASE + "/ACPortal/GetDataForOneScenario?senarioId={}"
UA = "validador-acr-educativo/1.0 (uso personal)"
DELAY_SEG = 0.6

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(RAIZ, "acr_cache")
INDEX_JSON = os.path.join(CACHE, "portal_index.json")
DATA_JSON = os.path.join(CACHE, "portal_data.json")

_CTX = ssl._create_unverified_context()


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "X-Requested-With": "XMLHttpRequest"})
    with urllib.request.urlopen(req, timeout=60, context=_CTX) as r:
        return r.read().decode("utf-8", "ignore")


def _texto(s):
    s = re.sub(r"<br\s*/?>", " ", s)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", ihtml.unescape(s)).strip()


# ----------------------------------------------------------------------
# 1) ÍNDICE de escenarios desde la tabla de la página principal
# ----------------------------------------------------------------------
_RE_FILA = re.compile(
    r'GetDataForOneScenario\?senarioId=(\d+).*?</tr>', re.S)


def parsear_indice(html):
    """Extrae filas de la tabla principal: id + columnas de metadatos."""
    escenarios = []
    # Cada fila <tr> contiene el link al escenario y celdas con metadatos.
    for tr in re.split(r'<tr[ >]', html):
        m = re.search(r'senarioId=(\d+)', tr)
        if not m:
            continue
        celdas = [_texto(c) for c in re.findall(r'<td[^>]*>(.*?)</td>', tr, re.S)]
        if len(celdas) < 7:
            continue
        # Columnas: 0 panel | 1 resolution_id | 2 escenario | 3 sexo |
        #           4 edad | 5 área corporal | 6 áreas clínicas prioritarias
        escenarios.append({
            "senario_id": m.group(1),
            "panel": celdas[0],
            "resolution_id": celdas[1],
            "escenario": celdas[2],
            "sexo": celdas[3],
            "edad": celdas[4],
            "area_corporal": celdas[5],
            "areas_clinicas_prioritarias": celdas[6],
        })
    return escenarios


def cmd_lista():
    os.makedirs(CACHE, exist_ok=True)
    print(f"Descargando índice del portal {PORTAL} ...")
    html = _get(PORTAL)
    esc = parsear_indice(html)
    # dedup por senario_id
    vistos, unicos = set(), []
    for e in esc:
        if e["senario_id"] not in vistos:
            vistos.add(e["senario_id"])
            unicos.append(e)
    with open(INDEX_JSON, "w", encoding="utf-8") as f:
        json.dump(unicos, f, ensure_ascii=False, indent=2)
    paneles = {}
    for e in unicos:
        paneles[e["panel"]] = paneles.get(e["panel"], 0) + 1
    print(f"OK: {len(unicos)} escenarios.")
    for p, n in sorted(paneles.items()):
        print(f"  {n:>4}  {p}")
    print(f"Guardado en: {INDEX_JSON}")


# ----------------------------------------------------------------------
# 2) DETALLE de un escenario: procedimientos + ratings
# ----------------------------------------------------------------------
_CAT_COLOR = {"green": "apropiado", "yellow": "puede",
              "pink": "no_apropiado", "red": "no_apropiado"}
_COLORES = "green|yellow|pink|red"


def parsear_detalle(html):
    """Devuelve dict con variante, topic y lista de procedimientos."""
    # Colapsar espacios ENTRE etiquetas (no toca el texto visible) para que
    # las regex no dependan de saltos de línea/indentación.
    html = re.sub(r'>\s+<', '><', html)
    # Variante (texto descriptivo) y topicId
    mvar = re.search(r'data-toggle="tab">(.*?)</a>', html, re.S)
    variante = _texto(mvar.group(1)) if mvar else ""
    mtopic = re.search(r'TopicNarrative\?topicId=(\d+)', html)
    topic_id = mtopic.group(1) if mtopic else None
    mtitulo = re.search(r'word-break">(.*?)</span>', html, re.S)
    topico = _texto(mtitulo.group(1)) if mtitulo else ""

    # Resolution doc id (el id que aparece junto al título del escenario)
    mrid = re.search(r'spanResolutionDocTitle">(\d{5,})</span>', html)
    resolution_id = mrid.group(1) if mrid else None

    procedimientos = []
    tb = html.find("<tbody>")
    body = html[tb:html.find("</tbody>", tb)] if tb >= 0 else html
    # La tabla anidada 'procedur-table' tiene su propio <tr>, así que NO se puede
    # dividir por <tr>. Delimitamos cada procedimiento por 'procedur-table'.
    cortes = [m.start() for m in re.finditer(r'procedur-table', body)]
    for k, ini in enumerate(cortes):
        fin = cortes[k + 1] if k + 1 < len(cortes) else len(body)
        bloque = body[ini:fin]
        mp = re.search(r'spanResolutionDocTitle">(.*?)</div>', bloque, re.S)
        if not mp:
            continue
        procedimiento = _texto(mp.group(1))
        # RRL adulto/peds: spans dentro de tdResDoc que contienen 'mSv'
        rrls = re.findall(
            r'tdResDoc"><span class="spanResolutionDocTitle"[^>]*>(.*?)</span>',
            bloque, re.S)
        rrl_adulto = _texto(rrls[0]) if len(rrls) >= 1 else ""
        rrl_peds = _texto(rrls[1]) if len(rrls) >= 2 else ""
        # categoría: celda con bg-COLOR
        mcat = re.search(r'bg-(' + _COLORES + r')"><span[^>]*>(.*?)</span>', bloque, re.S)
        cat_texto = _texto(mcat.group(2)) if mcat else ""
        mc = re.search(r'(' + _COLORES + r')-circle', bloque)
        color = (mcat.group(1) if mcat else (mc.group(1) if mc else ""))
        procedimientos.append({
            "procedimiento": procedimiento,
            "rrl_adulto": rrl_adulto,
            "rrl_peds": rrl_peds,
            "categoria": cat_texto,
            "adecuacion": _CAT_COLOR.get(color, color),
        })
    return {
        "topico": topico,
        "topic_id": topic_id,
        "variante": variante,
        "resolution_id": resolution_id,
        "procedimientos": procedimientos,
    }


def _cargar_index():
    if not os.path.exists(INDEX_JSON):
        raise SystemExit("Falta el índice. Corré: python tools/importar_portal_acr.py lista")
    with open(INDEX_JSON, encoding="utf-8") as f:
        return json.load(f)


def cmd_extraer(todos=False, panel=None, ids=None, limite=None):
    index = _cargar_index()
    sel = index
    if ids:
        pedidos = {i.strip() for i in ids.split(",") if i.strip()}
        sel = [e for e in sel if e["senario_id"] in pedidos]
    elif panel:
        sel = [e for e in sel if e["panel"].lower() == panel.lower()]
    elif not todos:
        raise SystemExit("Indicá --all, --panel P o --ids a,b")
    if limite:
        sel = sel[:limite]

    # cargar lo ya extraído (reanudable)
    data = {}
    if os.path.exists(DATA_JSON):
        with open(DATA_JSON, encoding="utf-8") as f:
            data = {d["senario_id"]: d for d in json.load(f)}

    pendientes = [e for e in sel if e["senario_id"] not in data]
    print(f"A extraer: {len(pendientes)} (ya teníamos {len(data)}). Delay {DELAY_SEG}s.")
    for i, e in enumerate(pendientes, 1):
        try:
            html = _get(DETALLE.format(e["senario_id"]))
            det = parsear_detalle(html)
            registro = {**e, **det}
            data[e["senario_id"]] = registro
            n = len(det["procedimientos"])
            print(f"  [{i}/{len(pendientes)}] {e['senario_id']} {e['escenario'][:55]} ({n} proc.)")
        except Exception as ex:
            print(f"  [{i}/{len(pendientes)}] ERROR {e['senario_id']}: {ex}")
        # guardar cada 25 por seguridad
        if i % 25 == 0:
            _guardar(data)
        time.sleep(DELAY_SEG)
    _guardar(data)
    print(f"Listo. {len(data)} escenarios en {DATA_JSON}")


def _guardar(data):
    with open(DATA_JSON, "w", encoding="utf-8") as f:
        json.dump(list(data.values()), f, ensure_ascii=False, indent=2)


def main():
    ap = argparse.ArgumentParser(description="Importador portal ACR AC (uso personal).")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("lista", help="Baja el índice de escenarios")
    pe = sub.add_parser("extraer", help="Extrae detalle (procedimientos + ratings)")
    pe.add_argument("--all", action="store_true", help="Todos los escenarios")
    pe.add_argument("--panel", help="Filtrar por panel")
    pe.add_argument("--ids", help="senario_id separados por coma")
    pe.add_argument("--limite", type=int, help="Máximo a procesar")
    args = ap.parse_args()

    if args.cmd == "lista":
        cmd_lista()
    elif args.cmd == "extraer":
        cmd_extraer(todos=args.all, panel=args.panel, ids=args.ids, limite=args.limite)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
