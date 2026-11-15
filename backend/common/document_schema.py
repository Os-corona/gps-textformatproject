"""
Documento Intermedio (DI) Schema - PrettyDocs
Especificación de modelos Pydantic v2 para el Documento Intermedio (Sprint 3).
Define el contrato canónico entre extracción (.docx), procesamiento por IA y reconstrucción.
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Annotated, Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# 1. Versión del Esquema
# ---------------------------------------------------------------------------
SCHEMA_VERSION: str = "di.v1"
schema_version: str = SCHEMA_VERSION


# ---------------------------------------------------------------------------
# 2. Funciones auxiliares de validación
# ---------------------------------------------------------------------------
def validate_runs_list(runs: List[Run]) -> List[Run]:
    """Valida que la lista de runs no sea vacía y que ningún run tenga texto vacío."""
    if not runs:
        raise ValueError("La lista de runs no puede estar vacía.")
    for idx, r in enumerate(runs):
        txt = r.text if hasattr(r, "text") else (r.get("text", "") if isinstance(r, dict) else "")
        if not txt:
            raise ValueError(f"El run en posición {idx} no puede tener texto vacío.")
    return runs


def validate_rectangular_table(rows: List[List[TableCell]]) -> List[List[TableCell]]:
    """
    Valida que todas las filas de la tabla tengan el mismo ancho total de columnas,
    tomando en cuenta la propiedad `h_span` (horizontal span / gridSpan) de cada celda.
    """
    if not rows:
        raise ValueError("La tabla debe contener al menos una fila.")

    row_widths: List[int] = []
    for r_idx, row in enumerate(rows):
        if not row:
            raise ValueError(f"La fila {r_idx} de la tabla está vacía y no contiene celdas.")

        current_width = 0
        for c_idx, cell in enumerate(row):
            h_span = cell.h_span if hasattr(cell, "h_span") else (cell.get("h_span", 1) if isinstance(cell, dict) else 1)
            if h_span < 1:
                raise ValueError(
                    f"El h_span de la celda {c_idx} en la fila {r_idx} debe ser >= 1, recibido: {h_span}"
                )
            current_width += h_span
        row_widths.append(current_width)

    first_width = row_widths[0]
    for r_idx, w in enumerate(row_widths):
        if w != first_width:
            raise ValueError(
                f"La tabla no es rectangular: la fila 0 tiene ancho {first_width} "
                f"(considerando h_span), pero la fila {r_idx} tiene ancho {w}."
            )

    return rows


# ---------------------------------------------------------------------------
# 3. Modelos Básicos: Run y Hints
# ---------------------------------------------------------------------------
class Run(BaseModel):
    """Segmento de texto continuo con un formato tipográfico consistente."""
    model_config = ConfigDict(extra="ignore")

    text: str = Field(..., min_length=1, description="Texto contenido en el run (no vacío)")
    bold: Optional[bool] = Field(default=None, description="Indica si el texto tiene formato negrita")
    italic: Optional[bool] = Field(default=None, description="Indica si el texto tiene formato cursiva")
    underline: Optional[bool] = Field(default=None, description="Indica si el texto tiene subrayado")
    font: Optional[str] = Field(default=None, description="Nombre de la fuente (e.g. 'Calibri')")
    size: Optional[float] = Field(default=None, ge=1.0, description="Tamaño de la fuente en puntos tipográficos (pt)")
    color: Optional[str] = Field(default=None, description="Color en hexadecimal o nombre")

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        if v == "":
            raise ValueError("El campo 'text' de Run no puede estar vacío.")
        return v


class Hints(BaseModel):
    """Pistas y sugerencias tipográficas o jerárquicas emitidas por el extractor o la IA."""
    model_config = ConfigDict(extra="allow")

    style_name: Optional[str] = Field(default=None, description="Nombre del estilo original en el documento de Word")
    suggested_type: Optional[str] = Field(default=None, description="Tipo sugerido por extractor o IA (e.g. 'heading')")
    suggested_level: Optional[int] = Field(default=None, ge=0, le=9, description="Nivel jerárquico sugerido (0 a 9)")
    is_list: Optional[bool] = Field(default=None, description="Indica si el bloque parece pertenecer a una lista")
    is_numbered: Optional[bool] = Field(default=None, description="Indica si la lista es numerada o viñeta")
    list_level: Optional[int] = Field(default=None, ge=0, le=8, description="Nivel de anidamiento de lista (0 a 8)")
    has_inline_image: Optional[bool] = Field(default=None, description="Indica si el bloque contiene imágenes embebidas")
    keep_with_next: Optional[bool] = Field(default=None, description="Regla de maquetación: mantener con el párrafo siguiente")
    grammar_checked: Optional[bool] = Field(default=None, description="Indica si el texto pasó por revisión gramatical")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Nivel de certeza de la sugerencia")
    notes: Optional[str] = Field(default=None, description="Notas explicativas adicionales")

    @field_validator("suggested_level")
    @classmethod
    def validate_suggested_level(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (0 <= v <= 9):
            raise ValueError(f"suggested_level debe estar entre 0 y 9, recibido: {v}")
        return v

    @field_validator("list_level")
    @classmethod
    def validate_list_level(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (0 <= v <= 8):
            raise ValueError(f"list_level debe estar entre 0 y 8, recibido: {v}")
        return v


class TableCell(BaseModel):
    """Celda individual dentro de una fila de tabla."""
    model_config = ConfigDict(extra="allow")

    text: str = Field(default="", description="Texto plano extraído de la celda")
    runs: Optional[List[Run]] = Field(default=None, description="Runs detallados con formato dentro de la celda")
    h_span: int = Field(default=1, ge=1, description="Extensión horizontal (column span / gridSpan)")
    v_merge: Optional[str] = Field(default=None, description="Fusión vertical ('restart', 'continue' o None)")
    hints: Optional[Hints] = Field(default=None, description="Pistas opcionales sobre la celda")


# ---------------------------------------------------------------------------
# 4. SourceBlock: Bloque de Origen (extraído del .docx)
# ---------------------------------------------------------------------------
class SourceBlock(BaseModel):
    """Bloque de contenido sin modificar tal como fue extraído del documento original."""
    model_config = ConfigDict(extra="allow")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Identificador único del bloque de origen")
    type: str = Field(..., description="Tipo de bloque: 'paragraph', 'heading', 'list_item', 'table', 'image'")
    text: Optional[str] = Field(default=None, description="Texto plano consolidado del bloque")
    runs: Optional[List[Run]] = Field(default=None, description="Runs de texto con formato")
    level: Optional[int] = Field(default=None, ge=0, le=9, description="Nivel jerárquico si aplica (0 a 9)")
    rows: Optional[List[List[TableCell]]] = Field(default=None, description="Filas de celdas para bloques tipo 'table'")
    hints: Optional[Hints] = Field(default=None, description="Pistas detectadas por el extractor")
    style_name: Optional[str] = Field(default=None, description="Estilo de párrafo original de Word")
    has_inline_image: Optional[Union[bool, List[str]]] = Field(default=None, description="Rutas o indicador de imágenes")
    list_info: Optional[Dict[str, Any]] = Field(default=None, description="Metadatos de numeración y viñetas")

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (0 <= v <= 9):
            raise ValueError(f"El campo 'level' debe estar entre 0 y 9, recibido: {v}")
        return v

    @field_validator("runs")
    @classmethod
    def validate_runs(cls, v: Optional[List[Run]]) -> Optional[List[Run]]:
        if v is not None:
            validate_runs_list(v)
        return v

    @field_validator("rows")
    @classmethod
    def validate_rows(cls, v: Optional[List[List[TableCell]]]) -> Optional[List[List[TableCell]]]:
        if v is not None:
            validate_rectangular_table(v)
        return v


# ---------------------------------------------------------------------------
# 5. OutBlock: Bloques de Salida (Unión discriminada por 'type')
# ---------------------------------------------------------------------------
class ParagraphOutBlock(BaseModel):
    """Párrafo normal de texto procesado."""
    model_config = ConfigDict(extra="ignore")

    type: Literal["paragraph"] = "paragraph"
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), description="ID único del bloque")
    runs: List[Run] = Field(..., min_length=1, description="Runs de texto que forman el párrafo")
    hints: Optional[Hints] = Field(default=None, description="Pistas opcionales de formato")

    @field_validator("runs")
    @classmethod
    def check_runs(cls, v: List[Run]) -> List[Run]:
        return validate_runs_list(v)


class HeadingOutBlock(BaseModel):
    """Título o encabezado jerárquico con nivel estricto entre 1 y 6."""
    model_config = ConfigDict(extra="ignore")

    type: Literal["heading"] = "heading"
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), description="ID único del bloque")
    level: int = Field(..., ge=1, le=6, description="Nivel del título (1 a 6: H1, H2, H3, H4, H5, H6)")
    runs: List[Run] = Field(..., min_length=1, description="Runs de texto que forman el título")
    hints: Optional[Hints] = Field(default=None, description="Pistas opcionales")

    @field_validator("level")
    @classmethod
    def check_level(cls, v: int) -> int:
        if not (1 <= v <= 6):
            raise ValueError(f"El nivel de título (level) debe estar entre 1 y 6, recibido: {v}")
        return v

    @field_validator("runs")
    @classmethod
    def check_runs(cls, v: List[Run]) -> List[Run]:
        return validate_runs_list(v)


class ListItemOutBlock(BaseModel):
    """Elemento de lista (viñeta o numerada) con nivel de anidamiento entre 0 y 8."""
    model_config = ConfigDict(extra="ignore")

    type: Literal["list_item"] = "list_item"
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), description="ID único del bloque")
    level: int = Field(default=0, ge=0, le=8, description="Nivel de anidamiento de la lista (0 a 8)")
    is_numbered: bool = Field(default=False, description="True si es lista numerada, False si es viñeta")
    runs: List[Run] = Field(..., min_length=1, description="Runs de texto del elemento de lista")
    hints: Optional[Hints] = Field(default=None, description="Pistas opcionales")

    @field_validator("level")
    @classmethod
    def check_level(cls, v: int) -> int:
        if not (0 <= v <= 8):
            raise ValueError(f"El nivel de lista (level) debe estar entre 0 y 8, recibido: {v}")
        return v

    @field_validator("runs")
    @classmethod
    def check_runs(cls, v: List[Run]) -> List[Run]:
        return validate_runs_list(v)


class TableOutBlock(BaseModel):
    """Tabla rectangular de celdas considerando la propiedad h_span."""
    model_config = ConfigDict(extra="ignore")

    type: Literal["table"] = "table"
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), description="ID único del bloque")
    rows: List[List[TableCell]] = Field(..., min_length=1, description="Filas de la tabla")
    hints: Optional[Hints] = Field(default=None, description="Pistas opcionales de formato de tabla")

    @field_validator("rows")
    @classmethod
    def check_rows_rectangular(cls, v: List[List[TableCell]]) -> List[List[TableCell]]:
        return validate_rectangular_table(v)


class ImageOutBlock(BaseModel):
    """Bloque de imagen preservada."""
    model_config = ConfigDict(extra="ignore")

    type: Literal["image"] = "image"
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), description="ID único del bloque")
    image_path: Optional[str] = Field(default=None, description="Ruta o URI de la imagen")
    caption: Optional[str] = Field(default=None, description="Pie de imagen opcional")
    hints: Optional[Hints] = Field(default=None, description="Pistas opcionales")


# Unión discriminada por 'type'
OutBlock = Annotated[
    Union[
        ParagraphOutBlock,
        HeadingOutBlock,
        ListItemOutBlock,
        TableOutBlock,
        ImageOutBlock,
    ],
    Field(discriminator="type", description="Bloque de salida discriminado por 'type'")
]


# ---------------------------------------------------------------------------
# 6. AIChunkInput y AIChunkOutput
# ---------------------------------------------------------------------------
class AIChunkInput(BaseModel):
    """Carga de entrada enviada al motor de IA para procesar un fragmento (chunk) del documento."""
    model_config = ConfigDict(extra="allow")

    schema_version: str = Field(default=SCHEMA_VERSION, description="Versión del esquema de documento intermedio")
    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Identificador único del chunk")
    document_id: Optional[Union[int, str]] = Field(default=None, description="ID del documento original")
    blocks: List[SourceBlock] = Field(default_factory=list, description="Bloques de origen contenidos en el chunk")
    hints: Optional[Hints] = Field(default=None, description="Pistas globales o contextuales para la IA")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Metadatos auxiliares de ejecución")

    @field_validator("schema_version")
    @classmethod
    def check_version(cls, v: str) -> str:
        if v != SCHEMA_VERSION:
            raise ValueError(f"schema_version no coincide: '{v}'. Se esperaba '{SCHEMA_VERSION}'.")
        return v


class AIChunkOutput(BaseModel):
    """Estructura de salida generada por la IA tras el análisis y reestructuración del chunk."""
    model_config = ConfigDict(extra="allow")

    schema_version: str = Field(default=SCHEMA_VERSION, description="Versión del esquema de documento intermedio")
    chunk_id: str = Field(..., description="Identificador del chunk al que corresponde esta salida")
    blocks: List[OutBlock] = Field(default_factory=list, description="Lista de bloques estructurados de salida")
    summary: Optional[str] = Field(default=None, description="Resumen breve de las correcciones o mejoras aplicadas")
    hints: Optional[Hints] = Field(default=None, description="Pistas generales generadas por el modelo")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Metadatos auxiliares del proveedor")

    @field_validator("schema_version")
    @classmethod
    def check_version(cls, v: str) -> str:
        if v != SCHEMA_VERSION:
            raise ValueError(f"schema_version no coincide: '{v}'. Se esperaba '{SCHEMA_VERSION}'.")
        return v


# ---------------------------------------------------------------------------
# 7. IntegrityReport
# ---------------------------------------------------------------------------
class IntegrityReport(BaseModel):
    """Reporte de integridad para verificar que la IA no alteró ni destruyó contenido crítico."""
    model_config = ConfigDict(extra="allow")

    schema_version: str = Field(default=SCHEMA_VERSION, description="Versión del esquema")
    is_valid: bool = Field(..., description="True si el documento supera todas las reglas de integridad")
    total_source_blocks: int = Field(default=0, ge=0, description="Total de bloques de origen analizados")
    total_out_blocks: int = Field(default=0, ge=0, description="Total de bloques de salida generados")
    source_characters: int = Field(default=0, ge=0, description="Total de caracteres en los bloques de origen")
    out_characters: int = Field(default=0, ge=0, description="Total de caracteres en los bloques de salida")
    warnings: List[str] = Field(default_factory=list, description="Lista de advertencias no bloqueantes")
    errors: List[str] = Field(default_factory=list, description="Lista de violaciones de integridad")
    preserved_elements: Dict[str, bool] = Field(
        default_factory=dict,
        description="Preservación de elementos críticos ('tables', 'images', 'lists')"
    )
    similarity_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Puntaje de similitud textual/semántica (0.0 a 1.0)"
    )
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Información adicional del reporte")

    @field_validator("schema_version")
    @classmethod
    def check_version(cls, v: str) -> str:
        if v != SCHEMA_VERSION:
            raise ValueError(f"schema_version no coincide: '{v}'. Se esperaba '{SCHEMA_VERSION}'.")
        return v


# ---------------------------------------------------------------------------
# 8. Exportador de JSON Schemas a docs/schemas/
# ---------------------------------------------------------------------------
def export_json_schemas(output_dir: Union[str, Path] = "docs/schemas") -> Dict[str, str]:
    """
    Exporta los JSON Schemas de los modelos principales a la carpeta especificada.
    Estos esquemas son consumidos por el proveedor de IA (structured outputs) y el frontend.
    """
    # Si la ruta es relativa, resolverla respecto a la raíz del repositorio
    out_path = Path(output_dir)
    if not out_path.is_absolute():
        # Raíz del repo: dos niveles arriba de este archivo (backend/common/ -> repo root)
        repo_root = Path(__file__).resolve().parent.parent.parent
        out_path = repo_root / output_dir

    out_path.mkdir(parents=True, exist_ok=True)

    schemas_to_export = {
        "aichunk_output.schema.json": AIChunkOutput,
        "aichunk_input.schema.json": AIChunkInput,
        "integrity_report.schema.json": IntegrityReport,
        "source_block.schema.json": SourceBlock,
    }

    generated_files: Dict[str, str] = {}
    for filename, model in schemas_to_export.items():
        file_path = out_path / filename
        schema_dict = model.model_json_schema()
        # Añadir metadatos de Schema
        schema_dict["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        schema_dict["schema_version"] = SCHEMA_VERSION

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(schema_dict, f, indent=2, ensure_ascii=False)
            f.write("\n")

        generated_files[filename] = str(file_path)

    return generated_files


if __name__ == "__main__":
    exported = export_json_schemas()
    print(f"Esquemas JSON exportados exitosamente ({len(exported)} archivos):")
    for name, path in exported.items():
        print(f" - {name} -> {path}")

