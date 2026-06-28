# -*- coding: utf-8 -*-
"""
Tests del traductor médico EN->ES. No requieren datos licenciados (glosario puro).
Ejecutar:  python -m pytest tests/test_traduccion.py -q
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import traduccion as T


# ----------------------------- procedimientos -----------------------------
def test_proc_tc_torax():
    assert T.traducir_procedimiento("CT chest with IV contrast") == \
        "TC de tórax con contraste EV"


def test_proc_rm_craneo():
    assert T.traducir_procedimiento("MRI head without and with IV contrast") == \
        "RM de cráneo sin y con contraste EV"


def test_proc_ecocardiograma():
    assert "ecocardiograma transesofágico" in \
        T.traducir_procedimiento("US echocardiography transesophageal").lower()


def test_proc_sin_doble_de():
    # 'abdomen and pelvis' no debe producir 'de abdomen y de pelvis'
    out = T.traducir_procedimiento("CT abdomen and pelvis with IV contrast")
    assert out == "TC de abdomen y pelvis con contraste EV"


# ----------------------------- categorías / dosis -------------------------
def test_categoria():
    assert T.traducir_categoria("Usually appropriate") == "Usualmente apropiado"
    assert T.traducir_categoria("Usually not appropriate") == "Usualmente no apropiado"


def test_panel():
    assert T.traducir_panel("Neurologic") == "Neurológico"
    assert T.traducir_panel("Breast") == "Mama"


# ----------------------------- escenarios (clínico) -----------------------
def test_clinico_apendicitis_orden():
    # 'acute appendicitis' -> reordena a 'apendicitis aguda'
    out = T.traducir_clinico("Suspected acute appendicitis, initial imaging")
    assert out == "Sospecha de apendicitis aguda, estudio inicial"


def test_clinico_tamizaje():
    assert T.traducir_clinico("Breast cancer screening") == "Tamizaje de cáncer de mama"


def test_clinico_no_queda_ingles_comun():
    # términos que SÍ deben estar traducidos
    out = T.traducir_clinico("Seizure disorder, change in clinical symptoms").lower()
    for w in ("seizure", "disorder", "change", "symptoms"):
        assert w not in out


# ----------------------------- no destructivo -----------------------------
def test_traduccion_no_muta_entrada():
    s = "CT chest with IV contrast"
    _ = T.traducir_procedimiento(s)
    assert s == "CT chest with IV contrast"


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
