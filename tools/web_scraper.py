import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any
import time

class WebScraper:
    """A simple, robust web scraper with retry logic and rate limiting."""
    
    def __init__(self, user_agent: str = "CouncilBot/1.0", timeout: int = 10, max_retries: int = 3):
        self.user_agent = user_agent
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})
    
    def fetch_html(self, url: str, retry_delay: float = 1.0) -> Optional[str]:
        """Fetch HTML content from a URL with retry logic."""
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                return response.text
            except requests.RequestException as e:
                if attempt < self.max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                else:
                    return None
        return None
    
    def extract_text(self, html: str, selector: Optional[str] = None) -> str:
        """Extract text from HTML, optionally using a CSS selector."""
        soup = BeautifulSoup(html, "html.parser")
        if selector:
            elements = soup.select(selector)
            return "\n".join(el.get_text(strip=True) for el in elements)
        return soup.get_text(separator="\n", strip=True)
    
    def scrape(self, url: str, selector: Optional[str] = None) -> Dict[str, Any]:
        """Scrape a URL and return structured result."""
        html = self.fetch_html(url)
        if html is None:
            return {"success": False, "error": "Failed to fetch URL after retries"}
        text = self.extract_text(html, selector)
        return {"success": True, "text": text, "url": url}
