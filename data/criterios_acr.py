# -*- coding: utf-8 -*-
"""
Base de conocimiento: indicaciones de estudios por imágenes codificadas a
partir de los ACR Appropriateness Criteria(R), pensada como apoyo a la
DECISIÓN de qué estudio pedir (guardia / sala / terapia intensiva).

==========================  AVISO IMPORTANTE  ==========================
Material EDUCATIVO / de APOYO. NO reemplaza el juicio médico ni el
protocolo de cada institución. Los criterios ACR son extensos y se
actualizan; aquí hay una versión SIMPLIFICADA de algunos escenarios.
Verificar siempre contra la fuente oficial: https://acsearch.acr.org/list
Los códigos SNOMED CT son CANDIDATOS y deben validarse en el navegador
oficial antes de cualquier uso real: https://browser.ihtsdotools.org
========================================================================

Modelo de datos
---------------
INDICACION:
  id, titulo, descripcion
  area        : dónde es útil  -> ["guardia","sala","terapia","ambulatorio"]
  snomed      : {concept_id, termino, estado: "verificado"|"a_verificar"}
  referencia  : cita de la fuente ACR
  preguntas   : variables clínicas que responde el usuario
  escenarios  : variantes clínicas. Cada ESCENARIO:
        id, descripcion, condiciones {id_pregunta: valor}
        urgencia        : "emergente" | "urgente" | "electivo"
        red_flags       : lista de banderas rojas a vigilar
        pedido_sugerido : texto listo para copiar en la orden
        estudios        : lista de recomendaciones. Cada ESTUDIO:
              modalidad, metodo, adecuacion, dosis, contraste, comentario

Niveles de adecuación (escala ACR resumida a 3 categorías):
  "apropiado"     -> Usualmente apropiado     (ACR 7-9)
  "puede"         -> Puede ser apropiado       (ACR 4-6)
  "no_apropiado"  -> Usualmente NO apropiado    (ACR 1-3)

Dosis de radiación relativa (estilo ACR, "O" a "ooooo"):
  "O" ninguna · "oo" baja · "ooo" media · "oooo" alta · "ooooo" muy alta
"""

ADECUACION = {
    "apropiado": "Usualmente apropiado",
    "puede": "Puede ser apropiado",
    "no_apropiado": "Usualmente NO apropiado",
}
ORDEN_ADECUACION = ["apropiado", "puede", "no_apropiado"]

# Métodos de imagen contemplados
METODOS = ["Rx", "Ecografía", "TC", "RM", "Medicina Nuclear", "Angiografía"]

URGENCIA = {
    "emergente": "EMERGENTE (minutos)",
    "urgente": "Urgente (horas)",
    "electivo": "Electivo (programado)",
}

# ----------------------------------------------------------------------
# Consideraciones de seguridad transversales (se muestran como recordatorio)
# ----------------------------------------------------------------------
CONSIDERACIONES_SEGURIDAD = {
    "contraste_yodado": (
        "Contraste yodado (TC/angio): preguntar por alergia previa, asma, "
        "función renal (eGFR). En eGFR < 30 evaluar riesgo/beneficio e "
        "hidratación. Metformina: suspender según protocolo si eGFR bajo."
    ),
    "gadolinio": (
        "Gadolinio (RM): precaución en eGFR < 30 (riesgo de fibrosis "
        "sistémica nefrogénica). Evaluar alternativas o agentes macrocíclicos."
    ),
    "embarazo": (
        "Embarazo: preferir métodos sin radiación (eco, RM sin gadolinio). "
        "Si la TC es imprescindible, justificar y minimizar dosis."
    ),
    "seguridad_rm": (
        "Seguridad RM: chequear marcapasos/DAI, clips, implantes, cuerpos "
        "extraños metálicos, claustrofobia. Confirmar compatibilidad."
    ),
    "paciente_critico": (
        "Paciente crítico/inestable: la RM y traslados largos pueden ser "
        "riesgosos. Priorizar estudios al lado de la cama (Rx, eco) o TC "
        "rápida según estabilidad."
    ),
}


INDICACIONES = [
    # ================================================================ 1
    {
        "id": "cefalea",
        "titulo": "Cefalea (dolor de cabeza)",
        "descripcion": "Adulto con cefalea. El escenario cambia radicalmente la conducta.",
        "area": ["guardia", "ambulatorio", "sala"],
        "snomed": {"concept_id": "25064002", "termino": "Cefalea (hallazgo)",
                   "estado": "a_verificar"},
        "referencia": "ACR Appropriateness Criteria(R) — Headache.",
        "acr_id": "69482",
        "acr_url": "https://acsearch.acr.org/docs/69482/Narrative/",
        "portal_topic_id": "140",
        "preguntas": [
            {"id": "thunderclap",
             "texto": "¿Cefalea súbita, severa, en 'estallido' (thunderclap, máxima "
                      "intensidad en <1 min)?", "tipo": "bool"},
            {"id": "banderas_rojas",
             "texto": "¿Signos de alarma? (déficit neurológico nuevo, inmunosupresión/"
                      "cáncer, edema de papila, >50 años de inicio nuevo, fiebre + "
                      "rigidez de nuca)", "tipo": "bool"},
        ],
        "escenarios": [
            {
                "id": "cefalea_thunderclap",
                "descripcion": "Cefalea en estallido (sospecha de hemorragia subaracnoidea).",
                "condiciones": {"thunderclap": True},
                "urgencia": "emergente",
                "red_flags": ["Peor cefalea de la vida", "Síncope o convulsión asociada",
                              "Rigidez de nuca"],
                "pedido_sugerido": "TC de cráneo sin contraste URGENTE por cefalea súbita "
                                   "en estallido — descartar hemorragia subaracnoidea. "
                                   "Si negativa y alta sospecha, valorar PL / angio-TC.",
                "estudios": [
                    {"modalidad": "TC de cráneo SIN contraste", "metodo": "TC",
                     "adecuacion": "apropiado", "dosis": "ooo", "contraste": "No",
                     "comentario": "Primera línea para hemorragia aguda. Si es negativa "
                                   "y persiste sospecha: punción lumbar o angio-TC."},
                    {"modalidad": "Angio-TC de cabeza y cuello", "metodo": "Angiografía",
                     "adecuacion": "puede", "dosis": "ooo", "contraste": "Yodado IV",
                     "comentario": "Útil para buscar aneurisma como causa."},
                    {"modalidad": "RM de cerebro sin/con contraste", "metodo": "RM",
                     "adecuacion": "puede", "dosis": "O", "contraste": "Gadolinio (según)",
                     "comentario": "Alternativa sin radiación, menor disponibilidad en agudo."},
                ],
            },
            {
                "id": "cefalea_banderas",
                "descripcion": "Cefalea con signos de alarma (sin estallido).",
                "condiciones": {"thunderclap": False, "banderas_rojas": True},
                "urgencia": "urgente",
                "red_flags": ["Déficit focal", "Edema de papila", "Cáncer/inmunosupresión"],
                "pedido_sugerido": "RM de cerebro sin y con contraste por cefalea con "
                                   "signos de alarma — descartar causa estructural.",
                "estudios": [
                    {"modalidad": "RM de cerebro sin y con contraste", "metodo": "RM",
                     "adecuacion": "apropiado", "dosis": "O", "contraste": "Gadolinio",
                     "comentario": "Mejor caracterización de causas estructurales/"
                                   "tumorales/inflamatorias."},
                    {"modalidad": "TC de cráneo sin contraste", "metodo": "TC",
                     "adecuacion": "puede", "dosis": "ooo", "contraste": "No",
                     "comentario": "Si RM no disponible o para descartar sangrado agudo."},
                ],
            },
            {
                "id": "cefalea_primaria",
                "descripcion": "Cefalea sin estallido y sin signos de alarma (tensional/migraña típica).",
                "condiciones": {"thunderclap": False, "banderas_rojas": False},
                "urgencia": "electivo",
                "red_flags": [],
                "pedido_sugerido": "No solicitar neuroimagen de rutina. Manejo clínico y "
                                   "reevaluación; imágenes solo si aparecen banderas rojas.",
                "estudios": [
                    {"modalidad": "TC de cráneo sin contraste", "metodo": "TC",
                     "adecuacion": "no_apropiado", "dosis": "ooo", "contraste": "No",
                     "comentario": "La neuroimagen de rutina NO está indicada en cefalea "
                                   "primaria típica sin banderas rojas (Choosing Wisely)."},
                    {"modalidad": "RM de cerebro", "metodo": "RM",
                     "adecuacion": "no_apropiado", "dosis": "O", "contraste": "Según",
                     "comentario": "Tampoco indicada de rutina; evaluar clínicamente."},
                ],
            },
        ],
    },

    # ================================================================ 2
    {
        "id": "fid_apendicitis",
        "titulo": "Dolor en fosa ilíaca derecha — sospecha de apendicitis",
        "descripcion": "Dolor abdominal agudo en cuadrante inferior derecho.",
        "area": ["guardia", "sala"],
        "snomed": {"concept_id": "74400008", "termino": "Apendicitis (trastorno)",
                   "estado": "a_verificar"},
        "referencia": "ACR Appropriateness Criteria(R) — Right Lower Quadrant Pain "
                      "(sospecha de apendicitis).",
        "acr_id": "69357",
        "acr_url": "https://acsearch.acr.org/docs/69357/Narrative/",
        "portal_topic_id": "21",
        "preguntas": [
            {"id": "grupo", "texto": "Grupo de paciente", "tipo": "opcion",
             "opciones": ["adulto", "embarazada", "nino"]},
        ],
        "escenarios": [
            {
                "id": "apendicitis_adulto",
                "descripcion": "Adulto, sospecha de apendicitis.",
                "condiciones": {"grupo": "adulto"},
                "urgencia": "urgente",
                "red_flags": ["Signos de peritonitis", "Sepsis"],
                "pedido_sugerido": "TC de abdomen y pelvis con contraste IV por sospecha "
                                   "de apendicitis aguda en adulto.",
                "estudios": [
                    {"modalidad": "TC de abdomen y pelvis CON contraste IV", "metodo": "TC",
                     "adecuacion": "apropiado", "dosis": "oooo", "contraste": "Yodado IV",
                     "comentario": "Alta sensibilidad/especificidad. Elección en el adulto."},
                    {"modalidad": "Ecografía de abdomen (cuadrante inferior derecho)",
                     "metodo": "Ecografía", "adecuacion": "puede", "dosis": "O",
                     "contraste": "No",
                     "comentario": "Razonable primero en delgados/jóvenes para evitar radiación."},
                    {"modalidad": "RM de abdomen y pelvis sin contraste", "metodo": "RM",
                     "adecuacion": "puede", "dosis": "O", "contraste": "No",
                     "comentario": "Alternativa sin radiación si está disponible."},
                ],
            },
            {
                "id": "apendicitis_embarazada",
                "descripcion": "Paciente embarazada, sospecha de apendicitis.",
                "condiciones": {"grupo": "embarazada"},
                "urgencia": "urgente",
                "red_flags": ["Signos de peritonitis", "Compromiso fetal"],
                "pedido_sugerido": "Ecografía de abdomen como primera línea; si no es "
                                   "concluyente, RM sin gadolinio. Evitar TC.",
                "estudios": [
                    {"modalidad": "Ecografía de abdomen (cuadrante inferior derecho)",
                     "metodo": "Ecografía", "adecuacion": "apropiado", "dosis": "O",
                     "contraste": "No", "comentario": "Primera línea: sin radiación."},
                    {"modalidad": "RM de abdomen y pelvis sin contraste", "metodo": "RM",
                     "adecuacion": "apropiado", "dosis": "O", "contraste": "No",
                     "comentario": "Si la ecografía no es concluyente. Preferida a la TC "
                                   "en el embarazo."},
                    {"modalidad": "TC de abdomen y pelvis con contraste", "metodo": "TC",
                     "adecuacion": "no_apropiado", "dosis": "oooo", "contraste": "Yodado IV",
                     "comentario": "Evitar por radiación salvo que no haya alternativa."},
                ],
            },
            {
                "id": "apendicitis_nino",
                "descripcion": "Paciente pediátrico, sospecha de apendicitis.",
                "condiciones": {"grupo": "nino"},
                "urgencia": "urgente",
                "red_flags": ["Signos de peritonitis", "Deshidratación/sepsis"],
                "pedido_sugerido": "Ecografía de abdomen como primera línea en pediatría; "
                                   "TC solo si eco/RM no resuelven (protocolo de baja dosis).",
                "estudios": [
                    {"modalidad": "Ecografía de abdomen (cuadrante inferior derecho)",
                     "metodo": "Ecografía", "adecuacion": "apropiado", "dosis": "O",
                     "contraste": "No", "comentario": "Primera línea en niños (sin radiación)."},
                    {"modalidad": "RM de abdomen y pelvis sin contraste", "metodo": "RM",
                     "adecuacion": "puede", "dosis": "O", "contraste": "No",
                     "comentario": "Si la ecografía no es concluyente y está disponible."},
                    {"modalidad": "TC de abdomen y pelvis con contraste", "metodo": "TC",
                     "adecuacion": "puede", "dosis": "oooo", "contraste": "Yodado IV",
                     "comentario": "Reservar para casos no resueltos; minimizar dosis."},
                ],
            },
        ],
    },

    # ================================================================ 3
    {
        "id": "tep",
        "titulo": "Sospecha de tromboembolismo pulmonar (TEP)",
        "descripcion": "Disnea/dolor torácico con sospecha de embolia pulmonar. Depende "
                       "de la probabilidad clínica y el dímero-D.",
        "area": ["guardia", "sala", "terapia"],
        "snomed": {"concept_id": "59282003", "termino": "Embolia pulmonar (trastorno)",
                   "estado": "a_verificar"},
        "referencia": "ACR Appropriateness Criteria(R) — Suspected Pulmonary Embolism.",
        "acr_id": "69404",
        "acr_url": "https://acsearch.acr.org/docs/69404/Narrative/",
        "portal_topic_id": "64",
        "preguntas": [
            {"id": "prob_clinica", "texto": "Probabilidad clínica pretest (Wells/Geneva)",
             "tipo": "opcion", "opciones": ["baja_intermedia", "alta"]},
            {"id": "dimero_d", "texto": "Dímero-D (solo aplica si la probabilidad NO es alta)",
             "tipo": "opcion", "opciones": ["negativo", "positivo", "no_realizado"]},
        ],
        "escenarios": [
            {
                "id": "tep_baja_dimero_neg",
                "descripcion": "Probabilidad baja/intermedia + dímero-D negativo.",
                "condiciones": {"prob_clinica": "baja_intermedia", "dimero_d": "negativo"},
                "urgencia": "electivo",
                "red_flags": ["Inestabilidad hemodinámica (replantea todo el algoritmo)"],
                "pedido_sugerido": "No solicitar imágenes: dímero-D negativo con baja "
                                   "probabilidad descarta TEP. Buscar diagnóstico alternativo.",
                "estudios": [
                    {"modalidad": "Ningún estudio de imagen", "metodo": "—",
                     "adecuacion": "apropiado", "dosis": "O", "contraste": "No",
                     "comentario": "Dímero-D negativo + baja probabilidad descarta TEP. "
                                   "La imagen NO está indicada (Choosing Wisely)."},
                    {"modalidad": "Angio-TC de tórax (CTPA)", "metodo": "Angiografía",
                     "adecuacion": "no_apropiado", "dosis": "ooo", "contraste": "Yodado IV",
                     "comentario": "Evitar: radiación y contraste innecesarios."},
                ],
            },
            {
                "id": "tep_indicado",
                "descripcion": "Probabilidad alta, O dímero-D positivo/no realizado.",
                "condiciones": {"prob_clinica": "alta"},
                "urgencia": "urgente",
                "red_flags": ["Hipotensión / shock (TEP de alto riesgo)",
                              "Hipoxemia severa"],
                "pedido_sugerido": "Angio-TC de tórax (protocolo TEP) por sospecha de "
                                   "embolia pulmonar. Si contraindicación al yodo o "
                                   "embarazo, valorar centellograma V/Q.",
                "estudios": [
                    {"modalidad": "Angio-TC de tórax (CTPA)", "metodo": "Angiografía",
                     "adecuacion": "apropiado", "dosis": "ooo", "contraste": "Yodado IV",
                     "comentario": "Estudio de elección para confirmar/descartar TEP."},
                    {"modalidad": "Centellograma V/Q pulmonar", "metodo": "Medicina Nuclear",
                     "adecuacion": "puede", "dosis": "oo", "contraste": "No",
                     "comentario": "Alternativa si contraindicación al contraste o para "
                                   "reducir dosis (jóvenes, embarazo)."},
                    {"modalidad": "Radiografía de tórax", "metodo": "Rx",
                     "adecuacion": "puede", "dosis": "oo", "contraste": "No",
                     "comentario": "Complementaria; ayuda a interpretar el V/Q y a buscar "
                                   "diagnósticos alternativos."},
                ],
            },
        ],
    },

    # ================================================================ 4
    {
        "id": "tce_leve",
        "titulo": "Traumatismo craneoencefálico (TCE) leve",
        "descripcion": "TCE con Glasgow 13-15. Reglas (ej. Canadian CT Head Rule) "
                       "definen a quién imagenear.",
        "area": ["guardia"],
        "snomed": {"concept_id": "127295002", "termino": "Lesión traumática cerebral (trastorno)",
                   "estado": "a_verificar"},
        "referencia": "ACR Appropriateness Criteria(R) — Head Trauma.",
        "acr_id": "69481",
        "acr_url": "https://acsearch.acr.org/docs/69481/Narrative/",
        "portal_topic_id": "139",
        "preguntas": [
            {"id": "criterios_riesgo",
             "texto": "¿Presenta criterios de riesgo? (Glasgow <15 a las 2 h, sospecha de "
                      "fractura abierta/hundimiento, signos de fractura de base, ≥2 vómitos, "
                      "≥65 años, anticoagulación, convulsión, déficit focal, amnesia >30 min, "
                      "mecanismo peligroso)", "tipo": "bool"},
        ],
        "escenarios": [
            {
                "id": "tce_con_criterios",
                "descripcion": "TCE leve CON criterios de riesgo.",
                "condiciones": {"criterios_riesgo": True},
                "urgencia": "urgente",
                "red_flags": ["Anticoagulación", "Deterioro del sensorio", "Vómitos repetidos"],
                "pedido_sugerido": "TC de cráneo sin contraste por TCE con criterios de "
                                   "riesgo — descartar lesión intracraneal aguda.",
                "estudios": [
                    {"modalidad": "TC de cráneo SIN contraste", "metodo": "TC",
                     "adecuacion": "apropiado", "dosis": "ooo", "contraste": "No",
                     "comentario": "Para descartar lesión intracraneal que requiera intervención."},
                    {"modalidad": "RM de cerebro", "metodo": "RM",
                     "adecuacion": "puede", "dosis": "O", "contraste": "Según",
                     "comentario": "Más sensible para lesión axonal difusa; no primera línea en agudo."},
                ],
            },
            {
                "id": "tce_sin_criterios",
                "descripcion": "TCE leve SIN criterios de riesgo.",
                "condiciones": {"criterios_riesgo": False},
                "urgencia": "electivo",
                "red_flags": [],
                "pedido_sugerido": "No solicitar TC de rutina: observación clínica y pautas "
                                   "de alarma. Imagen solo si aparece deterioro.",
                "estudios": [
                    {"modalidad": "TC de cráneo sin contraste", "metodo": "TC",
                     "adecuacion": "no_apropiado", "dosis": "ooo", "contraste": "No",
                     "comentario": "Sin criterios de riesgo, la TC de rutina NO está indicada."},
                ],
            },
        ],
    },

    # ================================================================ 5
    {
        "id": "colico_renal",
        "titulo": "Dolor lumbar agudo — sospecha de litiasis (cólico renal)",
        "descripcion": "Dolor en flanco de inicio agudo con sospecha de cálculo urinario.",
        "area": ["guardia", "ambulatorio"],
        "snomed": {"concept_id": "95570007", "termino": "Cálculo renal (trastorno)",
                   "estado": "a_verificar"},
        "referencia": "ACR Appropriateness Criteria(R) — Acute Onset Flank Pain, Suspicion "
                      "of Stone Disease (Urolithiasis).",
        "acr_id": "69362",
        "acr_url": "https://acsearch.acr.org/docs/69362/Narrative/",
        "portal_topic_id": "26",
        "preguntas": [
            {"id": "grupo", "texto": "Grupo de paciente", "tipo": "opcion",
             "opciones": ["adulto_general", "embarazada"]},
        ],
        "escenarios": [
            {
                "id": "litiasis_adulto",
                "descripcion": "Adulto con sospecha de litiasis.",
                "condiciones": {"grupo": "adulto_general"},
                "urgencia": "urgente",
                "red_flags": ["Fiebre (pielonefritis/obstrucción infectada = emergencia)",
                              "Riñón único", "Lesión renal aguda"],
                "pedido_sugerido": "TC de abdomen y pelvis sin contraste, protocolo de baja "
                                   "dosis, por sospecha de litiasis ureteral.",
                "estudios": [
                    {"modalidad": "TC de abdomen y pelvis SIN contraste (baja dosis)",
                     "metodo": "TC", "adecuacion": "apropiado", "dosis": "ooo", "contraste": "No",
                     "comentario": "Elección: alta sensibilidad para cálculos. Usar baja dosis."},
                    {"modalidad": "Ecografía renal y vesical", "metodo": "Ecografía",
                     "adecuacion": "puede", "dosis": "O", "contraste": "No",
                     "comentario": "Alternativa sin radiación; menor sensibilidad para "
                                   "cálculos pequeños/ureterales."},
                ],
            },
            {
                "id": "litiasis_embarazada",
                "descripcion": "Embarazada con sospecha de litiasis.",
                "condiciones": {"grupo": "embarazada"},
                "urgencia": "urgente",
                "red_flags": ["Fiebre / sospecha de infección", "Compromiso de la función renal"],
                "pedido_sugerido": "Ecografía renal y vesical como primera línea; si no es "
                                   "concluyente, RM sin gadolinio. Evitar TC.",
                "estudios": [
                    {"modalidad": "Ecografía renal y vesical", "metodo": "Ecografía",
                     "adecuacion": "apropiado", "dosis": "O", "contraste": "No",
                     "comentario": "Primera línea: sin radiación."},
                    {"modalidad": "RM de abdomen/pelvis sin contraste", "metodo": "RM",
                     "adecuacion": "puede", "dosis": "O", "contraste": "No",
                     "comentario": "Si la ecografía no es concluyente."},
                    {"modalidad": "TC de abdomen y pelvis sin contraste", "metodo": "TC",
                     "adecuacion": "no_apropiado", "dosis": "ooo", "contraste": "No",
                     "comentario": "Evitar por radiación; reservar para casos excepcionales."},
                ],
            },
        ],
    },

    # ================================================================ 6
    {
        "id": "acv_agudo",
        "titulo": "ACV agudo — déficit neurológico súbito",
        "descripcion": "Déficit neurológico focal de inicio súbito. El tiempo es cerebro: "
                       "imagen inmediata para decidir trombólisis/trombectomía.",
        "area": ["guardia", "terapia"],
        "snomed": {"concept_id": "230690007", "termino": "Accidente cerebrovascular (trastorno)",
                   "estado": "a_verificar"},
        "referencia": "ACR Appropriateness Criteria(R) — Cerebrovascular Diseases: "
                      "Stroke and Stroke-Related Conditions.",
        "acr_id": "3149012",
        "acr_url": "https://acsearch.acr.org/docs/3149012/Narrative/",
        "portal_topic_id": "280",
        "preguntas": [
            {"id": "ventana", "texto": "¿Está dentro de ventana para reperfusión "
                                       "(trombólisis/trombectomía)?",
             "tipo": "opcion", "opciones": ["si_candidato", "fuera_o_no_candidato"]},
        ],
        "escenarios": [
            {
                "id": "acv_candidato",
                "descripcion": "Sospecha de ACV, candidato a reperfusión.",
                "condiciones": {"ventana": "si_candidato"},
                "urgencia": "emergente",
                "red_flags": ["Tiempo de inicio incierto", "Anticoagulación",
                              "Deterioro rápido del sensorio"],
                "pedido_sugerido": "Código ACV: TC de cráneo sin contraste + angio-TC de "
                                   "cabeza y cuello +/- TC perfusión, URGENTE. Descartar "
                                   "hemorragia y evaluar oclusión de gran vaso.",
                "estudios": [
                    {"modalidad": "TC de cráneo SIN contraste", "metodo": "TC",
                     "adecuacion": "apropiado", "dosis": "ooo", "contraste": "No",
                     "comentario": "Primer paso: descartar hemorragia antes de trombólisis."},
                    {"modalidad": "Angio-TC de cabeza y cuello", "metodo": "Angiografía",
                     "adecuacion": "apropiado", "dosis": "ooo", "contraste": "Yodado IV",
                     "comentario": "Detecta oclusión de gran vaso (candidato a trombectomía)."},
                    {"modalidad": "RM de cerebro con difusión (DWI)", "metodo": "RM",
                     "adecuacion": "puede", "dosis": "O", "contraste": "Según",
                     "comentario": "Más sensible para isquemia precoz; usar si no demora "
                                   "el tratamiento."},
                ],
            },
            {
                "id": "acv_no_candidato",
                "descripcion": "Sospecha de ACV, fuera de ventana / no candidato a reperfusión.",
                "condiciones": {"ventana": "fuera_o_no_candidato"},
                "urgencia": "urgente",
                "red_flags": ["Deterioro del sensorio", "Crisis convulsivas"],
                "pedido_sugerido": "TC de cráneo sin contraste (o RM con difusión) para "
                                   "confirmar y caracterizar el ACV y guiar prevención secundaria.",
                "estudios": [
                    {"modalidad": "RM de cerebro con difusión (DWI)", "metodo": "RM",
                     "adecuacion": "apropiado", "dosis": "O", "contraste": "Según",
                     "comentario": "Mejor caracterización de extensión y cronología."},
                    {"modalidad": "TC de cráneo sin contraste", "metodo": "TC",
                     "adecuacion": "apropiado", "dosis": "ooo", "contraste": "No",
                     "comentario": "Disponible y rápida; descarta hemorragia."},
                ],
            },
        ],
    },

    # ================================================================ 7
    {
        "id": "diseccion_aortica",
        "titulo": "Dolor torácico — sospecha de disección/síndrome aórtico agudo",
        "descripcion": "Dolor torácico desgarrante, irradiado a la espalda, asimetría de "
                       "pulsos/TA. Emergencia que requiere imagen vascular inmediata.",
        "area": ["guardia", "terapia"],
        "snomed": {"concept_id": "308546005", "termino": "Disección de aorta (trastorno)",
                   "estado": "a_verificar"},
        "referencia": "ACR Appropriateness Criteria(R) — Suspected Acute Aortic Syndrome.",
        "acr_id": "69402",
        "acr_url": "https://acsearch.acr.org/docs/69402/Narrative/",
        "portal_topic_id": "62",
        "preguntas": [
            {"id": "estabilidad", "texto": "Estado hemodinámico del paciente",
             "tipo": "opcion", "opciones": ["estable", "inestable"]},
        ],
        "escenarios": [
            {
                "id": "diseccion_estable",
                "descripcion": "Sospecha de síndrome aórtico agudo, paciente estable.",
                "condiciones": {"estabilidad": "estable"},
                "urgencia": "emergente",
                "red_flags": ["Asimetría de pulsos/TA", "Déficit neurológico",
                              "Soplo de insuficiencia aórtica nuevo"],
                "pedido_sugerido": "Angio-TC de aorta (tórax-abdomen-pelvis) URGENTE por "
                                   "sospecha de disección aórtica.",
                "estudios": [
                    {"modalidad": "Angio-TC de aorta (tórax/abdomen/pelvis)", "metodo": "Angiografía",
                     "adecuacion": "apropiado", "dosis": "oooo", "contraste": "Yodado IV",
                     "comentario": "Estudio de elección: rápido y muy sensible para disección."},
                    {"modalidad": "RM/Angio-RM de aorta", "metodo": "RM",
                     "adecuacion": "puede", "dosis": "O", "contraste": "Gadolinio (según)",
                     "comentario": "Alternativa en alérgicos al yodo / seguimiento; más lenta."},
                    {"modalidad": "Radiografía de tórax", "metodo": "Rx",
                     "adecuacion": "puede", "dosis": "oo", "contraste": "No",
                     "comentario": "Complementaria (mediastino ensanchado); NO descarta disección."},
                ],
            },
            {
                "id": "diseccion_inestable",
                "descripcion": "Sospecha de síndrome aórtico agudo, paciente inestable.",
                "condiciones": {"estabilidad": "inestable"},
                "urgencia": "emergente",
                "red_flags": ["Shock / hipotensión", "Sospecha de taponamiento o ruptura"],
                "pedido_sugerido": "Ecocardiograma transesofágico al lado de la cama si no "
                                   "se puede trasladar; si se estabiliza, angio-TC de aorta urgente. "
                                   "Avisar a cirugía cardiovascular.",
                "estudios": [
                    {"modalidad": "Ecocardiograma transesofágico (a la cabecera)", "metodo": "Ecografía",
                     "adecuacion": "apropiado", "dosis": "O", "contraste": "No",
                     "comentario": "Útil en el inestable que no tolera traslado; evalúa aorta "
                                   "proximal y taponamiento."},
                    {"modalidad": "Angio-TC de aorta", "metodo": "Angiografía",
                     "adecuacion": "apropiado", "dosis": "oooo", "contraste": "Yodado IV",
                     "comentario": "Si se logra estabilizar para el traslado a TC."},
                ],
            },
        ],
    },

    # ================================================================ 8
    {
        "id": "disnea_aguda",
        "titulo": "Disnea aguda — neumonía vs. insuficiencia cardíaca",
        "descripcion": "Dificultad respiratoria de instalación reciente en sala o guardia. "
                       "Primer paso casi siempre Rx de tórax / eco al lado de la cama.",
        "area": ["guardia", "sala", "terapia"],
        "snomed": {"concept_id": "267036007", "termino": "Disnea (hallazgo)",
                   "estado": "a_verificar"},
        "referencia": "ACR Appropriateness Criteria(R) — Acute Respiratory Illness in "
                      "Immunocompetent Patients.",
        "acr_id": "69446",
        "acr_url": "https://acsearch.acr.org/docs/69446/Narrative/",
        "portal_topic_id": "104",
        "preguntas": [
            {"id": "sospecha", "texto": "Principal sospecha clínica",
             "tipo": "opcion", "opciones": ["infeccion_respiratoria", "insuf_cardiaca", "indeterminada"]},
        ],
        "escenarios": [
            {
                "id": "disnea_infeccion",
                "descripcion": "Sospecha de neumonía / infección respiratoria baja.",
                "condiciones": {"sospecha": "infeccion_respiratoria"},
                "urgencia": "urgente",
                "red_flags": ["Hipoxemia", "Sepsis", "Inmunosupresión"],
                "pedido_sugerido": "Radiografía de tórax (frente y perfil) por sospecha de "
                                   "neumonía. TC de tórax solo si dudas, complicación o "
                                   "inmunosupresión.",
                "estudios": [
                    {"modalidad": "Radiografía de tórax", "metodo": "Rx",
                     "adecuacion": "apropiado", "dosis": "oo", "contraste": "No",
                     "comentario": "Primera línea para confirmar/seguir una neumonía."},
                    {"modalidad": "TC de tórax", "metodo": "TC",
                     "adecuacion": "puede", "dosis": "ooo", "contraste": "Según",
                     "comentario": "Si Rx dudosa, sospecha de complicación o inmunosupresión."},
                    {"modalidad": "Ecografía pulmonar (a la cabecera)", "metodo": "Ecografía",
                     "adecuacion": "puede", "dosis": "O", "contraste": "No",
                     "comentario": "Útil en UTI para consolidación/derrame sin traslado."},
                ],
            },
            {
                "id": "disnea_cardiaca",
                "descripcion": "Sospecha de insuficiencia cardíaca / edema pulmonar.",
                "condiciones": {"sospecha": "insuf_cardiaca"},
                "urgencia": "urgente",
                "red_flags": ["Hipoxemia severa", "Hipotensión", "Dolor torácico asociado"],
                "pedido_sugerido": "Radiografía de tórax + ecocardiograma por sospecha de "
                                   "insuficiencia cardíaca. Correlacionar con BNP/NT-proBNP.",
                "estudios": [
                    {"modalidad": "Radiografía de tórax", "metodo": "Rx",
                     "adecuacion": "apropiado", "dosis": "oo", "contraste": "No",
                     "comentario": "Congestión, cardiomegalia, derrame."},
                    {"modalidad": "Ecocardiograma (a la cabecera)", "metodo": "Ecografía",
                     "adecuacion": "apropiado", "dosis": "O", "contraste": "No",
                     "comentario": "Evalúa función ventricular y guía el tratamiento."},
                ],
            },
            {
                "id": "disnea_indeterminada",
                "descripcion": "Disnea de causa indeterminada.",
                "condiciones": {"sospecha": "indeterminada"},
                "urgencia": "urgente",
                "red_flags": ["Considerar TEP en paralelo", "Hipoxemia que no mejora"],
                "pedido_sugerido": "Radiografía de tórax inicial; ampliar según hallazgos y "
                                   "considerar TEP si persiste hipoxemia sin foco.",
                "estudios": [
                    {"modalidad": "Radiografía de tórax", "metodo": "Rx",
                     "adecuacion": "apropiado", "dosis": "oo", "contraste": "No",
                     "comentario": "Estudio inicial orientador en disnea sin causa clara."},
                    {"modalidad": "Ecografía pulmonar/cardíaca (a la cabecera)", "metodo": "Ecografía",
                     "adecuacion": "puede", "dosis": "O", "contraste": "No",
                     "comentario": "Protocolo POCUS para diferenciar causas rápidamente."},
                ],
            },
        ],
    },

    # ================================================================ 9
    {
        "id": "compresion_medular",
        "titulo": "Sospecha de compresión medular / cauda equina",
        "descripcion": "Dolor de espalda con déficit neurológico, retención/incontinencia "
                       "o anestesia en silla de montar. EMERGENCIA neuroquirúrgica.",
        "area": ["guardia", "sala", "terapia"],
        "snomed": {"concept_id": "67809009", "termino": "Compresión de la médula espinal (trastorno)",
                   "estado": "a_verificar"},
        "referencia": "ACR Appropriateness Criteria(R) — Myelopathy "
                      "(ver también: Low Back Pain, id 69483).",
        "acr_id": "69484",
        "acr_url": "https://acsearch.acr.org/docs/69484/Narrative/",
        "portal_topic_id": "142",
        "preguntas": [
            {"id": "deficit", "texto": "¿Hay déficit neurológico, retención urinaria, "
                                       "incontinencia o anestesia en silla de montar?",
             "tipo": "bool"},
        ],
        "escenarios": [
            {
                "id": "compresion_con_deficit",
                "descripcion": "Dolor de espalda CON banderas rojas neurológicas.",
                "condiciones": {"deficit": True},
                "urgencia": "emergente",
                "red_flags": ["Anestesia en silla de montar", "Retención/incontinencia",
                              "Déficit motor progresivo", "Cáncer conocido"],
                "pedido_sugerido": "RM de columna (total si se sospecha causa oncológica) "
                                   "URGENTE por sospecha de compresión medular / cauda equina. "
                                   "Avisar a neurocirugía.",
                "estudios": [
                    {"modalidad": "RM de columna sin y con contraste", "metodo": "RM",
                     "adecuacion": "apropiado", "dosis": "O", "contraste": "Gadolinio (según)",
                     "comentario": "Estudio de elección: define nivel y causa de compresión."},
                    {"modalidad": "TC de columna (mielo-TC si RM contraindicada)", "metodo": "TC",
                     "adecuacion": "puede", "dosis": "oooo", "contraste": "Según",
                     "comentario": "Alternativa si la RM no es posible (marcapasos, etc.)."},
                ],
            },
            {
                "id": "lumbalgia_simple",
                "descripcion": "Dolor de espalda SIN banderas rojas.",
                "condiciones": {"deficit": False},
                "urgencia": "electivo",
                "red_flags": [],
                "pedido_sugerido": "No solicitar imágenes en las primeras 4-6 semanas si no "
                                   "hay banderas rojas (Choosing Wisely). Manejo conservador.",
                "estudios": [
                    {"modalidad": "RM de columna", "metodo": "RM",
                     "adecuacion": "no_apropiado", "dosis": "O", "contraste": "No",
                     "comentario": "Lumbalgia inespecífica sin banderas rojas NO requiere "
                                   "imagen temprana."},
                    {"modalidad": "Radiografía de columna", "metodo": "Rx",
                     "adecuacion": "no_apropiado", "dosis": "oo", "contraste": "No",
                     "comentario": "Bajo rendimiento; reservar para trauma/sospecha específica."},
                ],
            },
        ],
    },

    # ================================================================ 10
    {
        "id": "tvp",
        "titulo": "Sospecha de trombosis venosa profunda (TVP) de miembro inferior",
        "descripcion": "Edema/dolor unilateral de pierna. La estrategia depende de la "
                       "probabilidad (Wells) y el dímero-D.",
        "area": ["guardia", "sala", "ambulatorio"],
        "snomed": {"concept_id": "128053003", "termino": "Trombosis venosa profunda (trastorno)",
                   "estado": "a_verificar"},
        "referencia": "ACR Appropriateness Criteria(R) — Suspected Lower Extremity Deep "
                      "Vein Thrombosis.",
        "acr_id": "69416",
        "acr_url": "https://acsearch.acr.org/docs/69416/Narrative/",
        "portal_topic_id": "75",
        "preguntas": [
            {"id": "prob_wells", "texto": "Probabilidad clínica (Wells para TVP)",
             "tipo": "opcion", "opciones": ["baja", "intermedia_alta"]},
            {"id": "dimero_d", "texto": "Dímero-D (aplica si la probabilidad es baja)",
             "tipo": "opcion", "opciones": ["negativo", "positivo", "no_realizado"]},
        ],
        "escenarios": [
            {
                "id": "tvp_baja_dimero_neg",
                "descripcion": "Probabilidad baja + dímero-D negativo.",
                "condiciones": {"prob_wells": "baja", "dimero_d": "negativo"},
                "urgencia": "electivo",
                "red_flags": ["Sospecha de TEP concomitante"],
                "pedido_sugerido": "No solicitar eco: probabilidad baja + dímero-D negativo "
                                   "descarta TVP.",
                "estudios": [
                    {"modalidad": "Ningún estudio de imagen", "metodo": "—",
                     "adecuacion": "apropiado", "dosis": "O", "contraste": "No",
                     "comentario": "Probabilidad baja + dímero negativo descarta TVP."},
                    {"modalidad": "Eco-Doppler venoso de miembro inferior", "metodo": "Ecografía",
                     "adecuacion": "no_apropiado", "dosis": "O", "contraste": "No",
                     "comentario": "Innecesaria en este escenario."},
                ],
            },
            {
                "id": "tvp_indicada",
                "descripcion": "Probabilidad intermedia/alta, O dímero-D positivo/no realizado.",
                "condiciones": {"prob_wells": "intermedia_alta"},
                "urgencia": "urgente",
                "red_flags": ["Sospecha de flegmasía (pierna muy edematizada/cianótica)",
                              "Síntomas de TEP"],
                "pedido_sugerido": "Eco-Doppler venoso de miembro inferior por sospecha de TVP.",
                "estudios": [
                    {"modalidad": "Eco-Doppler venoso de miembro inferior", "metodo": "Ecografía",
                     "adecuacion": "apropiado", "dosis": "O", "contraste": "No",
                     "comentario": "Estudio de elección (compresibilidad venosa)."},
                    {"modalidad": "Venografía por TC/RM", "metodo": "Angiografía",
                     "adecuacion": "puede", "dosis": "ooo", "contraste": "Según",
                     "comentario": "Reservada para TVP proximal/pélvica con eco no concluyente."},
                ],
            },
        ],
    },

    # ================================================================ 11
    {
        "id": "abdomen_agudo",
        "titulo": "Abdomen agudo — sospecha de obstrucción intestinal",
        "descripcion": "Dolor abdominal, distensión, vómitos y falta de eliminación de "
                       "gases/heces. Diferenciar obstrucción de otras causas.",
        "area": ["guardia", "sala", "terapia"],
        "snomed": {"concept_id": "81060008", "termino": "Obstrucción intestinal (trastorno)",
                   "estado": "a_verificar"},
        "referencia": "ACR Appropriateness Criteria(R) — Suspected Small-Bowel Obstruction.",
        "acr_id": "69476",
        "acr_url": "https://acsearch.acr.org/docs/69476/Narrative/",
        "portal_topic_id": "134",
        "preguntas": [
            {"id": "gravedad", "texto": "Sospecha clínica",
             "tipo": "opcion", "opciones": ["obstruccion_probable", "dolor_inespecifico"]},
        ],
        "escenarios": [
            {
                "id": "obstruccion_probable",
                "descripcion": "Sospecha alta de obstrucción intestinal.",
                "condiciones": {"gravedad": "obstruccion_probable"},
                "urgencia": "urgente",
                "red_flags": ["Signos de estrangulación/isquemia", "Peritonitis", "Sepsis"],
                "pedido_sugerido": "TC de abdomen y pelvis con contraste IV por sospecha de "
                                   "obstrucción intestinal — definir nivel, causa y signos de "
                                   "complicación.",
                "estudios": [
                    {"modalidad": "TC de abdomen y pelvis con contraste IV", "metodo": "TC",
                     "adecuacion": "apropiado", "dosis": "oooo", "contraste": "Yodado IV",
                     "comentario": "Elección: define nivel, causa y signos de isquemia."},
                    {"modalidad": "Radiografía de abdomen (de pie y acostado)", "metodo": "Rx",
                     "adecuacion": "puede", "dosis": "oo", "contraste": "No",
                     "comentario": "Rápida y disponible; menos sensible/específica que la TC."},
                ],
            },
            {
                "id": "dolor_inespecifico",
                "descripcion": "Dolor abdominal inespecífico (sin claros signos de obstrucción).",
                "condiciones": {"gravedad": "dolor_inespecifico"},
                "urgencia": "urgente",
                "red_flags": ["Reevaluar si aparecen signos de alarma"],
                "pedido_sugerido": "Evaluación clínica + laboratorio; TC de abdomen y pelvis "
                                   "según hallazgos. Ecografía si se sospecha causa biliar/"
                                   "ginecológica.",
                "estudios": [
                    {"modalidad": "TC de abdomen y pelvis con contraste", "metodo": "TC",
                     "adecuacion": "puede", "dosis": "oooo", "contraste": "Yodado IV",
                     "comentario": "Útil cuando el cuadro no se aclara clínicamente."},
                    {"modalidad": "Ecografía de abdomen", "metodo": "Ecografía",
                     "adecuacion": "puede", "dosis": "O", "contraste": "No",
                     "comentario": "Primera línea si se sospecha patología biliar o pélvica."},
                ],
            },
        ],
    },
]


def indicacion_por_id(ind_id):
    """Devuelve la indicación con ese id, o None."""
    return next((i for i in INDICACIONES if i["id"] == ind_id), None)


def indicaciones_por_area(area):
    """Filtra indicaciones útiles en un área dada (guardia/sala/terapia/ambulatorio)."""
    return [i for i in INDICACIONES if area in i.get("area", [])]
