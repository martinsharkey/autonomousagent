import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any

class WebScraper:
    """Lightweight, provider-agnostic web scraper for autonomous data collection."""

    def __init__(self, timeout: int = 10, user_agent: Optional[str] = None):
        self.timeout = timeout
        self.user_agent = user_agent or "Mozilla/5.0 (compatible; BetaWorker/1.0)"
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})

    def fetch_html(self, url: str) -> Optional[str]:
        """Fetch raw HTML from a URL."""
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"[WebScraper] Error fetching {url}: {e}")
            return None

    def extract_text(self, url: str) -> Optional[str]:
        """Fetch and extract readable text from a URL."""
        html = self.fetch_html(url)
        if html is None:
            return None
        soup = BeautifulSoup(html, "html.parser")
        for tag in ["script", "style", "nav", "footer", "header"]:
            for element in soup.find_all(tag):
                element.decompose()
        return soup.get_text(separator="\n", strip=True)

    def extract_links(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch and extract all links from a URL."""
        html = self.fetch_html(url)
        if html is None:
            return None
        soup = BeautifulSoup(html, "html.parser")
        links = []
        for a in soup.find_all("a", href=True):
            links.append({"text": a.get_text(strip=True), "href": a["href"]})
        return {"url": url, "links": links}

    def close(self):
        self.session.close()
