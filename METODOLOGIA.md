# Metodología y validación

Cómo se construyó y verificó **ACR Explorer**. Pensado para transparencia y para
que un revisor (técnico o clínico) pueda auditar el proceso.

## 1. Fuentes de datos

| Fuente | Uso | Versión |
|---|---|---|
| ACR AC Portal (gravitas.acr.org) | 4115 escenarios estructurados (procedimiento + dosis RRL + categoría de adecuación) | scrapeado vía `tools/importar_portal_acr.py` |
| ACR acsearch.acr.org | Catálogo clásico (278 tópicos, IDs, citas) | `tools/importar_acr.py` |
| SNOMED CT — Edición Argentina (RF2) | Sinónimos de diagnósticos + jerarquía IS-A | release `20260520` (PRODUCTION) |

## 2. Pipeline de construcción

```
ACR AC Portal ──scrape──► portal_data.json (4115 escenarios)
SNOMED RF2    ──anclar──► crosswalk_resuelto.json (Dx → conceptId)
              ──extraer─► sinonimos_snomed.json (conceptos + descendientes IS-A + sinónimos)
```

- **Crosswalk (Dx → tópico ACR):** 175 anclas curadas a mano (`data/anclas_terminos.py`),
  cubriendo diagnósticos frecuentes de los 13 paneles. Los términos se resuelven a
  `conceptId` SNOMED en una pasada sobre el archivo de descripciones.
- **Expansión por jerarquía (↑ y ↓):** cada ancla se expande a **todos sus
  descendientes** (IS-A hacia abajo) y a sus **padres directos** (1 nivel hacia
  arriba, para captar sinónimos equivalentes como "infarto de miocardio" sobre el
  agudo). Resultado: 175 anclas → **18.278 conceptos** → 27.402 sinónimos. Así,
  subtipos no cargados a mano (p.ej. "leucemia mieloide aguda") resuelven solos.
  Se subió solo 1 nivel: a 2+ niveles aparecían falsos positivos (p.ej. "dolor"
  → un tópico específico).

### Extensión local + variantes lingüísticas (trazable)

SNOMED CT en español **no incluye** ciertos acrónimos clínicos de uso corriente
(TEP, HSA, TCE, ICC, HDA…) ni la forma **adjetival** de algunos términos
("disección aórtica" vs la forma preposicional "disección de aorta", que sí
está). Se verificó contra tres releases (AR Edition, AR Extension y Spanish
International, 1,16 M descripciones): no están en ninguno. Para no perder
usabilidad **sin inventar conceptos**, se agregan dos capas (`data/extension_local.py`):

- **Alias locales** (`origen = extension`): cada acrónimo se ata a un **conceptId
  SNOMED real ya anclado** (TEP → 59282003). Es el mecanismo de una extensión
  nacional: agregar una descripción a un concepto internacional. Limitado a
  acrónimos médicos estándar con tópico ACR (no coloquialismos).
- **Variantes lingüísticas** (`origen = variante`): reglas morfológicas
  (adjetivo ↔ preposición) que **transforman la consulta** a la forma que existe
  en SNOMED. No agregan términos.

**Transparencia:** cada interpretación se marca con su origen (`snomed`,
`extension`, `variante`) y la app lo muestra con un chip + nota, para que el
usuario sepa siempre si el término vino de SNOMED puro o de la capa local.

## 3. Traducción médica (no literal)

- **Procedimientos**: traductor por componentes (modalidad + región + contraste).
- **Categorías / dosis / paneles / áreas**: mapeo exacto.
- **Tópicos (270)**: **curados a mano** con terminología médica (`data/topicos_es.py`).
- **Escenarios** (texto libre): glosario clínico con reglas de orden y concordancia
  (p.ej. "acute appendicitis" → "apendicitis aguda", no "aguda apendicitis").

### Cómo se validó la cobertura de traducción
Se usó el **vocabulario español de SNOMED CT** (105.613 palabras del RF2) como
diccionario médico de referencia: toda palabra de una traducción que **no exista**
en ese vocabulario se marca como sospechosa (inglés o término incorrecto) y se
corrige. Cobertura por ocurrencia de palabra alcanzada:

| Capa | Cobertura |
|---|---|
| Procedimientos | ~98% |
| Escenarios (descripciones) | ~98% |
| Tópicos | ~99% |

El ~2% restante son términos rarísimos (1–2 apariciones). La app ofrece un toggle
para ver el **texto original en inglés** y verificar.

## 4. Verificación de integridad de los datos

`tools/verificar_integridad.py` compara los datos locales contra el ACR **en vivo**:
- Conteo de escenarios e IDs (local vs live).
- Comparación **profunda** de una muestra (campo por campo: procedimiento,
  dosis, categoría, adecuación).
- Integridad interna (campos completos, sin vacíos).
- Que la traducción **no mute** los datos fuente (función pura).

**Resultado de la última corrida (muestra de 130 escenarios, 13 paneles):**
`✅ DATOS ÍNTEGROS — 130/130 idénticos, 0 diferencias, 0 IDs faltantes.`

### Validación de los conceptos SNOMED
`tools/verificar_snomed.py` valida cada concepto del crosswalk contra el RF2:
- que el conceptId esté **ACTIVO** (no retirado),
- su nombre completamente especificado (FSN) en español,
- coherencia entre la etiqueta del diagnóstico y el concepto.

**Resultado:** `✅ 175/175 coherentes · 0 inactivos.` En la auditoría se detectaron
y **corrigieron 15 conceptos inactivos** (IDs retirados de SNOMED) reemplazándolos
por su concepto activo equivalente — lo que además mejoró la cobertura por
jerarquía (conceptos activos sí tienen descendientes).

### Validación clínica externa (guía SAR)
Las recomendaciones (basadas en ACR, americano) se contrastaron con la *Guía de
recomendaciones para la correcta solicitud de pruebas de diagnóstico por imagen*
de la **Sociedad Argentina de Radiología (SAR)** —de base europea PR/118— en las
condiciones más frecuentes (cefalea, ACV, lumbalgia, dolor biliar, pancreatitis,
cólico renal, apendicitis, tamizaje de mama). **Concuerdan en las decisiones
núcleo**; las diferencias son la divergencia conocida ACR-vs-europeo (la SAR es
más conservadora con la dosis: escalona clínica→ecografía→TC donde el ACR va
directo a TC). Ver `VALIDACION_CLINICA.md`.

## 5. Fase del escenario (estudio inicial primero)

Cada escenario ACR se clasifica por su **fase clínica** (`core/consulta_acr.fase_escenario`):
`inicial` (initial imaging — qué pedir primero), `siguiente` (estudio posterior
según resultado: "next imaging study", "US equivocal/negative"…), `seguimiento`
(vigilancia/restaging), `tamizaje` (screening) u `otro`. La app **ordena los
iniciales primero** y deja los posteriores en un desplegable, con un filtro por
fase. Es la decisión real al lado del paciente: *qué pido ahora*.

## 6. Performance

- **Traducciones cacheadas** (`lru_cache`): cada texto único se traduce una vez.
- **Índices cacheados a disco** (búsqueda y diagnóstico) con firma de invalidación
  (mtime+tamaño de los datos y del glosario): la primera búsqueda pasa de ~1,5 s a
  ~50 ms. Los caches viven en `acr_cache/` (ignorado por git) y se regeneran solos
  si cambian los datos o las traducciones.

## 7. Tests automatizados

**46 tests** en total:
- `tests/test_motor.py` — motor de reglas.
- `tests/test_traduccion.py` — traductor (sin datos licenciados; corre en CI).
- `tests/test_fase.py` — clasificador de fase del escenario (lógica pura).
- `tests/test_diagnostico.py` — resolver Dx, alias locales y variantes (se saltea
  si faltan datos SNOMED).

CI (GitHub Actions) corre los tests en cada push, sin depender de datos licenciados.

## 8. Limitaciones conocidas

- Nombres de **morfología** (glioblastoma, meningioma) no resuelven aún (son
  conceptos de morfología, no de enfermedad). Planeado: sumar el eje de morfología.
- **~98 tópicos sin ancla** son de flujo de imágenes (tamizaje de asintomáticos,
  planificación pre-procedimiento, post-operatorio) — no se alcanzan por un
  diagnóstico (por diseño); se llega por el buscador de texto.
- Los **29 tópicos pediátricos** requieren un selector de edad (pendiente).
- Términos coloquiales que **no existen en SNOMED ES** (ictus, derrame cerebral,
  pulmonía) no resuelven — se respeta SNOMED como única fuente.
- La traducción de escenarios libres es por reglas: cubre ~98%, no 100%.
- **No es un dispositivo médico** ni está clínicamente validado de forma formal
  (ver `VALIDACION_CLINICA.md`).
