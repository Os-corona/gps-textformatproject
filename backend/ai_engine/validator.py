"""Integrity checks over source references, critical data and content tokens."""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from unicodedata import category

from django.conf import settings
from pydantic import TypeAdapter, ValidationError

from common.document_schema import IntegrityReport, IntegrityViolation, OutBlock, SourceBlock
from .chunker import get_block_text

DEFAULTS = {
    "AI_MAX_BOLD_RATIO": 0.30,
    "AI_MAX_HEADING_WORDS": 20,
    "AI_MIN_TOKEN_RETENTION": 0.95,
    "AI_MAX_ADDED_TOKEN_RATIO": 0.05,
    "AI_MAX_GENERATED_HEADING_WORDS": 6,
}
_WORD = re.compile(r"\w+", re.UNICODE)
_TOKEN = re.compile(r"\w+|[^\w\s]", re.UNICODE)
_CRITICAL = re.compile(r"[+\-−]?\d+(?:[.,:/\-]\d+)*(?:\s?%)?|[^\w\s]")
_GLYPH = re.compile(r"^\s*(?:[•·◦▪*]\s*|[\-–]\s+)")
_NUMBER = re.compile(r"^\s*(?:\d+(?:\.\d+)+[.)]?|\d{1,3}[.)]|\(\d{1,3}\)|[a-zA-Z][.)]|[ivxlcdmIVXLCDM]+[.)])\s+")
_OUT = TypeAdapter(OutBlock)


def threshold(name):
    return getattr(settings, name, DEFAULTS[name]) if settings.configured else DEFAULTS[name]


def _critical(text):
    return [
        re.sub(r"\s+%", "%", m.group())
        for m in _CRITICAL.finditer(text)
        if any(c.isdecimal() or category(c) == "Sc" or c == "%" for c in m.group())
    ]


def _text(block):
    if block.get("runs") is not None:
        return "".join(run["text"] for run in block["runs"])
    return block.get("text") or ""


def _tokens(text, *, table=False, split_list=False):
    if split_list:
        return [
            token
            for clause in re.split(r"[,;]|\b(?:y|e|o)\b", text, flags=re.IGNORECASE)
            for token in _tokens(clause, table=table)
        ]
    tokens = _TOKEN.findall(text)
    if table:
        tokens = [t for t in tokens if t not in (":", "|")]
    for i, token in enumerate(tokens):
        if _WORD.fullmatch(token):
            tokens[i] = token.casefold()
            break
    return tokens


def _safe_refs(refs) -> list[str]:
    if isinstance(refs, (list, tuple)):
        return [str(r) for r in refs if r is not None]
    if isinstance(refs, str) and refs:
        return [refs]
    return []


def _source_bold_words(source: SourceBlock) -> int:
    if source.runs:
        return sum(len(_WORD.findall(r.text)) for r in source.runs if r.bold)
    if source.hints and source.hints.all_bold:
        return len(_WORD.findall(get_block_text(source)))
    return 0


def _table_text(block, *, include_generated=False):
    return " ".join(
        _text(cell) for row in block.get("rows", []) for cell in row
        if include_generated or not cell.get("generated")
    )


def _deduplicated_source(texts, table):
    """Recognize a pivot only when every source record has the exact header keys."""
    if not table.get("header_row") or not table.get("rows"):
        return None
    header = table["rows"][0]
    if any(cell.get("generated") for cell in header):
        return None
    keys = [_text(cell).strip() for cell in header]
    records = []
    for text in texts:
        parts = re.split(r"[;|\t\n]", text)
        pairs = [part.split(":", 1) for part in parts if part.strip()]
        if len(pairs) != len(keys) or any(len(pair) != 2 for pair in pairs):
            return None
        if [pair[0].strip() for pair in pairs] != keys:
            return None
        records.append([pair[1].strip() for pair in pairs])
    return [" ".join(keys)] + [" ".join(record) for record in records]


def validate_chunk(input_blocks, output_blocks) -> IntegrityReport:
    """Validate models or raw dictionaries; invalid output becomes a report, not an exception."""
    sources = [b if isinstance(b, SourceBlock) else SourceBlock.model_validate(b) for b in input_blocks]
    raw_outputs = list(output_blocks)
    violations, warnings, outputs = [], [], []

    def fail(kind, refs, message):
        violations.append(IntegrityViolation(type=kind, src=_safe_refs(refs), message=message))

    for block in raw_outputs:
        raw = block.model_dump(exclude_none=True) if hasattr(block, "model_dump") else block
        try:
            outputs.append(_OUT.validate_python(raw).model_dump(exclude_none=True))
        except (ValidationError, TypeError) as exc:
            refs = raw.get("src", []) if isinstance(raw, dict) else []
            fail("INVALID_SCHEMA", refs, str(exc))

    by_id = {b.id: b for b in sources}
    positions = {b.id: i for i, b in enumerate(sources)}
    if len(by_id) != len(sources):
        fail("DUPLICATE_SOURCE_ID", list(by_id), "Los IDs de origen deben ser únicos.")
    coverage = defaultdict(list)
    previous = -1
    parent = {b.id: b.id for b in sources}

    def root(ref):
        while parent[ref] != ref:
            parent[ref] = parent[parent[ref]]
            ref = parent[ref]
        return ref

    generated_headings = 0
    for index, block in enumerate(outputs):
        kind, refs = block["type"], block.get("src", [])
        if kind == "keep" and not refs and block.get("id"):
            refs = block["src"] = [block["id"]]
        generated = block.get("generated", False)
        if not refs and not (kind == "heading" and generated):
            fail("MISSING_SRC", [], "El bloque no tiene trazabilidad.")
        if len(set(refs)) != len(refs) or any(ref not in by_id for ref in refs):
            fail("INVALID_SRC", refs, "Referencias desconocidas o duplicadas.")
            continue
        if kind not in ("paragraph", "heading", "list_item", "table", "callout", "keep"):
            fail("UNSUPPORTED_BLOCK", refs, "Los elementos opacos deben conservarse como keep.")
        if generated:
            if kind != "heading" or not 1 <= block.get("level", 0) <= 3:
                fail("GENERATED_LOCATION", refs, "Solo se permiten subtítulos generados de nivel 1 a 3.")
            if len(_WORD.findall(_text(block))) > threshold("AI_MAX_GENERATED_HEADING_WORDS"):
                fail("GENERATED_LENGTH", refs, "El subtítulo generado supera el máximo de palabras.")
            generated_headings += 1
            warnings.append("GENERATED_HEADING: " + ", ".join(refs))
        else:
            indices = [positions[ref] for ref in refs]
            if indices != sorted(indices) or (indices and indices[0] < previous):
                fail("SOURCE_ORDER", refs, "Los bloques de origen cambiaron de orden.")
            if indices:
                previous = indices[-1]
            for ref in refs:
                coverage[ref].append(index)
                if refs:
                    parent[root(ref)] = root(refs[0])
            keep_refs = [ref for ref in refs if by_id[ref].type == "keep"]
            if (keep_refs and (kind != "keep" or len(refs) != 1)) or (kind == "keep" and not keep_refs):
                fail("KEEP_CHANGED", refs, "keep debe referenciar exactamente un bloque opaco original.")

        if kind == "heading":
            if not 0 <= block["level"] <= 3:
                fail("HEADING_LEVEL", refs, "Solo se permiten Title y niveles H1 a H3.")
            if len(_WORD.findall(_text(block))) > threshold("AI_MAX_HEADING_WORDS") or _text(block).rstrip().endswith("."):
                fail("HEADING_SHAPE", refs, "Título demasiado largo o con punto final.")
        if kind == "table":
            rows = block["rows"]
            widths = [sum(c.get("h_span", 1) for c in row) for row in rows]
            if len(rows) < 2 or min(widths, default=0) < 2 or len(set(widths)) != 1:
                fail("TABLE_SHAPE", refs, "La tabla debe ser rectangular y de al menos 2×2.")
            for row in rows:
                for cell in row:
                    if cell.get("generated"):
                        if len(_WORD.findall(_text(cell))) > threshold("AI_MAX_GENERATED_HEADING_WORDS"):
                            fail("GENERATED_LENGTH", refs, "La celda generada supera el máximo de palabras.")
                        warnings.append("GENERATED_HEADER: " + ", ".join(refs))
        # Check text blocks and individual table cells, never opaque XML.
        prose = [cell for row in block.get("rows", []) for cell in row] if kind == "table" else [block]
        orig_bold = 0 if generated else sum(_source_bold_words(by_id[ref]) for ref in refs)
        if kind != "keep":
            for item in prose:
                runs = item.get("runs", [])
                item_text = _text(item)
                total = len(_WORD.findall(item_text))
                bold = sum(len(_WORD.findall(r["text"])) for r in runs if r.get("bold"))
                added_bold = max(0, bold - orig_bold) if kind != "table" else bold
                # Permitir prefijo corto 'Etiqueta:' en negrita cuando le sigue texto sin negrita
                if added_bold and bold < total and ":" in item_text:
                    prefix_words = len(_WORD.findall(item_text.split(":", 1)[0]))
                    if 0 < prefix_words <= 6 and added_bold <= prefix_words:
                        added_bold = 0
                if total and added_bold / total > threshold("AI_MAX_BOLD_RATIO"):
                    fail("BOLD_RATIO", refs, "Se supera el porcentaje máximo de negritas.")

    text_sources = [s for s in sources if s.type != "keep"]
    if generated_headings and generated_headings > max(1, len(text_sources)):
        fail("GENERATED_EXCESS", [b.id for b in sources], "Demasiados subtítulos generados para el fragmento.")

    for source in sources:
        indices = coverage[source.id]
        if not indices:
            if source.type == "keep" and source.keep_kind == "empty":
                continue
            fail("SOURCE_OMITTED", [source.id], "El bloque original no aparece en la salida.")
        if source.type == "keep" and len(indices) != 1:
            if not (source.keep_kind == "empty" and len(indices) == 0):
                fail("KEEP_COUNT", [source.id], "keep debe aparecer exactamente una vez.")
        if len(indices) > 1 and not all(outputs[i]["type"] == "list_item" for i in indices):
            fail("SOURCE_DUPLICATED", [source.id], "Solo se admite dividir un origen en varios list_item.")

    groups = defaultdict(list)
    for source in sources:
        if source.type != "keep":
            groups[root(source.id)].append(source)
    retained, total_tokens, total_added = 0, 0, 0
    source_critical, output_critical = [], []
    for group in groups.values():
        refs = [b.id for b in group]
        indices = sorted({i for ref in refs for i in coverage[ref]})
        targets = [outputs[i] for i in indices if outputs[i]["type"] != "keep"]
        is_table = len(targets) == 1 and targets[0]["type"] == "table"
        split_list = len(targets) > 1 and all(b["type"] == "list_item" for b in targets)
        texts = []
        for source in group:
            text = get_block_text(source)
            own_targets = [outputs[i] for i in coverage[source.id]]
            if own_targets and all(b["type"] == "list_item" for b in own_targets):
                text = _GLYPH.sub("", text, count=1)
                if all(b.get("is_numbered") for b in own_targets):
                    text = _NUMBER.sub("", text, count=1)
            texts.append(text)
        if is_table and (deduplicated := _deduplicated_source(texts, targets[0])) is not None:
            source_critical.extend(_critical(" ".join(deduplicated)))
            expected_parts = [_tokens(text, table=True) for text in deduplicated]
            warnings.append("DEDUPLICATED_TABLE_KEYS: " + ", ".join(refs))
        else:
            source_critical.extend(_critical(" ".join(texts)))
            expected_parts = [_tokens(text, table=is_table, split_list=split_list) for text in texts]
        expected = [t for part in expected_parts for t in part]
        actual = []
        for target in targets:
            if target["type"] == "table":
                for row in target["rows"]:
                    text = " ".join(_text(c) for c in row if not c.get("generated"))
                    actual.extend(_tokens(text, table=True))
            else:
                actual.extend(_tokens(_text(target), split_list=split_list))
        matcher = SequenceMatcher(None, expected, actual, autojunk=False)
        matched = sum(size for _, _, size in matcher.get_matching_blocks())
        added = len(actual) - matched
        retention = matched / len(expected) if expected else 1.0
        added_ratio = added / max(1, len(expected))
        retained += matched
        total_tokens += len(expected)
        total_added += added
        if retention < threshold("AI_MIN_TOKEN_RETENTION"):
            fail("TOKEN_RETENTION", refs, f"Retención {retention:.3f} inferior al mínimo.")
        matched_indices = {i for a, _, size in matcher.get_matching_blocks() for i in range(a, a + size)}
        offset = 0
        for part in expected_parts:
            part_matches = sum(i in matched_indices for i in range(offset, offset + len(part)))
            if part and part_matches / len(part) < threshold("AI_MIN_TOKEN_RETENTION"):
                fail("SOURCE_CONTENT_OMITTED", refs, "Un bloque o registro no conserva el mínimo de contenido.")
            offset += len(part)
        if added_ratio > threshold("AI_MAX_ADDED_TOKEN_RATIO"):
            fail("ADDED_TOKENS", refs, f"Proporción de tokens nuevos {added_ratio:.3f} excesiva.")
        if added and any(b["type"] in ("paragraph", "callout") for b in targets):
            fail("PARAGRAPH_ADDED_TEXT", refs, "Los párrafos normales no pueden contener texto inventado.")
        deleted = Counter()
        inserted = Counter()
        for tag, a, b, c, d in matcher.get_opcodes():
            if tag != "equal":
                deleted.update(expected[a:b])
                inserted.update(actual[c:d])
        if deleted & inserted:
            fail("TOKEN_ORDER", refs, "El contenido se ha reordenado o duplicado.")
        if split_list or any(b["type"] == "list_item" for b in targets):
            warnings.append("LIST_STRUCTURE: " + ", ".join(refs))
        if is_table:
            warnings.append("TABLE_STRUCTURE: " + ", ".join(refs))

    # Critical data includes generated text: generation never permits invented figures.
    # Source groups are emitted in source order; output follows its physical reading order.
    for block in outputs:
        if block["type"] != "keep":
            text = _table_text(block, include_generated=True) if block["type"] == "table" else _text(block)
            output_critical.extend(_critical(text))
    if source_critical != output_critical:
        fail("CRITICAL_DATA", [b.id for b in sources], "Números, porcentajes o monedas alterados, omitidos o fuera de orden.")

    return IntegrityReport(
        is_valid=not violations, violations=violations,
        errors=[v.message for v in violations], warnings=list(dict.fromkeys(warnings)),
        total_source_blocks=len(sources), total_out_blocks=len(raw_outputs),
        source_characters=sum(len(get_block_text(b)) for b in sources),
        out_characters=sum(len(_table_text(b, include_generated=True) if b["type"] == "table" else _text(b)) for b in outputs),
        similarity_score=retained / total_tokens if total_tokens else 1.0,
        metadata={"source_tokens": total_tokens, "added_tokens": total_added},
        preserved_elements={"keep": not any(v.type.startswith("KEEP") or v.type == "SOURCE_ORDER" for v in violations)},
    )
