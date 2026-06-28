# -*- coding: utf-8 -*-
"""
Crosswalk Diagnóstico (SNOMED CT) -> Tópico(s) ACR.

CROSSWALK se carga de acr_cache/crosswalk_resuelto.json, generado por:
    python tools/importar_snomed.py anclar      (resuelve data/anclas_terminos.py)

Cada entrada: {dx, snomed, topicos:[nombres exactos de tópico ACR]}.
Los sinónimos de cada concepto (y sus descendientes por jerarquía IS-A) se
extraen del RF2 con `python tools/importar_snomed.py extraer`.

Si el JSON no existe (no se corrió el pipeline SNOMED), se usa un seed mínimo
para que la app no falle.
"""

import os, json

_JSON = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "acr_cache", "crosswalk_resuelto.json")

# Seed mínimo de respaldo (si falta el JSON resuelto)
_SEED = [
    {"dx": "Angina de pecho", "snomed": "194828000",
     "topicos": ["Chest Pain-Possible Acute Coronary Syndrome",
                 "Chronic Chest Pain-High Probability of Coronary Artery Disease"]},
    {"dx": "Embolia pulmonar", "snomed": "59282003",
     "topicos": ["Suspected Pulmonary Embolism"]},
    {"dx": "Apendicitis", "snomed": "74400008", "topicos": ["Right Lower Quadrant Pain"]},
]


def _cargar():
    if os.path.exists(_JSON):
        with open(_JSON, encoding="utf-8") as f:
            return json.load(f)
    return _SEED


CROSSWALK = _cargar()


def conceptos():
    return {e["snomed"] for e in CROSSWALK}
