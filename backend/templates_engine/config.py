import json
import os
from typing import Optional, Dict, Any, Union, List
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PRESETS_DIR = os.path.join(os.path.dirname(__file__), 'presets')
ALLOWED_FONTS = ["Times New Roman", "Arial", "Calibri", "Cambria", "Georgia", "Verdana"]
PRESET_ORDER = ["apa7", "reporte", "personalizado"]

COLOR_THEMES: Dict[str, Dict[str, str]] = {
    "azul_ejecutivo": {
        "name": "Azul Ejecutivo",
        "primary": "1F497D",
        "secondary": "2F5496",
        "accent": "B4C6E7",
        "header_fill": "D9E1F2",
        "zebra_fill": "F7F9FC",
        "callout_fill": "F2F5F9",
        "border": "BFBFBF",
    },
    "esmeralda": {
        "name": "Esmeralda Corporativo",
        "primary": "0F5132",
        "secondary": "198754",
        "accent": "A3CFBB",
        "header_fill": "D1E7DD",
        "zebra_fill": "F4FAF7",
        "callout_fill": "EDF7F2",
        "border": "B8D4C5",
    },
    "borgona": {
        "name": "Borgoña Directivo",
        "primary": "6B1D2F",
        "secondary": "8C2D41",
        "accent": "DFB0BA",
        "header_fill": "F2D7DD",
        "zebra_fill": "FCF6F7",
        "callout_fill": "FAF0F2",
        "border": "D8B8C0",
    },
    "indigo": {
        "name": "Índigo Tecnológico",
        "primary": "312E81",
        "secondary": "4F46E5",
        "accent": "C7D2FE",
        "header_fill": "E0E7FF",
        "zebra_fill": "F6F7FF",
        "callout_fill": "EEF2FF",
        "border": "C4C9E8",
    },
    "grafito": {
        "name": "Grafito Minimalista",
        "primary": "1F2937",
        "secondary": "4B5563",
        "accent": "CBD5E1",
        "header_fill": "E5E7EB",
        "zebra_fill": "F9FAFB",
        "callout_fill": "F3F4F6",
        "border": "9CA3AF",
    },
}


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
    document_type: Optional[str] = Field(default="reporte", description="Tipo de documento (reporte, academico, acta, propuesta, otro)")
    detect_headings: bool = Field(default=True, description="Detectar y jerarquizar títulos")
    detect_titles: bool = Field(default=True, description="Alias retrocompatible de detect_headings")
    detect_lists: bool = Field(default=True, description="Detectar listas")
    detect_tables: bool = Field(default=True, description="Detectar tablas")
    emphasis: Optional[str] = Field(default="light", description="Énfasis de IA: none|light|medium (o ninguno|ligero|medio)")
    creative_structure: bool = Field(
        default=False,
        description="Habilita el enriquecimiento estructural proactivo (subtítulos sugeridos, listas, tablas y destacados donde no existían)",
    )
    accepted_disclaimer: Optional[bool] = Field(default=True, description="Aceptación de aviso de IA")

    @model_validator(mode="before")
    @classmethod
    def sync_heading_aliases(cls, data: Any):
        if not isinstance(data, dict):
            return data
        data = data.copy()
        if "detect_headings" in data and "detect_titles" not in data:
            data["detect_titles"] = data["detect_headings"]
        elif "detect_titles" in data and "detect_headings" not in data:
            data["detect_headings"] = data["detect_titles"]
        return data


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
    color_theme: Optional[str] = None
    show_dividers: Optional[bool] = None
    ai: Optional[AIConfig] = None

    @model_validator(mode='before')
    @classmethod
    def normalize_fields(cls, data: Any):
        if not isinstance(data, dict):
            return data
        data = data.copy()

        # Requisito 5: Dejar de rechazar use_ai=True y validar submodelo ai
        # Solo activar use_ai cuando se pide explícitamente o se envía un bloque ai no nulo sin use_ai=False
        use_ai_val = data.get("use_ai")
        raw_ai = data.get("ai")
        raw_ai_options = data.get("ai_options")
        has_non_null_ai = raw_ai is not None or raw_ai_options is not None

        if use_ai_val is False:
            data["use_ai"] = False
            data["ai"] = None
        elif use_ai_val is True or has_non_null_ai:
            ai_data = raw_ai if raw_ai is not None else (raw_ai_options if raw_ai_options is not None else {})
            if isinstance(ai_data, dict):
                ai_dict = ai_data.copy()
                if "document_type" in data and "document_type" not in ai_dict:
                    ai_dict["document_type"] = data["document_type"]
                if "emphasis" in data and "emphasis" not in ai_dict:
                    ai_dict["emphasis"] = data["emphasis"]
                if "detect_headings" in data and "detect_headings" not in ai_dict:
                    ai_dict["detect_headings"] = data["detect_headings"]
                if "detect_titles" in data and "detect_titles" not in ai_dict:
                    ai_dict["detect_titles"] = data["detect_titles"]
                if "detect_lists" in data and "detect_lists" not in ai_dict:
                    ai_dict["detect_lists"] = data["detect_lists"]
                if "detect_tables" in data and "detect_tables" not in ai_dict:
                    ai_dict["detect_tables"] = data["detect_tables"]
                if "creative_structure" in data and "creative_structure" not in ai_dict:
                    ai_dict["creative_structure"] = data["creative_structure"]
                data["ai"] = AIConfig(**ai_dict)
            elif isinstance(ai_data, AIConfig):
                data["ai"] = ai_data
            else:
                data["ai"] = AIConfig(enabled=True)
            data["use_ai"] = True
        else:
            data["use_ai"] = False

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

        # Aplicar paleta cromática ejecutiva al documento Word si se especificó color_theme
        theme_key = data.get("color_theme")
        show_dividers = data.get("show_dividers")
        if isinstance(theme_key, str) and theme_key.strip().lower() in COLOR_THEMES:
            theme_key = theme_key.strip().lower()
            data["color_theme"] = theme_key
            palette = COLOR_THEMES[theme_key]
            use_dividers = True if show_dividers is None else bool(show_dividers)
            base_size = float(data.get("font_size") or 11.0)

            def _as_dict(val):
                if val is None:
                    return {}
                return val.model_dump() if hasattr(val, "model_dump") else dict(val)

            headings_map = _as_dict(data.get("headings"))
            default_sizes = {
                "title": round(base_size * 1.8 * 2) / 2,
                "h1": round(base_size * 1.45 * 2) / 2,
                "h2": round(base_size * 1.2 * 2) / 2,
                "h3": round(base_size * 1.05 * 2) / 2,
            }
            for level_key, default_sz in default_sizes.items():
                item = _as_dict(headings_map.get(level_key))
                item.setdefault("size_pt", default_sz)
                item.setdefault("bold", True)
                item.setdefault("align", "left")
                if level_key == "title":
                    item["color"] = palette["primary"]
                    item.setdefault("space_before_pt", 0.0)
                    item.setdefault("space_after_pt", 12.0)
                    if use_dividers:
                        item["bottom_border"] = palette["primary"]
                    else:
                        item.pop("bottom_border", None)
                elif level_key == "h1":
                    item["color"] = palette["primary"]
                    item.setdefault("space_before_pt", 16.0)
                    item.setdefault("space_after_pt", 6.0)
                    if use_dividers:
                        item["bottom_border"] = palette["secondary"]
                    else:
                        item.pop("bottom_border", None)
                elif level_key == "h2":
                    item["color"] = palette["secondary"]
                    item.setdefault("space_before_pt", 12.0)
                    item.setdefault("space_after_pt", 4.0)
                    if use_dividers:
                        item["left_border"] = palette["secondary"]
                    else:
                        item.pop("left_border", None)
                else:
                    item["color"] = palette["primary"]
                    item.setdefault("space_before_pt", 8.0)
                    item.setdefault("space_after_pt", 2.0)
                headings_map[level_key] = item
            data["headings"] = headings_map

            tables_map = _as_dict(data.get("tables"))
            tables_map["header_bold"] = True
            tables_map["header_fill"] = palette["header_fill"]
            tables_map["header_text_color"] = palette["primary"]
            tables_map["zebra_fill"] = palette["zebra_fill"]
            tables_map.setdefault("border_style", "grid")
            tables_map["border_color"] = palette["border"]
            tables_map.setdefault("cell_line_spacing", 1.0)
            data["tables"] = tables_map

            callout_map = _as_dict(data.get("callout"))
            callout_map.setdefault("italic", True)
            callout_map.setdefault("left_indent_cm", 0.9)
            callout_map["fill"] = palette["callout_fill"]
            callout_map["border_color"] = palette["primary"]
            data["callout"] = callout_map

            paragraph_map = _as_dict(data.get("paragraph"))
            if use_dividers:
                paragraph_map["accent_border_color"] = palette["accent"]
            else:
                paragraph_map.pop("accent_border_color", None)
            data["paragraph"] = paragraph_map
        elif show_dividers is False:
            # Permitir desactivar barras divisorias incluso sin cambiar color_theme
            headings_map = data.get("headings")
            if isinstance(headings_map, dict):
                cleaned_h = {}
                for k, v in headings_map.items():
                    if isinstance(v, dict):
                        item = dict(v)
                        item.pop("bottom_border", None)
                        item.pop("left_border", None)
                        cleaned_h[k] = item
                    else:
                        cleaned_h[k] = v
                data["headings"] = cleaned_h
            paragraph_map = data.get("paragraph")
            if isinstance(paragraph_map, dict):
                p_copy = dict(paragraph_map)
                p_copy.pop("accent_border_color", None)
                data["paragraph"] = p_copy

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
