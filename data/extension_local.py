# -*- coding: utf-8 -*-
"""
Extensión local del proyecto (capa de superficie sobre SNOMED CT).

SNOMED CT en español NO incluye ciertos acrónimos clínicos de uso corriente
(TEP, HSA, TCE…) ni la forma ADJETIVAL de algunos términos ("disección aórtica"
en vez de la forma preposicional "disección de aorta", que sí está en SNOMED).
Esta capa los reconoce SIN inventar conceptos:

  • ALIAS_LOCALES — cada alias se ata a un conceptId SNOMED REAL ya existente y
    anclado a un tópico ACR. Es el mecanismo de una extensión nacional: agregar
    una descripción/sinónimo a un concepto internacional. El match se marca con
    origen 'extension' y se muestra al usuario (transparencia total).

  • VARIANTES_LING — reglas morfológicas del español (adjetivo ↔ preposición).
    NO agregan términos nuevos: transforman la consulta a la forma que SÍ está
    en SNOMED. El match se marca con origen 'variante'.

Verificado (2026-06) contra tres releases: SNOMED-AR Edition, AR Extension y
Spanish International (1.16M descripciones). Ninguno contiene estos acrónimos;
sí llevan la abreviatura inglesa (p.ej. "PE" para embolia pulmonar), no la
española. Por eso esta capa es local y explícita.
"""

# Acrónimo (lo que el médico escribe) -> conceptId SNOMED real (ya anclado).
# Solo acrónimos médicos ESTÁNDAR cuyo concepto tiene tópico ACR (si no, no
# aportaría un estudio). No se incluyen coloquialismos.
ALIAS_LOCALES = [
    {"alias": "TEP", "snomed": "59282003",  "nota": "tromboembolismo pulmonar"},
    {"alias": "TVP", "snomed": "128053003", "nota": "trombosis venosa profunda"},
    {"alias": "TCE", "snomed": "82271004",  "nota": "traumatismo craneoencefálico"},
    {"alias": "HSA", "snomed": "21454007",  "nota": "hemorragia subaracnoidea"},
    {"alias": "ICC", "snomed": "84114007",  "nota": "insuficiencia cardíaca congestiva"},
    {"alias": "HDA", "snomed": "37372002",  "nota": "hemorragia digestiva alta"},
]

# Reglas lingüísticas: (regex sobre texto YA normalizado y sin acentos) -> forma
# preposicional que existe en SNOMED. Extensible: agregar pares verificados.
VARIANTES_LING = [
    (r"(?<![a-z])aortica(?![a-z])", "de aorta"),   # disección aórtica → de aorta
]
