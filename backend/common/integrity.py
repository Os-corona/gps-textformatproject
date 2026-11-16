"""Comparación compartida de tokens para el DI y los documentos reconstruidos."""

import re
from itertools import zip_longest

from common.document_schema import IntegrityReport


def tokenize(text):
    """Conserva palabras, números, acentos y mayúsculas en su orden original."""
    return re.findall(r"\w+", text, flags=re.UNICODE)


def validate_tokens(expected, actual, *, source_blocks=0, out_blocks=0):
    expected_tokens = tokenize(expected)
    actual_tokens = tokenize(actual)
    valid = expected_tokens == actual_tokens
    metadata = {
        "expected_tokens": len(expected_tokens),
        "actual_tokens": len(actual_tokens),
    }
    if not valid:
        metadata["first_mismatch"] = next(
            index for index, (left, right) in enumerate(
                zip_longest(expected_tokens, actual_tokens)
            ) if left != right
        )
    return IntegrityReport(
        is_valid=valid,
        total_source_blocks=source_blocks,
        total_out_blocks=out_blocks,
        source_characters=len(expected),
        out_characters=len(actual),
        errors=[] if valid else ["La secuencia de tokens del resultado difiere del DI."],
        metadata=metadata,
    )
