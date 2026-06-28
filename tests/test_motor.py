# -*- coding: utf-8 -*-
"""
Tests del motor de reglas. Ejecutar:  python -m pytest -q
(o sin pytest:  python tests/test_motor.py)
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.motor import evaluar


def _modalidad_top(res):
    """Modalidad de la recomendación mejor rankeada."""
    return res.estudios[0]["modalidad"]


def test_cefalea_thunderclap_es_tc():
    res = evaluar("cefalea", {"thunderclap": True})
    assert res.estudios[0]["adecuacion"] == "apropiado"
    assert "TC de cráneo" in _modalidad_top(res)


def test_cefalea_primaria_no_imagen():
    res = evaluar("cefalea", {"thunderclap": False, "banderas_rojas": False})
    assert all(e["adecuacion"] == "no_apropiado" for e in res.estudios)


def test_apendicitis_adulto_es_tc():
    res = evaluar("fid_apendicitis", {"grupo": "adulto"})
    assert "TC de abdomen" in _modalidad_top(res)


def test_apendicitis_embarazada_es_eco():
    res = evaluar("fid_apendicitis", {"grupo": "embarazada"})
    assert "Ecografía" in _modalidad_top(res)
    # la TC debe quedar como no apropiada
    tc = next(e for e in res.estudios if "TC" in e["modalidad"])
    assert tc["adecuacion"] == "no_apropiado"


def test_tep_baja_dimero_negativo_no_imagen():
    res = evaluar("tep", {"prob_clinica": "baja_intermedia", "dimero_d": "negativo"})
    assert res.escenario["id"] == "tep_baja_dimero_neg"
    assert _modalidad_top(res).startswith("Ningún estudio")


def test_tep_alta_probabilidad_es_ctpa():
    res = evaluar("tep", {"prob_clinica": "alta", "dimero_d": "no_realizado"})
    assert res.escenario["id"] == "tep_indicado"
    assert "Angio-TC" in _modalidad_top(res)


def test_tep_baja_dimero_positivo_es_ctpa():
    res = evaluar("tep", {"prob_clinica": "baja_intermedia", "dimero_d": "positivo"})
    assert res.escenario["id"] == "tep_indicado"


def test_tce_con_criterios_es_tc():
    res = evaluar("tce_leve", {"criterios_riesgo": True})
    assert "TC de cráneo" in _modalidad_top(res)
    assert res.estudios[0]["adecuacion"] == "apropiado"


def test_tce_sin_criterios_no_tc():
    res = evaluar("tce_leve", {"criterios_riesgo": False})
    assert res.estudios[0]["adecuacion"] == "no_apropiado"


def test_colico_renal_adulto_es_tc_sin_contraste():
    res = evaluar("colico_renal", {"grupo": "adulto_general"})
    assert "TC de abdomen" in _modalidad_top(res)
    assert "SIN contraste" in _modalidad_top(res)


def test_colico_renal_embarazada_es_eco():
    res = evaluar("colico_renal", {"grupo": "embarazada"})
    assert "Ecografía" in _modalidad_top(res)


def test_acv_candidato_es_tc_y_angiotc():
    res = evaluar("acv_agudo", {"ventana": "si_candidato"})
    metodos = {e["modalidad"] for e in res.estudios if e["adecuacion"] == "apropiado"}
    assert any("TC de cráneo" in m for m in metodos)
    assert any("Angio-TC" in m for m in metodos)


def test_diseccion_estable_es_angiotc_aorta():
    res = evaluar("diseccion_aortica", {"estabilidad": "estable"})
    assert "Angio-TC de aorta" in _modalidad_top(res)


def test_diseccion_inestable_incluye_ecocardio():
    res = evaluar("diseccion_aortica", {"estabilidad": "inestable"})
    assert any("Ecocardiograma" in e["modalidad"] for e in res.estudios)


def test_disnea_infeccion_es_rx():
    res = evaluar("disnea_aguda", {"sospecha": "infeccion_respiratoria"})
    assert "Radiografía de tórax" in _modalidad_top(res)


def test_compresion_con_deficit_es_rm_urgente():
    res = evaluar("compresion_medular", {"deficit": True})
    assert "RM de columna" in _modalidad_top(res)
    assert res.escenario["urgencia"] == "emergente"


def test_lumbalgia_simple_no_imagen():
    res = evaluar("compresion_medular", {"deficit": False})
    assert res.estudios[0]["adecuacion"] == "no_apropiado"


def test_tvp_baja_dimero_neg_no_imagen():
    res = evaluar("tvp", {"prob_wells": "baja", "dimero_d": "negativo"})
    assert res.escenario["id"] == "tvp_baja_dimero_neg"
    assert _modalidad_top(res).startswith("Ningún estudio")


def test_tvp_alta_es_eco_doppler():
    res = evaluar("tvp", {"prob_wells": "intermedia_alta", "dimero_d": "no_realizado"})
    assert "Eco-Doppler" in _modalidad_top(res)


def test_tvp_baja_dimero_positivo_es_eco():
    res = evaluar("tvp", {"prob_wells": "baja", "dimero_d": "positivo"})
    assert res.escenario["id"] == "tvp_indicada"


def test_obstruccion_probable_es_tc():
    res = evaluar("abdomen_agudo", {"gravedad": "obstruccion_probable"})
    assert "TC de abdomen" in _modalidad_top(res)


def test_todos_los_escenarios_tienen_campos_clinicos():
    """Cada escenario debe traer urgencia, pedido_sugerido y red_flags."""
    from data.criterios_acr import INDICACIONES
    for ind in INDICACIONES:
        for esc in ind["escenarios"]:
            assert esc.get("urgencia") in ("emergente", "urgente", "electivo"), ind["id"]
            assert esc.get("pedido_sugerido"), ind["id"]
            assert "red_flags" in esc, ind["id"]
            for est in esc["estudios"]:
                assert "metodo" in est and "contraste" in est, ind["id"]


def test_indicacion_desconocida_lanza_error():
    try:
        evaluar("no_existe", {})
        assert False, "debió lanzar ValueError"
    except ValueError:
        pass


if __name__ == "__main__":
    # Runner mínimo sin pytest
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    fallos = 0
    for fn in fns:
        try:
            fn()
            print(f"OK   {fn.__name__}")
        except AssertionError as e:
            fallos += 1
            print(f"FALLA {fn.__name__}: {e}")
    print(f"\n{len(fns) - fallos}/{len(fns)} tests pasaron.")
    sys.exit(1 if fallos else 0)
