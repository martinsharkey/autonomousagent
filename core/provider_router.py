from tools.ollama_adapter import OllamaAdapter

class ProviderRouter:
    def __init__(self):
        self.ollama = OllamaAdapter()
        # ... existing provider initializations ...

    def get_provider(self, provider_name: str):
        if provider_name == "ollama":
            return self.ollama
        # ... existing provider checks ...
        return None