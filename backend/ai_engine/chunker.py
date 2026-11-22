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
from typing import Any, Dict, List, Optional, Sequence, Union

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
    para procesamiento con IA (AI_MAX_DOC_CHARS = 60,000 caracteres) o cuando
    un bloque individual excede AI_MAX_CHUNK_CHARS (8,000 caracteres) y no
    puede dividirse sin partir el bloque.
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


class BlockTooLargeForAI(DocumentTooLargeForAI):
    """
    Excepción lanzada cuando un único bloque individual supera AI_MAX_CHUNK_CHARS
    (8,000 caracteres). Como no se permite partir bloques a la mitad ni exceder
    el máximo por fragmento, se rechaza explícitamente.
    """

    def __init__(
        self,
        *,
        block_id: Optional[str],
        block_chars: int,
        max_chunk_chars: int = AI_MAX_CHUNK_CHARS,
    ) -> None:
        self.block_id = block_id
        self.block_chars = int(block_chars)
        self.max_chunk_chars = int(max_chunk_chars)
        msg = (
            f"El bloque '{block_id}' tiene {self.block_chars} caracteres y excede el "
            f"tamaño máximo por fragmento ({self.max_chunk_chars} caracteres). "
            "No se permite partir bloques a la mitad."
        )
        super().__init__(msg, total_chars=self.block_chars, max_chars=self.max_chunk_chars)


class _TrackedHeadingPath(list):
    """
    Subclase de `list` que almacena internamente el nivel jerárquico (0..6) de cada
    título en la ruta, comportándose como una `list[str]` estándar en comparaciones
    y serialización JSON.
    """

    def __init__(
        self,
        items: Sequence[str] = (),
        levels: Optional[Sequence[int]] = None,
    ) -> None:
        super().__init__(items)
        if levels is not None and len(levels) == len(self):
            self._levels: List[int] = [int(lvl) for lvl in levels]
        else:
            self._levels = _infer_path_levels(self)


def _infer_path_levels(path: Sequence[str]) -> List[int]:
    """
    Infiere los niveles jerárquicos (0..6) de una ruta de títulos cuando proviene
    de una lista plana de strings (p. ej. `AIChunkInput.heading_path`).
    """
    if not path:
        return []

    levels: List[int] = []
    for idx, text in enumerate(path):
        stripped = (text or "").strip()
        num_match = _HEADING_NUMBER_PREFIX_RE.match(stripped)
        if num_match:
            lvl = min(6, max(1, num_match.group(1).count(".") + 1))
        elif idx == 0:
            # Si el primer elemento no está numerado y hay un siguiente elemento de nivel 1
            # o es un título raíz sin numeración, se trata como nivel 0 (Title) si le sigue
            # un H1, o nivel 0 por defecto para no perderse ante un H1 numerado.
            lvl = 0
        else:
            prev_lvl = levels[-1]
            lvl = min(6, max(1, prev_lvl + 1))
        levels.append(lvl)
    return levels


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
    Estima el nivel jerárquico (0..6, donde 0 = Title y 1..6 = Heading 1..6)
    de un bloque que es título o posible título, para mantener actualizado
    el heading_path acumulado entre fragmentos.
    """
    if block.level is not None and 0 <= block.level <= 6:
        return int(block.level)

    hints: Hints = block.hints or Hints()
    if hints.suggested_level is not None and 0 <= hints.suggested_level <= 6:
        return int(hints.suggested_level)

    style_name = (block.style_name or hints.style_name or "").strip().lower()
    if style_name in ("title", "título", "titulo") or style_name.startswith("title"):
        return 0
    for lvl in range(1, 7):
        if (
            f"heading {lvl}" in style_name
            or f"título {lvl}" in style_name
            or f"titulo {lvl}" in style_name
            or f"encabezado {lvl}" in style_name
        ):
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


def update_heading_path(current_path: Sequence[str], block: SourceBlock) -> List[str]:
    """
    Actualiza la ruta de títulos activa si el bloque es un título o posible título.
    Conserva todos los títulos ancestros con nivel estrictamente menor al nivel del
    nuevo título (por ejemplo, un título principal de nivel 0 se conserva cuando
    aparece un H1 de nivel 1).
    """
    if isinstance(current_path, _TrackedHeadingPath):
        existing_levels = list(current_path._levels)
    else:
        existing_levels = _infer_path_levels(current_path)

    if not is_potential_heading(block):
        return _TrackedHeadingPath(current_path, levels=existing_levels)

    heading_text = get_block_text(block).strip()
    if not heading_text:
        return _TrackedHeadingPath(current_path, levels=existing_levels)

    level = estimate_heading_level(block)

    kept_texts: List[str] = []
    kept_levels: List[int] = []
    for txt, lvl in zip(current_path, existing_levels):
        if lvl < level:
            kept_texts.append(txt)
            kept_levels.append(lvl)
        else:
            break

    kept_texts.append(heading_text)
    kept_levels.append(level)
    return _TrackedHeadingPath(kept_texts, levels=kept_levels)


def _split_blocks_into_groups(
    blocks: Sequence[SourceBlock],
    max_chunk_chars: int,
) -> List[List[SourceBlock]]:
    """
    Agrupa los bloques en listas de máximo `max_chunk_chars` caracteres sin
    partir bloques a la mitad, cortando preferentemente antes de un posible título.
    Si un único bloque supera `max_chunk_chars`, lanza `BlockTooLargeForAI`.
    """
    if not blocks:
        return []

    for block in blocks:
        b_chars = get_block_char_count(block)
        if b_chars > max_chunk_chars:
            raise BlockTooLargeForAI(
                block_id=block.id,
                block_chars=b_chars,
                max_chunk_chars=max_chunk_chars,
            )

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


def _extract_initial_heading_path(
    doc_or_blocks: Union[DocumentIntermediate, AIChunkInput, Sequence[Union[SourceBlock, Dict[str, Any]]]],
    explicit_heading_path: Optional[Sequence[str]] = None,
) -> _TrackedHeadingPath:
    """
    Extrae la ruta de títulos inicial si se provee explícitamente o si la entrada
    es un AIChunkInput que ya trae `heading_path`.
    """
    if explicit_heading_path is not None:
        if isinstance(explicit_heading_path, _TrackedHeadingPath):
            return _TrackedHeadingPath(explicit_heading_path, levels=explicit_heading_path._levels)
        return _TrackedHeadingPath(explicit_heading_path)

    if isinstance(doc_or_blocks, AIChunkInput):
        raw_path = doc_or_blocks.heading_path
        if not raw_path and doc_or_blocks.metadata:
            raw_path = doc_or_blocks.metadata.get("heading_path") or []
        raw_levels = (doc_or_blocks.metadata or {}).get("heading_levels") if doc_or_blocks.metadata else None
        if isinstance(raw_path, _TrackedHeadingPath):
            return _TrackedHeadingPath(raw_path, levels=raw_path._levels)
        return _TrackedHeadingPath(raw_path or (), levels=raw_levels)

    return _TrackedHeadingPath()


def chunk_document(
    doc_or_blocks: Union[DocumentIntermediate, AIChunkInput, Sequence[Union[SourceBlock, Dict[str, Any]]]],
    *,
    max_chunk_chars: Optional[int] = None,
    max_doc_chars: Optional[int] = None,
    document_id: Optional[Union[int, str]] = None,
    doc_context: Optional[Dict[str, Any]] = None,
    heading_path: Optional[Sequence[str]] = None,
) -> List[AIChunkInput]:
    """
    Divide un Documento Intermedio (DI), AIChunkInput o lista de SourceBlock en
    fragmentos AIChunkInput de máximo `AI_MAX_CHUNK_CHARS` (8000 caracteres).

    Garantías:
    1. Lanza `DocumentTooLargeForAI` si el total del documento supera `AI_MAX_DOC_CHARS` (60000).
    2. Lanza `BlockTooLargeForAI` (subclase de `DocumentTooLargeForAI`) si un bloque individual
       supera `max_chunk_chars` (8000), garantizando que ningún fragmento exceda el máximo y
       que ningún bloque se parta a la mitad.
    3. Corta preferentemente antes de un posible título.
    4. Conserva la ruta inicial `heading_path` (incluyendo cuando se recibe un `AIChunkInput`
       y preservando títulos de nivel 0 cuando aparecen títulos H1..H6) y la adjunta a cada fragmento.
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

    effective_doc_id = (
        document_id
        if document_id is not None
        else (doc_or_blocks.document_id if isinstance(doc_or_blocks, AIChunkInput) else None)
    )
    active_heading_path: List[str] = _extract_initial_heading_path(doc_or_blocks, explicit_heading_path=heading_path)

    chunks: List[AIChunkInput] = []
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
            document_id=effective_doc_id,
            heading_path=chunk_heading_path,
            blocks=list(group),
            metadata=metadata,
        )
        chunks.append(chunk_input)

        # Actualizar la ruta de títulos acumulada con los bloques de este fragmento
        for block in group:
            active_heading_path = update_heading_path(active_heading_path, block)

    return chunks
