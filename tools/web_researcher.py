import requests
from bs4 import BeautifulSoup
import re
import json
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

class WebResearcher:
    """Autonomous web research tool for gathering, validating, and synthesizing information."""

    def __init__(self, user_agent: str = "Mozilla/5.0 (compatible; WebResearcher/1.0)",
                 max_depth: int = 2,
                 max_pages: int = 10,
                 timeout: int = 10):
        self.user_agent = user_agent
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})

    def _is_valid_url(self, url: str) -> bool:
        """Check if a URL is valid and safe to scrape."""
        parsed = urlparse(url)
        return all([parsed.scheme in ["http", "https"], parsed.netloc])

    def _normalize_url(self, base_url: str, link: str) -> Optional[str]:
        """Normalize a URL relative to a base URL."""
        if not link:
            return None
        if link.startswith("http"):
            return link
        return urljoin(base_url, link)

    def _fetch_page(self, url: str) -> Optional[str]:
        """Fetch a single web page."""
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")
            return None

    def _extract_links(self, html: str, base_url: str) -> List[str]:
        """Extract all valid links from HTML content."""
        soup = BeautifulSoup(html, "html.parser")
        links = set()
        for link in soup.find_all("a", href=True):
            normalized = self._normalize_url(base_url, link["href"])
            if normalized and self._is_valid_url(normalized):
                links.add(normalized)
        return list(links)

    def _extract_main_content(self, html: str) -> str:
        """Extract the main content from a web page."""
        soup = BeautifulSoup(html, "html.parser")
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "aside"]):
            script.decompose()
        # Get text from the main content
        text = soup.get_text(separator=" ", strip=True)
        # Clean up excessive whitespace
        text = re.sub(r"\s+", " ", text)
        return text

    def _validate_source(self, url: str) -> bool:
        """Basic validation of a source URL."""
        domain = urlparse(url).netloc
        # Block known problematic domains
        blocked_domains = ["example.com", "test.com"]
        return domain not in blocked_domains

    def research(self, query: str, start_urls: Optional[List[str]] = None) -> Dict:
        """
        Perform autonomous web research on a given query.

        Args:
            query: The research query to investigate
            start_urls: Optional list of starting URLs to seed the research

        Returns:
            Dictionary containing research results, sources, and metadata
        """
        results = {
            "query": query,
            "sources": [],
            "content": [],
            "summary": "",
            "metadata": {
                "pages_visited": 0,
                "depth_reached": 0,
                "timestamp": None
            }
        }

        if not start_urls:
            # Default seed URLs based on query
            start_urls = [
                f"https://www.google.com/search?q={query.replace(' ', '+')}",
                f"https://en.wikipedia.org/wiki/{query.replace(' ', '_')}",
                f"https://www.reddit.com/search/?q={query.replace(' ', '+')}"
            ]

        visited = set()
        to_visit = [(url, 0) for url in start_urls if self._validate_source(url)]
        results["metadata"]["timestamp"] = str(datetime.datetime.now())

        while to_visit and len(visited) < self.max_pages:
            current_url, depth = to_visit.pop(0)

            if current_url in visited or depth > self.max_depth:
                continue

            visited.add(current_url)
            results["metadata"]["pages_visited"] += 1
            results["metadata"]["depth_reached"] = max(results["metadata"]["depth_reached"], depth)

            html = self._fetch_page(current_url)
            if not html:
                continue

            # Extract and store content
            content = self._extract_main_content(html)
            if content:
                results["content"].append({
                    "url": current_url,
                    "content": content,
                    "length": len(content)
                })

            # Extract links for further exploration
            links = self._extract_links(html, current_url)
            for link in links:
                if link not in visited and len(visited) < self.max_pages:
                    to_visit.append((link, depth + 1))

        # Generate a simple summary
        if results["content"]:
            combined_content = " ".join([c["content"] for c in results["content"]])
            results["summary"] = combined_content[:2000] + "..." if len(combined_content) > 2000 else combined_content

        return results

    def validate_facts(self, statements: List[str], sources: Optional[List[str]] = None) -> Dict:
        """
        Validate a list of factual statements against web sources.

        Args:
            statements: List of statements to validate
            sources: Optional list of source URLs to prioritize

        Returns:
            Dictionary with validation results for each statement
        """
        validation_results = {}

        for statement in statements:
            # Simple keyword-based validation for now
            # In a real implementation, this would use more sophisticated methods
            keywords = statement.lower().split()
            search_query = f"{' '.join(keywords)} fact check"

            research = self.research(search_query, sources)
            validation_results[statement] = {
                "research_results": research,
                "likely_true": any(keyword in research.get("summary", "").lower() for keyword in keywords),
                "confidence": 0.7  # Placeholder
            }

        return validation_results