import os
import pytest
from pathlib import Path
from playwright.sync_api import sync_playwright
import docx

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

@pytest.mark.e2e
def test_full_web_integration_flow():
    """
    S3T6 — Prueba de integración de flujo completo desde la interfaz web.
    Criterios de aceptación:
    1. Subir un .docx desde / redirige a /config.
    2. Seleccionar una plantilla (ej. APA 7) y dar clic en 'Aplicar formato'
       procesa el documento y redirige a /result.
    3. El botón 'Descargar' en /result descarga el archivo *_formateado.docx
       con los cambios aplicados.
    """
    fixture_path = FIXTURES_DIR / "01_planos.docx"
    assert fixture_path.exists(), f"Fixture no encontrado: {fixture_path}"

    frontend_url = os.environ.get("FRONTEND_URL", "http://127.0.0.1:5173")

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        # 1. Carga en / y redirección a /config
        page.goto(frontend_url, wait_until="networkidle")
        file_input = page.locator("#file-input")
        file_input.set_input_files(str(fixture_path))
        page.wait_for_selector("#selected-file-info")

        continue_btn = page.locator("#btn-continue")
        assert continue_btn.is_enabled()
        continue_btn.click()

        page.wait_for_url(f"{frontend_url}/config", timeout=10000)
        assert "/config" in page.url

        # 2. Selección de plantilla APA 7 y clic en 'Aplicar formato'
        page.wait_for_selector("#preset-select", timeout=10000)
        select_elem = page.locator("#preset-select")
        select_elem.select_option("apa7")

        apply_btn = page.locator("#btn-apply-format")
        page.wait_for_function("btn => !btn.disabled", arg=apply_btn.element_handle())
        apply_btn.click()

        page.wait_for_url(f"{frontend_url}/result", timeout=15000)
        assert "/result" in page.url

        # 3. Descarga y validación del documento final
        page.wait_for_selector("#btn-download", timeout=15000)
        with page.expect_download(timeout=10000) as download_info:
            page.locator("#btn-download").click()

        download = download_info.value
        filename = download.suggested_filename
        assert filename == "01_planos_formateado.docx"

        temp_download_path = FIXTURES_DIR / "temp_e2e_download.docx"
        download.save_as(str(temp_download_path))

        try:
            doc = docx.Document(str(temp_download_path))
            assert len(doc.paragraphs) > 0

            # Validar márgenes de APA 7 (2.54 cm)
            assert abs(doc.sections[0].top_margin.cm - 2.54) < 0.05
            assert abs(doc.sections[0].bottom_margin.cm - 2.54) < 0.05
            assert abs(doc.sections[0].left_margin.cm - 2.54) < 0.05
            assert abs(doc.sections[0].right_margin.cm - 2.54) < 0.05

            # Validar tipografía de APA 7 (Times New Roman, 12 pt)
            for p_elem in doc.paragraphs:
                for r in p_elem.runs:
                    if r.font.name:
                        assert r.font.name == "Times New Roman"
                    if r.font.size:
                        assert r.font.size.pt == 12.0
        finally:
            if temp_download_path.exists():
                temp_download_path.unlink()
            browser.close()
