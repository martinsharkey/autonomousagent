import unittest
from tools.web_scraper import WebScraper

class TestWebScraper(unittest.TestCase):
    def setUp(self):
        self.scraper = WebScraper(timeout=5)

    def test_fetch_invalid_url(self):
        result = self.scraper.fetch("https://nonexistent.example.com")
        self.assertIsNone(result)

    def test_parse_text_empty(self):
        text = self.scraper.parse_text("<html></html>")
        self.assertEqual(text, "")

    def test_parse_text_with_content(self):
        html = "<html><body><p>Hello World</p></body></html>"
        text = self.scraper.parse_text(html)
        self.assertIn("Hello World", text)

if __name__ == "__main__":
    unittest.main()
