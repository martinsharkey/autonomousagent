import requests
from bs4 import BeautifulSoup
from typing import Optional

class WebScraper:
    """A simple web scraper that fetches and extracts text content from a URL."""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; AlphaCouncil/1.0; +https://alphacouncil.ai)"
        })

    def fetch_text(self, url: str) -> Optional[str]:
        """Fetch the URL and return the visible text content."""
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            text = soup.get_text(separator="\n", strip=True)
            # Collapse multiple newlines
            lines = [line for line in text.split("\n") if line]
            return "\n".join(lines)
        except Exception as e:
            return f"Error fetching {url}: {e}"

    def fetch_structured(self, url: str) -> Optional[dict]:
        """Fetch the URL and return structured data: title, text, links."""
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            title = soup.title.string.strip() if soup.title else None
            for script in soup(["script", "style"]):
                script.decompose()
            text = soup.get_text(separator="\n", strip=True)
            lines = [line for line in text.split("\n") if line]
            links = [a.get("href") for a in soup.find_all("a", href=True)]
            return {
                "title": title,
                "text": "\n".join(lines),
                "links": links[:50]  # limit to first 50 links
            }
        except Exception as e:
            return {"error": f"Error fetching {url}: {e}"}
