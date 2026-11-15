# Rebuilder v2 — S3T11

`rebuild_document(original_path, structured_di)` devuelve un `docx.Document`
reconstruido sobre una copia en memoria del paquete original. También acepta
un stream binario o un `Document` como origen; el archivo y el objeto recibido
no se modifican.

```python
from docx_engine.extractor import extract_document
from docx_engine.rebuilder import rebuild_document

path = "tests/fixtures/06_secciones.docx"
di = extract_document(path)
document = rebuild_document(path, di)
document.save("resultado.docx")
```

Para aplicar propuestas estructuradas, se puede pasar un diccionario con
`blocks`, una lista de bloques o un `AIChunkOutput`:

```python
proposed = {"blocks": [
    {"type": "heading", "level": 0, "src": ["b0"],
     "runs": [{"text": "Título del documento"}]},
    {"type": "paragraph", "src": ["b1"],
     "runs": [{"text": "Texto de cuerpo", "underline": True}]},
    {"type": "keep", "src": ["b2"]},
]}
# Los IDs se refieren a posiciones del body del documento original.
```

## Reconstrucción

- Se vacía el body conservando su `sectPr` final. Los bloques se insertan en
  orden, antes de ese elemento. Si el DI incluye el `sectPr` final, no se duplica.
- `keep` hace `deepcopy` del XML original por `src`, o por `id` si no lleva
  `src`. Puede agrupar varios IDs en orden. Se ignora cualquier XML suministrado
  en el DI: las imágenes, tablas y secciones siempre proceden del paquete
  original, que conserva sus relaciones, estilos, encabezados y pies.
- Cada bloque opaco debe aparecer exactamente una vez y en el orden original.
  El `sectPr` final se conserva automáticamente, aunque se omita en la propuesta.
- `heading` de nivel 0 usa `Title`; los niveles 1–3 usan `Heading 1–3`.
  Se mantiene la compatibilidad del esquema anterior con niveles 4–6.
- `paragraph` usa `Normal`. `callout` con `kind="quote"` usa `Quote`;
  `kind="note"` o `"warning"` usa `Intense Quote`. Los estilos ausentes se crean.
- Los runs nuevos aplican `bold`, `italic` y `underline`, incluidos valores
  explícitos `False`. No aplican fuente, tamaño ni color: se delegan a la plantilla.
- Las tablas nuevas validan su ancho efectivo, respetan `h_span` y marcan la
  primera fila con `tblHeader`. Las celdas aceptan `text` o `runs`. Las tablas
  originales con fusiones verticales se mantienen mediante `keep`.

## Listas nativas

`list_item` utiliza `level` (0–8) y `ordered`, con compatibilidad para
`is_numbered`. El XML del párrafo contiene `numPr`, `numId` e `ilvl`.

`numbering.py` reutiliza definiciones compatibles de nueve niveles o crea un
`abstractNum` de viñetas y otro decimal según se necesiten. No modifica las
definiciones originales. También crea la parte de numeración si el paquete
no la contiene.

Una lista nueva obtiene su propio `numId` y comienza en 1. Un bloque que no
sea lista termina la secuencia. Las viñetas anidadas no interrumpen la
numeración de su lista padre. Para distinguir listas contiguas se puede usar
`list_id`; `restart: true` fuerza un reinicio explícito.

## Integridad y compatibilidad

Antes de devolver el resultado, se guarda en `BytesIO`, se reabre y se compara
su secuencia de palabras y números con el DI usando
`common.integrity.validate_tokens()`. Esta función devuelve un `IntegrityReport`.
Ante diferencias, `rebuild_document()` lanza `DocumentIntegrityError` y expone
el reporte en `error.report`. Los tokens conservan acentos, mayúsculas y orden;
la comparación incluye las celdas y evita duplicar el contenido de celdas fusionadas.

Esta comprobación verifica la reconstrucción contra la propuesta recibida.
La validación de cambios de contenido entre el original y una propuesta de IA,
incluidas las reglas de puntuación, corresponde al validador de estructuración.

`rebuild_from_structure()` sigue disponible para los consumidores del formato
v1. El flujo v2 no utiliza sus rutas temporales de imágenes.

## Pruebas

Desde `backend/`:

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_rebuilder_v2.py tests/test_docx_engine.py tests/test_extractor_v2.py tests/test_document_schema.py tests/test_templates_engine.py tests/test_template_formatting.py tests/test_templates_engine_v2.py -q
```

Se retiraron los dos `xfail` de secciones y se migraron esas comprobaciones
al flujo v2. `06_secciones` debe conservar sus tres secciones y la orientación
horizontal de la segunda. También se verifican relaciones de imágenes, estilos,
encabezados y pies, numeración nativa y reinicios, tablas, subrayado, referencias
`keep` inválidas y rechazo de corrupción de texto.
