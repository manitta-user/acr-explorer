# Guía de desarrollo

Notas para retomar el proyecto (uso interno). Para el "qué/por qué" ver
[README.md](README.md) y [METODOLOGIA.md](METODOLOGIA.md).

## Puesta en marcha

```bash
pip install -r requirements.txt
python -m streamlit run app_streamlit.py --server.port 8534
python -m pytest -q          # 46 tests
```

La app necesita los datos en `acr_cache/` (gitignored, no vienen en el repo).
Si faltan, ver "Regenerar datos".

## ⚠️ Gotcha importante (Streamlit y recarga)

- Editar **`app_streamlit.py`** (script principal) → alcanza con **refrescar el
  navegador** (Streamlit lo recarga solo).
- Editar **módulos importados** (`core/*.py`, `data/*.py`) → Streamlit **NO los
  recarga**. Hay que **matar y relanzar** el proceso:
  ```powershell
  Get-CimInstance Win32_Process -Filter "name='python.exe'" |
    Where-Object { $_.CommandLine -like '*streamlit*' } | Stop-Process -Force
  python -m streamlit run app_streamlit.py --server.port 8534
  ```
- Síntoma típico si no reiniciás: cambios de traducción no aparecen, o
  `TypeError` por firmas de función viejas.

## Estructura

```
core/
  motor.py          Reglas de las 11 patologías de guardia (criterio propio)
  consulta_acr.py   Consulta los 4115 escenarios + fase_escenario() + cache disco
  traduccion.py     Traductor EN→ES por glosarios (_PROC/_CLIN/_AREA), 1 pasada
  diagnostico.py    Resolver Dx→SNOMED→tópico, con procedencia (origen) + cache
data/
  topicos_es.py     270 tópicos ACR traducidos
  anclas_terminos.py 175 diagnósticos ancla → tópicos ACR (curado a mano)
  crosswalk_acr.py  Carga acr_cache/crosswalk_resuelto.json
  extension_local.py Alias acrónimos (TEP, HSA…) → conceptId SNOMED + variantes ling.
  criterios_acr.py  Reglas de las 11 patologías
tools/              Importadores (ACR portal, SNOMED RF2) + verificadores
app_streamlit.py    Interfaz (puerto 8534)
tests/              motor, traduccion, fase, diagnostico
```

## Conceptos clave del código

- **Traducción** (`traduccion.py`): `_aplicar(glosario, texto)` reemplaza en UNA
  pasada con regex de alternancia (frases largas primero, límites de letra). Para
  agregar términos: sumar `"en inglés": "en español"` al glosario correcto
  (`_PROC` procedimientos, `_CLIN` escenarios, `_AREA` áreas). Las regiones del
  cuerpo llevan `"de "` (ej. `"kidneys": "de riñones"`). Todo es `@lru_cache`.
- **Resolver** (`diagnostico.py`): normaliza la query → busca en el índice
  (sinónimos SNOMED + alias locales) → match exacto, variante lingüística, o
  contención segura. Devuelve `origen` ∈ {snomed, extension, variante} que la UI
  muestra como chip.
- **Fase** (`consulta_acr.fase_escenario`): clasifica cada escenario en
  inicial / siguiente / seguimiento / tamizaje / otro. La app muestra los
  iniciales primero + filtro por fase.
- **Caches a disco** (`acr_cache/_idx_*.json`): se regeneran solos si cambian los
  datos o `traduccion.py` (firma = mtime+tamaño). Si algo raro pasa, borralos.

## Regenerar datos (necesita las fuentes licenciadas)

```bash
python tools/importar_portal_acr.py lista
python tools/importar_portal_acr.py extraer --all
python tools/importar_snomed.py anclar  --rf2 <ruta_RF2_SNOMED>
python tools/importar_snomed.py extraer --rf2 <ruta_RF2_SNOMED>
python tools/verificar_integridad.py    # audita vs ACR en vivo
python tools/verificar_snomed.py        # valida conceptos activos
```

> Nota: la ruta por defecto del RF2 está hardcodeada en `tools/importar_snomed.py`
> (`RF2_DEFAULT`). Si se cambia de máquina, ajustar o pasar `--rf2`.

## Roadmap / pendientes

- [ ] "Resumen de estudio inicial recomendado" arriba del resultado (alta prioridad).
- [ ] Métricas tipo dashboard + resultados en 2 columnas.
- [ ] Selector de edad → desbloquear los 29 tópicos pediátricos.
- [ ] Eje de morfología (glioblastoma/meningioma no resuelven).
- [ ] Crosswalk procedimientos→SNOMED para FHIR ServiceRequest.code.
- [ ] Limpiar el ~2% de términos raros en inglés que quedan en escenarios.
