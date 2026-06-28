# -*- coding: utf-8 -*-
"""
Importador de sinónimos desde el archivo RF2 de SNOMED CT (Edición Argentina).

Lee el archivo de Descriptions (≈459 MB) UNA vez y, para una lista de conceptos,
extrae todos sus sinónimos activos en español/inglés -> JSON chico y offline.

Comandos
--------
  buscar "<término>"   Busca conceptos cuyo término (es, activo) coincide.
                       Sirve para armar el crosswalk (encontrar el conceptId).
  extraer              Dado el crosswalk, vuelca los sinónimos de cada concepto
                       a acr_cache/sinonimos_snomed.json

==========================  LICENCIA  ==========================
Datos de SNOMED CT bajo licencia (gratuita en Argentina, país miembro).
El JSON generado es para uso del proyecto. No redistribuir el RF2.
================================================================

Uso:
    python tools/importar_snomed.py buscar "embolia pulmonar"
    python tools/importar_snomed.py extraer
"""

import os, re, sys, json, argparse, unicodedata

# Ruta por defecto al release (ajustable con --rf2)
RF2_DEFAULT = (r"C:\Users\cuent\OneDrive\Escritorio"
               r"\SnomedCT_Argentina-EditionRelease_PRODUCTION_20260520T120000Z"
               r"\SnomedCT_Argentina-EditionRelease_PRODUCTION_20260520T120000Z")
DESC_REL = r"Snapshot\Terminology\sct2_Description_Snapshot_ArgentinaEdition_20260520.txt"
REL_REL = r"Snapshot\Terminology\sct2_Relationship_Snapshot_ArgentinaEdition_20260520.txt"
ISA = "116680003"          # typeId de la relación 'es un' (IS-A)
MAX_DESC = 6000            # tope de descendientes por ancla (evita explosión)
MAX_UP = 1                 # niveles de ancestros a subir (solo padres directos)
# Conceptos demasiado generales: nunca incluirlos como ancestros.
BLOQUEO_UP = {"404684003", "64572001", "118234003", "138875005", "362965005",
              "123037004", "417163006", "301857004", "118940003", "53619000",
              "49601007", "362969004", "363788007", "248536006", "302292003",
              # conceptos demasiado genéricos detectados en stress test
              "118538004", "300848003", "4147007", "118531000"}   # "masa", etc.

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALIDA = os.path.join(RAIZ, "acr_cache", "sinonimos_snomed.json")
CROSSWALK_JSON = os.path.join(RAIZ, "acr_cache", "crosswalk_resuelto.json")

# typeId de SNOMED: FSN (nombre completamente especificado) vs sinónimo
FSN = "900000000000003001"


def _desc_path(rf2):
    return os.path.join(rf2, DESC_REL)


def _limpiar_fsn(term):
    """Quita el sufijo semántico del FSN: 'angina de pecho (trastorno)' -> ..."""
    return re.sub(r"\s*\([^)]+\)\s*$", "", term).strip()


def norm(texto):
    """Normaliza para indexar/buscar: minúsculas, sin acentos, sin sufijo FSN."""
    t = _limpiar_fsn((texto or "").lower())
    t = unicodedata.normalize("NFKD", t)
    return "".join(c for c in t if not unicodedata.combining(c)).strip()


def cmd_anclar(rf2):
    """Resuelve los términos de data/anclas_terminos.py a concept IDs (una pasada)
    y escribe acr_cache/crosswalk_resuelto.json."""
    from data.anclas_terminos import ANCLAS
    desc = _desc_path(rf2)
    # términos a buscar (los que no traen 'snomed' explícito)
    objetivo = {}
    for a in ANCLAS:
        if not a.get("snomed") and a.get("termino"):
            objetivo[norm(a["termino"])] = None
    print(f"Resolviendo {len(objetivo)} términos en SNOMED (una pasada) ...")
    encontrado = {}  # norm -> (conceptId, term_más_corto)
    with open(desc, encoding="utf-8") as f:
        next(f)
        for line in f:
            c = line.rstrip("\n").split("\t")
            if len(c) < 8 or c[2] != "1" or c[5] != "es":
                continue
            n = norm(c[7])
            if n in objetivo:
                t = _limpiar_fsn(c[7])
                prev = encontrado.get(n)
                if prev is None or len(t) < len(prev[1]):
                    encontrado[n] = (c[4], t)

    resuelto, no_res = [], []
    for a in ANCLAS:
        sid = a.get("snomed")
        if not sid and a.get("termino"):
            hit = encontrado.get(norm(a["termino"]))
            sid = hit[0] if hit else None
        if sid:
            resuelto.append({"dx": a["dx"], "snomed": sid, "topicos": a["topicos"]})
        else:
            no_res.append(a["dx"])
    os.makedirs(os.path.dirname(CROSSWALK_JSON), exist_ok=True)
    with open(CROSSWALK_JSON, "w", encoding="utf-8") as f:
        json.dump(resuelto, f, ensure_ascii=False, indent=2)
    print(f"OK: {len(resuelto)}/{len(ANCLAS)} anclas resueltas -> {CROSSWALK_JSON}")
    if no_res:
        print(f"⚠️ SIN resolver ({len(no_res)}) — revisar término:")
        for dx in no_res:
            print(f"   - {dx}")


def cmd_buscar(termino, rf2, limite=40):
    desc = _desc_path(rf2)
    q = norm(termino)
    print(f"Buscando '{termino}' (norm: '{q}') en {os.path.basename(desc)} ...")
    hits = {}  # conceptId -> term representativo
    with open(desc, encoding="utf-8") as f:
        next(f)
        for line in f:
            c = line.rstrip("\n").split("\t")
            if len(c) < 8:
                continue
            active, cid, lang, typeid, term = c[2], c[4], c[5], c[6], c[7]
            if active == "1" and lang == "es" and q in norm(term):
                # preferimos el término más corto (suele ser el preferido)
                if cid not in hits or len(term) < len(hits[cid]):
                    hits[cid] = term
    print(f"{len(hits)} concepto(s):")
    for cid, term in sorted(hits.items(), key=lambda x: len(x[1]))[:limite]:
        print(f"  {cid:<20} {term}")


def _mapa_jerarquia(rf2):
    """Devuelve (hijos, padres) según IS-A activo (una pasada al archivo de relaciones).
    hijos: padre -> set(hijos) | padres: hijo -> set(padres)."""
    from collections import defaultdict
    rel = os.path.join(rf2, REL_REL)
    hijos, padres = defaultdict(set), defaultdict(set)
    with open(rel, encoding="utf-8") as f:
        next(f)
        for line in f:
            c = line.rstrip("\n").split("\t")
            if len(c) < 8:
                continue
            # 2 active | 4 sourceId(hijo) | 5 destinationId(padre) | 7 typeId
            if c[2] == "1" and c[7] == ISA:
                hijos[c[5]].add(c[4])
                padres[c[4]].add(c[5])
    return hijos, padres


def _ancestros(ancla, padres, niveles):
    """Ancestros de 'ancla' hasta 'niveles' arriba (excluye conceptos muy generales).
    Solo se toman sus SINÓNIMOS, no sus subárboles."""
    visto, frontera = set(), {ancla}
    for _ in range(niveles):
        nueva = set()
        for c in frontera:
            for p in padres.get(c, ()):
                if p not in visto and p not in BLOQUEO_UP:
                    visto.add(p)
                    nueva.add(p)
        frontera = nueva
    return visto


def _descendientes(ancla, hijos):
    """Todos los conceptos bajo 'ancla' (cierre transitivo hacia abajo)."""
    visto, pila = set(), [ancla]
    while pila and len(visto) < MAX_DESC:
        c = pila.pop()
        if c in visto:
            continue
        visto.add(c)
        pila.extend(h for h in hijos.get(c, ()) if h not in visto)
    return visto


def cmd_extraer(rf2):
    from data.crosswalk_acr import CROSSWALK
    from collections import defaultdict
    anclas = {e["snomed"] for e in CROSSWALK}
    print(f"Construyendo jerarquía IS-A desde el archivo de relaciones ...")
    hijos, padres = _mapa_jerarquia(rf2)
    print(f"  {len(hijos)} conceptos con hijos · {len(padres)} con padres.")

    # Expandir cada ancla: descendientes (hacia abajo) + ancestros (hacia arriba)
    concepto_anclas = defaultdict(set)
    n_up = 0
    for e in CROSSWALK:
        desc_set = _descendientes(e["snomed"], hijos)
        if len(desc_set) >= MAX_DESC:
            print(f"  ⚠️ {e['dx']} ({e['snomed']}) alcanzó el tope {MAX_DESC} descendientes.")
        for c in desc_set:
            concepto_anclas[c].add(e["snomed"])
        for a in _ancestros(e["snomed"], padres, MAX_UP):   # hacia arriba
            concepto_anclas[a].add(e["snomed"])
            n_up += 1
    print(f"  Total conceptos cubiertos (anclas + descendientes + ancestros): "
          f"{len(concepto_anclas)} (+{n_up} ancestros)")

    # Sinónimos de todos esos conceptos (una pasada al archivo de descripciones)
    print(f"Extrayendo sinónimos ...")
    desc = _desc_path(rf2)
    datos = {c: {"es": [], "en": [], "anclas": sorted(concepto_anclas[c])}
             for c in concepto_anclas}
    with open(desc, encoding="utf-8") as f:
        next(f)
        for line in f:
            c = line.rstrip("\n").split("\t")
            if len(c) < 8:
                continue
            active, cid, lang, typeid, term = c[2], c[4], c[5], c[6], c[7]
            if cid in datos and active == "1" and typeid != FSN and lang in ("es", "en"):
                t = _limpiar_fsn(term)
                if t and t not in datos[cid][lang]:
                    datos[cid][lang].append(t)

    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    tot_es = sum(len(v["es"]) for v in datos.values())
    print(f"OK: {len(datos)} conceptos, {tot_es} sinónimos ES -> {SALIDA}")
    # resumen por ancla
    porancla = defaultdict(int)
    for c, v in datos.items():
        for a in v["anclas"]:
            porancla[a] += 1
    cw = {e["snomed"]: e["dx"] for e in CROSSWALK}
    print("Cobertura por diagnóstico (conceptos resueltos, incluye subtipos):")
    for a, n in sorted(porancla.items(), key=lambda x: -x[1]):
        print(f"  {n:>4}  {cw.get(a, a)}")


def main():
    sys.path.insert(0, RAIZ)
    ap = argparse.ArgumentParser(description="Importador de sinónimos SNOMED (RF2).")
    ap.add_argument("--rf2", default=RF2_DEFAULT, help="Ruta a la carpeta del release RF2")
    sub = ap.add_subparsers(dest="cmd")
    pb = sub.add_parser("buscar", help="Buscar conceptos por término español")
    pb.add_argument("termino")
    sub.add_parser("anclar", help="Resolver anclas_terminos -> crosswalk_resuelto.json")
    sub.add_parser("extraer", help="Volcar sinónimos del crosswalk a JSON")
    args = ap.parse_args()

    if args.cmd == "buscar":
        cmd_buscar(args.termino, args.rf2)
    elif args.cmd == "anclar":
        cmd_anclar(args.rf2)
    elif args.cmd == "extraer":
        cmd_extraer(args.rf2)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
