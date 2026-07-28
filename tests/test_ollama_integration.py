import unittest
from tools.ollama_adapter import OllamaAdapter

class TestOllamaIntegration(unittest.TestCase):
    def setUp(self):
        self.adapter = OllamaAdapter()

    def test_health_check(self):
        self.assertTrue(self.adapter.health_check())

    def test_model_listing(self):
        models = self.adapter.list_models()
        self.assertIsNotNone(models)
        self.assertIn("models", models)

if __name__ == "__main__":
    unittest.main()