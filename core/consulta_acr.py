# -*- coding: utf-8 -*-
"""
Consulta del dataset estructurado del portal ACR AC (acr_cache/portal_data.json).

Permite:
  - escenarios_por_topico(topic_id)  -> todos los escenarios de un tópico
  - buscar(texto, panel, limite)     -> búsqueda libre en los 4115 escenarios
  - disponible()                     -> si el dataset fue extraído

El dataset es de CONSULTA PERSONAL (ver acr_cache/.gitignore). Si no existe,
las funciones devuelven vacío y la app sigue funcionando con sus criterios
propios.
"""

import os, json, functools, re, unicodedata
from core import traduccion as _T


def _stem(tok):
    """Stem mínimo: tolera género/número quitando plural y vocal final."""
    if len(tok) > 4 and tok.endswith("s"):
        tok = tok[:-1]
    if len(tok) > 3 and tok[-1] in "aeo":
        tok = tok[:-1]
    return tok


def _norm(texto):
    """Normaliza para búsqueda: minúsculas, sin acentos, expande 'o/a' a ambas
    formas, y aplica stemming por token (gé­nero/número-insensible)."""
    texto = (texto or "").lower()
    texto = re.sub(r'(\w+?)o/a\b', r'\1o \1a', texto)  # agudo/a -> agudo aguda
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(_stem(t) for t in texto.split())

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_JSON = os.path.join(RAIZ, "acr_cache", "portal_data.json")
_CACHE_BUSQ = os.path.join(RAIZ, "acr_cache", "_idx_busqueda.json")


def _firma(*paths):
    """Firma de invalidación: mtime+tamaño de los archivos fuente."""
    partes = []
    for p in paths:
        try:
            st = os.stat(p)
            partes.append(f"{int(st.st_mtime)}:{st.st_size}")
        except OSError:
            partes.append("-")
    return "|".join(partes)

# Etiqueta legible de categoría (igual esquema que el motor)
CATEGORIA = {
    "apropiado": "Usualmente apropiado",
    "puede": "Puede ser apropiado",
    "no_apropiado": "Usualmente NO apropiado",
}
ORDEN = {"apropiado": 0, "puede": 1, "no_apropiado": 2}

# Fase clínica del escenario ACR: qué pedir PRIMERO (inicial) vs después.
# Permite mostrar siempre los estudios iniciales arriba.
FASE_RANK = {"inicial": 0, "tamizaje": 1, "otro": 2, "siguiente": 3, "seguimiento": 4}
FASE_ES = {
    "inicial": "Inicial",
    "tamizaje": "Tamizaje",
    "siguiente": "Siguiente estudio",
    "seguimiento": "Seguimiento",
    "otro": "",
}


def fase_escenario(escenario):
    """Clasifica un escenario ACR por su fase: 'inicial' (qué pedir primero),
    'siguiente' (estudio posterior según resultado), 'seguimiento'
    (vigilancia/restaging), 'tamizaje' o 'otro'."""
    s = (escenario or "").lower()
    if "screening" in s:
        return "tamizaje"
    if "initial" in s and "imaging" in s:
        return "inicial"
    if any(k in s for k in ("next imaging", "next study", "next test",
                            "equivocal", "negative", "positive,")):
        return "siguiente"
    if any(k in s for k in ("follow-up", "follow up", "surveillance", "restaging",
                            "recurren", "posttreatment", "post-treatment",
                            "after treatment", "after therapy", "treatment response",
                            "remission", "response assessment")):
        return "seguimiento"
    return "otro"


def _ordenar_escenarios(escenarios):
    """Devuelve los escenarios con la fase anotada y ordenados: iniciales primero.
    Estable: respeta el orden original dentro de cada fase."""
    out = []
    for e in escenarios:
        ec = dict(e)
        ec["procedimientos"] = _ordenar_procs(e.get("procedimientos", []))
        ec["fase"] = fase_escenario(e.get("escenario", ""))
        out.append(ec)
    out.sort(key=lambda e: FASE_RANK.get(e["fase"], 2))
    return out


def disponible():
    return os.path.exists(DATA_JSON)


@functools.lru_cache(maxsize=1)
def _cargar():
    if not disponible():
        return []
    with open(DATA_JSON, encoding="utf-8") as f:
        return json.load(f)


def _ordenar_procs(procs):
    return sorted(procs, key=lambda p: ORDEN.get(p.get("adecuacion"), 9))


@functools.lru_cache(maxsize=1)
def _indice_busqueda():
    """Blob de búsqueda por escenario (clave = senario_id): inglés + traducción ES.
    Cacheado a disco con firma de invalidación → primera búsqueda instantánea."""
    firma = _firma(DATA_JSON, _T.__file__)
    # 1) intentar cache a disco
    if os.path.exists(_CACHE_BUSQ):
        try:
            with open(_CACHE_BUSQ, encoding="utf-8") as f:
                cache = json.load(f)
            if cache.get("firma") == firma:
                return cache["idx"]
        except Exception:
            pass
    # 2) construir y guardar
    idx = {}
    for e in _cargar():
        en = e.get("escenario", "") + " " + e.get("topico", "")
        es = (_T.traducir_clinico(e.get("escenario", "")) + " " +
              _T.traducir_topico(e.get("topico", "")))
        idx[e["senario_id"]] = _norm(en + " " + es)
    try:
        with open(_CACHE_BUSQ, "w", encoding="utf-8") as f:
            json.dump({"firma": firma, "idx": idx}, f, ensure_ascii=False)
    except Exception:
        pass
    return idx


def escenarios_por_topico(topic_id):
    """Escenarios ACR de un tópico, con fase anotada y los iniciales primero."""
    if topic_id is None:
        return []
    return _ordenar_escenarios(
        [e for e in _cargar() if str(e.get("topic_id")) == str(topic_id)])


def escenarios_por_nombre_topico(nombre):
    """Igual que escenarios_por_topico pero por el nombre del tópico (campo 'topico')."""
    if not nombre:
        return []
    return _ordenar_escenarios(
        [e for e in _cargar() if e.get("topico") == nombre])


def buscar(texto="", panel=None, limite=50):
    """Búsqueda libre por texto del escenario / tópico, opcionalmente por panel."""
    texto = (texto or "").lower().strip()
    claves = [c for c in texto.split() if c]
    res = []
    for e in _cargar():
        if panel and e.get("panel", "").lower() != panel.lower():
            continue
        blob = (e.get("escenario", "") + " " + e.get("topico", "")).lower()
        if all(c in blob for c in claves):
            res.append(e)
        if len(res) >= limite:
            break
    return res


def filtrar(texto="", paneles=None, sexos=None, areas=None, fases=None,
            solo_con_apropiado=False, limite=60):
    """Filtro combinado para el explorador. Devuelve (resultados, total_sin_limite)."""
    claves = [c for c in _norm(texto).split() if c]
    paneles = set(paneles or [])
    sexos = set(sexos or [])
    areas = set(areas or [])
    fases = set(fases or [])
    idx = _indice_busqueda() if claves else {}
    res, total = [], 0
    for e in _cargar():
        if paneles and e.get("panel") not in paneles:
            continue
        if sexos and e.get("sexo") not in sexos:
            continue
        if areas and e.get("area_corporal") not in areas:
            continue
        if fases and fase_escenario(e.get("escenario", "")) not in fases:
            continue
        if claves:
            blob = idx.get(e["senario_id"], "")
            if not all(c in blob for c in claves):
                continue
        if solo_con_apropiado and not any(
                p.get("adecuacion") == "apropiado" for p in e.get("procedimientos", [])):
            continue
        total += 1
        if len(res) < limite:
            ec = dict(e)
            ec["procedimientos"] = _ordenar_procs(e.get("procedimientos", []))
            ec["fase"] = fase_escenario(e.get("escenario", ""))
            res.append(ec)
    return res, total


def paneles():
    return sorted({e.get("panel", "") for e in _cargar() if e.get("panel")})


def valores(campo):
    """Valores distintos de un campo (ej. 'sexo', 'area_corporal'), ordenados."""
    return sorted({e.get(campo, "") for e in _cargar() if e.get(campo)})


def estadisticas():
    d = _cargar()
    return {
        "escenarios": len(d),
        "procedimientos": sum(len(e.get("procedimientos", [])) for e in d),
        "topicos": len({e.get("topic_id") for e in d}),
    }
