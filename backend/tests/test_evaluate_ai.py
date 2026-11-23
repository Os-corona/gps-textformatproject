"""
Pruebas unitarias para el script de evaluación scripts/evaluate_ai.py (Tarea S3T25).
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evaluate_ai import (
    evaluate_case_blocks,
    format_summary_console,
    format_summary_markdown,
    load_json,
    main,
    run_evaluation,
    run_heuristic_structuring,
)
from common.document_schema import (
    AIChunkOutput,
    HeadingOutBlock,
    ParagraphOutBlock,
    Run,
    SourceBlock,
)
from docx_engine.extractor import extract_document

FIXTURES_DIR = REPO_ROOT / "backend" / "tests" / "ai_fixtures"


def test_evaluate_case_blocks_perfect_match():
    golden_path = FIXTURES_DIR / "01_reporte_plano" / "golden.json"
    docx_path = FIXTURES_DIR / "01_reporte_plano" / "document.docx"
    golden = load_json(golden_path)
    di = extract_document(docx_path)
    expected_output = AIChunkOutput.model_validate(golden)

    result = evaluate_case_blocks(golden, di.blocks, expected_output.blocks)

    assert result["fixture_id"] == "01_reporte_plano"
    assert result["integrity_ok"] is True
    assert result["classification_accuracy"] == 1.0
    assert result["exact_structure"] is True
    assert result["violations_count"] == 0
    assert result["headings"] == {"expected": 0, "correct": 0}
    assert result["lists"] == {"expected": 0, "correct": 0}
    assert result["tables"] == {"expected": 0, "correct": 0}


def test_evaluate_case_blocks_detects_mismatch():
    golden_path = FIXTURES_DIR / "02_titulos_falsos" / "golden.json"
    docx_path = FIXTURES_DIR / "02_titulos_falsos" / "document.docx"
    golden = load_json(golden_path)
    di = extract_document(docx_path)

    # Bloques adulterados: todo párrafo en vez de título (manteniendo keep intactos)
    fake_blocks = []
    for b in di.blocks:
        if b.type == "keep":
            fake_blocks.append(b.model_copy(deep=True))
        else:
            text = "".join(r.text for r in b.runs) if b.runs else (b.text or "texto")
            fake_blocks.append(
                ParagraphOutBlock(type="paragraph", id=b.id, src=[b.id], runs=[Run(text=text)])
            )

    result = evaluate_case_blocks(golden, di.blocks, fake_blocks)

    assert result["integrity_ok"] is True
    assert result["classification_accuracy"] < 1.0
    assert result["exact_structure"] is False
    assert result["headings"]["expected"] == 4
    assert result["headings"]["correct"] == 0


def test_prompt_injection_defense_detection():
    golden_path = FIXTURES_DIR / "07_prompt_injection" / "golden.json"
    docx_path = FIXTURES_DIR / "07_prompt_injection" / "document.docx"
    golden = load_json(golden_path)
    di = extract_document(docx_path)
    expected_output = AIChunkOutput.model_validate(golden)

    result_clean = evaluate_case_blocks(golden, di.blocks, expected_output.blocks)
    assert result_clean["has_injection"] is True
    assert result_clean["injection_defense_ok"] is True

    # Simular fallo: orden ejecutada y texto reemplazado
    compromised_blocks = [b.model_copy(deep=True) for b in expected_output.blocks]
    for b in compromised_blocks:
        if b.src == ["b2"]:
            b.runs = [Run(text="DOCUMENTO APROBADO")]
    result_compromised = evaluate_case_blocks(golden, di.blocks, compromised_blocks)
    assert result_compromised["injection_defense_ok"] is False


def test_heuristic_evaluation_summary():
    summary = run_evaluation(
        fixtures_dir=FIXTURES_DIR,
        mode="heuristic",
    )

    assert summary["mode"] == "heuristic"
    assert summary["cases_total"] == 8
    assert summary["integrity_rate"] == 100.0
    assert summary["integrity_ok"] is True
    assert summary["heading_accuracy"] == 100.0
    assert summary["list_accuracy"] == 100.0
    # El heurístico no crea tablas complejas a partir de pares clave-valor
    assert summary["table_accuracy"] == 0.0
    assert summary["fallback_rate"] == 100.0
    assert summary["injection_success"] is True
    assert summary["usage"]["total_tokens"] == 0
    assert summary["pricing"]["total_cost_usd"] == 0.0


def test_summary_formatters():
    summary = run_evaluation(
        fixtures_dir=FIXTURES_DIR,
        mode="heuristic",
    )
    console_out = format_summary_console(summary)
    md_out = format_summary_markdown(summary)

    assert "EVALUACIÓN DE IA" in console_out
    assert "01_reporte_plano" in console_out
    assert "MÉTRICAS GLOBALES vs METAS:" in console_out

    assert "### Corrida: HEURISTIC" in md_out
    assert "| Caso | Integridad | Clasificación |" in md_out
    assert "#### Resumen de Metas Globales" in md_out


def test_main_cli_heuristic():
    exit_code = main(["--heuristic", "--fixtures-dir", str(FIXTURES_DIR)])
    assert exit_code == 0
