# -*- coding: utf-8 -*-
"""
Traductor médico EN->ES para el dataset ACR.

No es traducción literal: usa un glosario de terminología radiológica curada.
- Categorías de adecuación y RRL: mapeo exacto (100%).
- Procedimientos: traducción por componentes (modalidad + región + contraste).
- Escenarios y tópicos: glosario clínico por frases (cobertura alta; lo no
  cubierto queda legible y se puede ver el original en la app).

Convenciones de terminología usadas:
- IV contrast -> contraste EV (endovenoso)   | oral contrast -> contraste oral
- CT -> TC | MRI -> RM | US -> Ecografía | CTA -> Angio-TC | MRA -> Angio-RM
- head -> cráneo | chest -> tórax | RLQ -> FID (fosa ilíaca derecha)
"""

import re
from functools import lru_cache

# ----------------------------------------------------------------------
# Categorías de adecuación (exacto)
# ----------------------------------------------------------------------
CATEGORIAS = {
    "Usually appropriate": "Usualmente apropiado",
    "May be appropriate": "Puede ser apropiado",
    "May be appropriate (Disagreement)": "Puede ser apropiado (sin consenso)",
    "Usually not appropriate": "Usualmente no apropiado",
}

# ----------------------------------------------------------------------
# RRL / dosis (exacto; 'mSv' y símbolos ☢ se conservan)
# ----------------------------------------------------------------------
RRL = {
    "0 mSv O": "0 mSv O",
    "<0.1 mSv ☢": "<0.1 mSv ☢",
    "0.1-1mSv ☢☢": "0,1-1 mSv ☢☢",
    "1-10 mSv ☢☢☢": "1-10 mSv ☢☢☢",
    "10-30 mSv ☢☢☢☢": "10-30 mSv ☢☢☢☢",
    "30-100 mSv ☢☢☢☢☢": "30-100 mSv ☢☢☢☢☢",
    "Varies": "Variable",
    "": "",
}


_REGEX_CACHE = {}


def _compilar(glosario):
    """Compila (una vez) una regex de alternancia, frases más largas primero,
    y el mapa de reemplazo. Permite traducir en UNA pasada: cada posición se
    reemplaza una sola vez, evitando re-traducir términos español-idénticos."""
    key = id(glosario)
    if key not in _REGEX_CACHE:
        claves = sorted(glosario, key=len, reverse=True)
        patron = re.compile(
            r'(?<![A-Za-z])(' + "|".join(re.escape(k) for k in claves) + r')(?![A-Za-z])',
            re.IGNORECASE)
        mapa = {k.lower(): v for k, v in glosario.items()}
        _REGEX_CACHE[key] = (patron, mapa)
    return _REGEX_CACHE[key]


def _aplicar(glosario, texto):
    """Traduce en una sola pasada con el glosario (frases largas primero)."""
    if not texto:
        return texto
    patron, mapa = _compilar(glosario)
    out = patron.sub(lambda m: mapa.get(m.group(0).lower(), m.group(0)), texto)
    return re.sub(r'\s+', ' ', out).strip()


# ----------------------------------------------------------------------
# Glosario de PROCEDIMIENTOS (las regiones llevan "de " para leer natural)
# ----------------------------------------------------------------------
_PROC = {
    # --- contraste (primero, frases largas) ---
    "without and with IV contrast": "sin y con contraste EV",
    "with IV and oral contrast": "con contraste EV y oral",
    "without and with IV and oral contrast": "sin y con contraste EV y oral",
    "with IV contrast": "con contraste EV",
    "without IV contrast": "sin contraste EV",
    "with oral contrast": "con contraste oral",
    "without contrast": "sin contraste",
    "with contrast": "con contraste",
    "IV contrast": "contraste EV",
    "oral contrast": "contraste oral",
    "contrast": "contraste",

    # --- modalidades ---
    "FDG-PET/CT": "PET/TC con FDG",
    "FDG-PET/MRI": "PET/RM con FDG",
    "DOTATATE PET/CT": "PET/TC con DOTATATE",
    "DOTATATE PET/MRI": "PET/RM con DOTATATE",
    "Fluciclovine PET/CT": "PET/TC con fluciclovina",
    "PSMA PET/CT": "PET/TC con PSMA",
    "PET/CT": "PET/TC",
    "PET/MRI": "PET/RM",
    "PET": "PET",
    "Bone scan": "centellograma óseo",
    "Bone densitometry": "densitometría ósea",
    "Lymphoscintigraphy": "linfocentellografía",
    "Lymphangiography": "linfangiografía",
    # ecocardiografía (técnicas) — antes que 'US' para no partirlas
    "US echocardiography transesophageal": "ecocardiograma transesofágico",
    "US echocardiography transthoracic": "ecocardiograma transtorácico",
    "echocardiography transesophageal": "ecocardiograma transesofágico",
    "echocardiography transthoracic": "ecocardiograma transtorácico",
    "echocardiography": "ecocardiograma",
    "transesophageal": "transesofágico",
    "transthoracic": "transtorácico",
    "at rest": "en reposo",
    # estudios -grafía (terminología radiológica estándar en español)
    "arthrography": "artrografía",
    "myelography": "mielografía",
    "CT myelography": "mielo-TC",
    "cystography": "cistografía",
    "urethrography": "uretrografía",
    "voiding cystourethrography": "cistouretrografía miccional",
    "cystourethrography": "cistouretrografía",
    "urography": "urografía",
    "CT urography": "uro-TC",
    "MR urography": "uro-RM",
    "urosonography": "urosonografía",
    "hysterosalpingography": "histerosalpingografía",
    "sonohysterography": "sonohisterografía",
    "fistulography": "fistulografía",
    "sialography": "sialografía",
    "dacryocystography": "dacriocistografía",
    "ventriculography": "ventriculografía",
    "cisternography": "cisternografía",
    "discography": "discografía",
    "post-discography": "posdiscografía",
    "ductography": "ductografía",
    "defecography": "defecografía",
    "enterography": "enterografía",
    "CT enterography": "entero-TC",
    "MR enterography": "entero-RM",
    "elastography": "elastografía",
    "esophagram": "esofagograma",
    "esophagography": "esofagografía",
    "small bowel follow-through": "tránsito de intestino delgado",
    "follow-through": "tránsito",
    "radiotherapy": "radioterapia",
    # intervencionismo vascular
    "thrombolysis": "trombólisis",
    "thrombectomy": "trombectomía",
    "thrombolytic": "trombolítico",
    "pharmacomechanical": "farmacomecánico",
    "catheterization": "cateterismo",
    "anesthetic": "anestésico",
    "multiphase": "multifásico",
    "high-frequency": "de alta frecuencia",
    "lymphatic": "linfático",
    # corazón / función-morfología
    "heart function and morphology": "de función y morfología cardíaca",
    "heart function": "de función cardíaca",
    "heart": "cardíaco",
    "function": "función",
    "morphology": "morfología",
    "thyroid": "tiroides",
    "parathyroid": "paratiroides",
    "thoracic": "torácico",
    "thigh": "muslo",
    "urethra": "uretra",
    # intervencionismo / técnicas (terminología médica)
    "therapy": "terapia", "radiotherapy": "radioterapia",
    "locoregional": "locorregional", "combination": "combinada",
    "compression": "compresiva", "ablation": "ablación",
    "embolization": "embolización", "sclerotherapy": "escleroterapia",
    "vertebroplasty": "vertebroplastia", "kyphoplasty": "cifoplastia",
    "nephrostomy": "nefrostomía", "gastrostomy": "gastrostomía",
    "cholangiography": "colangiografía", "pyelography": "pielografía",
    "vaginography": "vaginografía", "functional": "funcional",
    "antegrade": "anterógrada", "retrograde": "retrógrada",
    "pharynx": "faringe", "dynamic": "dinámico", "static": "estático",
    "saphenous": "safena", "ablation": "ablación",
    "pulmonary": "pulmonar", "artery": "arteria", "vein": "vena",
    "drainage": "drenaje", "aspiration": "aspiración",
    "needle": "aguja", "wire": "guía", "balloon": "balón",
    "angioplasty": "angioplastia", "stenting": "colocación de stent",
    "spectroscopy": "espectroscopía", "diffusion": "difusión",
    # --- QA: anatomía de procedimientos (regiones con "de ") ---
    "sacroiliac joints": "de articulaciones sacroilíacas",
    "sacroiliac joint": "de articulación sacroilíaca",
    "sacroiliac": "sacroilíaco", "joints": "articulaciones", "joint": "articulación",
    "forearm": "de antebrazo", "orbits": "de órbitas", "orbit": "de órbita",
    "paranasal sinuses": "de senos paranasales", "sinuses": "senos paranasales",
    "sinus": "seno", "maxillofacial": "maxilofacial",
    "internal auditory canal": "de conducto auditivo interno",
    "auditory": "auditivo", "sella": "de silla turca",
    "aortoiliac": "aortoilíaco", "iliac": "ilíaco", "sacrum": "de sacro",
    "kidneys": "de riñones", "kidney": "de riñón", "ureters": "de uréteres",
    "brachial plexus": "de plexo braquial", "lumbosacral plexus": "de plexo lumbosacro",
    "lumbosacral": "lumbosacro", "plexus": "plexo", "brachial": "braquial",
    "ribs": "de costillas", "rib": "de costilla",
    "humerus": "de húmero", "radius": "de radio", "ulna": "de cúbito",
    "fibula": "de peroné", "tibia": "de tibia", "femur": "de fémur",
    "parotid": "de parótida", "salivary glands": "de glándulas salivales",
    "veins": "venas", "vein": "vena", "arteries": "arterias",
    "jugular": "yugular", "subclavian": "subclavia", "femoral": "femoral",
    "groin": "de ingle", "mesenteric": "mesentérico", "internal": "interno",
    "prostatectomy bed": "de lecho de prostatectomía", "bed": "lecho",
    "coronary arteries": "de arterias coronarias", "coronary": "coronario",
    # --- QA: técnicas / agentes ---
    "colloid": "coloide", "barium enema": "colon por enema con bario",
    "barium": "bario", "enema": "enema", "double-contrast": "doble contraste",
    "single-contrast": "simple contraste", "pertechnetate": "pertecnetato",
    "enteroclysis": "enteroclisis",
    "embolectomy": "embolectomía",
    "anticoagulation": "anticoagulación", "hemodialysis": "hemodiálisis",
    "prostatectomy": "prostatectomía",
    "corticosteroid": "corticoide",
    "abbreviated": "abreviado", "targeted": "dirigido",
    "cone beam": "de haz cónico", "uptake": "captación",
    "ammonia": "amonio", "trus": "ecografía transrectal",
    "tunneled": "tunelizado", "nontunneled": "no tunelizado",
    "port": "reservorio subcutáneo", "runoff": "de salida arterial distal",
    # --- QA tanda 2: técnicas/agentes/cirugía ---
    "transcranial": "transcraneal", "carotid": "carótida",
    "venous sampling": "muestreo venoso", "sampling": "muestreo",
    "vasodilator": "vasodilatador", "adjunctive": "complementario",
    "choline": "colina", "fluciclovine": "fluciclovina", "fluoride": "fluoruro de sodio",
    "hepatic": "hepático", "chemotherapy": "quimioterapia", "infusion": "infusión",
    "revascularization": "revascularización", "hybrid": "híbrido",
    "endarterectomy": "endarterectomía", "recanalization": "recanalización",
    "myomectomy": "miomectomía", "hysteroscopic": "histeroscópica",
    "laparoscopic": "laparoscópica", "open": "abierta",
    "axillary": "axilar", "axilla": "de axila",
    "inotropic": "inotrópico", "radionuclide": "radionúclido",
    "peptide": "peptídico", "receptor": "receptor",
    "skeleton": "esqueleto", "appendicular": "apendicular",
    "lipid profile": "perfil lipídico", "analysis": "análisis",
    "consultation": "consulta", "radiation oncology": "oncología radioterápica",
    "core biopsy": "biopsia con aguja gruesa", "core": "con aguja gruesa",
    "double lumen": "de doble luz", "lumen": "luz",
    "pregnant uterus": "de útero gestante", "pregnant": "gestante",
    "follow-up": "seguimiento", "mechanical": "mecánico",
    # acrónimos (equivalente español estándar)
    "mpi": "perfusión miocárdica (MPI)", "mrcp": "colangiopancreatografía por RM",
    "mru": "urografía por RM", "qct": "TC cuantitativa",
    "pyp": "pirofosfato", "systemic": "sistémico", "lateral": "lateral",
    # --- QA tanda 3: cola larga (medicina nuclear / intervencionismo) ---
    "bone marrow": "de médula ósea", "marrow": "médula ósea",
    "ace inhibitor": "inhibidor de ECA", "inhibitor": "inhibidor",
    "renography": "renografía", "amyloid": "amiloide",
    "antiplatelet": "antiplaquetario", "bronchial": "bronquial",
    "craniofacial": "craneofacial", "bland": "sin fármaco",
    "colonography": "colonografía", "triple rule out": "triple descarte",
    "rule out": "descarte", "ctu": "urografía por TC",
    "catheter directed": "por catéter dirigido", "directed": "dirigido",
    "conservative": "conservador", "surveillance": "vigilancia",
    "vfa": "evaluación de fractura vertebral",
    "body composition": "composición corporal", "composition": "composición",
    "endobronchial": "endobronquial", "esophageal transit": "tránsito esofágico",
    "esophageal": "esofágico", "transit": "tránsito",
    "extracorporeal membrane oxygenation": "oxigenación por membrana extracorpórea (ECMO)",
    "extracorporeal": "extracorpóreo", "membrane": "membrana", "oxygenation": "oxigenación",
    "dedicated": "dedicado", "fiducial": "fiducial", "marker": "marcador",
    "loopogram": "loopograma", "cystocolpoproctography": "cistocolpoproctografía",
    "anus": "ano", "small bowel": "de intestino delgado", "bowel": "intestino",
    "hysterectomy": "histerectomía", "cholecystostomy": "colecistostomía",
    "spleen": "bazo", "transplantation": "trasplante", "transplant": "trasplante",
    "somatostatin analogs": "análogos de somatostatina", "somatostatin": "somatostatina",
    "analogs": "análogos", "long-acting": "de acción prolongada",
    # --- QA: conectores / palabras de procedimiento ---
    "repeat": "repetir", "days": "días", "only": "solo", "single": "simple",
    "including": "incluyendo", "additional": "adicional",
    "surrounding": "circundante", "structures": "estructuras",
    "segment": "segmento", "access": "acceso", "use": "uso", "new": "nuevo",
    "via": "vía", "during": "durante", "projection": "proyección",
    "continued": "continuar", "possible": "posible",
    "management": "tratamiento", "best medical": "mejor tratamiento médico",
    "supervised exercise program": "programa de ejercicio supervisado",
    "exercise": "ejercicio", "program": "programa", "supervised": "supervisado",
    "Image-guided": "guiado por imagen",
    "Catheter-directed": "por catéter dirigido",
    "Catheter": "por catéter",
    "Percutaneous": "percutáneo",
    "Arteriography": "arteriografía",
    "Aortography": "aortografía",
    "Venography": "venografía",
    "Angiography": "angiografía",
    "Fluoroscopy": "fluoroscopía",
    "Radiography": "radiografía",
    "Radiographic": "radiográfico",
    "Mammography": "mamografía",
    "Tomosynthesis": "tomosíntesis",
    "Ultrasound": "ecografía",
    "Sestamibi": "centellograma con sestamibi",
    "MIBG": "centellograma con MIBG",
    "Octreotide": "centellograma con octreótido",
    "Gallium": "centellograma con galio",
    "WBC scan": "centellograma con leucocitos marcados",
    "RBC scan": "centellograma con glóbulos rojos marcados",
    "Tagged WBC": "leucocitos marcados",
    "SPECT/CT": "SPECT/TC",
    "SPECT": "SPECT",
    "DXA": "densitometría (DXA)",
    "CTA": "angio-TC",
    "CTV": "veno-TC",
    "MRA": "angio-RM",
    "MRV": "veno-RM",
    "MRI": "RM",
    "MR": "RM",
    "CT": "TC",
    "US": "ecografía",
    "Nuclear medicine scan": "centellograma de medicina nuclear",
    "Ventilation/perfusion scan": "centellograma ventilación/perfusión (V/Q)",
    "Image guided": "guiado por imagen",

    # --- regiones (llevan "de ") ---
    "whole body": "de cuerpo entero",
    "skull base to mid-thigh": "de base de cráneo a muslo medio",
    "skull base to mid thigh": "de base de cráneo a muslo medio",
    "head and neck": "de cabeza y cuello",
    "neck": "de cuello",
    "head": "de cráneo",
    "brain": "de cerebro",
    "chest abdomen pelvis": "de tórax-abdomen-pelvis",
    "chest and abdomen": "de tórax y abdomen",
    "abdomen and pelvis": "de abdomen y pelvis",
    "abdomen pelvis": "de abdomen y pelvis",
    "chest": "de tórax",
    "abdomen RLQ": "de abdomen (FID)",
    "abdomen RUQ": "de abdomen (HD)",
    "abdomen": "de abdomen",
    "pelvis": "de pelvis",
    "cervical spine": "de columna cervical",
    "thoracic spine": "de columna dorsal",
    "lumbar spine": "de columna lumbar",
    "lumbosacral spine": "de columna lumbosacra",
    "whole spine": "de columna completa",
    "spine": "de columna",
    "lower extremities": "de miembros inferiores",
    "upper extremities": "de miembros superiores",
    "lower extremity": "de miembro inferior",
    "upper extremity": "de miembro superior",
    "extremities": "de extremidades",
    "extremity": "de extremidad",
    "skull": "de cráneo",
    "long bone": "de hueso largo",
    "shoulder": "de hombro",
    "elbow": "de codo",
    "wrist": "de muñeca",
    "hand": "de mano",
    "hip": "de cadera",
    "knee": "de rodilla",
    "ankle": "de tobillo",
    "foot": "de pie",
    "breast": "de mama",
    "area of interest": "de la zona de interés",
    "soft tissue": "de partes blandas",
    "kidney": "de riñón",
    "renal": "renal",
    "scrotum": "de escroto",
    "transvaginal": "transvaginal",
    "transrectal": "transrectal",
    "duplex Doppler": "Doppler dúplex",
    "Doppler": "Doppler",

    # --- otras regiones / estructuras ---
    "liver": "de hígado",
    "lymph nodes": "de ganglios linfáticos",
    "lymph node": "de ganglio linfático",
    "nodes": "ganglios",
    "node": "ganglio",
    "gland": "glándula",
    "joint": "articulación",
    "wall": "pared",
    "artery": "arteria",
    "vein": "vena",
    "bladder": "vejiga",
    "prostate": "próstata",
    "uterus": "útero",
    "ovary": "ovario",

    # --- conectores frecuentes ---
    "3-phase": "trifásico",
    "with stress and rest": "con estrés y reposo",
    "stress and rest": "estrés y reposo",
    "with stress": "con estrés",
    "stress": "estrés",
    "resting": "en reposo",
    "rest": "reposo",
    "arterial phase": "fase arterial",
    "venous phase": "fase venosa",
    "delayed phase": "fase tardía",
    "phase": "fase",
    "guided": "guiado",
    "view": "proyección",
    "views": "proyecciones",
    "right": "derecho",
    "left": "izquierdo",
    "bilateral": "bilateral",
    "both": "ambos",
    "upper": "superior",
    "lower": "inferior",
    "bone": "óseo",
    "body": "cuerpo",
    "Surgical": "quirúrgico",
    "biopsy": "biopsia",
    "drainage": "drenaje",
    "aspiration": "aspiración",
    "placement": "colocación",
    "imaging": "",
    "of": "de",
    "and": "y",
    "with": "con",
    "without": "sin",
    "scan": "centellograma",
}


@lru_cache(maxsize=None)
def traducir_procedimiento(texto):
    t = _aplicar(_PROC, texto)
    # limpieza: "TC de abdomen ... de pelvis" ya viene bien; quitar "de de"
    t = re.sub(r'\bde de\b', 'de', t)
    # capitalizar inicial
    return t[:1].upper() + t[1:] if t else t


# ----------------------------------------------------------------------
# Glosario CLÍNICO para escenarios y tópicos (frases comunes ACR)
# ----------------------------------------------------------------------
_CLIN = {
    "initial imaging": "estudio inicial",
    "initial exam": "estudio inicial",
    "next imaging study": "siguiente estudio por imágenes",
    "next study": "siguiente estudio",
    "follow-up": "seguimiento",
    "follow up": "seguimiento",
    "surveillance": "vigilancia",
    "staging": "estadificación",
    "restaging": "reestadificación",
    "screening": "tamizaje",
    "suspected": "sospecha de",
    "known": "conocido/a",
    "newly diagnosed": "recién diagnosticado/a",
    "pretreatment": "pretratamiento",
    "post-treatment": "postratamiento",
    "post treatment": "postratamiento",
    "preprocedural": "preprocedimiento",
    "postoperative": "postoperatorio",
    "preoperative": "preoperatorio",
    "recurrent": "recurrente",
    "recurrence": "recurrencia",
    "acute": "agudo/a",
    "chronic": "crónico/a",
    "subacute": "subagudo/a",
    "child": "niño/a",
    "adult": "adulto/a",
    "infant": "lactante",
    "neonate": "neonato",
    "pregnant": "embarazada",
    "peripartum period": "período periparto",
    "reproductive age": "edad reproductiva",
    "postmenopausal": "posmenopáusica",
    "immunocompromised": "inmunocomprometido/a",
    "immunocompetent": "inmunocompetente",
    "negative": "negativo/a",
    "positive": "positivo/a",
    "indeterminate": "indeterminado/a",
    "asymptomatic": "asintomático/a",
    "symptomatic": "sintomático/a",
    "low risk": "riesgo bajo",
    "intermediate clinical risk": "riesgo clínico intermedio",
    "high clinical risk": "riesgo clínico alto",
    "low clinical risk": "riesgo clínico bajo",
    "intermediate risk": "riesgo intermedio",
    "high risk": "riesgo alto",
    "clinical risk": "riesgo clínico",
    "intermediate": "intermedio/a",
    "maximal severity within an hour": "intensidad máxima en una hora",
    "within an hour": "en una hora",
    "maximal severity": "intensidad máxima",
    "mild": "leve",
    "moderate": "moderado/a",
    "unilateral": "unilateral",
    "progressive": "progresivo/a",
    "persistent": "persistente",
    "lasting": "de duración",
    "high probability": "probabilidad alta",
    "low probability": "probabilidad baja",
    "sudden onset": "inicio súbito",
    "new onset": "inicio reciente",
    "acute onset": "inicio agudo",
    "onset": "inicio",
    "severe": "severo/a",
    "headache": "cefalea",
    "fever": "fiebre",
    "trauma": "traumatismo",
    "blunt": "cerrado",
    "penetrating": "penetrante",
    "neuro deficit": "déficit neurológico",
    "neurologic deficit": "déficit neurológico",
    "neurological deficit": "déficit neurológico",
    "focal": "focal",
    "generalized": "generalizado/a",
    "seizure": "convulsión",
    "stroke": "ACV",
    "hemorrhage": "hemorragia",
    "aneurysm": "aneurisma",
    "dissection": "disección",
    "aortic": "aórtico/a",
    "pulmonary embolism": "embolia pulmonar",
    "deep vein thrombosis": "trombosis venosa profunda",
    "appendicitis": "apendicitis",
    "bowel obstruction": "obstrucción intestinal",
    "small-bowel obstruction": "obstrucción de intestino delgado",
    "flank pain": "dolor en flanco",
    "stone disease": "litiasis",
    "urolithiasis": "litiasis urinaria",
    "low back pain": "lumbalgia",
    "back pain": "dolor de espalda",
    "neck pain": "cervicalgia",
    "chest pain": "dolor torácico",
    "abdominal pain": "dolor abdominal",
    "pelvic pain": "dolor pélvico",
    "shoulder pain": "dolor de hombro",
    "knee pain": "dolor de rodilla",
    "hip pain": "dolor de cadera",
    "respiratory illness": "enfermedad respiratoria",
    "dyspnea": "disnea",
    "cough": "tos",
    "hemoptysis": "hemoptisis",
    "myelopathy": "mielopatía",
    "radiculopathy": "radiculopatía",
    "cancer": "cáncer",
    "tumor": "tumor",
    "mass": "masa",
    "nodule": "nódulo",
    "metastasis": "metástasis",
    "metastatic": "metastásico/a",
    "lymphadenopathy": "adenopatía",
    "infection": "infección",
    "inflammation": "inflamación",
    "abscess": "absceso",
    "ischemia": "isquemia",
    "ischemic": "isquémico/a",
    "bleeding": "sangrado",
    "obstruction": "obstrucción",
    "palpable": "palpable",
    "history": "antecedente",
    "cancer hx": "antecedente de cáncer",
    "imaging": "estudio por imágenes",
    "evaluation": "evaluación",
    "assessment": "evaluación",
    "management": "manejo",
    "suspicion of": "sospecha de",
    "suspicion": "sospecha",
    "features": "signos",
    "normal": "normal",
    "abnormal": "anormal",
    "no red flags": "sin banderas rojas",
    "increasing": "creciente",
    "frequency": "frecuencia",
    "severity": "severidad",
    "first trimester": "primer trimestre",
    "second trimester": "segundo trimestre",
    "third trimester": "tercer trimestre",
    "vaginal bleeding": "sangrado vaginal",
    "wks": "sem", "wk": "sem",
    # regiones / estructuras (para reordenar 'X pain' -> 'dolor de X', etc.)
    "cervical spine": "columna cervical",
    "thoracic spine": "columna dorsal",
    "lumbar spine": "columna lumbar",
    "lumbosacral spine": "columna lumbosacra",
    "spine": "columna",
    "soft tissue": "partes blandas",
    "lower extremity": "miembro inferior",
    "upper extremity": "miembro superior",
    "extremity": "extremidad",
    "shoulder": "hombro", "elbow": "codo", "wrist": "muñeca", "hand": "mano",
    "hip": "cadera", "knee": "rodilla", "ankle": "tobillo", "foot": "pie",
    "chest wall": "pared torácica", "abdominal wall": "pared abdominal",
    "bone": "hueso", "joint": "articulación", "kidney": "riñón",
    "liver": "hígado", "lung": "pulmón", "brain": "cerebro",
    "stress fracture": "fractura de estrés",
    "fracture": "fractura",
    "osteomyelitis": "osteomielitis",
    "septic arthritis": "artritis séptica",
    "soft tissue infection": "infección de partes blandas",
    "spine infection": "infección de columna",
    "primary bone tumor": "tumor óseo primario",
    "soft tissue mass": "masa de partes blandas",
    "physical abuse": "maltrato físico",
    "cutaneous melanoma": "melanoma cutáneo",
    "muco-cutaneous melanoma": "melanoma mucocutáneo",
    "melanoma": "melanoma",
    "breast cancer": "cáncer de mama",
    "lung cancer": "cáncer de pulmón",
    "colon cancer": "cáncer de colon",
    "prostate cancer": "cáncer de próstata",
    "local recurrence": "recurrencia local",
    "radiography normal": "radiografía normal",
    "radiography negative": "radiografía negativa",
    "radiography indeterminate": "radiografía indeterminada",
    "treated": "tratado/a",
    "symptoms": "síntomas",
    "no symptoms": "sin síntomas",
    # términos médicos (latín/griego)
    "cholecystitis": "colecistitis",
    "cholangitis": "colangitis",
    "pancreatitis": "pancreatitis",
    "pyelonephritis": "pielonefritis",
    "diverticulitis": "diverticulitis",
    "appendicitis": "apendicitis",
    "cholelithiasis": "colelitiasis",
    "nephrolithiasis": "nefrolitiasis",
    "pneumonia": "neumonía",
    "pneumothorax": "neumotórax",
    "endocarditis": "endocarditis",
    "osteonecrosis": "osteonecrosis",
    "spondylolisthesis": "espondilolistesis",
    "spondylitis": "espondilitis",
    "encephalitis": "encefalitis",
    "meningitis": "meningitis",
    "myelitis": "mielitis",
    "thrombosis": "trombosis",
    "embolism": "embolia",
    "ischemia": "isquemia",
    "hydronephrosis": "hidronefrosis",
    "hematuria": "hematuria",
    "hemoptysis": "hemoptisis",
    "dysphagia": "disfagia",
    "syncope": "síncope",
    "vertigo": "vértigo",
    "ataxia": "ataxia",
    "dementia": "demencia",
    "epilepsy": "epilepsia",
    "stenosis": "estenosis",
    # oncología / órganos
    "renal cell carcinoma": "carcinoma de células renales",
    "hepatocellular carcinoma": "carcinoma hepatocelular",
    "carcinoma": "carcinoma",
    "pulmonary nodule": "nódulo pulmonar",
    "pulmonary": "pulmonar",
    "renal": "renal",
    "hepatic": "hepático/a",
    "adrenal": "suprarrenal",
    "right upper quadrant": "cuadrante superior derecho",
    "right lower quadrant": "fosa ilíaca derecha",
    "left upper quadrant": "cuadrante superior izquierdo",
    "left lower quadrant": "fosa ilíaca izquierda",
    "RLQ": "FID", "RUQ": "HD", "LLQ": "FII", "LUQ": "HI",
    "leukocytosis": "leucocitosis",
    "leukopenia": "leucopenia",
    "afebrile": "afebril",
    "reproductive age group": "grupo de edad reproductiva",
    "age group": "grupo de edad",
    "right": "derecho",
    "left": "izquierdo",
    "group": "grupo",
    "next": "siguiente",
    # sustantivos / adjetivos sueltos frecuentes
    "disease": "enfermedad",
    "injury": "lesión",
    "lesion": "lesión",
    "node": "ganglio",
    "nodes": "ganglios",
    "stage": "estadio",
    "risk": "riesgo",
    "initial": "inicial",
    "abnormal": "anormal",
    "symptom": "síntoma",
    "new": "nuevo/a",
    "old": "antiguo/a",
    "chronic pain": "dolor crónico",
    "acute pain": "dolor agudo",
    # conectores
    "screening for": "tamizaje de",
    "and": "y",
    "with": "con",
    "without": "sin",
    "of the": "de",
    "of": "de",
    "for": "para",
    "after": "después de",
    "before": "antes de",
    "the": "",
    "in": "en",
    "on": "en",
    "to": "a",
    "or": "o",
    "at": "en",
    "up": "",
    "than": "que",
    "more": "más",
    "not": "no",
    "high": "alto/a",
    "low": "bajo/a",
    "average": "promedio",
    "based on": "según",
    "based": "según",
    # anatomía / regiones (versión clínica, sin 'de')
    "chest wall": "pared torácica",
    "abdominal wall": "pared abdominal",
    "chest": "tórax",
    "neck": "cuello",
    "head": "cabeza",
    "thoracic": "torácico/a",
    "abdominal": "abdominal",
    "back": "espalda",
    "forearm": "antebrazo",
    "breast": "mama",
    "scalp": "cuero cabelludo",
    "limb": "miembro",
    "axial": "axial",
    "articular": "articular",
    "lower": "inferior",
    "upper": "superior",
    # patología
    "arthritis": "artritis",
    "septic": "séptico/a",
    "malignancy": "malignidad",
    "malignant": "maligno/a",
    "benign": "benigno/a",
    "malformation": "malformación",
    "hemangioma": "hemangioma",
    "osteoid osteoma": "osteoma osteoide",
    "osteoma": "osteoma",
    "spondyloarthritis": "espondiloartritis",
    "spondyloarthropathy": "espondiloartropatía",
    "axial spondyloarthropathy": "espondiloartropatía axial",
    "pheochromocytoma": "feocromocitoma",
    "effusion": "derrame",
    "swelling": "tumefacción",
    "syndrome": "síndrome",
    "inflammatory": "inflamatorio/a",
    "idiopathic": "idiopático/a",
    "suspicious": "sospechoso/a",
    "aggressive": "agresivo/a",
    "indeterminate": "indeterminado/a",
    "inconclusive": "no concluyente",
    "nondiagnostic": "no diagnóstico",
    "noncontrast": "sin contraste",
    "abuse": "maltrato",
    "seizure disorder": "trastorno convulsivo",
    "disorder": "trastorno",
    "change": "cambio",
    # proceso clínico
    "study": "estudio",
    "exam": "examen",
    "radiography": "radiografía",
    "findings": "hallazgos",
    "signs": "signos",
    "therapy": "terapia",
    "treatment": "tratamiento",
    "diagnosis": "diagnóstico",
    "diagnosed": "diagnosticado/a",
    "surgery": "cirugía",
    "surgical": "quirúrgico/a",
    "presentation": "presentación",
    "abnormality": "anormalidad",
    "loss": "pérdida",
    "planning": "planificación",
    "performed": "realizado/a",
    "suggest": "sugiere",
    "clinical symptoms": "síntomas clínicos",
    "clinical": "clínico/a",
    # cirugía / dispositivos
    "mastectomy": "mastectomía",
    "reconstruction": "reconstrucción",
    "side": "lado",
    "hardware": "material de osteosíntesis",
    "implanted": "implantado/a",
    "implant": "implante",
    # abreviaturas
    "hx": "antecedente",
    "cns": "SNC",
    "ct": "TC",
    "mri": "RM",
    "cm": "cm",
    "muco-cutaneous": "mucocutáneo",
    "neuro": "neurológico",
    # segunda tanda (gaps frecuentes restantes)
    "soft": "blando/a", "tissue": "tejido",
    "stress": "estrés", "physical": "físico/a",
    "lymph node": "ganglio linfático", "lymph nodes": "ganglios linfáticos",
    "lymph": "linfático", "newly": "recién",
    "osteoid": "osteoide", "osteonecrosis": "osteonecrosis",
    "osteoporosis": "osteoporosis", "osteomyelitis": "osteomielitis",
    "mastectomy side": "lado de mastectomía", "mastectomy": "mastectomía",
    "no reconstruction": "sin reconstrucción",
    "one": "uno", "wound": "herida", "mets": "metástasis",
    "yrs": "años", "yr": "año", "use": "uso", "prior": "previo/a",
    "etiology": "etiología", "access": "acceso", "appearance": "aspecto",
    "lesions": "lesiones", "adrenocortical": "corticosuprarrenal",
    "red flags": "banderas rojas", "red flag": "bandera roja",
    "weakness": "debilidad", "numbness": "entumecimiento",
    "swelling": "tumefacción", "deformity": "deformidad",
    "dislocation": "luxación", "sprain": "esguince",
    "instability": "inestabilidad", "impingement": "pinzamiento",
    "tear": "desgarro", "rupture": "ruptura", "avulsion": "avulsión",
    "foreign body": "cuerpo extraño", "abscess": "absceso",
    "fistula": "fístula", "cyst": "quiste", "polyp": "pólipo",
    "varices": "várices", "varix": "variz", "edema": "edema",
    "ascites": "ascitis", "jaundice": "ictericia",
    "incontinence": "incontinencia", "retention": "retención",
    "infertility": "infertilidad", "menstrual": "menstrual",
    "menopause": "menopausia", "delivery": "parto",
    "gestation": "gestación", "trimester": "trimestre",
    "weight loss": "pérdida de peso", "vision loss": "pérdida de visión",
    "hearing loss": "pérdida auditiva", "vision": "visión",
    "hearing": "audición", "fall": "caída", "abuse": "maltrato",
    "complication": "complicación", "complications": "complicaciones",
    "recurrent": "recurrente", "persistent": "persistente",
    "unresolved": "no resuelto/a", "resolved": "resuelto/a",
    "worsening": "empeoramiento", "improving": "en mejoría",
    "stable": "estable", "unstable": "inestable",
    "function": "función", "dysfunction": "disfunción",
    "failure": "insuficiencia", "transplant": "trasplante",
    "device": "dispositivo", "catheter": "catéter", "stent": "stent",
    "graft": "injerto", "shunt": "derivación",
    "etiology unknown": "etiología desconocida", "unknown": "desconocido/a",
    "origin": "origen", "source": "origen",
    # tercera tanda: anatomía ortopédica + clínica
    "us": "ecografía",
    "fibula": "peroné", "humerus": "húmero", "femur": "fémur",
    "tibia": "tibia", "radius": "radio", "ulna": "cúbito",
    "patella": "rótula", "clavicle": "clavícula", "scapula": "escápula",
    "sternum": "esternón", "ribs": "costillas", "rib": "costilla",
    "sacrum": "sacro", "coccyx": "cóccix", "vertebra": "vértebra",
    "vertebral": "vertebral", "calcaneus": "calcáneo",
    "metatarsal": "metatarsiano", "metacarpal": "metacarpiano",
    "phalanx": "falange", "leg": "pierna", "arm": "brazo", "thigh": "muslo",
    "nerve": "nervio", "tendon": "tendón", "ligament": "ligamento",
    "cartilage": "cartílago", "muscle": "músculo",
    "deficit": "déficit", "artery": "arteria", "vein": "vena",
    "pelvic": "pélvico/a", "spinal": "raquídeo/a", "skeletal": "esquelético/a",
    "subchondral": "subcondral", "intracranial": "intracraneal",
    "visceral": "visceral", "coronary": "coronario/a",
    "ovarian": "ovárico/a", "urinary": "urinario/a", "vaginal": "vaginal",
    "neurological": "neurológico/a", "respiratory": "respiratorio/a",
    "traumatic": "traumático/a", "nontraumatic": "no traumático/a",
    "nonspecific": "inespecífico/a", "erosive": "erosivo/a",
    "suggestive": "sugestivo/a", "isolated": "aislado/a",
    "equivocal": "dudoso/a", "apparent": "aparente",
    "contraindicated": "contraindicado/a", "replaced": "reemplazado/a",
    "posttreatment": "postratamiento", "post-treatment": "postratamiento",
    # patología
    "osteoarthritis": "artrosis", "osteoma": "osteoma",
    "hemangioma": "hemangioma", "scoliosis": "escoliosis",
    "gout": "gota", "pseudogout": "pseudogota",
    "seronegative": "seronegativo/a", "seropositive": "seropositivo/a",
    "otitis": "otitis", "sinusitis": "sinusitis",
    "pheochromocytoma": "feocromocitoma",
    # proceso clínico
    "puncture": "punción", "completion": "finalización",
    "complete": "completo/a", "pathology": "patología",
    "biopsy": "biopsia", "repair": "reparación", "survey": "rastreo",
    "factors": "factores", "factor": "factor", "concern": "sospecha",
    "finding": "hallazgo", "injuries": "lesiones", "injury": "lesión",
    "illness": "enfermedad", "patient": "paciente", "family": "familia",
    "site": "localización", "following": "tras", "recent": "reciente",
    "minor": "menor", "major": "mayor", "higher": "mayor",
    "multiple": "múltiple", "possible": "posible", "first": "primer",
    "immediate": "inmediato/a", "guide": "guía", "follow": "seguimiento",
    "weeks": "semanas", "week": "semana", "days": "días",
    "microscopic": "microscópico/a", "gross": "macroscópico/a",
    "foreign": "extraño/a", "unilateral": "unilateral",
    "hormone": "hormonal", "hormonal": "hormonal",
    "hemodialysis": "hemodiálisis", "dialysis": "diálisis",
    "bisphosphonate": "bifosfonato",
    "transfeminine": "transfemenino", "transmasculine": "transmasculino",
    "transgender": "transgénero",
    "cell": "célula", "gas": "gas", "yo": "años", "wound": "herida",
    # cuarta tanda
    "spinal cord injury": "lesión medular", "spinal cord": "médula espinal",
    "cord": "médula", "body": "cuerpo", "wall": "pared", "gland": "glándula",
    "skin": "piel", "superficial": "superficial", "deep": "profundo/a",
    "routine": "de rutina", "cause": "causa", "intervention": "intervención",
    "consistent": "compatible", "extent": "extensión", "genetic": "genético/a",
    "necrotizing": "necrotizante", "inadequate": "inadecuado/a",
    "weight": "peso", "occlusion": "oclusión", "pancreatic": "pancreático/a",
    "mechanical": "mecánico/a", "compression": "compresión",
    "gestations": "gestaciones", "highly": "altamente",
    "ir": "RI", "tte": "ecocardiograma transtorácico", "tee": "ecocardiograma transesofágico",
    "stones": "cálculos", "stone": "cálculo", "calculus": "cálculo",
    "bowel": "intestino", "biliary": "biliar", "ductal": "ductal",
    "vascular malformation": "malformación vascular",
    "hydrocephalus": "hidrocefalia", "shunt malfunction": "disfunción de la derivación",
    "malfunction": "disfunción", "graft": "injerto",
    "anomaly": "anomalía", "anomalies": "anomalías",
    "screening exam": "examen de tamizaje",
    "incidental": "incidental", "incidentally": "de forma incidental",
    "detected": "detectado/a", "elevated": "elevado/a",
    "elevation": "elevación", "enlarged": "agrandado/a",
    "enlargement": "agrandamiento", "reduced": "reducido/a",
    "decreased": "disminuido/a", "increased": "aumentado/a",
    # quinta tanda (cola)
    "crystalline": "cristalino/a", "associated": "asociado/a",
    "smoking": "tabaquismo", "pack": "paquete", "assess": "evaluar",
    "involvement": "compromiso", "atrial": "auricular",
    "cannulation": "canulación", "predisposition": "predisposición",
    "lumbosacral": "lumbosacro/a", "uterine": "uterino/a",
    "dcis": "CDIS", "neoadjuvant": "neoadyuvante", "mammo": "mamografía",
    "adjuvant": "adyuvante", "uterus": "útero", "cervix": "cérvix",
    "ovary": "ovario", "prostate": "próstata", "bladder": "vejiga",
    "kidney": "riñón", "spleen": "bazo", "thyroid": "tiroides",
    "parathyroid": "paratiroides", "adrenal": "suprarrenal",
    "biliary obstruction": "obstrucción biliar",
    "claudication": "claudicación", "aneurysmal": "aneurismático/a",
    "occlusive": "oclusivo/a", "perfusion": "perfusión",
    "viability": "viabilidad", "ejection fraction": "fracción de eyección",
    "endoleak": "endofuga", "restenosis": "reestenosis",
    "calcification": "calcificación", "calcified": "calcificado/a",
    # vascular / cardíaco
    "arterial occlusion": "oclusión arterial",
    "venous occlusion": "oclusión venosa",
    "mesenteric arterial system": "sistema arterial mesentérico",
    "arterial system": "sistema arterial",
    "arterial": "arterial",
    "mesenteric": "mesentérico/a", "embolic": "embólico/a",
    "embolic source": "fuente embólica", "source": "fuente",
    "embolism": "embolia", "embolus": "émbolo", "thromboembolism": "tromboembolismo",
    "systemic": "sistémico/a", "noncerebral": "no cerebral",
    "cerebral": "cerebral", "system": "sistema",
    "claudication": "claudicación", "ischemia": "isquemia",
    "ischemic": "isquémico/a", "stenosis": "estenosis",
    "atherosclerosis": "aterosclerosis", "atherosclerotic": "aterosclerótico/a",
    "nonatherosclerotic": "no aterosclerótico/a",
    "vasculitis": "vasculitis", "vasospasm": "vasoespasmo",
    "perforation": "perforación", "rupture": "ruptura",
    "pseudoaneurysm": "pseudoaneurisma", "aneurysmal": "aneurismático/a",
    "arteriovenous": "arteriovenoso/a", "venous": "venoso/a",
    "thrombus": "trombo", "clot": "coágulo", "occluded": "ocluido/a",
    "patency": "permeabilidad", "revascularization": "revascularización",
    "bypass": "bypass", "endovascular": "endovascular",
    "cyclical": "cíclico/a", "pattern": "patrón", "quantify": "cuantificar",
    "tenderness": "dolor a la palpación", "mobile": "móvil",
    "fixed": "fijo/a", "discharge": "secreción", "nipple": "pezón",
    "lump": "nódulo", "lumps": "nódulos", "density": "densidad",
    "calcifications": "calcificaciones", "architectural": "arquitectural",
    "distortion": "distorsión", "asymmetry": "asimetría",
    "augmentation": "aumento", "reconstructed": "reconstruido/a",
    "silicone": "silicona", "rupture": "ruptura", "leak": "fuga",
    # --- QA escenarios: términos clínicos frecuentes ---
    "morning stiffness": "rigidez matutina", "stiffness": "rigidez",
    "gait abnormality": "alteración de la marcha", "gait": "marcha",
    "night pain": "dolor nocturno", "night": "nocturno", "morning": "matutino",
    "radiating": "irradiado", "unintentional": "no intencional",
    "weight loss": "pérdida de peso", "limp": "cojera",
    "rotator cuff": "manguito rotador", "rotator": "rotador",
    "altered mental status": "alteración del estado mental",
    "altered": "alterado", "mental status": "estado mental",
    "cognitive impairment": "deterioro cognitivo", "impairment": "deterioro",
    "behavioral": "conductual", "vomiting": "vómitos",
    "skull base": "base de cráneo", "base of skull": "base de cráneo",
    "asthma": "asma", "exacerbation": "exacerbación",
    "uncomplicated": "no complicado/a", "complicated": "complicado/a",
    "adnexal": "anexial", "neoplasm": "neoplasia", "morphology": "morfología",
    "specific": "específico/a", "nonspecific": "inespecífico/a",
    "localized": "localizado/a", "nonlocalized": "no localizado/a",
    "premenopausal": "premenopáusica", "perimenopausal": "perimenopáusica",
    "fasciitis": "fascitis", "nonsuperficial": "no superficial",
    "superficial": "superficial", "curvature": "curvatura",
    "hypotension": "hipotensión", "hypertension": "hipertensión",
    "response": "respuesta", "progression": "progresión",
    "reduction": "reducción", "evaluate": "evaluar", "determining": "determinar",
    "criteria": "criterios", "murmur": "soplo", "solitary": "solitario/a",
    "hemodynamically": "hemodinámicamente", "hemodynamic": "hemodinámico/a",
    "arthroplasty": "artroplastia", "sacroiliac": "sacroilíaco/a",
    "colorectal": "colorrectal", "axillary": "axilar", "axilla": "axila",
    "distant": "a distancia", "metastases": "metástasis",
    "sentinel node": "ganglio centinela", "sentinel": "centinela",
    "satellite": "satélite", "wide local excision": "escisión local amplia",
    "excision": "escisión", "wide": "amplio/a",
    "acquired": "adquirido/a", "congenital": "congénito/a",
    "retained": "retenido/a", "foreign body": "cuerpo extraño",
    "squamous cell": "células escamosas", "squamous": "escamoso/a",
    "ground glass": "vidrio esmerilado", "nodule": "nódulo",
    "any": "cualquier", "single": "único/a", "multiple": "múltiples",
    "iliac": "ilíaco/a", "past": "antecedente de", "vascular murmur": "soplo vascular",
    "orthostatic": "ortostático/a", "exclusionary": "de exclusión",
    "preop": "preoperatorio", "postop": "postoperatorio",
    "noncardiothoracic": "no cardiotorácico", "cardiothoracic": "cardiotorácico",
    "need": "necesidad de", "know": "saber", "cannot": "no puede",
    "communicate": "comunicarse", "altered sensorium": "alteración del sensorio",
    "sensorium": "sensorio", "hrs": "horas", "average": "promedio",
    "infiltrate": "infiltrado", "consolidation": "consolidación",
    "atelectasis": "atelectasia", "effusion": "derrame",
    "displaced": "desplazado/a", "nondisplaced": "no desplazado/a",
    "comminuted": "conminuta", "intraarticular": "intraarticular",
    "growth": "crecimiento", "developmental": "del desarrollo",
    "dysplasia": "displasia", "abuse": "maltrato",
    "ingested": "ingerido/a", "aspirated": "aspirado/a",
    "foreign": "extraño/a", "limping": "con cojera",
    "febrile": "febril", "afebrile": "afebril", "sepsis": "sepsis",
    # --- QA escenarios tanda 2 (≥3 apariciones, diccionario médico) ---
    "skull": "cráneo", "excluded": "excluido/a", "orchiectomy": "orquiectomía",
    "current": "actual", "thoracoabdominal": "toracoabdominal", "occult": "oculto/a",
    "female": "femenino", "male": "masculino", "icu": "UCI", "cavity": "cavidad",
    "joints": "articulaciones", "joint": "articulación", "fibroids": "miomas",
    "plexopathy": "plexopatía", "candidate": "candidato/a",
    "extrahepatic": "extrahepático/a", "overlying": "suprayacente",
    "changes": "cambios", "demyelinating": "desmielinizante", "selection": "selección",
    "requiring": "que requiere", "antepartum": "anteparto", "placement": "colocación",
    "mammoplasty": "mamoplastia", "copd": "EPOC", "leukocoria": "leucocoria",
    "chemo": "quimioterapia", "decubitus": "decúbito", "breasts": "mamas",
    "lactating": "en lactancia", "conservation": "conservación", "chylothorax": "quilotórax",
    "lifetime": "de por vida", "defecatory": "defecatorio/a",
    "characterization": "caracterización", "fibrillation": "fibrilación",
    "monochorionic": "monocorial", "dichorionic": "bicorial",
    "multichorionic": "multicorial", "due": "debido a",
    "musculoskeletal": "musculoesquelético/a", "tests": "pruebas",
    "supplemental": "complementario/a", "localizing": "localizador/a", "exams": "exámenes",
    "clinically": "clínicamente", "other": "otro/a", "esophageal": "esofágico/a",
    "incomplete": "incompleto/a", "ankylosis": "anquilosis",
    "leakage": "fuga", "ligamentous": "ligamentario/a", "neuroendocrine": "neuroendocrino/a",
    "determine": "determinar", "rules": "reglas", "twisting": "torsión",
    "during": "durante", "mediastinal": "mediastínico/a", "prosthesis": "prótesis",
    "nonvariceal": "no variceal", "endoscopy": "endoscopía", "occupational": "ocupacional",
    "painful": "doloroso/a", "painless": "indoloro/a", "untested": "no evaluado/a",
    "degree": "grado", "twins": "gemelos", "procedures": "procedimientos",
    "colonoscopy": "colonoscopía", "paralysis": "parálisis",
    "degenerative": "degenerativo/a", "refractory": "refractario/a",
    "immunosuppressed": "inmunosuprimido/a", "outlet": "opérculo", "parotid": "parótida",
    "shows": "muestra", "within": "dentro de", "that": "que", "midface": "tercio medio facial",
    "neurogenic": "neurogénico/a", "mechanism": "mecanismo", "thoracolumbar": "toracolumbar",
    "gestational": "gestacional", "trophoblastic": "trofoblástico/a",
    "irradiation": "irradiación", "collapse": "colapso", "planned": "planificado/a",
    "cardiomyopathy": "miocardiopatía", "tube": "sonda", "noninfectious": "no infeccioso/a",
    "dense": "denso/a", "nondense": "no denso/a", "gravid": "gestante", "pulsatile": "pulsátil",
    "nonpulsatile": "no pulsátil", "normotensive": "normotenso/a", "labral": "labral",
    "osteochondral": "osteocondral", "contraindication": "contraindicación",
    "iodinated": "yodado/a", "oropharynx": "orofaringe", "oropharyngeal": "orofaríngeo/a",
    "nasopharynx": "nasofaringe", "hypopharynx": "hipofaringe", "larynx": "laringe",
    "preprocedure": "preprocedimiento", "postprocedure": "postprocedimiento",
    "months": "meses", "nonseminoma": "no seminoma", "nonmuscle": "no muscular",
    "steal": "robo", "defect": "defecto", "could": "podría", "flow": "flujo",
    "patch": "parche", "salivary": "salival", "polycystic": "poliquístico/a",
    "hyperparathyroidism": "hiperparatiroidismo", "sinuses": "senos paranasales",
    "poorly": "mal", "previously": "previamente", "solid": "sólido/a",
    "chemotherapy": "quimioterapia", "pretest": "pretest", "probability": "probabilidad",
    "synovial": "sinovial", "pulse": "pulso", "collaterals": "colaterales",
    "pituitary": "hipofisario/a", "postpartum": "posparto", "collision": "colisión",
    "abnormalities": "anomalías", "bariatric": "bariátrico/a", "scores": "puntajes",
    "subdeltoid": "subdeltoideo", "marked": "marcado/a", "spontaneous": "espontáneo/a",
    "sensorimotor": "sensitivomotor", "cirrhotic": "cirrótico/a",
    "gynecological": "ginecológico/a", "gynecologic": "ginecológico/a", "order": "orden",
    "failed": "fallido/a", "thrombotic": "trombótico/a", "nonthrombotic": "no trombótico/a",
    "disorders": "trastornos", "tenosynovitis": "tenosinovitis", "arteries": "arterias",
    "less": "menos", "cholangiocarcinoma": "colangiocarcinoma", "margins": "márgenes",
    "significant": "significativo/a", "buttock": "glúteo", "emboli": "émbolos",
    "done": "realizado/a", "bilious": "bilioso/a", "etiologies": "etiologías",
    "scaphoid": "escafoides", "splanchnic": "esplácnico/a", "cardiopulmonary": "cardiopulmonar",
    "palliation": "paliación", "unexplained": "inexplicado/a", "predominance": "predominio",
    "decline": "deterioro", "bulk": "voluminoso/a", "fullness": "plenitud",
    "carpal tunnel": "túnel carpiano", "carpal": "carpiano/a", "emergent": "emergente",
    "varicose veins": "várices", "varicose": "varicoso/a", "retrotympanic": "retrotimpánico/a",
    "otoscopy": "otoscopía", "rhinosinusitis": "rinosinusitis", "repaired": "reparado/a",
    "osseous": "óseo/a", "hyperplasia": "hiperplasia", "indicated": "indicado/a",
    "nonacute": "no agudo/a", "patellar": "rotuliano/a", "scrotum": "escroto",
    "hyperbilirubinemia": "hiperbilirrubinemia", "frequent": "frecuente",
    "trochanteric": "trocantérico/a", "controlled": "controlado/a",
    "nuchal translucency": "translucencia nucal", "nuchal": "nucal",
    "translucency": "translucencia", "measurement": "medición", "empirical": "empírico/a",
    "resection": "resección", "discoloration": "decoloración",
    "tracheomalacia": "traqueomalacia", "chiasm": "quiasma", "eschar": "escara",
    "noninvasive": "no invasivo/a", "parenchymal": "parenquimatoso/a", "thinning": "adelgazamiento",
    "ulceration": "ulceración", "tolerate": "tolerar", "probably": "probablemente",
    "vessel": "vaso", "teeth": "dientes", "restriction": "restricción", "accreta": "acreta",
    "discordance": "discordancia", "between": "entre", "fetuses": "fetos", "filling": "llenado",
    "infective": "infeccioso/a", "tracheal": "traqueal", "community": "comunitario/a",
    "deterioration": "deterioro", "instrumentation": "instrumentación",
    "connective": "conectivo/a", "trunk": "tronco", "involving": "que afecta",
    "sustained": "sostenido/a", "entrapment": "atrapamiento", "bodies": "cuerpos",
    "demonstrates": "demuestra", "parapneumonic": "paraneumónico/a", "fungal": "fúngico/a",
    "midline": "línea media", "postsurgical": "posquirúrgico/a", "bronchiectasis": "bronquiectasias",
    "celiac": "celíaco/a", "aminotransferase": "aminotransferasa", "increase": "aumento",
    "diaphragmatic": "diafragmático/a", "fertility": "fertilidad", "diameter": "diámetro",
    "person": "persona", "smokes": "fuma", "preterm": "pretérmino", "assault": "agresión",
    "unlikely": "poco probable", "nonballistic": "no balístico/a", "concurrent": "concurrente",
    "bronchomalacia": "broncomalacia", "extremely": "extremadamente", "infarct": "infarto",
    "walk": "caminar", "enlarging": "en aumento", "differentiated": "diferenciado/a",
    "bruises": "hematomas", "overuse": "sobreuso", "tendinopathy": "tendinopatía",
    "ballistic": "balístico/a", "bronchial": "bronquial", "labor": "trabajo de parto",
    "peripheral": "periférico/a", "sickle": "falciforme", "mature": "maduro/a",
    "prophylactic": "profiláctico/a", "evidence": "evidencia", "echocardiogram": "ecocardiograma",
    "anticipated": "previsto/a", "shorter": "más corto/a", "fractures": "fracturas",
    "metabolic": "metabólico/a", "disturbance": "alteración", "brainstem": "tronco encefálico",
    "anatomy": "anatomía", "repetitive": "repetitivo/a", "troponin": "troponina",
    "suggested": "sugerido/a", "xray": "radiografía", "locoregional": "locorregional",
    "hairy cell": "células peludas", "leukemia": "leucemia",
    "phase": "fase", "brachial": "braquial", "conservative": "conservador/a",
    "ablation": "ablación", "additional": "adicional", "draining": "supurante",
    "hairy": "velloso/a", "variceal": "variceal", "labral": "labral",
}

# Patrones estructurales por SUFIJO del segmento (se reordena a español).
# (sufijo_en, plantilla_es) — el {} recibe la traducción del resto.
_PATRONES = [
    (" suspected", "sospecha de {}"),
    (" screening", "tamizaje de {}"),
    (" surveillance", "vigilancia de {}"),
    (" mass", "masa de {}"),
]

# Patrones por PREFIJO del segmento.
_PREFIJOS = [
    ("suspected ", "sospecha de {}"),
    ("screening for ", "tamizaje de {}"),
    ("surveillance of ", "vigilancia de {}"),
    ("evaluation of ", "evaluación de {}"),
    ("workup of ", "estudio de {}"),
    ("workup for ", "estudio de {}"),
    ("imaging of ", "estudio por imágenes de {}"),
    ("management of ", "manejo de {}"),
    ("staging of ", "estadificación de {}"),
    ("assessment of ", "evaluación de {}"),
]

# Segmentos frecuentes con traducción curada (gramática perfecta).
_SEGMENTOS = {
    "initial imaging": "estudio inicial",
    "next imaging study": "siguiente estudio por imágenes",
    "initial exam": "estudio inicial",
    "initial staging": "estadificación inicial",
    "follow-up imaging": "imágenes de seguimiento",
    "local recurrence surveillance": "vigilancia de recurrencia local",
    "lesion on radiography": "lesión en la radiografía",
    "radiography normal": "radiografía normal",
    "radiography negative": "radiografía negativa",
    "radiography indeterminate": "radiografía indeterminada",
}


def _genero(palabra):
    """Heurística de género del sustantivo por terminación (f por defecto en -a/-is...)."""
    p = palabra.lower()
    if re.search(r'(ción|sión|sis|itis|dad|tis|triz|umbre)$', p):
        return "f"
    if p.endswith("a"):
        return "f"
    return "m"


def _reordenar_adjetivo(t):
    """Mueve un adjetivo 'Xo/a' inicial al FINAL de la frase, concordando con el
    sustantivo (núcleo). 'agudo/a embolia pulmonar' -> 'embolia pulmonar aguda'."""
    palabras = t.split()
    # Solo en frases cortas: en frases largas (con preposiciones) mover el
    # adjetivo al final daría mal resultado, así que se deja como está.
    if 2 <= len(palabras) <= 4 and palabras[0].endswith("o/a"):
        base = palabras[0][:-3]                    # 'agudo/a' -> 'agud'
        resto = palabras[1:]
        adj = base + ("a" if _genero(resto[0]) == "f" else "o")
        return " ".join(resto + [adj])
    return t


def _frase(seg):
    """Traduce una frase nominal con el glosario clínico (sin capitalizar)."""
    return _reordenar_adjetivo(_aplicar(_CLIN, seg))


def _traducir_segmento(seg):
    seg = seg.strip()
    if not seg:
        return ""
    low = seg.lower()
    if low in _SEGMENTOS:
        return _SEGMENTOS[low]
    # prefijos estructurales ('Suspected acute X' -> 'sospecha de X agudo')
    for pre, plantilla in _PREFIJOS:
        if low.startswith(pre):
            resto = seg[len(pre):].strip()
            return plantilla.format(_frase(resto))
    # patrones estructurales por sufijo (reordenan: 'X suspected' -> 'sospecha de X')
    for suf, plantilla in _PATRONES:
        if low.endswith(suf):
            resto = seg[:-len(suf)].strip()
            return plantilla.format(_frase(resto))
    # traducción por glosario
    t = _frase(seg)
    # reordenar 'X pain' -> 'dolor de X' si quedó 'pain' al final
    m = re.search(r'^(.*?)\s+pain$', t, flags=re.IGNORECASE)
    if m:
        t = "dolor de " + m.group(1).strip()
    return t


@lru_cache(maxsize=None)
def traducir_clinico(texto):
    """Traduce escenario/tópico por segmentos, con reglas de orden/concordancia.
    Lo no cubierto queda en inglés (legible)."""
    if not texto:
        return texto
    partes = [_traducir_segmento(s) for s in texto.split(",")]
    t = ", ".join(p for p in partes if p)
    # red de seguridad: 'pain' suelto que no se pudo reordenar
    t = re.sub(r'(?i)\bpain\b', "dolor", t)
    return t[:1].upper() + t[1:] if t else t


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
PANELES_ES = {
    "Breast": "Mama",
    "Cardiac": "Cardíaco",
    "Gastrointestinal": "Gastrointestinal",
    "Gyn and OB": "Ginecología y Obstetricia",
    "Interventional Radiology": "Radiología Intervencionista",
    "Musculoskeletal": "Musculoesquelético",
    "Neurologic": "Neurológico",
    "Pediatric": "Pediátrico",
    "Polytrauma": "Politrauma",
    "Systemic Oncology": "Oncología Sistémica",
    "Thoracic": "Torácico",
    "Urologic": "Urológico",
    "Vascular": "Vascular",
}

# Áreas corporales (los compuestos con guion se arman por partes)
_AREA = {
    "abdomen": "abdomen", "pelvis": "pelvis", "breast": "mama", "cardiac": "cardíaco",
    "chest": "tórax", "head": "cabeza", "neck": "cuello", "spine": "columna",
    "extremity": "extremidad", "extremities": "extremidades", "shoulder": "hombro",
    "knee": "rodilla", "hip": "cadera", "ankle": "tobillo", "foot": "pie",
    "hand": "mano", "wrist": "muñeca", "elbow": "codo", "whole body": "cuerpo entero",
    "vascular": "vascular", "scrotum": "escroto",
    "maxface": "macizo facial", "unspecified": "no especificado",
}

# Frases de área que reordenan el adjetivo (se chequean ANTES del split por palabra).
_AREA_FRASE = {
    "lower extremity": "miembro inferior",
    "upper extremity": "miembro superior",
}


@lru_cache(maxsize=None)
def traducir_panel(texto):
    return PANELES_ES.get((texto or "").strip(), texto)


@lru_cache(maxsize=None)
def traducir_area(texto):
    """Traduce 'Chest-abdomen-pelvis' -> 'tórax-abdomen-pelvis'."""
    if not texto:
        return texto
    frase = _AREA_FRASE.get(texto.lower())
    if frase:
        return frase[:1].upper() + frase[1:]
    partes = re.split(r'([-/ ])', texto)
    out = "".join(_AREA.get(p.lower(), p) if p.strip() else p for p in partes)
    return out[:1].upper() + out[1:]


@lru_cache(maxsize=None)
def traducir_topico(texto):
    """Tópico: usa la tabla curada (terminología médica) y cae a las reglas."""
    try:
        from data.topicos_es import traducir_topico as _curado
        curado = _curado(texto)
        if curado:
            return curado
    except Exception:
        pass
    return traducir_clinico(texto)


@lru_cache(maxsize=None)
def traducir_categoria(texto):
    return CATEGORIAS.get((texto or "").strip(), texto)


@lru_cache(maxsize=None)
def traducir_rrl(texto):
    return RRL.get((texto or "").strip(), texto)
