import json
import os
from typing import Optional, Dict, Any, Union, List
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PRESETS_DIR = os.path.join(os.path.dirname(__file__), 'presets')
ALLOWED_FONTS = ["Times New Roman", "Arial", "Calibri", "Cambria", "Georgia", "Verdana"]
PRESET_ORDER = ["apa7", "reporte", "personalizado"]


# ---------------------------------------------------------------------------
# Submodelos para Templates Engine v2 (S3T12)
# ---------------------------------------------------------------------------
class ParagraphConfig(BaseModel):
    """Configuración de formato para párrafos de cuerpo."""
    model_config = ConfigDict(extra="allow")

    alignment: Optional[str] = Field(default=None, description="left | justify | center | right")
    first_line_indent_cm: Optional[float] = Field(default=None, description="Sangría de primera línea en cm (ej. 1.27 para APA 7)")
    space_after_pt: Optional[float] = Field(default=None, description="Espacio posterior al párrafo en puntos")
    space_before_pt: Optional[float] = Field(default=None, description="Espacio anterior al párrafo en puntos")
    line_spacing: Optional[float] = Field(default=None, description="Interlineado específico del párrafo")


class HeadingItemConfig(BaseModel):
    """Configuración tipográfica y espacial de un nivel específico de título."""
    model_config = ConfigDict(extra="allow")

    size_pt: Optional[float] = Field(default=None, description="Tamaño de fuente en puntos")
    bold: Optional[bool] = Field(default=None, description="Si el título va en negrita")
    italic: Optional[bool] = Field(default=None, description="Si el título va en cursiva")
    align: Optional[str] = Field(default=None, description="Alineación (left | center | right | justify)")
    space_before_pt: Optional[float] = Field(default=None, description="Espacio anterior en puntos")
    space_after_pt: Optional[float] = Field(default=None, description="Espacio posterior en puntos")
    color: Optional[str] = Field(default=None, description="Color en hexadecimal o nombre")


class HeadingsConfig(BaseModel):
    """Configuración de títulos para h1, h2, h3 y title."""
    model_config = ConfigDict(extra="allow")

    h1: Optional[HeadingItemConfig] = None
    h2: Optional[HeadingItemConfig] = None
    h3: Optional[HeadingItemConfig] = None
    title: Optional[HeadingItemConfig] = None


class ListsConfig(BaseModel):
    """Configuración de listas con viñetas y numeradas."""
    model_config = ConfigDict(extra="allow")

    indent_cm_per_level: Optional[float] = Field(default=None, description="Sangría por nivel en cm")


class TablesConfig(BaseModel):
    """Configuración de tablas."""
    model_config = ConfigDict(extra="allow")

    style: Optional[str] = Field(default=None, description="Nombre de estilo de tabla")
    header_bold: Optional[bool] = Field(default=None, description="Negrita en primera fila (encabezado)")
    header_fill: Optional[str] = Field(default=None, description="Color de fondo en encabezado (hex, ej. 'F2F2F2')")
    cell_line_spacing: Optional[float] = Field(default=1.0, description="Interlineado en celdas (1.0 por defecto)")


class CalloutConfig(BaseModel):
    """Configuración de bloques destacados o citas."""
    model_config = ConfigDict(extra="allow")

    italic: Optional[bool] = Field(default=None, description="Texto en cursiva")
    left_indent_cm: Optional[float] = Field(default=None, description="Sangría izquierda en cm")
    fill: Optional[str] = Field(default=None, description="Color de fondo (hex)")


class AIConfig(BaseModel):
    """Configuración para el procesamiento con Inteligencia Artificial (Sprint 3)."""
    model_config = ConfigDict(extra="allow")

    enabled: bool = Field(default=True, description="Habilitar estructuración con IA")
    document_type: Optional[str] = Field(default="general", description="Tipo de documento (general, academico, reporte)")
    detect_titles: bool = Field(default=True, description="Detectar y jerarquizar títulos")
    detect_lists: bool = Field(default=True, description="Detectar listas")
    detect_tables: bool = Field(default=True, description="Detectar tablas")
    emphasis: Optional[str] = Field(default="ligero", description="Énfasis de IA: ninguno, ligero, medio")
    accepted_disclaimer: Optional[bool] = Field(default=True, description="Aceptación de aviso de IA")


class TemplateConfig(BaseModel):
    margin_top: float = Field(..., ge=0.5, le=5.0, description="Margen superior en cm")
    margin_bottom: float = Field(..., ge=0.5, le=5.0, description="Margen inferior en cm")
    margin_left: float = Field(..., ge=0.5, le=5.0, description="Margen izquierdo en cm")
    margin_right: float = Field(..., ge=0.5, le=5.0, description="Margen derecho en cm")
    font_name: str
    font_size: Union[int, float] = Field(..., ge=8, le=24, description="Tamaño de la fuente")
    line_spacing: float = Field(..., ge=1.0, le=3.0, description="Interlineado")
    heading_sizes: Optional[Dict[str, Union[int, float]]] = None
    use_ai: bool = False

    # Campos extendidos v2 (S3T12)
    paragraph: Optional[ParagraphConfig] = None
    headings: Optional[HeadingsConfig] = None
    lists: Optional[ListsConfig] = None
    tables: Optional[TablesConfig] = None
    callout: Optional[CalloutConfig] = None
    page_numbers: Optional[bool] = False
    ai: Optional[AIConfig] = None

    @model_validator(mode='before')
    @classmethod
    def normalize_fields(cls, data: Any):
        if not isinstance(data, dict):
            return data
        data = data.copy()

        # Requisito 5: Dejar de rechazar use_ai=True y validar submodelo ai
        use_ai_val = data.get("use_ai", False)
        if use_ai_val is True or "ai" in data or "ai_options" in data:
            ai_data = data.get("ai") or data.get("ai_options") or {}
            if isinstance(ai_data, dict):
                ai_dict = ai_data.copy()
                if "document_type" in data and "document_type" not in ai_dict:
                    ai_dict["document_type"] = data["document_type"]
                if "emphasis" in data and "emphasis" not in ai_dict:
                    ai_dict["emphasis"] = data["emphasis"]
                if "detect_titles" in data and "detect_titles" not in ai_dict:
                    ai_dict["detect_titles"] = data["detect_titles"]
                if "detect_lists" in data and "detect_lists" not in ai_dict:
                    ai_dict["detect_lists"] = data["detect_lists"]
                if "detect_tables" in data and "detect_tables" not in ai_dict:
                    ai_dict["detect_tables"] = data["detect_tables"]
                data["ai"] = AIConfig(**ai_dict)
            elif isinstance(ai_data, AIConfig):
                data["ai"] = ai_data
            else:
                data["ai"] = AIConfig(enabled=True)
            data["use_ai"] = True

        # Soportar config anidado si se recibe el objeto completo de un preset
        if "config" in data and isinstance(data["config"], dict):
            inner = data["config"].copy()
            for k, v in inner.items():
                if k not in data:
                    data[k] = v

        # Soportar margins_cm anidado
        if "margins_cm" in data and isinstance(data["margins_cm"], dict):
            margins = data["margins_cm"]
            for side in ["top", "bottom", "left", "right"]:
                key = f"margin_{side}"
                if side in margins:
                    data[key] = margins[side]

        # Soportar font_family (sobrescribe font_name si se especifica)
        if "font_family" in data:
            data["font_name"] = data["font_family"]

        # Soportar font_size_pt (sobrescribe font_size si se especifica)
        if "font_size_pt" in data:
            data["font_size"] = data["font_size_pt"]

        # Soportar heading_sizes_pt (sobrescribe heading_sizes si se especifica)
        if "heading_sizes_pt" in data:
            data["heading_sizes"] = data["heading_sizes_pt"]

        # Sincronizar heading_sizes con headings si se proporciona uno de ellos
        if "headings" in data and isinstance(data["headings"], dict):
            h_cfg = data["headings"]
            if "heading_sizes" not in data or not data["heading_sizes"]:
                hs = {}
                for k in ["h1", "h2", "h3"]:
                    if k in h_cfg and isinstance(h_cfg[k], dict) and "size_pt" in h_cfg[k]:
                        hs[k] = h_cfg[k]["size_pt"]
                if hs:
                    data["heading_sizes"] = hs
        elif "heading_sizes" in data and isinstance(data["heading_sizes"], dict) and "headings" not in data:
            h_dict = {}
            for k, v in data["heading_sizes"].items():
                if v is not None:
                    h_dict[k] = {"size_pt": float(v)}
            if h_dict:
                data["headings"] = h_dict

        return data

    @field_validator('font_name')
    @classmethod
    def validate_font(cls, value):
        if value not in ALLOWED_FONTS:
            raise ValueError(f"Fuente '{value}' no permitida. Opciones válidas: {ALLOWED_FONTS}")
        return value


def load_preset_raw(preset_id: str) -> Dict[str, Any]:
    file_path = os.path.join(PRESETS_DIR, f"{preset_id}.json")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"El preset '{preset_id}' no existe.")

    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_preset(preset_id: str) -> 'TemplateConfig':
    data = load_preset_raw(preset_id)
    config_data = data.get("config", data)
    return TemplateConfig(**config_data)


def list_presets(include_all: bool = False) -> List[Dict[str, Any]]:
    if not os.path.exists(PRESETS_DIR):
        return []

    if include_all:
        preset_files = [f.replace('.json', '') for f in os.listdir(PRESETS_DIR) if f.endswith('.json')]
        preset_files.sort(key=lambda pid: PRESET_ORDER.index(pid) if pid in PRESET_ORDER else 999)
    else:
        preset_files = [pid for pid in PRESET_ORDER if os.path.exists(os.path.join(PRESETS_DIR, f"{pid}.json"))]

    presets = []
    for pid in preset_files:
        try:
            data = load_preset_raw(pid)
            if "config" in data and "id" in data:
                presets.append(data)
            else:
                presets.append({
                    "id": pid,
                    "name": data.get("name", pid.capitalize()),
                    "description": data.get("description", ""),
                    "config": data.get("config", data)
                })
        except Exception:
            continue
    return presets


def list_preset_ids(include_all: bool = False) -> List[str]:
    if not os.path.exists(PRESETS_DIR):
        return []
    if include_all:
        preset_files = [f.replace('.json', '') for f in os.listdir(PRESETS_DIR) if f.endswith('.json')]
        preset_files.sort(key=lambda pid: PRESET_ORDER.index(pid) if pid in PRESET_ORDER else 999)
        return preset_files
    return [pid for pid in PRESET_ORDER if os.path.exists(os.path.join(PRESETS_DIR, f"{pid}.json"))]
