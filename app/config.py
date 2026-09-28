import os
from pathlib import Path
from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(ENV_PATH, override=True)


# Supported providers and their default base URLs
PROVIDER_DEFAULTS = {
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "model": "llama3.1:8b",
        "api_key": "ollama",
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.1-8b-instant",
        "api_key": "",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model": "gemini-2.0-flash-lite",
        "api_key": "",
    },
    "lmstudio": {
        "base_url": "http://localhost:1234/v1",
        "model": "local-model",
        "api_key": "lm-studio",
    },
    "huggingface": {
        "base_url": "https://api-inference.huggingface.co/v1",
        "model": "mistralai/Mistral-7B-Instruct-v0.3",
        "api_key": "",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "api_key": "",
    },
}

# Max tokens per domain — controls response length and speed
DOMAIN_MAX_TOKENS = {
    "code_generator": 2048,
    "test_engineer": 2048,
    "doc_analyzer": 1024,
    "data_analytics": 2048,
    "general_qa": 512,
    "router": 32,
}

# Registry of 5 domain-specific AI models
MODEL_DOMAINS = {
    "code_generator": {
        "name": "Code Generator",
        "description": "Generates production-quality code from software specifications and requirements",
        "icon": "code",
        "keywords": ["code", "function", "class", "implement", "build", "create", "program", "script",
                     "api", "endpoint", "module", "library", "generate code", "develop", "software"],
    },
    "test_engineer": {
        "name": "Test Engineer",
        "description": "Creates test specifications, generates pytest test cases, and executes them with full reports",
        "icon": "flask-conical",
        "keywords": ["test", "testing", "unittest", "pytest", "qa", "quality", "verify", "validate",
                     "test case", "test spec", "coverage", "bug", "regression", "assert"],
    },
    "doc_analyzer": {
        "name": "Document Analyzer",
        "description": "Analyzes technical documents, extracts insights, generates summaries and key findings",
        "icon": "file-text",
        "keywords": ["document", "analyze", "summary", "summarize", "extract", "insight", "report",
                     "review", "explain", "understand", "describe", "documentation", "spec", "requirement"],
    },
    "data_analytics": {
        "name": "Data Analytics",
        "description": "Generates data analysis code, statistical insights, and visualization scripts from data descriptions",
        "icon": "bar-chart-3",
        "keywords": ["data", "analytics", "analysis", "chart", "graph", "visualize", "statistics",
                     "csv", "dataframe", "pandas", "plot", "metric", "trend", "dashboard", "dataset"],
    },
    "general_qa": {
        "name": "General Q&A",
        "description": "Answers general questions, provides information, explanations, and conversational responses",
        "icon": "message-circle",
        "keywords": ["who", "what", "when", "where", "why", "how", "explain", "tell me", "what is",
                     "who is", "define", "meaning", "question", "answer", "help", "info", "information"],
    },
}


class Settings:
    def __init__(self):
        load_dotenv(ENV_PATH, override=True)
        self.LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama").lower()
        self.LLM_MODEL: str = os.getenv("LLM_MODEL", "")
        self.LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "")
        self.LLM_API_KEY: str = os.getenv("LLM_API_KEY", os.getenv("OPENAI_API_KEY", ""))
        self.DEMO_MODE: bool = os.getenv("DEMO_MODE", "false").lower() == "true"
        self.OUTPUT_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs")
        # Fallback chain: try providers in order if primary fails
        fallback_str = os.getenv("LLM_FALLBACK_PROVIDERS", "")
        self.FALLBACK_PROVIDERS: list[str] = [p.strip() for p in fallback_str.split(",") if p.strip()]

    def get_provider_config(self) -> dict:
        defaults = PROVIDER_DEFAULTS.get(self.LLM_PROVIDER, PROVIDER_DEFAULTS["ollama"])
        return {
            "base_url": self.LLM_BASE_URL or defaults["base_url"],
            "model": self.LLM_MODEL or defaults["model"],
            "api_key": self.LLM_API_KEY or defaults["api_key"],
        }

    def get_provider_config_for(self, provider: str) -> dict:
        """Get config for a specific provider (used for fallback chain)."""
        defaults = PROVIDER_DEFAULTS.get(provider, PROVIDER_DEFAULTS["ollama"])
        # For fallback providers, use their defaults but check for provider-specific env vars
        api_key = os.getenv(f"{provider.upper()}_API_KEY", defaults["api_key"])
        return {
            "base_url": defaults["base_url"],
            "model": defaults["model"],
            "api_key": api_key,
        }

    def validate(self):
        if self.DEMO_MODE:
            os.makedirs(self.OUTPUT_DIR, exist_ok=True)
            return
        config = self.get_provider_config()
        if self.LLM_PROVIDER == "huggingface" and not config["api_key"]:
            raise ValueError("LLM_API_KEY (or HF token) is required for HuggingFace provider.")
        if self.LLM_PROVIDER == "openai" and not config["api_key"]:
            raise ValueError("LLM_API_KEY is required for OpenAI provider.")
        if self.LLM_PROVIDER == "groq" and not config["api_key"]:
            raise ValueError("LLM_API_KEY is required for Groq provider. Get a free key at https://console.groq.com")
        if self.LLM_PROVIDER == "gemini" and not config["api_key"]:
            raise ValueError("LLM_API_KEY is required for Gemini provider. Get a free key at https://aistudio.google.com/apikey")
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)

    def info(self) -> dict:
        config = self.get_provider_config()
        return {
            "provider": "demo" if self.DEMO_MODE else self.LLM_PROVIDER,
            "model": "demo-mode" if self.DEMO_MODE else config["model"],
            "base_url": "local" if self.DEMO_MODE else config["base_url"],
            "demo_mode": self.DEMO_MODE,
        }


settings = Settings()


def reload_settings():
    """Reload settings from .env (call after .env changes).
    
    Mutates the existing singleton in-place so all modules that
    imported 'settings' see the updated values.
    """
    load_dotenv(ENV_PATH, override=True)
    settings.LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()
    settings.LLM_MODEL = os.getenv("LLM_MODEL", "")
    settings.LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")
    settings.LLM_API_KEY = os.getenv("LLM_API_KEY", os.getenv("OPENAI_API_KEY", ""))
    settings.DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
    fallback_str = os.getenv("LLM_FALLBACK_PROVIDERS", "")
    settings.FALLBACK_PROVIDERS = [p.strip() for p in fallback_str.split(",") if p.strip()]
    return settings
