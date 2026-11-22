"""Deterministic structuring of extracted document blocks, without an AI service."""
import re

from common.document_schema import AIChunkOutput, Hints, Run

_GLYPH = re.compile(r'^\s*([•◦▪▫‣⁃·●○■□◆◇►▶➢*–—-])(?:\s*)')
_NUMBER = re.compile(r'^\s*(?:\d+(?:\.\d+)+[.)]?|\d+[.)]|\(\d+(?:\.\d+)*\)|[A-Za-z][.)]|\([A-Za-z]\)|[IVXLCDMivxlcdm]+[.)])\s+')
_KEY = re.compile(r'^\s*(?!https?://)[^:\n]{2,40}:\s+\S+')
_HEADING_STYLE = re.compile(r'^(?:heading|encabezado|título|titulo)\s*([1-6])$', re.IGNORECASE)


def _native_heading_level(style_name):
    if not style_name:
        return None
    normalized = style_name.strip()
    if normalized.lower() in ('title', 'título', 'titulo'):
        return 0
    match = _HEADING_STYLE.match(normalized)
    return int(match.group(1)) if match else None


def _cut(runs, count):
    result = []
    for run in runs:
        take = min(count, len(run.text))
        count -= take
        if run.text[take:]:
            result.append(run.model_copy(update={'text': run.text[take:]}))
    return result


def _bold_prefix(runs, length):
    result = []
    for run in runs:
        n = min(length, len(run.text))
        if n:
            result.append(run.model_copy(update={'text': run.text[:n], 'bold': True}))
        if n < len(run.text):
            result.append(run.model_copy(update={'text': run.text[n:]}))
        length -= n
    return result


def structure(chunk):
    """Return one structured block per input, retaining source references and runs."""
    blocks = []
    for i, source in enumerate(chunk.blocks):
        if source.type == 'keep' or not (source.runs or source.text):
            blocks.append({'type': 'keep', 'src': [source.id]})
            continue
        hints = source.hints or Hints()
        runs = [r.model_copy(deep=True) for r in (source.runs or [Run(text=source.text)])]
        text = ''.join(r.text for r in runs)
        common = {'id': source.id, 'src': [source.id], 'runs': runs, 'hints': source.hints}
        native_heading = _native_heading_level(source.style_name or hints.style_name)
        list_info = source.list_info or {}
        is_native_list = bool(hints.is_native_list or list_info.get('is_list'))
        heading = hints.size_ratio >= 1.2 or (hints.all_bold and 0 < hints.words <= 12 and not hints.ends_with_period)
        if native_heading is not None:
            blocks.append({'type': 'heading', 'level': native_heading, **common})
        elif is_native_list:
            native_level = hints.list_level if hints.list_level is not None else list_info.get('level', 0)
            native_numbered = bool(hints.is_numbered if hints.is_numbered is not None else list_info.get('is_numbered', False))
            blocks.append({'type': 'list_item', 'level': min(8, max(0, int(native_level))), 'is_numbered': native_numbered, **common})
        elif heading:
            ratio = hints.size_ratio
            level = 1 if ratio >= 1.5 else 2 if ratio >= 1.3 else 3
            blocks.append({'type': 'heading', 'level': level, **common})
        elif hints.starts_with_glyph and (match := _GLYPH.match(text)) and text[match.end():]:
            glyph_level = {'◦': 1, '○': 1, '▫': 2, '▪': 2, '■': 2, '□': 2}.get(match.group(1), 0)
            blocks.append({'type': 'list_item', 'level': min(8, max(hints.indent_level, glyph_level)), 'is_numbered': False, **{**common, 'runs': _cut(runs, match.end())}})
        elif hints.manual_numbering and (match := _NUMBER.match(text)) and text[match.end():]:
            blocks.append({'type': 'list_item', 'level': min(8, hints.indent_level), 'is_numbered': True, **{**common, 'runs': _cut(runs, match.end())}})
        else:
            adjacent = any(0 <= j < len(chunk.blocks) and chunk.blocks[j].type != 'keep' and _KEY.match(''.join(r.text for r in (chunk.blocks[j].runs or [])) or chunk.blocks[j].text or '') for j in (i - 1, i + 1))
            if adjacent and _KEY.match(text):
                common['runs'] = _bold_prefix(runs, text.index(':') + 1)
            blocks.append({'type': 'paragraph', **common})
    return AIChunkOutput(chunk_id=chunk.chunk_id, blocks=blocks)
