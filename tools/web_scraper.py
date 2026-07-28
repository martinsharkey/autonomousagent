import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any

class WebScraper:
    """Lightweight web scraper for fetching and parsing HTML content."""
    
    def __init__(self, timeout: int = 10, user_agent: Optional[str] = None):
        self.timeout = timeout
        self.user_agent = user_agent or "Mozilla/5.0 (compatible; Autobot/1.0)"
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})
    
    def fetch_text(self, url: str) -> Optional[str]:
        """Fetch and return the visible text content of a webpage."""
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            return soup.get_text(separator="\n", strip=True)
        except Exception as e:
            print(f"WebScraper error fetching {url}: {e}")
            return None
    
    def fetch_soup(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and return the BeautifulSoup object for advanced parsing."""
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return BeautifulSoup(response.text, "html.parser")
        except Exception as e:
            print(f"WebScraper error fetching {url}: {e}")
            return None
    
    def close(self):
        self.session.close()
