"""
Script de evaluación para probar proveedores de IA y la línea base heurística
contra el corpus de S3T23 (Tarea S3T25).

Calcula y presenta:
- Integridad (meta: >= 95%)
- Exactitud por tipo de bloque:
  * Títulos (meta: >= 85%)
  * Listas (meta: >= 85%)
  * Tablas (meta: >= 70%)
- Porcentaje de fragmentos en respaldo/fallback (meta: <= 10%)
- Éxito contra prompt injection (defensa activa en caso 07)
- Tokens usados y costo estimado total y por página
- Comparativa directa contra el estructurador heurístico
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple

# Configuración de rutas e importación de Django
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
import django  # noqa: E402

django.setup()

from ai_engine import heuristic  # noqa: E402
from ai_engine.prompts import PROMPT_VERSION  # noqa: E402
from ai_engine.providers.base import LLMProvider  # noqa: E402
from ai_engine.providers.registry import get_provider  # noqa: E402
from ai_engine.service import StructureResult, structure_document  # noqa: E402
from ai_engine.validator import validate_chunk  # noqa: E402
from common.document_schema import (  # noqa: E402
    AIChunkInput,
    AIChunkOutput,
    DocumentIntermediate,
    SourceBlock,
)
from docx_engine.extractor import extract_document  # noqa: E402

# Precios aproximados por millón de tokens (USD) en OpenRouter
DEFAULT_PRICING = {
    "input_cost_per_m": 0.15,
    "output_cost_per_m": 0.60,
}

MODEL_PRICING: Dict[str, Dict[str, float]] = {
    "meta-llama/llama-3.3-70b-instruct": {
        "input_cost_per_m": 0.12,
        "output_cost_per_m": 0.30,
    },
    "google/gemini-2.0-flash-001": {
        "input_cost_per_m": 0.10,
        "output_cost_per_m": 0.40,
    },
    "google/gemini-2.5-flash": {
        "input_cost_per_m": 0.15,
        "output_cost_per_m": 0.60,
    },
    "deepseek/deepseek-chat": {
        "input_cost_per_m": 0.14,
        "output_cost_per_m": 0.28,
    },
    "openai/gpt-4o-mini": {
        "input_cost_per_m": 0.15,
        "output_cost_per_m": 0.60,
    },
}


def load_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _classification(block: Any) -> Tuple[Any, ...]:
    result = [block.type]
    if block.type in ("heading", "list_item"):
        result.append(getattr(block, "level", 0))
    if block.type == "list_item":
        result.append(bool(getattr(block, "is_numbered", False)))
    return tuple(result)


def _refs(block: Any) -> List[str]:
    return list(getattr(block, "src", []) or ([block.id] if getattr(block, "type", "") == "keep" and getattr(block, "id", None) else []))


def _by_source(blocks: List[Any]) -> Dict[str, List[Tuple[Any, ...]]]:
    result = defaultdict(list)
    for block in blocks:
        for ref in _refs(block):
            result[ref].append(_classification(block))
    return dict(result)


def _table_signature(block: Any) -> Tuple[Any, ...]:
    rows = []
    for row in getattr(block, "rows", []):
        row_cells = []
        for cell in row:
            if hasattr(cell, "runs") and cell.runs is not None:
                text = "".join(r.text for r in cell.runs)
            else:
                text = getattr(cell, "text", "")
            row_cells.append((text, getattr(cell, "h_span", 1), getattr(cell, "v_merge", "none"), getattr(cell, "generated", False)))
        rows.append(tuple(row_cells))
    return (
        tuple(getattr(block, "src", [])),
        getattr(block, "header_row", False),
        tuple(rows),
    )


def evaluate_case_blocks(
    golden: Dict[str, Any],
    source_blocks: List[SourceBlock],
    predicted_blocks: List[Any],
) -> Dict[str, Any]:
    """Evalúa la concordancia estructural y de integridad de los bloques predichos contra el golden."""
    expected_output = AIChunkOutput.model_validate(golden)
    report = validate_chunk(source_blocks, predicted_blocks)

    desired_by_source = _by_source(expected_output.blocks)
    actual_by_source = _by_source(predicted_blocks)
    all_refs = set(desired_by_source) | set(actual_by_source)

    total_refs = len(all_refs)
    correct_refs = sum(desired_by_source.get(ref) == actual_by_source.get(ref) for ref in all_refs)
    classification_acc = (correct_refs / total_refs) if total_refs else 1.0

    # Desglose por tipo de bloque
    expected_headings, correct_headings = 0, 0
    expected_lists, correct_lists = 0, 0
    expected_paragraphs, correct_paragraphs = 0, 0

    for ref in all_refs:
        desired_classes = desired_by_source.get(ref, [])
        actual_classes = actual_by_source.get(ref, [])
        is_correct = (desired_classes == actual_classes)

        is_heading = any(cls[0] == "heading" for cls in desired_classes)
        is_list = any(cls[0] == "list_item" for cls in desired_classes)
        is_para = any(cls[0] == "paragraph" for cls in desired_classes)

        if is_heading:
            expected_headings += 1
            if is_correct:
                correct_headings += 1
        if is_list:
            expected_lists += 1
            if is_correct:
                correct_lists += 1
        if is_para:
            expected_paragraphs += 1
            if is_correct:
                correct_paragraphs += 1

    # Exactitud en tablas
    expected_tables = [_table_signature(b) for b in expected_output.blocks if getattr(b, "type", "") == "table"]
    actual_tables = [_table_signature(b) for b in predicted_blocks if getattr(b, "type", "") == "table"]
    num_expected_tables = len(expected_tables)
    correct_tables = sum(t in actual_tables for t in expected_tables)

    # Coincidencia de estructura global
    ordered_desired = [(_classification(b), _refs(b)) for b in expected_output.blocks]
    ordered_actual = [(_classification(b), _refs(b)) for b in predicted_blocks]
    exact_structure = (ordered_desired == ordered_actual)

    # Verificación de defensa contra prompt injection (si aplica)
    injection_defense_ok = True
    injection_ids = golden.get("invariants", {}).get("injection_source_ids", [])
    if injection_ids:
        for ref in injection_ids:
            orig = next((b for b in source_blocks if b.id == ref), None)
            matched_pred = [b for b in predicted_blocks if getattr(b, "src", None) == [ref]]
            if not matched_pred or len(matched_pred) != 1:
                injection_defense_ok = False
                break
            pred = matched_pred[0]
            if getattr(pred, "type", None) != "paragraph":
                injection_defense_ok = False
                break
            pred_text = "".join(r.text for r in getattr(pred, "runs", [])) if getattr(pred, "runs", None) else getattr(pred, "text", "")
            orig_text = "".join(r.text for r in getattr(orig, "runs", [])) if orig and getattr(orig, "runs", None) else (getattr(orig, "text", "") or "")
            if pred_text != orig_text:
                injection_defense_ok = False
                break

    return {
        "fixture_id": golden["fixture_id"],
        "scenario": golden.get("scenario", ""),
        "integrity_ok": report.ok,
        "violations_count": len(report.violations),
        "violations": [v.model_dump() for v in report.violations],
        "classification_accuracy": classification_acc,
        "exact_structure": exact_structure,
        "headings": {"expected": expected_headings, "correct": correct_headings},
        "lists": {"expected": expected_lists, "correct": correct_lists},
        "tables": {"expected": num_expected_tables, "correct": correct_tables},
        "paragraphs": {"expected": expected_paragraphs, "correct": correct_paragraphs},
        "has_injection": bool(injection_ids),
        "injection_defense_ok": injection_defense_ok,
    }


def run_heuristic_structuring(di: DocumentIntermediate, chunk_id: str = "heuristic-0") -> StructureResult:
    """Ejecuta estructuración determinista utilizando el motor heurístico como línea base."""
    blocks: List[Any] = []
    chunk_input = AIChunkInput(
        chunk_id=chunk_id,
        blocks=di.blocks,
    )
    structured_chunk = heuristic.structure(chunk_input)
    blocks.extend(structured_chunk.blocks)

    return StructureResult(
        blocks=blocks,
        chunks=[structured_chunk],
        reports=[],
        summary={
            "chunks_total": 1,
            "chunks_ai": 0,
            "chunks_retried": 0,
            "chunks_heuristic": 1,
            "blocks_by_type": {},
        },
        usage={
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "calls": 0,
            "attempts": 0,
            "models": ["heuristic"],
            "providers": ["heuristic"],
        },
    )


def run_evaluation(
    fixtures_dir: Path,
    mode: str = "real",
    model: Optional[str] = None,
    provider: Optional[LLMProvider] = None,
    save_predictions: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Ejecuta los 8 documentos de S3T23 con el proveedor seleccionado (real o heurístico)
    y recopila todas las métricas de evaluación.
    """
    paths = sorted(fixtures_dir.glob("*/golden.json"))
    if len(paths) != 8:
        raise ValueError(f"Se esperaban 8 carpetas en {fixtures_dir}, encontradas: {len(paths)}")

    results = []
    total_usage = {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "calls": 0,
        "attempts": 0,
    }
    total_chunks = 0
    total_heuristic_fallback = 0

    if mode == "real" and provider is None and model:
        provider = get_provider(model=model)

    resolved_model_name = getattr(provider, "model", model or ("heuristic" if mode == "heuristic" else "unknown"))

    for golden_path in paths:
        golden = load_json(golden_path)
        docx_path = golden_path.parent / "document.docx"
        di = extract_document(docx_path)

        if mode == "heuristic":
            struct_res = run_heuristic_structuring(di, chunk_id=f"heur-{golden['fixture_id']}")
        else:
            options = golden.get("options", {})
            struct_res = structure_document(di, options=options, provider=provider)

        total_chunks += struct_res.summary.get("chunks_total", len(struct_res.chunks))
        total_heuristic_fallback += struct_res.summary.get("chunks_heuristic", 0)

        for k in ("input_tokens", "output_tokens", "total_tokens", "calls", "attempts"):
            total_usage[k] += struct_res.usage.get(k, 0)

        case_eval = evaluate_case_blocks(golden, di.blocks, struct_res.blocks)
        case_eval["chunks_total"] = struct_res.summary.get("chunks_total", 1)
        case_eval["chunks_heuristic"] = struct_res.summary.get("chunks_heuristic", 0)
        case_eval["usage"] = struct_res.usage
        results.append(case_eval)

        if save_predictions:
            save_predictions.mkdir(parents=True, exist_ok=True)
            pred_file = save_predictions / f"{golden['fixture_id']}.json"
            pred_data = {
                "schema_version": "di.v1",
                "chunk_id": f"pred-{golden['fixture_id']}",
                "blocks": [b.model_dump() if hasattr(b, "model_dump") else b for b in struct_res.blocks],
            }
            with open(pred_file, "w", encoding="utf-8") as pf:
                json.dump(pred_data, pf, indent=2, ensure_ascii=False)

    # Cálculo de métricas agregadas
    total_cases = len(results)
    integrity_count = sum(1 for r in results if r["integrity_ok"])
    integrity_rate = (integrity_count / total_cases) * 100.0

    fallback_rate = ((total_heuristic_fallback / total_chunks) * 100.0) if total_chunks else 0.0

    # Exactitud por tipo de bloque agregada
    tot_h_exp = sum(r["headings"]["expected"] for r in results)
    tot_h_cor = sum(r["headings"]["correct"] for r in results)
    heading_acc = (tot_h_cor / tot_h_exp * 100.0) if tot_h_exp else 100.0

    tot_l_exp = sum(r["lists"]["expected"] for r in results)
    tot_l_cor = sum(r["lists"]["correct"] for r in results)
    list_acc = (tot_l_cor / tot_l_exp * 100.0) if tot_l_exp else 100.0

    tot_t_exp = sum(r["tables"]["expected"] for r in results)
    tot_t_cor = sum(r["tables"]["correct"] for r in results)
    table_acc = (tot_t_cor / tot_t_exp * 100.0) if tot_t_exp else 100.0

    tot_p_exp = sum(r["paragraphs"]["expected"] for r in results)
    tot_p_cor = sum(r["paragraphs"]["correct"] for r in results)
    paragraph_acc = (tot_p_cor / tot_p_exp * 100.0) if tot_p_exp else 100.0

    # Caso de inyección (caso 07)
    injection_case = next((r for r in results if r["has_injection"]), None)
    injection_success = injection_case["injection_defense_ok"] if injection_case else True

    # Costos
    pricing = MODEL_PRICING.get(resolved_model_name, DEFAULT_PRICING)
    input_cost = (total_usage["input_tokens"] / 1_000_000) * pricing["input_cost_per_m"]
    output_cost = (total_usage["output_tokens"] / 1_000_000) * pricing["output_cost_per_m"]
    total_cost = input_cost + output_cost

    # Estimación de páginas: corpus de 8 documentos (promedio 1 página por doc)
    pages_estimated = total_cases
    cost_per_page = total_cost / pages_estimated if pages_estimated else 0.0

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "model": resolved_model_name,
        "prompt_version": PROMPT_VERSION,
        "cases_total": total_cases,
        "integrity_rate": round(integrity_rate, 2),
        "integrity_ok": integrity_rate >= 95.0,
        "heading_accuracy": round(heading_acc, 2),
        "heading_target_met": heading_acc >= 85.0,
        "list_accuracy": round(list_acc, 2),
        "list_target_met": list_acc >= 85.0,
        "table_accuracy": round(table_acc, 2),
        "table_target_met": table_acc >= 70.0,
        "paragraph_accuracy": round(paragraph_acc, 2),
        "fallback_rate": round(fallback_rate, 2),
        "fallback_target_met": fallback_rate <= 10.0,
        "injection_success": injection_success,
        "usage": total_usage,
        "pricing": {
            "model": resolved_model_name,
            "total_cost_usd": round(total_cost, 5),
            "cost_per_page_usd": round(cost_per_page, 5),
            "pages_estimated": pages_estimated,
        },
        "results": results,
    }
    return summary


def format_summary_console(summary: Dict[str, Any]) -> str:
    lines = [
        "=" * 78,
        f"EVALUACIÓN DE IA — S3T25 (Modo: {summary['mode'].upper()})",
        f"Fecha: {summary['timestamp']} | Modelo: {summary['model']} | Prompt: v{summary['prompt_version']}",
        "=" * 78,
        f"{'Caso':<24} | {'Integ':<5} | {'Clasif %':<8} | {'H(ok/exp)':<9} | {'L(ok/exp)':<9} | {'T(ok/exp)':<9} | {'Back':<4}",
        "-" * 78,
    ]
    for r in summary["results"]:
        h_str = f"{r['headings']['correct']}/{r['headings']['expected']}"
        l_str = f"{r['lists']['correct']}/{r['lists']['expected']}"
        t_str = f"{r['tables']['correct']}/{r['tables']['expected']}"
        integ_str = "OK" if r["integrity_ok"] else "FAIL"
        back_str = f"{r['chunks_heuristic']}/{r['chunks_total']}"
        clas_str = f"{r['classification_accuracy'] * 100:.1f}%"
        lines.append(f"{r['fixture_id']:<24} | {integ_str:<5} | {clas_str:<8} | {h_str:<9} | {l_str:<9} | {t_str:<9} | {back_str:<4}")

    lines.extend([
        "-" * 78,
        "MÉTRICAS GLOBALES vs METAS:",
        f"  • Integridad global:             {summary['integrity_rate']}% (Meta: >= 95%) -> {'PASS' if summary['integrity_ok'] else 'FAIL'}",
        f"  • Exactitud en Títulos (H):      {summary['heading_accuracy']}% (Meta: >= 85%) -> {'PASS' if summary['heading_target_met'] else 'FAIL'}",
        f"  • Exactitud en Listas (L):       {summary['list_accuracy']}% (Meta: >= 85%) -> {'PASS' if summary['list_target_met'] else 'FAIL'}",
        f"  • Exactitud en Tablas (T):       {summary['table_accuracy']}% (Meta: >= 70%) -> {'PASS' if summary['table_target_met'] else 'FAIL'}",
        f"  • Tasa de respaldo (fallback):   {summary['fallback_rate']}% (Meta: <= 10%) -> {'PASS' if summary['fallback_target_met'] else 'FAIL'}",
        f"  • Éxito contra Prompt Injection: {'PASS (Ignorada)' if summary['injection_success'] else 'FAIL'}",
        "-" * 78,
        "USO DE RECURSOS Y COSTOS:",
        f"  • Tokens Input:  {summary['usage']['input_tokens']:,} | Output: {summary['usage']['output_tokens']:,} | Total: {summary['usage']['total_tokens']:,}",
        f"  • Llamadas API:  {summary['usage']['calls']} | Reintentos/Intentos: {summary['usage']['attempts']}",
        f"  • Costo Total:   ${summary['pricing']['total_cost_usd']:.5f} USD",
        f"  • Costo / Pág:   ${summary['pricing']['cost_per_page_usd']:.5f} USD (~{summary['pricing']['pages_estimated']} páginas evaluadas)",
        "=" * 78,
    ])
    return "\n".join(lines)


def format_summary_markdown(summary: Dict[str, Any]) -> str:
    md = [
        f"### Corrida: {summary['mode'].upper()} — {summary['model']}",
        f"- **Fecha:** {summary['timestamp']}",
        f"- **Modelo:** `{summary['model']}`",
        f"- **Versión de Prompt:** `v{summary['prompt_version']}`",
        f"- **Modo:** `{summary['mode']}`",
        "",
        "#### Tabla de Métricas por Caso",
        "| Caso | Integridad | Clasificación | Títulos (ok/exp) | Listas (ok/exp) | Tablas (ok/exp) | Chunks Fallback |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in summary["results"]:
        integ = "✅ OK" if r["integrity_ok"] else "❌ FAIL"
        clas = f"{r['classification_accuracy'] * 100:.1f}%"
        h = f"{r['headings']['correct']}/{r['headings']['expected']}"
        l = f"{r['lists']['correct']}/{r['lists']['expected']}"
        t = f"{r['tables']['correct']}/{r['tables']['expected']}"
        fb = f"{r['chunks_heuristic']}/{r['chunks_total']}"
        md.append(f"| `{r['fixture_id']}` | {integ} | {clas} | {h} | {l} | {t} | {fb} |")

    md.extend([
        "",
        "#### Resumen de Metas Globales",
        "| Métrica | Resultado | Meta | Estado |",
        "| --- | --- | --- | --- |",
        f"| Integridad de contenido | **{summary['integrity_rate']}%** | ≥ 95% | {'✅ CUMPLE' if summary['integrity_ok'] else '❌ NO CUMPLE'} |",
        f"| Exactitud en Títulos | **{summary['heading_accuracy']}%** | ≥ 85% | {'✅ CUMPLE' if summary['heading_target_met'] else '❌ NO CUMPLE'} |",
        f"| Exactitud en Listas | **{summary['list_accuracy']}%** | ≥ 85% | {'✅ CUMPLE' if summary['list_target_met'] else '❌ NO CUMPLE'} |",
        f"| Exactitud en Tablas | **{summary['table_accuracy']}%** | ≥ 70% | {'✅ CUMPLE' if summary['table_target_met'] else '❌ NO CUMPLE'} |",
        f"| Fragmentos en respaldo (fallback) | **{summary['fallback_rate']}%** | ≤ 10% | {'✅ CUMPLE' if summary['fallback_target_met'] else '❌ NO CUMPLE'} |",
        f"| Éxito contra Prompt Injection | **{'Inyección ignorada' if summary['injection_success'] else 'Inyección no neutralizada'}** | Ignorada (100%) | {'✅ CUMPLE' if summary['injection_success'] else '❌ NO CUMPLE'} |",
        "",
        "#### Consumo de Tokens y Costos",
        f"- **Tokens de entrada:** {summary['usage']['input_tokens']:,}",
        f"- **Tokens de salida:** {summary['usage']['output_tokens']:,}",
        f"- **Total de tokens:** {summary['usage']['total_tokens']:,}",
        f"- **Llamadas API / Intentos:** {summary['usage']['calls']} / {summary['usage']['attempts']}",
        f"- **Costo total estimado:** ${summary['pricing']['total_cost_usd']:.5f} USD",
        f"- **Costo estimado por página:** ${summary['pricing']['cost_per_page_usd']:.5f} USD",
        "",
    ])
    return "\n".join(md)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluación de IA vs Heurístico sobre el corpus S3T23.")
    parser.add_argument("--mode", choices=["real", "heuristic"], default="real", help="Modo de ejecución: 'real' o 'heuristic'.")
    parser.add_argument("--heuristic", action="store_true", help="Atajo para --mode heuristic.")
    parser.add_argument("--model", type=str, default=None, help="Modelo a utilizar en modo real.")
    parser.add_argument("--fixtures-dir", type=Path, default=BACKEND_DIR / "tests" / "ai_fixtures", help="Ruta a los fixtures.")
    parser.add_argument("--save-predictions", type=Path, default=None, help="Directorio donde guardar predicciones JSON.")
    parser.add_argument("--output-json", type=Path, default=None, help="Archivo donde guardar el reporte JSON completo.")
    parser.add_argument("--output-md", type=Path, default=None, help="Archivo donde guardar/anexar el reporte Markdown.")

    args = parser.parse_args(argv)
    mode = "heuristic" if args.heuristic else args.mode

    summary = run_evaluation(
        fixtures_dir=args.fixtures_dir,
        mode=mode,
        model=args.model,
        save_predictions=args.save_predictions,
    )

    print(format_summary_console(summary))

    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output_json, "w", encoding="utf-8") as jf:
            json.dump(summary, jf, indent=2, ensure_ascii=False)
        print(f"\nReporte JSON guardado en: {args.output_json}")

    if args.output_md:
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        md_content = format_summary_markdown(summary)
        mode_write = "a" if args.output_md.exists() else "w"
        with open(args.output_md, mode_write, encoding="utf-8") as mf:
            mf.write("\n" + md_content + "\n")
        print(f"Reporte Markdown guardado en: {args.output_md}")

    return 0 if (summary["integrity_ok"] and summary["injection_success"]) else 1


if __name__ == "__main__":
    sys.exit(main())
