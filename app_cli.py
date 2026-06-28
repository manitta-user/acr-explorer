# -*- coding: utf-8 -*-
"""
Validador de adecuación de estudios (estilo ACR) — interfaz de consola.

Uso:
    python app_cli.py

No requiere dependencias externas. Para la versión web: app_streamlit.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# En la consola de Windows, forzar UTF-8 para que los acentos se vean bien.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

from data.criterios_acr import INDICACIONES, URGENCIA, CONSIDERACIONES_SEGURIDAD
from core.motor import evaluar, etiqueta_adecuacion

DISCLAIMER = (
    "\n" + "=" * 70 + "\n"
    "  HERRAMIENTA EDUCATIVA — NO para uso clínico real.\n"
    "  Basada de forma SIMPLIFICADA en los ACR Appropriateness Criteria(R).\n"
    "  Siempre validar con un médico y con la fuente oficial:\n"
    "  https://acsearch.acr.org/list\n"
    + "=" * 70
)

ICONO = {
    "apropiado": "[ OK ]",
    "puede": "[ ~  ]",
    "no_apropiado": "[ NO ]",
}


def _preguntar_opcion(texto, opciones):
    print("\n" + texto)
    for i, op in enumerate(opciones, 1):
        print(f"  {i}) {op}")
    while True:
        sel = input("Elegí número: ").strip()
        if sel.isdigit() and 1 <= int(sel) <= len(opciones):
            return opciones[int(sel) - 1]
        print("  Opción inválida.")


def _preguntar_bool(texto):
    while True:
        sel = input(f"\n{texto}\n  (s/n): ").strip().lower()
        if sel in ("s", "si", "sí", "y"):
            return True
        if sel in ("n", "no"):
            return False
        print("  Respondé s o n.")


def recolectar_respuestas(indicacion):
    respuestas = {}
    for p in indicacion["preguntas"]:
        # En TEP, el dímero-D solo se pregunta si la prob no es alta
        if (indicacion["id"] == "tep" and p["id"] == "dimero_d"
                and respuestas.get("prob_clinica") == "alta"):
            respuestas[p["id"]] = "no_realizado"
            continue
        # En TVP, el dímero-D solo aplica si la probabilidad es baja
        if (indicacion["id"] == "tvp" and p["id"] == "dimero_d"
                and respuestas.get("prob_wells") != "baja"):
            respuestas[p["id"]] = "no_realizado"
            continue
        if p["tipo"] == "bool":
            respuestas[p["id"]] = _preguntar_bool(p["texto"])
        elif p["tipo"] == "opcion":
            respuestas[p["id"]] = _preguntar_opcion(p["texto"], p["opciones"])
    return respuestas


def mostrar_resultado(res):
    esc = res.escenario
    ind = res.indicacion
    print("\n" + "-" * 70)
    print(f"INDICACIÓN: {ind['titulo']}")
    print(f"ESCENARIO : {esc['descripcion']}")
    print(f"URGENCIA  : {URGENCIA.get(esc.get('urgencia'), esc.get('urgencia',''))}")
    print("-" * 70)
    for e in res.estudios:
        print(f"\n{ICONO.get(e['adecuacion'], '')} {e['modalidad']}  [{e.get('metodo','')}]")
        print(f"      Adecuación: {etiqueta_adecuacion(e['adecuacion'])}"
              f"   |   Radiación: {e['dosis'] or '—'}"
              f"   |   Contraste: {e.get('contraste','—')}")
        print(f"      {e['comentario']}")

    if esc.get("red_flags"):
        print("\n  BANDERAS ROJAS a vigilar:")
        for rf in esc["red_flags"]:
            print(f"    - {rf}")

    print("\n  PEDIDO SUGERIDO (copiar a la orden):")
    print(f"    \"{esc.get('pedido_sugerido','')}\"")

    # Recordatorios de seguridad según contraste presente
    contrastes = " ".join(e.get("contraste", "") for e in res.estudios).lower()
    avisos = []
    if "yodado" in contrastes:
        avisos.append(CONSIDERACIONES_SEGURIDAD["contraste_yodado"])
    if "gadolinio" in contrastes:
        avisos.append(CONSIDERACIONES_SEGURIDAD["gadolinio"])
    if any("RM" == e.get("metodo") for e in res.estudios):
        avisos.append(CONSIDERACIONES_SEGURIDAD["seguridad_rm"])
    if avisos:
        print("\n  SEGURIDAD:")
        for a in avisos:
            print(f"    ! {a}")

    sn = ind.get("snomed")
    print("\n" + "-" * 70)
    print(f"Fuente: {res.referencia}")
    if ind.get("acr_url"):
        print(f"        {ind['acr_url']}  (ACR id {ind.get('acr_id','')})")
    if sn:
        print(f"SNOMED CT (candidato, {sn['estado']}): {sn['concept_id']} — {sn['termino']}")
    print("-" * 70)


def main():
    print(DISCLAIMER)
    print("\nIndicaciones disponibles:")
    for i, ind in enumerate(INDICACIONES, 1):
        print(f"  {i}) {ind['titulo']}")

    while True:
        sel = input("\nElegí una indicación (número, o 'q' para salir): ").strip()
        if sel.lower() == "q":
            print("Listo. ¡Hasta luego!")
            return
        if sel.isdigit() and 1 <= int(sel) <= len(INDICACIONES):
            indicacion = INDICACIONES[int(sel) - 1]
            respuestas = recolectar_respuestas(indicacion)
            try:
                res = evaluar(indicacion["id"], respuestas)
                mostrar_resultado(res)
            except ValueError as e:
                print(f"\n[error] {e}")
        else:
            print("  Opción inválida.")


if __name__ == "__main__":
    main()
