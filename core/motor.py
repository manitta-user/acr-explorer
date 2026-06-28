# -*- coding: utf-8 -*-
"""
Motor de evaluación: dada una indicación y las respuestas del usuario,
selecciona el escenario clínico que corresponde y devuelve los estudios
ordenados por adecuación.

Sin dependencias externas: pura lógica de reglas.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.criterios_acr import (
    INDICACIONES, ADECUACION, ORDEN_ADECUACION, indicacion_por_id,
)


class ResultadoEvaluacion:
    def __init__(self, indicacion, escenario, estudios):
        self.indicacion = indicacion
        self.escenario = escenario
        self.estudios = estudios  # ya ordenados

    @property
    def referencia(self):
        return self.indicacion["referencia"]


def _coincide(escenario, respuestas):
    """True si TODAS las condiciones del escenario se cumplen en respuestas."""
    for clave, esperado in escenario["condiciones"].items():
        if respuestas.get(clave) != esperado:
            return False
    return True


def _ordenar_estudios(estudios):
    prioridad = {cat: i for i, cat in enumerate(ORDEN_ADECUACION)}
    return sorted(estudios, key=lambda e: prioridad.get(e["adecuacion"], 99))


def seleccionar_escenario(indicacion, respuestas):
    """
    Devuelve el escenario que aplica.

    Caso especial TEP: el escenario 'indicado' aplica cuando la probabilidad
    es alta O (probabilidad baja/intermedia con dímero-D positivo o no
    realizado). Esa lógica de 'O' no se expresa con un dict simple de
    condiciones, así que se resuelve aquí.
    """
    if indicacion["id"] == "tep":
        prob = respuestas.get("prob_clinica")
        dimero = respuestas.get("dimero_d")
        if prob == "baja_intermedia" and dimero == "negativo":
            return next(e for e in indicacion["escenarios"]
                        if e["id"] == "tep_baja_dimero_neg")
        return next(e for e in indicacion["escenarios"]
                    if e["id"] == "tep_indicado")

    # Caso especial TVP: misma lógica de 'O'. Solo se descarta sin imagen
    # cuando probabilidad baja Y dímero-D negativo.
    if indicacion["id"] == "tvp":
        prob = respuestas.get("prob_wells")
        dimero = respuestas.get("dimero_d")
        if prob == "baja" and dimero == "negativo":
            return next(e for e in indicacion["escenarios"]
                        if e["id"] == "tvp_baja_dimero_neg")
        return next(e for e in indicacion["escenarios"]
                    if e["id"] == "tvp_indicada")

    # Caso general: primer escenario cuyas condiciones coinciden
    for escenario in indicacion["escenarios"]:
        if _coincide(escenario, respuestas):
            return escenario
    return None


def evaluar(ind_id, respuestas):
    """
    Punto de entrada principal.
      ind_id     : id de la indicación (str)
      respuestas : dict {id_pregunta: valor}
    Devuelve ResultadoEvaluacion o lanza ValueError.
    """
    indicacion = indicacion_por_id(ind_id)
    if indicacion is None:
        raise ValueError(f"Indicación desconocida: {ind_id}")

    escenario = seleccionar_escenario(indicacion, respuestas)
    if escenario is None:
        raise ValueError("No se encontró un escenario que coincida con las "
                         "respuestas dadas.")

    estudios = _ordenar_estudios(escenario["estudios"])
    return ResultadoEvaluacion(indicacion, escenario, estudios)


def etiqueta_adecuacion(clave):
    return ADECUACION.get(clave, clave)
