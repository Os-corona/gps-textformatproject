import json
import os
from pydantic import BaseModel, Field, field_validator

PRESETS_DIR = os.path.join(os.path.dirname(__file__), 'presets')
ALLOWED_FONTS = ["Times New Roman", "Calibri", "Arial"]

class TemplateConfig(BaseModel):
    margin_top: float = Field(..., gt=0, description="Margen superior en cm")
    margin_bottom: float = Field(..., gt=0, description="Margen inferior en cm")
    margin_left: float = Field(..., gt=0, description="Margen izquierdo en cm")
    margin_right: float = Field(..., gt=0, description="Margen derecho en cm")
    font_name: str
    font_size: int = Field(..., gt=0, description="Tamaño de la fuente")
    line_spacing: float = Field(..., gt=0, description="Interlineado")

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