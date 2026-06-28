# -*- coding: utf-8 -*-
"""
Resolver Dx -> Estudio recomendado (ACR).

Flujo:
  texto libre del médico  ("angor")
     -> normaliza
     -> busca en el índice de sinónimos SNOMED (del crosswalk)
     -> concepto SNOMED  (Angina de pecho, 194828000)
     -> tópico(s) ACR    (Dolor torácico - posible SCA, ...)
     -> escenarios + estudios apropiados

Es EXPLICABLE: devuelve la interpretación (qué entendió y por qué).
Offline: usa acr_cache/sinonimos_snomed.json (sembrado del RF2 SNOMED).
"""

import os, json, functools, unicodedata, re

from core import consulta_acr
from data.crosswalk_acr import CROSSWALK
from data.extension_local import ALIAS_LOCALES as EXTENSION_LOCAL, VARIANTES_LING

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SINONIMOS = os.path.join(RAIZ, "acr_cache", "sinonimos_snomed.json")
_CROSSWALK_JSON = os.path.join(RAIZ, "acr_cache", "crosswalk_resuelto.json")
_EXT_FILE = os.path.join(RAIZ, "data", "extension_local.py")
_CACHE_IDX = os.path.join(RAIZ, "acr_cache", "_idx_dx.json")


def _firma():
    partes = []
    for p in (SINONIMOS, _CROSSWALK_JSON, _EXT_FILE):
        try:
            st = os.stat(p)
            partes.append(f"{int(st.st_mtime)}:{st.st_size}")
        except OSError:
            partes.append("-")
    return "|".join(partes)


def disponible():
    return os.path.exists(SINONIMOS)


def _norm(texto):
    t = (texto or "").lower().strip()
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", t)


@functools.lru_cache(maxsize=1)
def _sinonimos():
    if not disponible():
        return {}
    with open(SINONIMOS, encoding="utf-8") as f:
        return json.load(f)


@functools.lru_cache(maxsize=1)
def _por_ancla():
    """snomed del ancla -> entrada del crosswalk."""
    return {e["snomed"]: e for e in CROSSWALK}


@functools.lru_cache(maxsize=1)
def _indice():
    """norm(sinónimo) -> entrada del crosswalk.

    Recorre TODOS los conceptos del diccionario (anclas + descendientes por
    jerarquía SNOMED). Cada concepto apunta a su(s) ancla(s); indexamos todos
    sus sinónimos ES/EN hacia la entrada del crosswalk correspondiente.
    """
    porancla = _por_ancla()
    firma = _firma()
    # 1) cache a disco (norm -> [snomed, origen]); se reconstruye norm -> (entrada, origen)
    if os.path.exists(_CACHE_IDX):
        try:
            with open(_CACHE_IDX, encoding="utf-8") as f:
                cache = json.load(f)
            if cache.get("firma") == firma:
                return {n: (porancla[s], o) for n, (s, o) in cache["idx"].items()
                        if s in porancla}
        except Exception:
            pass
    # 2) construir. Cada clave guarda (entrada, origen): 'snomed' (descripción
    #    oficial) o 'extension' (alias local atado a un conceptId SNOMED real).
    syn = _sinonimos()
    idx = {}
    for e in CROSSWALK:                      # los 'dx' curados siempre entran
        n = _norm(e["dx"])
        if n:
            idx.setdefault(n, (e, "snomed"))
    for cid, info in syn.items():            # sinónimos de cada concepto del árbol
        entradas = [porancla[a] for a in info.get("anclas", []) if a in porancla]
        if not entradas:
            continue
        entrada = entradas[0]
        for t in info.get("es", []) + info.get("en", []):
            n = _norm(t)
            if n:
                idx.setdefault(n, (entrada, "snomed"))
    for a in EXTENSION_LOCAL:                # extensión local (alias -> concepto)
        entrada = porancla.get(a["snomed"])
        if entrada:
            n = _norm(a["alias"])
            if n:
                idx.setdefault(n, (entrada, "extension"))
    # 3) guardar (norm -> [snomed, origen], liviano)
    try:
        plano = {n: [e["snomed"], o] for n, (e, o) in idx.items()}
        with open(_CACHE_IDX, "w", encoding="utf-8") as f:
            json.dump({"firma": firma, "idx": plano}, f, ensure_ascii=False)
    except Exception:
        pass
    return idx


def _variantes(q):
    """Formas alternativas de la consulta por reglas lingüísticas (adjetivo ↔
    preposición), p.ej. 'diseccion aortica' -> 'diseccion de aorta'. No inventa
    términos: lleva la consulta a la forma que existe en SNOMED."""
    out = []
    for pat, rep in VARIANTES_LING:
        qv = re.sub(pat, rep, q)
        if qv != q and qv not in out:
            out.append(qv)
    return out


def _coincidencias(texto):
    """Devuelve lista de (entrada, termino_que_matcheo, origen).

    origen ∈ {'snomed' (descripción oficial), 'extension' (alias local),
              'variante' (forma lingüística llevada a la forma SNOMED)}.

    1) Match EXACTO con un término conocido (sinónimo SNOMED o alias local).
    2) Variantes lingüísticas de la consulta (adjetivo ↔ preposición).
    3) Contención SEGURA: un término conocido (≥3 letras) aparece como
       palabra(s) completa(s) DENTRO de la consulta (la consulta es más
       específica, ej. "tos seca" contiene "tos"). NO al revés.
    """
    q = _norm(texto)
    if not q:
        return []
    idx = _indice()
    if q in idx:
        entrada, origen = idx[q]
        return [(entrada, q, origen)]

    # Tier 1.5: variantes lingüísticas (la consulta llevada a la forma SNOMED).
    for qv in _variantes(q):
        if qv in idx:
            entrada, _ = idx[qv]
            return [(entrada, texto, "variante")]

    # Tier 2: un término conocido aparece como palabra(s) COMPLETA(S) dentro de
    # la consulta. Límite de palabra → seguro con términos cortos (tos, IAM…).
    res, vistos = [], set()
    for n, (e, origen) in idx.items():
        if len(n) >= 3 and re.search(r"(?<![a-z])" + re.escape(n) + r"(?![a-z])", q):
            if e["snomed"] not in vistos:
                vistos.add(e["snomed"])
                res.append((e, n, origen))
    res.sort(key=lambda x: -len(x[1]))
    return res


def resolver(texto):
    """
    Devuelve un dict explicable:
      {match, query, resultados: [ {dx, snomed, sinonimos, termino_match, origen,
                                    topicos: [{topico_en, topico_es, escenarios}]} ]}
    """
    out = {"match": False, "query": texto, "resultados": []}
    syn = _sinonimos()
    for entrada, termino, origen in _coincidencias(texto):
        topicos = []
        for nombre in entrada["topicos"]:
            escen = consulta_acr.escenarios_por_nombre_topico(nombre)
            topicos.append({"topico_en": nombre, "escenarios": escen})
        out["resultados"].append({
            "dx": entrada["dx"],
            "snomed": entrada["snomed"],
            "sinonimos": syn.get(entrada["snomed"], {}).get("es", []),
            "termino_match": termino,
            "origen": origen,
            "topicos": topicos,
        })
    out["match"] = bool(out["resultados"])
    return out


def diagnosticos_disponibles():
    """Lista de Dx del crosswalk (para autocompletar / mostrar)."""
    return sorted(e["dx"] for e in CROSSWALK)
