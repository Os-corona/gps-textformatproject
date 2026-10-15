import json
import os
from typing import Optional, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator, model_validator

PRESETS_DIR = os.path.join(os.path.dirname(__file__), 'presets')
ALLOWED_FONTS = ["Times New Roman", "Arial", "Calibri", "Cambria", "Georgia", "Verdana"]

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

    @model_validator(mode='before')
    @classmethod
    def normalize_fields(cls, data: Any):
        if not isinstance(data, dict):
            return data
        data = data.copy()
        if data.get("use_ai") is True:
            raise ValueError("La corrección con IA aún no está disponible.")

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

        return data

    @field_validator('font_name')
    @classmethod
    def validate_font(cls, value):
        if value not in ALLOWED_FONTS:
            raise ValueError(f"Fuente '{value}' no permitida. Opciones válidas: {ALLOWED_FONTS}")
        return value

def list_presets():
    if not os.path.exists(PRESETS_DIR):
        return []
    return [f.replace('.json', '') for f in os.listdir(PRESETS_DIR) if f.endswith('.json')]

def load_preset(preset_id: str) -> 'TemplateConfig':
    file_path = os.path.join(PRESETS_DIR, f"{preset_id}.json")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"El preset '{preset_id}' no existe.")

    with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

    return TemplateConfig(**data)