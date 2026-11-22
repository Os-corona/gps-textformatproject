"""Offline scoring of saved AI outputs against the curated S3T23 corpus."""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1]))
from ai_engine.validator import validate_chunk  # noqa: E402
from common.document_schema import AIChunkOutput  # noqa: E402
from docx_engine.extractor import extract_document  # noqa: E402


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=_unique_object)


def load_case(path):
    path = Path(path)
    golden = load_json(path)
    if golden["fixture_id"] != path.parent.name or golden["document"] != "document.docx":
        raise ValueError("Fixture ID or document path does not match its directory.")
    document = path.parent / "document.docx"
    if hashlib.sha256(document.read_bytes()).hexdigest() != golden["source_sha256"]:
        raise ValueError(f"DOCX hash mismatch: {golden['fixture_id']}")
    output = AIChunkOutput.model_validate(golden)
    return golden, extract_document(document), output


def golden_fingerprint(golden):
    content = {key: value for key, value in golden.items() if key != "review"}
    return hashlib.sha256(json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def review_approved(golden):
    review = golden["review"]
    if review["status"] != "approved":
        return False
    if not review.get("reviewer") or review.get("reviewer") != review.get("designated_reviewer"):
        return False
    if review.get("reviewed_content_sha256") != golden_fingerprint(golden):
        return False
    evidence = review.get("evidence_url") or ""
    if not evidence.startswith("https://github.com/") or "#pullrequestreview-" not in evidence:
        return False
    try:
        approved_at = datetime.fromisoformat(review.get("reviewed_at") or "")
    except ValueError:
        return False
    return approved_at.tzinfo is not None


def _classification(block):
    result = [block.type]
    if block.type in ("heading", "list_item"):
        result.append(block.level)
    if block.type == "list_item":
        result.append(block.is_numbered)
    return tuple(result)


def _refs(block):
    return getattr(block, "src", []) or ([block.id] if block.type == "keep" and block.id else [])


def _by_source(blocks):
    result = defaultdict(list)
    for block in blocks:
        for ref in _refs(block):
            result[ref].append(_classification(block))
    return dict(result)


def _table_signature(block):
    return (
        tuple(block.src), block.header_row,
        tuple(tuple(("".join(r.text for r in cell.runs) if cell.runs is not None else cell.text,
                     cell.h_span, cell.v_merge, cell.generated) for cell in row) for row in block.rows),
    )


def score_prediction(golden, sources, expected, raw_prediction):
    """IDs/chunk IDs and run segmentation do not affect structural scores."""
    predicted = AIChunkOutput.model_validate(raw_prediction)
    report = validate_chunk(sources.blocks, predicted.blocks)
    desired, actual = _by_source(expected.blocks), _by_source(predicted.blocks)
    refs = set(desired) | set(actual)
    correct = sum(desired.get(ref) == actual.get(ref) for ref in refs)
    desired_tables = [_table_signature(b) for b in expected.blocks if b.type == "table"]
    actual_tables = [_table_signature(b) for b in predicted.blocks if b.type == "table"]
    ordered_desired = [(_classification(b), _refs(b)) for b in expected.blocks]
    ordered_actual = [(_classification(b), _refs(b)) for b in predicted.blocks]
    return {
        "fixture_id": golden["fixture_id"], "integrity_ok": report.ok,
        "classification_accuracy": correct / len(refs) if refs else 1.0,
        "exact_structure": ordered_desired == ordered_actual,
        "exact_created_tables": desired_tables == actual_tables,
        "violations": [v.model_dump() for v in report.violations],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", type=Path, help="Directory containing <fixture_id>.json model outputs.")
    parser.add_argument("--require-review", action="store_true", help="Fail until all eight goldens have a recorded human approval.")
    args = parser.parse_args(argv)
    paths = sorted(ROOT.glob("*/golden.json"))
    if len(paths) != 8:
        raise SystemExit("The corpus must contain exactly eight golden.json files.")
    results, pending = [], []
    for path in paths:
        golden, sources, expected = load_case(path)
        baseline = validate_chunk(sources.blocks, expected.blocks)
        if not baseline.ok:
            raise SystemExit(f"Invalid golden {golden['fixture_id']}: {baseline.errors}")
        if not review_approved(golden):
            pending.append(golden["fixture_id"])
        if args.predictions:
            prediction = args.predictions / f"{golden['fixture_id']}.json"
            try:
                results.append(score_prediction(golden, sources, expected, load_json(prediction)))
            except (OSError, ValueError) as exc:
                results.append({"fixture_id": golden["fixture_id"], "integrity_ok": False, "error": str(exc)})
    summary = {"cases": len(paths), "pending_review": pending, "results": results}
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return int(bool(args.require_review and pending) or any(
        not row.get("integrity_ok") or not row.get("exact_structure") or not row.get("exact_created_tables")
        for row in results
    ))


if __name__ == "__main__":
    raise SystemExit(main())
