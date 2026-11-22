"""
Divisor de documentos (Chunker) para el Documento Intermedio (S3T17 / S3T9).

Divide un Documento Intermedio (DI) en fragmentos (AIChunkInput) de máximo
AI_MAX_CHUNK_CHARS (8000 caracteres) sin partir bloques a la mitad, cortando
preferentemente antes de un posible título y adjuntando el heading_path
acumulado a cada fragmento.

Regla de dependencias: ai_engine no importa python-docx ni docx_engine;
únicamente trabaja con common.document_schema.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from common.document_schema import (
    AIChunkInput,
    DocumentIntermediate,
    Hints,
    SCHEMA_VERSION,
    SourceBlock,
)
from .providers.base import ProviderError

AI_MAX_CHUNK_CHARS: int = 8000
AI_MAX_DOC_CHARS: int = 60000

_HEADING_NUMBER_PREFIX_RE = re.compile(r"^\s*(\d+(?:\.\d+)*)(?:[.)]|\s)\s*\S+")


class DocumentTooLargeForAI(ProviderError):
    """
    Excepción lanzada cuando el documento supera el límite máximo permitido
    para procesamiento con IA (AI_MAX_DOC_CHARS = 60,000 caracteres).
    """

    error_code: str = "DOCUMENT_TOO_LARGE_FOR_AI"
    http_status: int = 400

    def __init__(
        self,
        message: Optional[str] = None,
        *,
        total_chars: int = 0,
        max_chars: int = AI_MAX_DOC_CHARS,
    ) -> None:
        self.total_chars = int(total_chars)
        self.max_chars = int(max_chars)
        default_msg = (
            f"El documento excede el límite máximo para estructuración con IA "
            f"({self.total_chars} caracteres > máximo permitido de {self.max_chars})."
        )
        super().__init__(message or default_msg, error_code=self.error_code)


def _extract_blocks(
    doc_or_blocks: Union[DocumentIntermediate, AIChunkInput, Sequence[Union[SourceBlock, Dict[str, Any]]]]
) -> List[SourceBlock]:
    """Normaliza la entrada a una lista de objetos SourceBlock."""
    if isinstance(doc_or_blocks, DocumentIntermediate):
        return list(doc_or_blocks.blocks)
    if isinstance(doc_or_blocks, AIChunkInput):
        return list(doc_or_blocks.blocks)
    result: List[SourceBlock] = []
    for item in doc_or_blocks:
        if isinstance(item, SourceBlock):
            result.append(item)
        else:
            result.append(SourceBlock.model_validate(item))
    return result


def get_block_text(block: SourceBlock) -> str:
    """Obtiene el texto plano efectivo de un SourceBlock."""
    if block.text is not None and block.text != "":
        return block.text
    if block.runs:
        return "".join(r.text for r in block.runs)
    if block.rows:
        cell_texts: List[str] = []
        for row in block.rows:
            for cell in row:
                if cell.text:
                    cell_texts.append(cell.text)
                elif cell.runs:
                    cell_texts.append("".join(r.text for r in cell.runs))
        return " ".join(cell_texts)
    return ""


def get_block_char_count(block: SourceBlock) -> int:
    """Devuelve la cantidad de caracteres de contenido textual de un bloque."""
    return len(get_block_text(block))


def get_document_char_count(
    doc_or_blocks: Union[DocumentIntermediate, AIChunkInput, Sequence[Union[SourceBlock, Dict[str, Any]]]]
) -> int:
    """Calcula el total de caracteres de texto en el documento o secuencia de bloques."""
    blocks = _extract_blocks(doc_or_blocks)
    return sum(get_block_char_count(b) for b in blocks)


def ensure_within_limit(
    doc_or_blocks: Union[DocumentIntermediate, AIChunkInput, Sequence[Union[SourceBlock, Dict[str, Any]]]],
    *,
    max_chars: Optional[int] = None,
) -> int:
    """
    Verifica que el documento no exceda AI_MAX_DOC_CHARS (60,000 caracteres).
    Si lo excede, lanza DocumentTooLargeForAI. Devuelve el total de caracteres.
    """
    limit = int(max_chars if max_chars is not None else AI_MAX_DOC_CHARS)
    total_chars = get_document_char_count(doc_or_blocks)
    if total_chars > limit:
        raise DocumentTooLargeForAI(total_chars=total_chars, max_chars=limit)
    return total_chars


def is_potential_heading(block: SourceBlock) -> bool:
    """
    Determina si un bloque es un título explícito o un posible título falso
    para preferir cortar los fragmentos justo antes de él.
    """
    if block.type == "keep":
        return False
    if block.type == "heading":
        return True

    style_name = (block.style_name or (block.hints.style_name if block.hints else "") or "").strip()
    if style_name and any(
        style_name.lower().startswith(prefix)
        for prefix in ("heading", "title", "título", "titulo", "encabezado")
    ):
        return True

    hints: Hints = block.hints or Hints()
    if hints.suggested_type == "heading":
        return True

    text = get_block_text(block).strip()
    if not text:
        return False

    words = hints.words if hints.words > 0 else len(text.split())
    ends_with_period = hints.ends_with_period if block.hints is not None else text.endswith(".")

    if hints.size_ratio >= 1.2 and words <= 20:
        return True
    if hints.all_bold and 0 < words <= 15 and not ends_with_period:
        return True
    if hints.is_all_caps and 0 < words <= 15 and not ends_with_period and not hints.starts_with_glyph:
        return True

    return False


def estimate_heading_level(block: SourceBlock) -> int:
    """
    Estima el nivel jerárquico (1..6) de un bloque que es título o posible título,
    para mantener actualizado el heading_path acumulado entre fragmentos.
    """
    if block.level is not None and block.level >= 1:
        return min(6, int(block.level))

    hints: Hints = block.hints or Hints()
    if hints.suggested_level is not None and hints.suggested_level >= 1:
        return min(6, int(hints.suggested_level))

    style_name = (block.style_name or hints.style_name or "").strip()
    for lvl in range(1, 7):
        if f"heading {lvl}" in style_name.lower() or f"título {lvl}" in style_name.lower():
            return lvl

    text = get_block_text(block).strip()
    num_match = _HEADING_NUMBER_PREFIX_RE.match(text)
    if num_match:
        depth = num_match.group(1).count(".") + 1
        return min(6, max(1, depth))

    if hints.size_ratio >= 1.5:
        return 1
    if hints.size_ratio >= 1.3:
        return 2
    if hints.size_ratio >= 1.2:
        return 3

    return 1


def update_heading_path(current_path: List[str], block: SourceBlock) -> List[str]:
    """
    Actualiza la ruta de títulos activa si el bloque es un título o posible título.
    """
    if not is_potential_heading(block):
        return list(current_path)

    heading_text = get_block_text(block).strip()
    if not heading_text:
        return list(current_path)

    level = estimate_heading_level(block)
    # Truncar la ruta al nivel padre (level - 1) y colocar el título actual
    parent_depth = max(0, level - 1)
    updated = list(current_path[:parent_depth])
    updated.append(heading_text)
    return updated


def _split_blocks_into_groups(
    blocks: Sequence[SourceBlock],
    max_chunk_chars: int,
) -> List[List[SourceBlock]]:
    """
    Agrupa los bloques en listas de máximo `max_chunk_chars` caracteres sin
    partir bloques a la mitad, cortando preferentemente antes de un posible título.
    """
    if not blocks:
        return []

    groups: List[List[SourceBlock]] = []
    n = len(blocks)
    idx = 0

    while idx < n:
        current_group: List[SourceBlock] = []
        current_chars = 0
        # Índice dentro de current_group donde apareció el último posible título (> 0)
        last_heading_cut_idx: Optional[int] = None

        while idx < n:
            block = blocks[idx]
            b_chars = get_block_char_count(block)

            # Si el grupo está vacío, siempre debemos incluir al menos un bloque
            # (incluso si él solo supera max_chunk_chars, nunca se parte a la mitad).
            if not current_group:
                current_group.append(block)
                current_chars += b_chars
                idx += 1
                continue

            # Si agregar este bloque excede el límite máximo del fragmento:
            if current_chars + b_chars > max_chunk_chars:
                # Si el bloque actual NO es un título pero dentro de current_group hubo
                # un posible título reciente, cortamos justo antes de ese título para que
                # el título no quede separado de sus párrafos siguientes.
                if not is_potential_heading(block) and last_heading_cut_idx is not None:
                    rewind_count = len(current_group) - last_heading_cut_idx
                    current_group = current_group[:last_heading_cut_idx]
                    idx -= rewind_count
                break

            # Si este bloque es un posible título, registramos su posición como punto
            # de corte preferente (o cortamos de inmediato si ya estamos cerca del límite
            # y el título + el siguiente bloque desbordarían el fragmento).
            if is_potential_heading(block):
                next_chars = get_block_char_count(blocks[idx + 1]) if (idx + 1) < n else 0
                if current_chars + b_chars + next_chars > max_chunk_chars:
                    # Cortar antes de este título para no dejarlo huérfano al final del chunk
                    break
                last_heading_cut_idx = len(current_group)

            current_group.append(block)
            current_chars += b_chars
            idx += 1

        groups.append(current_group)

    return groups


def chunk_document(
    doc_or_blocks: Union[DocumentIntermediate, AIChunkInput, Sequence[Union[SourceBlock, Dict[str, Any]]]],
    *,
    max_chunk_chars: Optional[int] = None,
    max_doc_chars: Optional[int] = None,
    document_id: Optional[Union[int, str]] = None,
    doc_context: Optional[Dict[str, Any]] = None,
) -> List[AIChunkInput]:
    """
    Divide un Documento Intermedio (DI) o lista de SourceBlock en fragmentos
    AIChunkInput de máximo `AI_MAX_CHUNK_CHARS` (8000 caracteres).

    Garantías:
    1. Lanza `DocumentTooLargeForAI` si el total del documento supera `AI_MAX_DOC_CHARS` (60000).
    2. Nunca parte un bloque a la mitad.
    3. Corta preferentemente antes de un posible título.
    4. Adjunta `heading_path` acumulado al inicio de cada fragmento.
    5. Conserva el 100% de los bloques en su orden exacto sin pérdidas ni duplicados.
    """
    ensure_within_limit(doc_or_blocks, max_chars=max_doc_chars)
    blocks = _extract_blocks(doc_or_blocks)

    chunk_limit = int(max_chunk_chars if max_chunk_chars is not None else AI_MAX_CHUNK_CHARS)
    if chunk_limit <= 0:
        raise ValueError(f"max_chunk_chars debe ser > 0, recibido: {chunk_limit}")

    if not blocks:
        return []

    block_groups = _split_blocks_into_groups(blocks, max_chunk_chars=chunk_limit)

    chunks: List[AIChunkInput] = []
    active_heading_path: List[str] = []
    total_chunks = len(block_groups)

    for chunk_idx, group in enumerate(block_groups, start=1):
        chunk_heading_path = list(active_heading_path)
        chunk_chars = sum(get_block_char_count(b) for b in group)

        metadata: Dict[str, Any] = {
            "chunk_index": chunk_idx,
            "total_chunks": total_chunks,
            "char_count": chunk_chars,
            "heading_path": chunk_heading_path,
        }
        if doc_context:
            metadata["doc_context"] = dict(doc_context)

        chunk_input = AIChunkInput(
            schema_version=SCHEMA_VERSION,
            chunk_id=f"chunk-{chunk_idx:03d}",
            document_id=document_id,
            heading_path=chunk_heading_path,
            blocks=list(group),
            metadata=metadata,
        )
        chunks.append(chunk_input)

        # Actualizar la ruta de títulos acumulada con los bloques de este fragmento
        for block in group:
            active_heading_path = update_heading_path(active_heading_path, block)

    return chunks
