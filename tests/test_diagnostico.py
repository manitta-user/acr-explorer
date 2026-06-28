# -*- coding: utf-8 -*-
"""
Tests del resolver Dx -> tópico ACR.

El diccionario de sinónimos (acr_cache/sinonimos_snomed.json) se genera del RF2
SNOMED y NO está en el repo. Si falta, estos tests se SALTAN (skip), así el CI
pasa sin datos licenciados. Localmente, con los datos, validan el resolver.
Ejecutar:  python -m pytest tests/test_diagnostico.py -q
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from core import diagnostico as Dx

pytestmark = pytest.mark.skipif(
    not Dx.disponible(),
    reason="Falta acr_cache/sinonimos_snomed.json (datos SNOMED no incluidos en el repo)")


def _dx(q):
    r = Dx.resolver(q)
    return r["resultados"][0]["dx"] if r["match"] else None


def test_angor_es_angina():
    assert _dx("angor") == "Angina de pecho"


def test_iam():
    # "IAM" debe resolver a un Dx de infarto de miocardio (etiqueta exacta puede
    # variar entre concepto agudo/general; ambos van al mismo tópico ACR).
    assert "miocardio" in (_dx("IAM") or "").lower()


def test_subtipo_por_jerarquia():
    # subtipo no cargado a mano: resuelve por jerarquía IS-A
    assert _dx("leucemia mieloide aguda") == "Leucemia"
    assert _dx("neumonía bacteriana") == "Neumonía"


def test_no_match_falso():
    # 'colangitis' NO debe caer en un tópico equivocado (mejor sin match)
    r = Dx.resolver("colangitis")
    assert (not r["match"]) or (r["resultados"][0]["dx"] != "Hemorragia digestiva alta")


def test_dx_devuelve_topicos_y_snomed():
    r = Dx.resolver("apendicitis")
    assert r["match"]
    res = r["resultados"][0]
    assert res["snomed"] and res["topicos"]


def test_alias_local_marca_extension():
    # "TEP" no está en SNOMED-ES; lo reconoce la extensión local atada a 59282003.
    r = Dx.resolver("TEP")
    assert r["match"]
    res = r["resultados"][0]
    assert res["dx"] == "Embolia pulmonar"
    assert res["snomed"] == "59282003"
    assert res["origen"] == "extension"


def test_variante_linguistica_aortica():
    # "disección aórtica" (adjetivo) -> "disección de aorta" (forma SNOMED).
    r = Dx.resolver("disección aórtica")
    assert r["match"]
    res = r["resultados"][0]
    assert res["dx"] == "Disección de aorta"
    assert res["origen"] == "variante"


def test_termino_snomed_marca_origen_snomed():
    res = Dx.resolver("embolia pulmonar")["resultados"][0]
    assert res["origen"] == "snomed"


if __name__ == "__main__":
    if not Dx.disponible():
        print("SKIP: faltan datos SNOMED locales."); sys.exit(0)
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    fallos = 0
    for fn in fns:
        try:
            fn(); print(f"OK   {fn.__name__}")
        except AssertionError as e:
            fallos += 1; print(f"FALLA {fn.__name__}: {e}")
    print(f"\n{len(fns)-fallos}/{len(fns)} tests pasaron.")
    sys.exit(1 if fallos else 0)
