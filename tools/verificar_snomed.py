# -*- coding: utf-8 -*-
"""
Validación de los conceptos SNOMED del crosswalk Dx → tópico ACR.

Para CADA ancla verifica, contra el RF2 SNOMED:
  1) que el conceptId esté ACTIVO (archivo de conceptos).
  2) su nombre completamente especificado (FSN) en español.
  3) que la etiqueta del diagnóstico (dx) sea COHERENTE con el concepto
     (comparte raíz médica con el FSN o con algún sinónimo).

Marca para revisión manual las anclas donde el dx y el concepto no coinciden.

Uso:  python tools/verificar_snomed.py --rf2 <ruta_RF2>
"""

import os, re, sys, json, argparse, unicodedata
from collections import defaultdict

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "tools"))
import importar_snomed as S

CONCEPT_REL = r"Snapshot\Terminology\sct2_Concept_Snapshot_ArgentinaEdition_20260520.txt"
FSN = "900000000000003001"
SINONIMOS = os.path.join(RAIZ, "acr_cache", "sinonimos_snomed.json")
CROSSWALK = os.path.join(RAIZ, "acr_cache", "crosswalk_resuelto.json")

# palabras vacías que no cuentan para la coincidencia
STOP = set("de la el los las un una y o en del al con sin por para enfermedad "
           "trastorno sindrome agudo aguda cronico cronica".split())

# Anclas revisadas y confirmadas correctas a mano (equivalencias médicas:
# tumor=neoplasia, gástrico=estómago, osteoartritis=artrosis, telorrea=secreción
# por pezón, espondilodiscitis=discitis, politraumatismo=traumatismos múltiples…).
VALIDADAS = {
    "126953009", "3548001", "2304001", "267981009", "372143007", "448315008",
    "396275006", "126537000", "54302000", "89164003", "262519004",
    "299513007",   # Dolor de pie → dolor articular del pie (correcto)
}


def _norm(t):
    t = (t or "").lower()
    t = unicodedata.normalize("NFKD", t)
    return "".join(c for c in t if not unicodedata.combining(c))


def _palabras(t):
    return {w for w in re.findall(r"[a-z]+", _norm(t)) if len(w) >= 4 and w not in STOP}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rf2", default=S.RF2_DEFAULT)
    args = ap.parse_args()

    cw = json.load(open(CROSSWALK, encoding="utf-8"))
    syn = json.load(open(SINONIMOS, encoding="utf-8"))
    conceptos = {e["snomed"] for e in cw}

    # 1) activos (archivo de conceptos)
    activos = {}
    with open(os.path.join(args.rf2, CONCEPT_REL), encoding="utf-8") as f:
        next(f)
        for line in f:
            c = line.rstrip("\n").split("\t")
            if len(c) >= 3 and c[0] in conceptos:
                activos[c[0]] = (c[2] == "1")

    # 2) FSN en español (archivo de descripciones)
    fsn = {}
    with open(S._desc_path(args.rf2), encoding="utf-8") as f:
        next(f)
        for line in f:
            c = line.rstrip("\n").split("\t")
            if len(c) >= 8 and c[4] in conceptos and c[2] == "1" and c[5] == "es" and c[6] == FSN:
                fsn[c[4]] = c[7]

    # 3) coherencia dx ↔ concepto
    print(f"Validando {len(cw)} anclas contra el RF2 SNOMED ...\n")
    inactivos, sin_fsn, dudosas, ok = [], [], [], 0
    for e in cw:
        cid, dx = e["snomed"], e["dx"]
        act = activos.get(cid)
        fsn_es = fsn.get(cid, "")
        sinos = syn.get(cid, {}).get("es", [])
        if act is False:
            inactivos.append((dx, cid))
        if not fsn_es:
            sin_fsn.append((dx, cid))
        # coincidencia: palabras del dx vs (FSN + sinónimos)
        pal_dx = _palabras(dx)
        pal_concepto = _palabras(fsn_es + " " + " ".join(sinos))
        blob = _norm(fsn_es + " " + " ".join(sinos))
        comparte = (bool(pal_dx & pal_concepto) or cid in VALIDADAS
                    or _norm(dx) in blob)   # dx idéntico/contenido (ej. "tos crónica")
        if not comparte:
            dudosas.append((dx, cid, fsn_es))
        else:
            ok += 1

    print(f"✅ Coherentes: {ok}/{len(cw)}")
    print(f"❌ Conceptos INACTIVOS: {len(inactivos)}")
    for dx, cid in inactivos:
        print(f"   - {dx}  ({cid})")
    if sin_fsn:
        print(f"⚠️ Sin FSN español: {len(sin_fsn)}")
        for dx, cid in sin_fsn:
            print(f"   - {dx}  ({cid})")
    if dudosas:
        print(f"\n🔍 A REVISAR (dx no comparte raíz con el concepto):")
        for dx, cid, f_es in dudosas:
            print(f"   - dx «{dx}»  →  {cid} = «{f_es}»")
    print("\n" + ("✅ TODO OK" if not inactivos and not dudosas
                  else "⚠️ Revisar lo marcado arriba"))


if __name__ == "__main__":
    main()
