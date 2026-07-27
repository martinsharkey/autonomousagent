import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any

class WebScraper:
    """A simple web scraper for fetching and parsing HTML content."""

    def __init__(self, timeout: int = 10, user_agent: str = "Mozilla/5.0 (compatible; Autobot/1.0)"):
        self.timeout = timeout
        self.headers = {"User-Agent": user_agent}

    def fetch(self, url: str) -> Optional[str]:
        """Fetch raw HTML from a URL."""
        try:
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"WebScraper fetch error: {e}")
            return None

    def parse_text(self, html: str) -> str:
        """Extract visible text from HTML."""
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)

    def scrape(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape a URL and return structured content."""
        html = self.fetch(url)
        if html is None:
            return None
        text = self.parse_text(html)
        return {"url": url, "content": text, "length": len(text)}
