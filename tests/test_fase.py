# -*- coding: utf-8 -*-
"""
Tests del clasificador de fase del escenario ACR (inicial vs siguiente/seguimiento).
Es lógica pura (no usa datos licenciados), así que corre siempre.
Ejecutar:  python -m pytest tests/test_fase.py -q
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.consulta_acr import fase_escenario, FASE_RANK, _ordenar_escenarios


def test_inicial():
    assert fase_escenario("RUQ pain, etiology unknown, initial imaging") == "inicial"
    assert fase_escenario("Axillary lump, palpable, initial axilla imaging") == "inicial"


def test_siguiente():
    assert fase_escenario("RUQ pain, US equivocal, next imaging study") == "siguiente"


def test_seguimiento():
    assert fase_escenario("Lung cancer, surveillance after treatment") == "seguimiento"


def test_tamizaje():
    assert fase_escenario("Breast cancer screening, average risk") == "tamizaje"


def test_inicial_va_primero():
    crudos = [
        {"escenario": "X, US negative, next imaging study", "procedimientos": []},
        {"escenario": "X, initial imaging", "procedimientos": []},
        {"escenario": "X, surveillance", "procedimientos": []},
    ]
    fases = [e["fase"] for e in _ordenar_escenarios(crudos)]
    assert fases[0] == "inicial"
    assert FASE_RANK[fases[0]] <= FASE_RANK[fases[1]] <= FASE_RANK[fases[2]]


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    fallos = 0
    for fn in fns:
        try:
            fn(); print(f"OK   {fn.__name__}")
        except AssertionError as e:
            fallos += 1; print(f"FALLA {fn.__name__}: {e}")
    print(f"\n{len(fns)-fallos}/{len(fns)} tests pasaron.")
    sys.exit(1 if fallos else 0)
