from django.test import SimpleTestCase
from rest_framework.test import APIClient
from templates_engine.config import list_presets, load_preset, list_preset_ids, TemplateConfig


class TemplatesEngineConfigTests(SimpleTestCase):
    def test_list_preset_ids(self):
        ids = list_preset_ids()
        self.assertEqual(ids, ["apa7", "reporte", "personalizado"])

    def test_list_presets_structure(self):
        presets = list_presets()
        self.assertEqual(len(presets), 3)
        
        apa7 = presets[0]
        self.assertEqual(apa7["id"], "apa7")
        self.assertEqual(apa7["name"], "Formato académico (APA 7)")
        self.assertIn("Times New Roman", apa7["description"])
        self.assertEqual(apa7["config"]["font_family"], "Times New Roman")
        self.assertEqual(apa7["config"]["font_size_pt"], 12)
        self.assertEqual(apa7["config"]["line_spacing"], 2.0)
        self.assertEqual(apa7["config"]["margins_cm"], {"top": 2.54, "bottom": 2.54, "left": 2.54, "right": 2.54})
        self.assertEqual(apa7["config"]["heading_sizes_pt"], {"h1": 12, "h2": 12, "h3": 12})

        reporte = presets[1]
        self.assertEqual(reporte["id"], "reporte")
        self.assertEqual(reporte["name"], "Reporte ejecutivo")
        self.assertEqual(reporte["config"]["font_family"], "Calibri")
        self.assertEqual(reporte["config"]["font_size_pt"], 11)
        self.assertEqual(reporte["config"]["line_spacing"], 1.15)
        self.assertEqual(reporte["config"]["margins_cm"], {"top": 2.5, "bottom": 2.5, "left": 2.5, "right": 2.5})
        self.assertEqual(reporte["config"]["heading_sizes_pt"], {"h1": 16, "h2": 14, "h3": 12})

        personalizado = presets[2]
        self.assertEqual(personalizado["id"], "personalizado")
        self.assertEqual(personalizado["name"], "Personalizado")
        self.assertEqual(personalizado["config"]["font_family"], "Calibri")
        self.assertEqual(personalizado["config"]["font_size_pt"], 11)
        self.assertEqual(personalizado["config"]["line_spacing"], 1.15)
        self.assertEqual(personalizado["config"]["margins_cm"], {"top": 2.54, "bottom": 2.54, "left": 2.54, "right": 2.54})
        self.assertIsNone(personalizado["config"]["heading_sizes_pt"])

    def test_load_preset(self):
        config_apa7 = load_preset("apa7")
        self.assertIsInstance(config_apa7, TemplateConfig)
        self.assertEqual(config_apa7.font_name, "Times New Roman")
        self.assertEqual(config_apa7.font_size, 12)
        self.assertEqual(config_apa7.line_spacing, 2.0)
        self.assertEqual(config_apa7.margin_top, 2.54)
        self.assertEqual(config_apa7.heading_sizes, {"h1": 12, "h2": 12, "h3": 12})

        config_reporte = load_preset("reporte")
        self.assertEqual(config_reporte.font_name, "Calibri")
        self.assertEqual(config_reporte.font_size, 11)
        self.assertEqual(config_reporte.margin_top, 2.5)
        self.assertEqual(config_reporte.heading_sizes, {"h1": 16, "h2": 14, "h3": 12})

        config_personalizado = load_preset("personalizado")
        self.assertEqual(config_personalizado.font_name, "Calibri")
        self.assertIsNone(config_personalizado.heading_sizes)


class TemplatesEndpointAPITests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()

    def test_get_templates_contract(self):
        response = self.client.get('/api/templates/')
        self.assertEqual(response.status_code, 200)
        self.assertIn("presets", response.data)
        
        presets = response.data["presets"]
        self.assertEqual(len(presets), 3)
        self.assertEqual([p["id"] for p in presets], ["apa7", "reporte", "personalizado"])

        for preset in presets:
            self.assertIn("id", preset)
            self.assertIn("name", preset)
            self.assertIn("description", preset)
            self.assertIn("config", preset)
            cfg = preset["config"]
            self.assertIn("margins_cm", cfg)
            self.assertIn("top", cfg["margins_cm"])
            self.assertIn("bottom", cfg["margins_cm"])
            self.assertIn("left", cfg["margins_cm"])
            self.assertIn("right", cfg["margins_cm"])
            self.assertIn("font_family", cfg)
            self.assertIn("font_size_pt", cfg)
            self.assertIn("line_spacing", cfg)
            self.assertIn("heading_sizes_pt", cfg)

    def test_get_documents_templates_route(self):
        response = self.client.get('/api/documents/templates/')
        self.assertEqual(response.status_code, 200)
        self.assertIn("presets", response.data)
