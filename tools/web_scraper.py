import requests
from bs4 import BeautifulSoup
from typing import Optional

def fetch_web_content(url: str, timeout: int = 10) -> Optional[str]:
    """
    Fetch and extract readable text content from a given URL.
    Returns the extracted text as a string, or None on failure.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        text = soup.get_text(separator="\n", strip=True)
        # Collapse multiple newlines
        lines = [line for line in text.splitlines() if line.strip()]
        return "\n".join(lines)
    except Exception as e:
        print(f"Web scraping error for {url}: {e}")
        return None
