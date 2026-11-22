import io
import os
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from docx import Document as DocxDocument
from rest_framework import status
from rest_framework.test import APITestCase

from documents.models import Document, ProcessingJob


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
INVALID_FIXTURES_DIR = FIXTURES_DIR / "invalid"


class DocumentAPITests(APITestCase):
    def setUp(self):
        self.valid_docx_path = FIXTURES_DIR / "01_planos.docx"

    def _get_valid_uploaded_file(self):
        with open(self.valid_docx_path, "rb") as f:
            return SimpleUploadedFile(
                "01_planos.docx",
                f.read(),
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

    # -------------------------------------------------------------------------
    # 2) Test de carga válida: responde 201 con los ids.
    # -------------------------------------------------------------------------
    def test_valid_upload_returns_201_with_ids(self):
        """
        Valida que subir un archivo .docx válido responda 201 Created
        e incluya document_id, job_id y status 'pending'.
        """
        uploaded_file = self._get_valid_uploaded_file()

        response = self.client.post(
            "/api/documents/",
            {"file": uploaded_file},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("document_id", response.data)
        self.assertIn("job_id", response.data)
        self.assertIsInstance(response.data["document_id"], int)
        self.assertIsInstance(response.data["job_id"], int)
        self.assertEqual(response.data["status"], "pending")
        self.assertEqual(response.data["original_name"], "01_planos.docx")

        # Verificar persistencia en base de datos
        self.assertTrue(Document.objects.filter(id=response.data["document_id"]).exists())
        self.assertTrue(ProcessingJob.objects.filter(id=response.data["job_id"]).exists())

    def test_valid_upload_via_upload_url(self):
        """
        Verifica compatibilidad con la ruta alternativa /api/documents/upload/.
        """
        uploaded_file = self._get_valid_uploaded_file()

        response = self.client.post(
            "/api/documents/upload/",
            {"file": uploaded_file},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("document_id", response.data)
        self.assertIn("job_id", response.data)

    # -------------------------------------------------------------------------
    # 3) Tests de carga inválida: falso.docx, vacio.docx, corrupto.docx,
    #    un archivo mayor a 10 MB y un .pdf. Todos responden 400 con el código esperado.
    # -------------------------------------------------------------------------
    def test_invalid_upload_falso_docx(self):
        """
        Archivo con extensión .docx pero con contenido PDF (falso.docx).
        Debe responder 400 con error INVALID_FILE.
        """
        falso_path = INVALID_FIXTURES_DIR / "falso.docx"
        with open(falso_path, "rb") as f:
            uploaded_file = SimpleUploadedFile("falso.docx", f.read())

        response = self.client.post(
            "/api/documents/",
            {"file": uploaded_file},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data.get("error"), "INVALID_FILE")

    def test_invalid_upload_vacio_docx(self):
        """
        Archivo ZIP vacío de 22 bytes sin estructura OOXML (vacio.docx).
        Debe responder 400 con error INVALID_FILE.
        """
        vacio_path = INVALID_FIXTURES_DIR / "vacio.docx"
        with open(vacio_path, "rb") as f:
            uploaded_file = SimpleUploadedFile("vacio.docx", f.read())

        response = self.client.post(
            "/api/documents/",
            {"file": uploaded_file},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data.get("error"), "INVALID_FILE")

    def test_invalid_upload_corrupto_docx(self):
        """
        Archivo DOCX truncado/corrupto (corrupto.docx).
        Debe responder 400 con error INVALID_FILE.
        """
        corrupto_path = INVALID_FIXTURES_DIR / "corrupto.docx"
        with open(corrupto_path, "rb") as f:
            uploaded_file = SimpleUploadedFile("corrupto.docx", f.read())

        response = self.client.post(
            "/api/documents/",
            {"file": uploaded_file},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data.get("error"), "INVALID_FILE")

    def test_invalid_upload_file_larger_than_10mb(self):
        """
        Archivo mayor a 10 MB (10 * 1024 * 1024 + 1024 bytes).
        Debe responder 400 con error FILE_TOO_LARGE.
        """
        large_size = 10 * 1024 * 1024 + 1024
        # Generar contenido que exceda los 10 MB con encabezado ZIP
        large_content = b"PK\x03\x04" + b"0" * (large_size - 4)
        uploaded_file = SimpleUploadedFile(
            "archivo_grande.docx",
            large_content,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        response = self.client.post(
            "/api/documents/",
            {"file": uploaded_file},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data.get("error"), "FILE_TOO_LARGE")

    def test_invalid_upload_pdf(self):
        """
        Archivo con extensión .pdf.
        Debe responder 400 con error INVALID_FILE.
        """
        uploaded_file = SimpleUploadedFile(
            "documento.pdf",
            b"%PDF-1.4 contenido de prueba",
            content_type="application/pdf",
        )

        response = self.client.post(
            "/api/documents/",
            {"file": uploaded_file},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data.get("error"), "INVALID_FILE")

    # -------------------------------------------------------------------------
    # 4) Tests de configuración fuera de rango (margen de 20 cm, tamaño de 2 pt,
    #    fuente no permitida): responde 400 INVALID_CONFIG.
    # -------------------------------------------------------------------------
    def test_format_out_of_range_margin(self):
        """
        Configuración con margen de 20 cm (el límite permitido es 0.5 a 5.0 cm).
        Debe responder 400 INVALID_CONFIG.
        """
        upload_resp = self.client.post(
            "/api/documents/",
            {"file": self._get_valid_uploaded_file()},
            format="multipart",
        )
        doc_id = upload_resp.data["document_id"]

        invalid_config = {
            "preset_id": "apa7",
            "margins_cm": {"top": 20.0},
        }

        response = self.client.post(
            f"/api/documents/{doc_id}/format/",
            invalid_config,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data.get("error"), "INVALID_CONFIG")

    def test_format_out_of_range_font_size(self):
        """
        Configuración con tamaño de fuente de 2 pt (el límite permitido es 8 a 24 pt).
        Debe responder 400 INVALID_CONFIG.
        """
        upload_resp = self.client.post(
            "/api/documents/",
            {"file": self._get_valid_uploaded_file()},
            format="multipart",
        )
        doc_id = upload_resp.data["document_id"]

        invalid_config = {
            "preset_id": "apa7",
            "font_size_pt": 2,
        }

        response = self.client.post(
            f"/api/documents/{doc_id}/format/",
            invalid_config,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data.get("error"), "INVALID_CONFIG")

    def test_format_disallowed_font(self):
        """
        Configuración con una fuente no permitida (e.g. Comic Sans MS).
        Debe responder 400 INVALID_CONFIG.
        """
        upload_resp = self.client.post(
            "/api/documents/",
            {"file": self._get_valid_uploaded_file()},
            format="multipart",
        )
        doc_id = upload_resp.data["document_id"]

        invalid_config = {
            "preset_id": "apa7",
            "font_family": "Comic Sans MS",
        }

        response = self.client.post(
            f"/api/documents/{doc_id}/format/",
            invalid_config,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data.get("error"), "INVALID_CONFIG")

    def test_format_nonexistent_document_returns_404(self):
        """
        Intentar formatear un document_id inexistente debe responder 404 NOT_FOUND.
        """
        response = self.client.post(
            "/api/documents/999999/format/",
            {"preset_id": "apa7"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data.get("error"), "NOT_FOUND")

    # -------------------------------------------------------------------------
    # 5) Tests de descarga: id inexistente responde 404 y descarga antes de
    #    formatear responde 409.
    # -------------------------------------------------------------------------
    def test_download_nonexistent_id_returns_404(self):
        """
        Intentar descargar un documento inexistente debe responder 404 NOT_FOUND.
        """
        response = self.client.get("/api/documents/999999/download/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data.get("error"), "NOT_FOUND")

    def test_download_before_formatting_returns_409(self):
        """
        Intentar descargar un documento que aún no ha sido formateado (status='pending')
        debe responder 409 NOT_READY.
        """
        upload_resp = self.client.post(
            "/api/documents/",
            {"file": self._get_valid_uploaded_file()},
            format="multipart",
        )
        doc_id = upload_resp.data["document_id"]

        response = self.client.get(f"/api/documents/{doc_id}/download/")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data.get("error"), "NOT_READY")

    # -------------------------------------------------------------------------
    # 6) Test de flujo completo: carga → formateo → consulta de estado done →
    #    descarga → abrir los bytes con python-docx y verificar margen y fuente.
    # -------------------------------------------------------------------------
    def test_complete_flow_upload_format_status_download_and_verify(self):
        """
        Flujo completo:
        1. Carga del documento (POST /api/documents/) -> 201 Created
        2. Formateo (POST /api/documents/{id}/format/) con márgenes y fuente específicos -> 200 OK
        3. Consulta de estado (GET /api/documents/{id}/) -> 200 OK y status 'done'
        4. Descarga (GET /api/documents/{id}/download/) -> 200 OK archivo binario DOCX
        5. Abrir bytes descargados con python-docx y verificar márgenes y fuente aplicada
        """
        # 1. Carga
        uploaded_file = self._get_valid_uploaded_file()
        upload_resp = self.client.post(
            "/api/documents/",
            {"file": uploaded_file},
            format="multipart",
        )
        self.assertEqual(upload_resp.status_code, status.HTTP_201_CREATED)
        doc_id = upload_resp.data["document_id"]
        job_id = upload_resp.data["job_id"]
        self.assertIsNotNone(doc_id)
        self.assertIsNotNone(job_id)

        # 2. Formateo con márgenes de 3.0 cm y fuente Arial de 12 pt
        target_margin = 3.0
        target_font = "Arial"
        format_config = {
            "preset_id": "apa7",
            "margins_cm": {
                "top": target_margin,
                "bottom": target_margin,
                "left": target_margin,
                "right": target_margin,
            },
            "font_family": target_font,
            "font_size_pt": 12,
            "line_spacing": 1.5,
        }
        format_resp = self.client.post(
            f"/api/documents/{doc_id}/format/",
            format_config,
            format="json",
        )
        self.assertEqual(format_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(format_resp.data.get("status"), "done")

        # 3. Consulta de estado
        status_resp = self.client.get(f"/api/documents/{doc_id}/")
        self.assertEqual(status_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(status_resp.data.get("status"), "done")
        self.assertEqual(status_resp.data.get("document_id"), doc_id)
        self.assertEqual(
            status_resp.data.get("download_url"),
            f"/api/documents/{doc_id}/download/",
        )

        # 4. Descarga del documento resultante
        download_resp = self.client.get(f"/api/documents/{doc_id}/download/")
        self.assertEqual(download_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(
            download_resp["Content-Type"],
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        self.assertIn("01_planos_formateado.docx", download_resp["Content-Disposition"])

        if hasattr(download_resp, "streaming_content"):
            download_bytes = b"".join(download_resp.streaming_content)
        else:
            download_bytes = download_resp.content

        self.assertGreater(len(download_bytes), 0)

        # 5. Abrir los bytes con python-docx
        result_doc = DocxDocument(io.BytesIO(download_bytes))
        self.assertIsNotNone(result_doc)

        # 6. Verificar margen y fuente
        # Verificar márgenes en todas las secciones
        self.assertGreater(len(result_doc.sections), 0)
        for i, section in enumerate(result_doc.sections):
            self.assertEqual(
                round(section.top_margin.cm, 2),
                target_margin,
                f"Sección {i} top_margin incorrecto",
            )
            self.assertEqual(
                round(section.bottom_margin.cm, 2),
                target_margin,
                f"Sección {i} bottom_margin incorrecto",
            )
            self.assertEqual(
                round(section.left_margin.cm, 2),
                target_margin,
                f"Sección {i} left_margin incorrecto",
            )
            self.assertEqual(
                round(section.right_margin.cm, 2),
                target_margin,
                f"Sección {i} right_margin incorrecto",
            )

        # Verificar fuente en el estilo Normal y en los runs
        self.assertEqual(result_doc.styles["Normal"].font.name, target_font)
        self.assertGreater(len(result_doc.paragraphs), 0)
        for p in result_doc.paragraphs:
            for run in p.runs:
                if run.text.strip():
                    self.assertEqual(
                        run.font.name,
                        target_font,
                        f"Run con texto '{run.text}' no tiene la fuente configurada",
                    )

    # -------------------------------------------------------------------------
    # 7) Test de listado de plantillas / presets (S3T1)
    # -------------------------------------------------------------------------
    def test_list_templates_returns_contract_presets(self):
        """
        Valida que GET /api/templates/ devuelva {"presets": [...]}
        con la estructura completa según api-contract.md.
        """
        response = self.client.get("/api/templates/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("presets", response.data)

        presets = response.data["presets"]
        self.assertEqual(len(presets), 3)

        preset_ids = [p["id"] for p in presets]
        self.assertEqual(preset_ids, ["apa7", "reporte", "personalizado"])

        for preset in presets:
            self.assertIn("id", preset)
            self.assertIn("name", preset)
            self.assertIn("description", preset)
            self.assertIn("config", preset)
            config = preset["config"]
            self.assertIn("margins_cm", config)
            self.assertIn("font_family", config)
            self.assertIn("font_size_pt", config)
            self.assertIn("line_spacing", config)
            self.assertIn("heading_sizes_pt", config)

    # -------------------------------------------------------------------------
    # 8) Tests S3T20: Endpoints de estructuración con IA, estructura y revisión
    # -------------------------------------------------------------------------
    def _upload_fixture(self, fixture_name: str) -> int:
        fixture_path = FIXTURES_DIR / fixture_name
        with open(fixture_path, "rb") as f:
            uploaded = SimpleUploadedFile(
                fixture_name,
                f.read(),
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        resp = self.client.post("/api/documents/", {"file": uploaded}, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        return resp.data["document_id"]

    def test_structure_and_review_require_review_state_else_409(self):
        """
        GET /structure/ y POST /review/ deben responder 409 INVALID_STATE
        si el job está en pending, processing, done o error.
        También download debe responder 409 NOT_READY en review/processing/pending/error.
        """
        doc_id = self._upload_fixture("01_planos.docx")
        job = ProcessingJob.objects.filter(document_id=doc_id).last()

        for non_review_state in ("pending", "processing", "done", "error"):
            ProcessingJob.objects.filter(pk=job.pk).update(status=non_review_state)

            struct_resp = self.client.get(f"/api/documents/{doc_id}/structure/")
            self.assertEqual(struct_resp.status_code, status.HTTP_409_CONFLICT)
            self.assertEqual(struct_resp.data.get("error"), "INVALID_STATE")

            rev_resp = self.client.post(
                f"/api/documents/{doc_id}/review/",
                {"action": "accept", "revert": []},
                format="json",
            )
            self.assertEqual(rev_resp.status_code, status.HTTP_409_CONFLICT)
            self.assertEqual(rev_resp.data.get("error"), "INVALID_STATE")

            if non_review_state != "done":
                dl_resp = self.client.get(f"/api/documents/{doc_id}/download/")
                self.assertEqual(dl_resp.status_code, status.HTTP_409_CONFLICT)
                self.assertEqual(dl_resp.data.get("error"), "NOT_READY")

    def test_structure_and_review_404_for_nonexistent_document(self):
        struct_resp = self.client.get("/api/documents/999999/structure/")
        self.assertEqual(struct_resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(struct_resp.data.get("error"), "NOT_FOUND")

        rev_resp = self.client.post(
            "/api/documents/999999/review/",
            {"action": "accept"},
            format="json",
        )
        self.assertEqual(rev_resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(rev_resp.data.get("error"), "NOT_FOUND")

    def test_review_validation_errors_keep_job_in_review(self):
        """
        Validar que POST /review/ con action inválida o IDs en revert inexistentes
        responda 400 INVALID_CONFIG y deje el job en estado 'review'.
        """
        doc_id = self._upload_fixture("02_headings_mixto.docx")
        with self.captureOnCommitCallbacks(execute=True):
            fmt_resp = self.client.post(
                f"/api/documents/{doc_id}/format/",
                {"preset_id": "reporte", "use_ai": True},
                format="json",
            )
        self.assertEqual(fmt_resp.status_code, status.HTTP_202_ACCEPTED)

        # En modo sync, tras ejecutarse el callback on_commit el job ya llegó a 'review'
        status_resp = self.client.get(f"/api/documents/{doc_id}/")
        self.assertEqual(status_resp.data["status"], "review")

        # 1. Acción inválida
        bad_action = self.client.post(
            f"/api/documents/{doc_id}/review/",
            {"action": "invalid_action"},
            format="json",
        )
        self.assertEqual(bad_action.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(bad_action.data.get("error"), "INVALID_CONFIG")

        # 2. ID de revert inexistente
        bad_revert = self.client.post(
            f"/api/documents/{doc_id}/review/",
            {"action": "accept", "revert": ["id_que_no_existe_999"]},
            format="json",
        )
        self.assertEqual(bad_revert.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(bad_revert.data.get("error"), "INVALID_CONFIG")

        # 3. Tipo inválido en revert
        bad_revert_type = self.client.post(
            f"/api/documents/{doc_id}/review/",
            {"action": "accept", "revert": "b0"},
            format="json",
        )
        self.assertEqual(bad_revert_type.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(bad_revert_type.data.get("error"), "INVALID_CONFIG")

        # El job sigue en 'review' y aún no permite descarga (409 NOT_READY)
        still_review = self.client.get(f"/api/documents/{doc_id}/")
        self.assertEqual(still_review.data["status"], "review")
        dl_before = self.client.get(f"/api/documents/{doc_id}/download/")
        self.assertEqual(dl_before.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(dl_before.data.get("error"), "NOT_READY")

    def test_ai_flow_accept_and_revert_across_fixtures_01_02_05(self):
        """
        Flujo completo v1.1 con FakeProvider sobre los fixtures 01_planos.docx,
        02_headings_mixto.docx y 05_listas.docx:
        upload -> format(use_ai=True) 202 -> status(review) -> structure 200 ->
        review(accept con revert) 200 -> status(done) -> download 200.
        """
        for fixture_name in ("01_planos.docx", "02_headings_mixto.docx", "05_listas.docx"):
            doc_id = self._upload_fixture(fixture_name)

            # 1. Iniciar formateo con IA -> 202 Accepted
            with self.captureOnCommitCallbacks(execute=True):
                fmt_resp = self.client.post(
                    f"/api/documents/{doc_id}/format/",
                    {
                        "preset_id": "reporte",
                        "use_ai": True,
                        "ai": {
                            "document_type": "reporte",
                            "detect_headings": True,
                            "detect_lists": True,
                            "detect_tables": True,
                            "emphasis": "light",
                        },
                    },
                    format="json",
                )
            self.assertEqual(fmt_resp.status_code, status.HTTP_202_ACCEPTED)
            self.assertEqual(fmt_resp.data["status"], "processing")
            self.assertEqual(fmt_resp.data["document_id"], doc_id)

            # 2. Consultar estado -> 'review' con progress, ai_summary y error_code=None
            st_resp = self.client.get(f"/api/documents/{doc_id}/")
            self.assertEqual(st_resp.status_code, status.HTTP_200_OK)
            self.assertEqual(st_resp.data["status"], "review")
            self.assertIsNotNone(st_resp.data["progress"])
            self.assertIn("stage", st_resp.data["progress"])
            self.assertIn("done", st_resp.data["progress"])
            self.assertIn("total", st_resp.data["progress"])
            self.assertIsNotNone(st_resp.data["ai_summary"])
            self.assertIsNone(st_resp.data["error_code"])
            self.assertIsNone(st_resp.data["download_url"])

            # 3. Consultar estructura en 'review' -> 200 OK
            struct_resp = self.client.get(f"/api/documents/{doc_id}/structure/")
            self.assertEqual(struct_resp.status_code, status.HTTP_200_OK)
            self.assertEqual(struct_resp.data["document_id"], doc_id)
            self.assertEqual(struct_resp.data["status"], "review")
            self.assertEqual(struct_resp.data["original"]["schema_version"], "di.v1")
            self.assertEqual(struct_resp.data["proposed"]["schema_version"], "di.v1")
            self.assertGreater(len(struct_resp.data["original"]["blocks"]), 0)
            self.assertGreater(len(struct_resp.data["proposed"]["blocks"]), 0)
            self.assertIn("revertible_blocks", struct_resp.data["summary"])

            revertible = struct_resp.data["summary"]["revertible_blocks"]
            revert_selection = [revertible[0]] if revertible else []

            # 4. Confirmar revisión (accept) -> 200 OK
            rev_resp = self.client.post(
                f"/api/documents/{doc_id}/review/",
                {"action": "accept", "revert": revert_selection},
                format="json",
            )
            self.assertEqual(rev_resp.status_code, status.HTTP_200_OK)
            self.assertEqual(rev_resp.data["status"], "done")
            self.assertEqual(rev_resp.data["action"], "accept")
            self.assertIn("summary", rev_resp.data)
            self.assertIn("headings_applied", rev_resp.data["summary"])
            self.assertIn("lists_applied", rev_resp.data["summary"])
            self.assertIn("tables_applied", rev_resp.data["summary"])
            self.assertEqual(
                rev_resp.data["summary"]["reverted_blocks_count"],
                len(revert_selection),
            )
            self.assertEqual(
                rev_resp.data["download_url"],
                f"/api/documents/{doc_id}/download/",
            )
            self.assertIsNotNone(rev_resp.data["finished_at"])

            # 5. Descargar documento final -> 200 OK y verificar apertura con python-docx
            dl_resp = self.client.get(f"/api/documents/{doc_id}/download/")
            self.assertEqual(dl_resp.status_code, status.HTTP_200_OK)
            dl_bytes = (
                b"".join(dl_resp.streaming_content)
                if hasattr(dl_resp, "streaming_content")
                else dl_resp.content
            )
            reopened = DocxDocument(io.BytesIO(dl_bytes))
            self.assertGreater(len(reopened.paragraphs), 0)

    def test_ai_flow_reject_runs_sprint2_template_only(self):
        """
        Valida que POST /api/documents/{id}/review/ con {"action": "reject"}
        descarte la propuesta de IA, ejecute el flujo de solo plantilla del Sprint 2
        y deje el documento listo para descarga en estado 'done'.
        """
        doc_id = self._upload_fixture("02_headings_mixto.docx")
        with self.captureOnCommitCallbacks(execute=True):
            fmt_resp = self.client.post(
                f"/api/documents/{doc_id}/format/",
                {"preset_id": "apa7", "use_ai": True},
                format="json",
            )
        self.assertEqual(fmt_resp.status_code, status.HTTP_202_ACCEPTED)

        rev_resp = self.client.post(
            f"/api/documents/{doc_id}/review/",
            {"action": "reject"},
            format="json",
        )
        self.assertEqual(rev_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(rev_resp.data["status"], "done")
        self.assertEqual(rev_resp.data["action"], "reject")
        self.assertEqual(
            rev_resp.data["summary"],
            {
                "headings_applied": 0,
                "lists_applied": 0,
                "tables_applied": 0,
                "reverted_blocks_count": 0,
            },
        )
        self.assertEqual(rev_resp.data["download_url"], f"/api/documents/{doc_id}/download/")

        dl_resp = self.client.get(f"/api/documents/{doc_id}/download/")
        self.assertEqual(dl_resp.status_code, status.HTTP_200_OK)
        dl_bytes = (
            b"".join(dl_resp.streaming_content)
            if hasattr(dl_resp, "streaming_content")
            else dl_resp.content
        )
        result_doc = DocxDocument(io.BytesIO(dl_bytes))
        self.assertEqual(result_doc.styles["Normal"].font.name, "Times New Roman")


