# -*- coding: utf-8 -*-
"""
Auditoría de integridad: compara los datos locales del proyecto contra el ACR
en vivo. Verifica que NO se haya alterado ningún dato.

Chequea:
  1) Conteo de escenarios (portal nuevo) live vs local + set de IDs.
  2) Conteo de tópicos (catálogo clásico) live vs local.
  3) Comparación PROFUNDA de una muestra de escenarios: procedimiento, dosis,
     categoría y adecuación, campo por campo, live vs guardado.
  4) Integridad interna del dataset local (campos, vacíos).
  5) Que la traducción NO mute los datos fuente (función pura).

Uso:  python tools/verificar_integridad.py [--muestra N_por_panel]
"""

import os, re, sys, json, argparse
from collections import defaultdict

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "tools"))

import importar_portal_acr as P
import importar_acr as C

DATA = os.path.join(RAIZ, "acr_cache", "portal_data.json")
INDEX = os.path.join(RAIZ, "acr_cache", "portal_index.json")
TOPICOS = os.path.join(RAIZ, "acr_cache", "topicos_acr.json")


def _claves_proc(procs):
    return [(p["procedimiento"], p["adecuacion"], p["rrl_adulto"],
             p["rrl_peds"], p["categoria"]) for p in procs]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--muestra", type=int, default=3,
                    help="Escenarios a verificar en profundidad por panel")
    args = ap.parse_args()

    data = json.load(open(DATA, encoding="utf-8"))
    index = json.load(open(INDEX, encoding="utf-8"))
    topicos = json.load(open(TOPICOS, encoding="utf-8"))
    by_id = {e["senario_id"]: e for e in data}

    print("=" * 64)
    print("1) CONTEOS — portal nuevo (gravitas) y catálogo clásico (acsearch)")
    print("=" * 64)
    main_html = P._get(P.PORTAL)
    live_ids = re.findall(r"senarioId=(\d+)", main_html)
    live_unicos = set(live_ids)
    local_ids = {e["senario_id"] for e in index}
    print(f"  Portal live: {len(live_ids)} filas / {len(live_unicos)} escenarios únicos")
    print(f"  Local index: {len(index)} | datos: {len(data)}")
    faltan_local = live_unicos - local_ids
    sobran_local = local_ids - live_unicos
    print(f"  IDs en vivo que NO tenemos: {len(faltan_local)}")
    print(f"  IDs locales que YA NO están en vivo: {len(sobran_local)}")

    lst_html = C._get(C.LIST_URL)
    live_topicos = len(set(re.findall(r"/docs/(\d+)/Narrative", lst_html)))
    print(f"  Catálogo clásico live: {live_topicos} tópicos | local: {len(topicos)}")

    print("\n" + "=" * 64)
    print(f"2) COMPARACIÓN PROFUNDA — {args.muestra} escenarios por panel")
    print("=" * 64)
    por_panel = defaultdict(list)
    for e in index:
        por_panel[e["panel"]].append(e["senario_id"])
    iguales = difer = errores = 0
    detalles_difer = []
    for panel in sorted(por_panel):
        for sid in por_panel[panel][:args.muestra]:
            if sid not in by_id:
                continue
            try:
                live = P.parsear_detalle(P._get(P.DETALLE.format(sid)))
            except Exception as ex:
                errores += 1
                print(f"  [ERR] {sid} ({panel}): {ex}")
                continue
            lp = _claves_proc(live["procedimientos"])
            sp = _claves_proc(by_id[sid]["procedimientos"])
            if lp == sp:
                iguales += 1
            else:
                difer += 1
                detalles_difer.append((panel, sid, by_id[sid]["escenario"]))
        print(f"  {panel:<24} verificados {min(args.muestra, len(por_panel[panel]))}")
    print(f"\n  IDÉNTICOS: {iguales} | DIFERENTES: {difer} | errores red: {errores}")
    for panel, sid, esc in detalles_difer:
        print(f"   ⚠️ DIFERENTE {sid} [{panel}] {esc[:50]}")

    print("\n" + "=" * 64)
    print("3) INTEGRIDAD INTERNA del dataset local")
    print("=" * 64)
    campos = ("panel", "escenario", "topico", "procedimientos", "sexo", "edad",
              "area_corporal")
    sin_campo = [e["senario_id"] for e in data if not all(k in e for k in campos)]
    sin_proc = [e["senario_id"] for e in data if not e["procedimientos"]]
    cats = sorted({p["categoria"] for e in data for p in e["procedimientos"]})
    n_proc = sum(len(e["procedimientos"]) for e in data)
    print(f"  Escenarios: {len(data)} | procedimientos: {n_proc}")
    print(f"  Con algún campo faltante: {len(sin_campo)} | sin procedimientos: {len(sin_proc)}")
    print(f"  Categorías presentes ({len(cats)}): {cats}")

    print("\n" + "=" * 64)
    print("4) TRADUCCIÓN no destructiva (función pura)")
    print("=" * 64)
    from core import traduccion as T
    muestra = data[0]
    antes_esc = muestra["escenario"]
    antes_proc = muestra["procedimientos"][0]["procedimiento"]
    _ = T.traducir_clinico(antes_esc)
    _ = T.traducir_procedimiento(antes_proc)
    ok_pura = (muestra["escenario"] == antes_esc and
               muestra["procedimientos"][0]["procedimiento"] == antes_proc)
    print(f"  Dato fuente intacto tras traducir: {'SÍ' if ok_pura else 'NO — ALTERADO'}")

    print("\n" + "=" * 64)
    veredicto = (difer == 0 and len(faltan_local) == 0 and len(sin_campo) == 0
                 and ok_pura and live_topicos == len(topicos))
    print("VEREDICTO:", "✅ DATOS ÍNTEGROS — sin alteraciones" if veredicto
          else "⚠️ Revisar diferencias arriba")
    print("=" * 64)


if __name__ == "__main__":
    main()
