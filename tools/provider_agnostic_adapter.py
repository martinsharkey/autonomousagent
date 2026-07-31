import json
import re
from typing import Any, Dict, List, Optional

class ProviderAgnosticAdapter:
    """Normalize prompts and responses across LLM providers."""

    # Common prompt formatting differences
    PROMPT_NORMALIZERS = {
        'anthropic': lambda p: p,  # Anthropic uses similar format
        'openai': lambda p: p,
        'google': lambda p: p,  # Gemini uses similar
        'cohere': lambda p: p,
    }

    # Response extraction patterns for different providers
    RESPONSE_EXTRACTORS = {
        'anthropic': lambda r: r.get('content', [{}])[0].get('text', ''),
        'openai': lambda r: r.get('choices', [{}])[0].get('message', {}).get('content', ''),
        'google': lambda r: r.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', ''),
        'cohere': lambda r: r.get('text', ''),
    }

    def __init__(self, provider: str):
        self.provider = provider.lower()
        if self.provider not in self.PROMPT_NORMALIZERS:
            raise ValueError(f"Unsupported provider: {provider}")

    def normalize_prompt(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Convert a standard prompt into provider-specific format."""
        # Ensure system prompt is included consistently
        if system_prompt:
            prompt = f"{system_prompt}\n\n{prompt}"
        # Apply provider-specific normalization (placeholder for future)
        normalized = self.PROMPT_NORMALIZERS[self.provider](prompt)
        return {"prompt": normalized}

    def adapt_response(self, response: Dict[str, Any]) -> str:
        """Extract text content from provider-specific response format."""
        extractor = self.RESPONSE_EXTRACTORS.get(self.provider)
        if not extractor:
            raise ValueError(f"No extractor for provider: {self.provider}")
        try:
            text = extractor(response)
            return text.strip() if text else ""
        except (KeyError, IndexError, TypeError):
            # Fallback: try to find any text-like field
            return self._fallback_extract(response)

    def _fallback_extract(self, response: Any) -> str:
        """Attempt to extract text from unknown response structures."""
        if isinstance(response, str):
            return response
        if isinstance(response, dict):
            for key in ['text', 'content', 'message', 'output']:
                if key in response:
                    val = response[key]
                    if isinstance(val, str):
                        return val
                    if isinstance(val, list) and val:
                        return self._fallback_extract(val[0])
                    if isinstance(val, dict):
                        return self._fallback_extract(val)
        if isinstance(response, list) and response:
            return self._fallback_extract(response[0])
        return ""

    @staticmethod
    def detect_provider(response: Dict[str, Any]) -> Optional[str]:
        """Heuristically detect provider from response structure."""
        if 'choices' in response:
            return 'openai'
        if 'content' in response and isinstance(response['content'], list):
            return 'anthropic'
        if 'candidates' in response:
            return 'google'
        if 'text' in response:
            return 'cohere'
        return None

    @staticmethod
    def standardize_response(response: Dict[str, Any]) -> Dict[str, Any]:
        """Convert any provider response to a unified format."""
        provider = ProviderAgnosticAdapter.detect_provider(response)
        if not provider:
            return {"text": str(response), "provider": "unknown"}
        adapter = ProviderAgnosticAdapter(provider)
        text = adapter.adapt_response(response)
        return {"text": text, "provider": provider}
