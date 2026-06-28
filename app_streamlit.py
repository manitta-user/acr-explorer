# -*- coding: utf-8 -*-
"""
Explorador ACR Appropriateness Criteria® — interfaz web moderna.

Construido sobre el dataset estructurado del ACR AC Portal (4115 escenarios).
Educativo / de apoyo: NO reemplaza el juicio médico.

Ejecutar:
    pip install streamlit
    streamlit run app_streamlit.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import html
import streamlit as st
from core import consulta_acr
from core import traduccion as T
from core import diagnostico as Dx

# --------------------------------------------------------------------------
st.set_page_config(page_title="ACR Explorer — adecuación de estudios",
                   page_icon="🩻", layout="wide",
                   initial_sidebar_state="expanded")

ADEC = {
    "apropiado":    {"pill": "#34d399", "bg": "#10b9811f", "txt": "Apropiado",  "ic": "✓"},
    "puede":        {"pill": "#fbbf24", "bg": "#f59e0b1f", "txt": "Puede",      "ic": "~"},
    "no_apropiado": {"pill": "#f87171", "bg": "#ef44441f", "txt": "No aprop.",  "ic": "✕"},
    "":             {"pill": "#94a3b8", "bg": "#64748b1f", "txt": "—",          "ic": "·"},
}

# ----------------------------- estilos ------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
  --bg:#0a0f1c; --card:#111a2e; --card2:#0e1626; --line:#1f2c44;
  --line2:#2a3a58; --muted:#94a3b8; --text:#e8eefb; --accent:#3b82f6;
}
html, body, [class*="css"], .stApp { font-family:'Inter',system-ui,sans-serif; }
.stApp { background:
   radial-gradient(1200px 500px at 80% -10%, #16213d55, transparent),
   radial-gradient(1000px 400px at -10% 0%, #1b1a3a44, transparent), var(--bg); }
.block-container { padding-top:3.2rem; padding-bottom:4rem; max-width:1600px;
  padding-left:2.6rem; padding-right:2.6rem; }
#MainMenu, footer { visibility:hidden; }
[data-testid="stHeader"] { background:transparent; height:2.6rem; }
[data-testid="stToolbar"] { display:none; }

/* sidebar SIEMPRE visible: se oculta el botón de colapsar/expandir */
[data-testid="stSidebarCollapseButton"], [data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"] { display:none !important; }
section[data-testid="stSidebar"] { transform:none !important; visibility:visible !important;
  min-width:300px !important; }

/* sidebar */
section[data-testid="stSidebar"] { background:#0b1322; border-right:1px solid var(--line); }
section[data-testid="stSidebar"] .stTextInput input,
section[data-testid="stSidebar"] [data-baseweb="select"] > div {
  background:#0e1830; border:1px solid var(--line2); border-radius:10px; }
.stTextInput input:focus { border-color:var(--accent)!important;
  box-shadow:0 0 0 3px #3b82f633!important; }

/* enterprise app bar */
.appbar { display:flex; align-items:center; justify-content:space-between; gap:1rem;
  padding:.1rem 0 1rem; margin-bottom:1.4rem; border-bottom:1px solid var(--line);
  flex-wrap:wrap; }
.brand { display:flex; align-items:center; gap:.85rem; }
.brand .logo { width:46px; height:46px; border-radius:13px; flex:none;
  background:linear-gradient(135deg,#2563eb,#7c3aed); display:flex; align-items:center;
  justify-content:center; box-shadow:0 8px 22px #3b82f644; }
.brand .pname { font-size:1.22rem; font-weight:800; letter-spacing:-.4px; color:var(--text);
  line-height:1.1; }
.brand .pname b { background:linear-gradient(90deg,#60a5fa,#a78bfa);
  -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
.brand .ptag { font-size:.74rem; color:var(--muted); margin-top:.12rem; letter-spacing:.2px; }
.trust { display:flex; gap:.45rem; flex-wrap:wrap; align-items:center; }
.tchip { font-size:.66rem; font-weight:600; color:#a8b6cf; background:#0e1830;
  border:1px solid var(--line2); border-radius:999px; padding:.3rem .72rem; letter-spacing:.2px; }
.tchip.alt { color:#d9c97e; border-color:#4d4118; background:#2a230d66; }

/* lead / value proposition */
.lead { margin:.1rem 0 1.2rem; }
.lead h2 { font-size:1.75rem; font-weight:800; letter-spacing:-.7px; color:var(--text);
  margin:0 0 .35rem; line-height:1.16; }
.lead h2 .hl { background:linear-gradient(90deg,#60a5fa,#a78bfa);
  -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
.lead p { color:var(--muted); font-size:.95rem; margin:0; max-width:700px; line-height:1.5; }
.searchlbl { font-size:.76rem; font-weight:700; color:#9fb1cc; text-transform:uppercase;
  letter-spacing:.7px; margin:.7rem 0 .4rem; }

/* stat cards */
.statbar { display:flex; gap:.8rem; flex-wrap:wrap; margin:.2rem 0 1.1rem; }
.stat { background:linear-gradient(180deg,var(--card),var(--card2));
  border:1px solid var(--line); border-radius:14px; padding:.7rem 1.1rem; min-width:140px;
  box-shadow:0 1px 0 #ffffff08 inset; }
.stat .n { font-size:1.5rem; font-weight:800; color:var(--text); letter-spacing:-.5px;
  line-height:1.1; }
.stat .l { font-size:.7rem; color:var(--muted); text-transform:uppercase;
  letter-spacing:.8px; font-weight:600; margin-top:.1rem; }

.disc { font-size:.8rem; color:#d9c97e; background:#2a230d66; border:1px solid #4d4118;
  border-radius:12px; padding:.6rem .9rem; margin-bottom:1.3rem; }

/* scenario cards */
.scn { position:relative; background:linear-gradient(180deg,var(--card),var(--card2));
  border:1px solid var(--line); border-radius:16px; padding:1rem 1.2rem; margin-bottom:.85rem;
  transition:border-color .15s, transform .15s, box-shadow .15s; }
.scn:hover { border-color:var(--line2); transform:translateY(-1px);
  box-shadow:0 10px 30px #00000040; }
.scn-title { font-size:1.04rem; font-weight:700; color:#f2f6ff; line-height:1.35; }
.scn-topic { color:#7aa7ec; font-size:.8rem; font-weight:600; margin-top:.1rem;
  text-transform:uppercase; letter-spacing:.4px; }
.metarow { display:flex; gap:.4rem; flex-wrap:wrap; margin:.55rem 0 .7rem; }
.tag { font-size:.72rem; padding:.2rem .6rem; border-radius:8px; border:1px solid var(--line2);
  color:#c3d0e6; background:#0d1730; font-weight:500; }
.tag.panel { border-color:#3b528077; color:#a8c6ff;
  background:linear-gradient(180deg,#16294a,#122039); }

/* procedure table */
table.pt { width:100%; border-collapse:collapse; margin-top:.35rem; }
table.pt td { padding:.42rem .55rem; border-top:1px solid #ffffff0d; font-size:.88rem;
  vertical-align:middle; }
table.pt tr:first-child td { border-top:none; }
table.pt tr:hover td { background:#ffffff06; }
.dot { display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:.55rem;
  box-shadow:0 0 8px currentColor; }
.pill { font-size:.7rem; font-weight:700; padding:.18rem .6rem; border-radius:999px;
  white-space:nowrap; letter-spacing:.2px; }
.proc { color:#eaf0fb; font-weight:500; }
.rrl { color:var(--muted); font-size:.78rem; white-space:nowrap; text-align:right;
  font-variant-numeric:tabular-nums; }

/* Dx recognition card */
.dxcard { background:linear-gradient(135deg,#10224a,#141b35);
  border:1px solid #2f4f86; border-radius:16px; padding:1rem 1.2rem; margin-bottom:1rem;
  box-shadow:0 8px 30px #1d3a7233; }
.dxcard .lbl { font-size:.72rem; color:#7aa7ec; text-transform:uppercase;
  letter-spacing:1px; font-weight:700; }
.dxcard .dx { font-size:1.3rem; font-weight:800; color:#fff; letter-spacing:-.3px; }
.dxcard .meta { color:#9fb4d6; font-size:.8rem; margin-top:.3rem; }
.dxcard code { background:#0c1530; color:#9ec1ff; padding:.05rem .4rem; border-radius:6px; }
.toph { font-size:1.05rem; font-weight:700; color:#dfe8fb; margin:1rem 0 .4rem;
  display:flex; align-items:center; gap:.5rem; }

/* chip de modalidad (TC/RM/Eco…) */
.modchip { display:inline-block; font-size:.62rem; font-weight:800; letter-spacing:.3px;
  padding:.1rem .42rem; border-radius:6px; border:1px solid; margin-right:.5rem;
  vertical-align:middle; min-width:38px; text-align:center; }

/* buscador principal (protagonista) */
.stTextInput input { font-size:1.02rem !important; padding:.7rem .95rem !important;
  border-radius:12px !important; background:#0e1830 !important;
  border:1px solid var(--line2) !important; }
.stTextInput input::placeholder { color:#6b7a93 !important; }

/* leyenda */
.legend { display:flex; gap:1.1rem; flex-wrap:wrap; font-size:.74rem; color:var(--muted);
  margin:.1rem 0 1rem; align-items:center; }
.legend b { color:#cdd8ea; }

/* buttons (chips) */
.stButton > button { background:#101b33; border:1px solid var(--line2); border-radius:10px;
  color:#cdd9ef; font-weight:600; transition:all .15s; }
.stButton > button:hover { border-color:var(--accent); color:#fff;
  background:#16244a; transform:translateY(-1px); }
.stButton > button[kind="primary"] { background:linear-gradient(135deg,#2563eb,#7c3aed);
  border:none; color:#fff; box-shadow:0 6px 18px #3b82f63d; }
.stButton > button[kind="primary"]:hover { filter:brightness(1.08); transform:translateY(-1px); }
</style>
""", unsafe_allow_html=True)


# ----------------------- detección de modalidad ---------------------------
# Nomenclatura estándar (estilo DICOM/radiología internacional).
_MODCOLOR = {"CT": "#fb923c", "CTA": "#fb923c", "CTV": "#fb923c", "XA": "#fb923c",
             "MR": "#38bdf8", "MRA": "#38bdf8", "MRV": "#38bdf8",
             "US": "#34d399", "XR": "#94a3b8", "RF": "#94a3b8", "MG": "#f472b6",
             "NM": "#eab308", "PET": "#c084fc", "SPECT": "#c084fc", "DXA": "#f472b6"}
_MODPREFIX = [
    ("FDG-PET", "PET"), ("DOTATATE PET", "PET"), ("PSMA PET", "PET"),
    ("Fluciclovine PET", "PET"), ("PET", "PET"), ("SPECT", "SPECT"),
    ("CTA", "CTA"), ("CTV", "CTV"), ("CT", "CT"),
    ("MRA", "MRA"), ("MRV", "MRV"), ("MRI", "MR"), ("MR ", "MR"),
    ("US", "US"), ("Ultrasound", "US"),
    ("Radiography", "XR"), ("Radiograph", "XR"),
    ("Mammography", "MG"), ("Tomosynthesis", "MG"), ("DXA", "DXA"),
    ("Fluoroscopy", "RF"),
    ("Bone scan", "NM"), ("Lymphoscintigraphy", "NM"), ("Sestamibi", "NM"),
    ("MIBG", "NM"), ("Arteriography", "XA"), ("Aortography", "XA"),
    ("Angiography", "XA"), ("Venography", "XA"),
]


def _modhtml(proc_en):
    """Chip de modalidad (nomenclatura inglesa CT/MR/US…) detectado del nombre EN."""
    lbl = None
    for key, m in _MODPREFIX:
        if proc_en.startswith(key):
            lbl = m
            break
    if lbl is None:
        pl = proc_en.lower()
        if "echocard" in pl:
            lbl = "US"
        elif "scan" in pl or "scintigraph" in pl:
            lbl = "NM"
    if not lbl:
        return ""
    c = _MODCOLOR.get(lbl, "#94a3b8")
    return (f'<span class="modchip" style="color:{c};border-color:{c}66;'
            f'background:{c}1a">{lbl}</span>')

# --------------------------- sin dataset ----------------------------------
if not consulta_acr.disponible():
    st.markdown('<div class="hero"><h1>🩻 ACR Explorer</h1></div>', unsafe_allow_html=True)
    st.error("El dataset ACR no está descargado todavía.")
    st.code("python tools/importar_portal_acr.py lista\n"
            "python tools/importar_portal_acr.py extraer --all", language="bash")
    st.stop()

S = consulta_acr.estadisticas()

SEXO_ES = {"All": "Ambos sexos", "Female Only": "Solo mujeres",
           "Male Only": "Solo hombres"}

# Un atajo (chip) deja su término en '_pending'; lo pasamos al buscador ANTES
# de instanciar el widget (Streamlit no permite modificarlo después).
if "_pending" in st.session_state:
    st.session_state["busqueda"] = st.session_state.pop("_pending")


def _nueva_busqueda():
    """Limpia el buscador para empezar otra consulta (callback de botón)."""
    st.session_state["_pending"] = ""

# ------------------------------ sidebar -----------------------------------
with st.sidebar:
    es = st.toggle("🌐 Traducir al español", value=True,
                   help="Procedimientos, categorías y dosis: traducción médica "
                        "curada. Descripciones: traducción automática.")
    st.markdown("### Filtros")
    paneles_sel = st.multiselect("Panel", consulta_acr.paneles(),
                                 format_func=T.traducir_panel,
                                 placeholder="Todos los paneles")
    sexos_sel = st.multiselect("Sexo", consulta_acr.valores("sexo"),
                               format_func=lambda s: SEXO_ES.get(s, s),
                               placeholder="Todos")
    areas_all = consulta_acr.valores("area_corporal")
    areas_sel = st.multiselect("Área corporal", areas_all,
                               format_func=T.traducir_area, placeholder="Todas")
    _FASE_LBL = {"inicial": "🟢 Inicial", "siguiente": "🔵 Siguiente",
                 "seguimiento": "⚪ Seguimiento", "tamizaje": "🩵 Tamizaje"}
    fases_sel = st.multiselect("Fase del estudio", list(_FASE_LBL),
                               format_func=lambda f: _FASE_LBL.get(f, f),
                               placeholder="Todas las fases",
                               help="Qué pedir primero (Inicial) vs. estudios "
                                    "posteriores según resultado o seguimiento.")
    solo_aprop = st.toggle("✅ Mostrar solo lo apropiado", value=False,
                           help="Muestra en cada escenario solo lo usualmente "
                                "apropiado pedir.")
    st.divider()
    st.caption("⚠️ Educativo / de apoyo. No reemplaza el juicio médico.")
    st.caption("Fuentes: ACR Appropriateness Criteria® © American College of "
               "Radiology · SNOMED CT® © SNOMED International.")

# ------------------------------ header ------------------------------------
_LOGO_SVG = (
    '<svg width="23" height="23" viewBox="0 0 24 24" fill="none" stroke="#fff" '
    'stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="7.5"/>'
    '<path d="M12 1.5v3.2M12 19.3v3.2M1.5 12h3.2M19.3 12h3.2"/>'
    '<circle cx="12" cy="12" r="2.3" fill="#fff" stroke="none"/></svg>')

st.markdown(
    f'<div class="appbar">'
    f'<div class="brand"><div class="logo">{_LOGO_SVG}</div>'
    f'<div><div class="pname">ACR <b>Explorer</b></div>'
    f'<div class="ptag">Sistema de apoyo a la decisión clínica · estudios por imágenes</div>'
    f'</div></div>'
    f'<div class="trust"><span class="tchip">ACR Appropriateness Criteria®</span>'
    f'<span class="tchip">SNOMED CT®</span>'
    f'<span class="tchip alt">Uso educativo</span></div></div>'
    '<div class="lead"><h2>Del diagnóstico al <span class="hl">estudio correcto</span>, '
    'con evidencia.</h2>'
    '<p>El estudio por imágenes recomendado por el ACR, con el estudio inicial '
    'priorizado y trazabilidad a SNOMED CT.</p></div>',
    unsafe_allow_html=True)

# Buscador protagonista (área principal)
st.markdown('<div class="searchlbl">Escribí un diagnóstico, síntoma o patología</div>',
            unsafe_allow_html=True)
q = st.text_input(
    "Buscar", key="busqueda", label_visibility="collapsed",
    placeholder="🔎   ej. angor · cefalea súbita · cáncer de mama · TEP")

st.markdown(
    '<div class="legend"><span>✅ <b>Apropiado</b></span>'
    '<span>🟡 <b>Puede</b></span><span>⛔ <b>No apropiado</b></span>'
    '<span style="margin-left:.5rem">Modalidad:</span>'
    '<span class="modchip" style="color:#fb923c;border-color:#fb923c66;background:#fb923c1a">CT</span>'
    '<span class="modchip" style="color:#38bdf8;border-color:#38bdf866;background:#38bdf81a">MR</span>'
    '<span class="modchip" style="color:#34d399;border-color:#34d39966;background:#34d3991a">US</span>'
    '<span class="modchip" style="color:#94a3b8;border-color:#94a3b866;background:#94a3b81a">XR</span>'
    '<span class="modchip" style="color:#eab308;border-color:#eab30866;background:#eab3081a">NM</span>'
    '<span class="modchip" style="color:#c084fc;border-color:#c084fc66;background:#c084fc1a">PET</span>'
    '</div>', unsafe_allow_html=True)


def _tabla_procs(procs, solo_ap=True):
    """HTML de tabla de procedimientos (traducidos)."""
    filas = ""
    for p in procs:
        if solo_ap and p["adecuacion"] != "apropiado":
            continue
        c = ADEC.get(p["adecuacion"], ADEC[""])
        nombre = T.traducir_procedimiento(p["procedimiento"]) if es else p["procedimiento"]
        cat = T.traducir_categoria(p["categoria"]) if es else p["categoria"]
        rrl = T.traducir_rrl(p.get("rrl_adulto", "")) if es else p.get("rrl_adulto", "")
        filas += (f'<tr><td style="width:58%">{_modhtml(p["procedimiento"])}'
                  f'<span class="proc">{html.escape(nombre)}</span></td>'
                  f'<td style="width:24%"><span class="pill" style="background:{c["bg"]};'
                  f'color:{c["pill"]};border:1px solid {c["pill"]}55">{html.escape(cat)}</span></td>'
                  f'<td class="rrl">{html.escape(rrl)}</td></tr>')
    return f'<table class="pt">{filas}</table>' if filas else ""


# Procedencia del match (transparencia): de dónde salió la interpretación.
_ORIGEN_CHIP = {
    "snomed":    ("#34d399", "✓ SNOMED CT"),
    "extension": ("#fb923c", "+ extensión local"),
    "variante":  ("#38bdf8", "≈ variante lingüística"),
}


def _chip_origen(origen):
    c, txt = _ORIGEN_CHIP.get(origen, _ORIGEN_CHIP["snomed"])
    return (f'<span class="modchip" style="color:{c};border-color:{c}66;'
            f'background:{c}1a">{txt}</span>')


# Badge de fase del escenario (qué pedir primero vs. después).
_FASE_CHIP = {
    "inicial":     ("#34d399", "INICIAL"),
    "tamizaje":    ("#22d3ee", "TAMIZAJE"),
    "siguiente":   ("#7aa7ec", "SIGUIENTE"),
    "seguimiento": ("#94a3b8", "SEGUIMIENTO"),
}


def _chip_fase(fase):
    if fase not in _FASE_CHIP:
        return ""
    c, txt = _FASE_CHIP[fase]
    return (f'<span class="modchip" style="color:{c};border-color:{c}66;'
            f'background:{c}1a">{txt}</span>')


def _render_escenario(e):
    """Renderiza un escenario ACR (título traducido + badge de fase + tabla)."""
    titulo = T.traducir_clinico(e["escenario"]) if es else e["escenario"]
    tabla = _tabla_procs(e["procedimientos"], solo_ap=solo_aprop)
    cuerpo = tabla or ("<i style='color:#8a98ad'>Sin opción 'apropiada' "
                       "(destildá 'solo lo apropiado' para ver todo)</i>"
                       if solo_aprop else "")
    st.markdown(
        f'<div class="scn"><div class="scn-title" style="font-size:.95rem">'
        f'{_chip_fase(e.get("fase", ""))} {html.escape(titulo)}</div>{cuerpo}</div>',
        unsafe_allow_html=True)


def render_dx(dxres, dxq):
    """Vista Dx → Estudio: interpretación explicable + tópicos y estudios apropiados."""
    for res in dxres["resultados"]:
        sinos = ", ".join(res["sinonimos"][:8])
        org = res.get("origen", "snomed")
        st.markdown(
            f'<div class="dxcard"><div class="lbl">🩺 Diagnóstico reconocido '
            f'· «{html.escape(dxq)}»</div>'
            f'<div class="dx">{html.escape(res["dx"])}</div>'
            f'<div class="meta">{_chip_origen(org)} &nbsp; SNOMED CT '
            f'<code>{res["snomed"]}</code> &nbsp;·&nbsp; '
            f'sinónimos: {html.escape(sinos)}</div></div>',
            unsafe_allow_html=True)
        if org == "extension":
            st.caption("ℹ️ Reconocido por la **extensión local del proyecto** "
                       "(acrónimo de uso clínico no presente en SNOMED-ES), mapeado "
                       f"al concepto SNOMED CT `{res['snomed']}`.")
        elif org == "variante":
            st.caption("ℹ️ Reconocido por **variante lingüística** (forma adjetival) "
                       "y llevado a la forma equivalente que sí existe en SNOMED CT.")
        for tp in res["topicos"]:
            nombre = T.traducir_topico(tp["topico_en"]) if es else tp["topico_en"]
            st.markdown(f'<div class="toph">📚 {html.escape(nombre)}</div>',
                        unsafe_allow_html=True)
            escs = tp["escenarios"]
            if fases_sel:
                escs = [e for e in escs if e.get("fase") in fases_sel]
            if not escs:
                st.caption("Sin escenarios para la fase elegida." if fases_sel
                           else "Sin escenarios cargados para este tópico.")
                continue
            # Estudios INICIALES primero; los posteriores en un desplegable.
            iniciales = [e for e in escs if e.get("fase") in ("inicial", "tamizaje", "otro")]
            posteriores = [e for e in escs if e.get("fase") in ("siguiente", "seguimiento")]
            if not iniciales:                 # tópico sin escenario inicial → mostrar todo
                for e in posteriores:
                    _render_escenario(e)
                continue
            for e in iniciales:
                _render_escenario(e)
            if posteriores:
                with st.expander(f"➕ Estudios siguientes / de seguimiento "
                                 f"({len(posteriores)})"):
                    for e in posteriores:
                        _render_escenario(e)


# ------------------------------ resultados --------------------------------
LIMITE = 40

# 1) Si lo escrito es un DIAGNÓSTICO reconocido por SNOMED -> vista Dx → Estudio
if q.strip() and Dx.disponible():
    dxres = Dx.resolver(q)
    if dxres["match"]:
        st.button("← Buscar otro diagnóstico", on_click=_nueva_busqueda,
                  type="primary", key="volver_top")
        render_dx(dxres, q)
        st.caption("☝️ Reconocido como **diagnóstico** (vía SNOMED CT). "
                   "Si querías buscar texto en los criterios, agregá más palabras.")
        st.button("← Buscar otro diagnóstico", on_click=_nueva_busqueda,
                  key="volver_bottom")
        st.stop()

# 2) Si no, búsqueda de texto normal en los criterios
resultados, total = consulta_acr.filtrar(
    texto=q, paneles=paneles_sel, sexos=sexos_sel, areas=areas_sel,
    fases=fases_sel, solo_con_apropiado=solo_aprop, limite=LIMITE)

hay_filtro = bool(q or paneles_sel or sexos_sel or areas_sel or fases_sel or solo_aprop)
if not hay_filtro:
    st.markdown("**Diagnósticos frecuentes (probá tocando uno):**")
    chips = ["angor", "IAM", "ACV", "TEP", "apendicitis", "cólico renal",
             "cefalea", "lumbalgia", "neumonía", "diverticulitis",
             "cáncer de mama", "litiasis renal"]
    cols = st.columns(4)
    for i, term in enumerate(chips):
        if cols[i % 4].button(term, use_container_width=True):
            st.session_state["_pending"] = term
            st.rerun()
    st.stop()

# 3) No se encontró nada
if hay_filtro and total == 0:
    if q.strip():
        st.markdown(
            f'<div class="scn" style="border-left:4px solid #f87171">'
            f'<div class="scn-title">🔍 No encontré «{html.escape(q)}» en el ACR</div>'
            f'<div class="scn-topic" style="text-transform:none;color:#aebbd2;'
            f'font-weight:400;margin-top:.6rem;line-height:1.5">'
            f'<b>«{html.escape(q)}»</b> no está mapeado a un estudio del '
            f'<b>ACR Appropriateness Criteria®</b> — la guía del '
            f'<b>American College of Radiology</b> que define qué estudio por '
            f'imágenes es apropiado según el cuadro clínico.<br><br>'
            f'Puede deberse a que:<br>'
            f'&nbsp;&nbsp;• el ACR <b>no tiene un criterio de imágenes</b> para ese diagnóstico, o<br>'
            f'&nbsp;&nbsp;• el término está <b>mal escrito o incompleto</b>.<br><br>'
            f'👉 Revisá la ortografía o probá con <b>otro diagnóstico</b> '
            f'(o uno más específico).</div></div>',
            unsafe_allow_html=True)
    else:
        st.info("No hay escenarios con esos filtros. Probá aflojar alguno.")
    st.stop()

if hay_filtro:
    st.markdown(f"**{total}** escenario(s)"
                + (f" · mostrando {len(resultados)}" if total > len(resultados) else ""))

    def pill(adec, texto):
        c = ADEC.get(adec, ADEC[""])
        return (f'<span class="pill" style="background:{c["bg"]};color:{c["pill"]};'
                f'border:1px solid {c["pill"]}55">{html.escape(texto)}</span>')

    def dot(adec):
        c = ADEC.get(adec, ADEC[""])
        return f'<span class="dot" style="background:{c["pill"]}"></span>'

    SEXO_ES = {"All": "Ambos sexos", "Female Only": "Solo mujeres",
               "Male Only": "Solo hombres"}

    for e in resultados:
        procs = e.get("procedimientos", [])
        if solo_aprop:
            procs = [p for p in procs if p["adecuacion"] == "apropiado"]
        filas = ""
        for p in procs:
            nombre = T.traducir_procedimiento(p["procedimiento"]) if es else p["procedimiento"]
            cat = T.traducir_categoria(p["categoria"]) if es else p["categoria"]
            rrl = T.traducir_rrl(p.get("rrl_adulto", "")) if es else p.get("rrl_adulto", "")
            filas += (
                f'<tr><td style="width:55%">{_modhtml(p["procedimiento"])}'
                f'<span class="proc">{html.escape(nombre)}</span></td>'
                f'<td style="width:25%">{pill(p["adecuacion"], cat)}</td>'
                f'<td class="rrl">{html.escape(rrl)}</td></tr>')
        titulo = T.traducir_clinico(e.get("escenario", "")) if es else e.get("escenario", "")
        topico = T.traducir_topico(e.get("topico", "")) if es else e.get("topico", "")
        meta = ""
        if e.get("panel"):
            meta += f'<span class="tag panel">{html.escape(e["panel"])}</span>'
        sx = e.get("sexo", "")
        if sx and sx != "All":
            meta += f'<span class="tag">{html.escape(SEXO_ES.get(sx, sx) if es else sx)}</span>'
        edad = e.get("edad", "")
        if edad and edad != "All":
            meta += f'<span class="tag">{html.escape(edad)}</span>'
        area = e.get("area_corporal", "")
        if area and area != "All":
            area_txt = T.traducir_area(area) if es else area
            meta += f'<span class="tag">{html.escape(area_txt)}</span>'
        st.markdown(
            f'<div class="scn">'
            f'<div class="scn-title">{_chip_fase(e.get("fase", ""))} {html.escape(titulo)}</div>'
            f'<div class="scn-topic">{html.escape(topico)}</div>'
            f'<div class="metarow">{meta}</div>'
            f'<table class="pt">{filas}</table></div>',
            unsafe_allow_html=True)

    if total > len(resultados):
        st.caption(f"Hay {total - len(resultados)} escenarios más. Afiná la búsqueda "
                   "para verlos.")
