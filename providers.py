"""AI provider adapters.

The rest of the project only talks to two tiny interfaces:

    chat_provider.chat(system, messages)  -> reply text
    embedder.embed(texts, kind)           -> list of vectors

Pick your providers in .env (CHAT_PROVIDER / EMBED_PROVIDER). To support a new
service, add a class here and register it in build_chat_provider() or
build_embedder(). Nothing else needs to change.

Supported out of the box
------------------------
Chat:        ollama, openai, anthropic, gemini, groq, openrouter, lmstudio, custom
Embeddings:  ollama, openai, gemini, openrouter, lmstudio, custom, keyword

"custom" means any server that speaks the OpenAI API (vLLM, Together, Mistral,
DeepSeek, a company gateway, ...): set CHAT_BASE_URL / EMBED_BASE_URL.
"keyword" needs no AI model at all (see retrieval.py).

SDKs are imported only when used, so you only need to install the ones for the
providers you picked.
"""
import os


class ProviderError(Exception):
    """Raised for setup problems (missing key, missing package...). Message is user-friendly."""


# Services that speak the OpenAI API, with their default endpoint and API-key variable.
OPENAI_COMPATIBLE = {
    "openai": {"base_url": None, "key_env": "OPENAI_API_KEY"},
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "key_env": "GEMINI_API_KEY",
    },
    "groq": {"base_url": "https://api.groq.com/openai/v1", "key_env": "GROQ_API_KEY"},
    "openrouter": {"base_url": "https://openrouter.ai/api/v1", "key_env": "OPENROUTER_API_KEY"},
    "lmstudio": {"base_url": "http://127.0.0.1:1234/v1", "key_env": None, "default_key": "lm-studio"},
    "custom": {"base_url": None, "key_env": None},
}

CHAT_PROVIDERS = ["ollama", "anthropic"] + list(OPENAI_COMPATIBLE)
EMBED_PROVIDERS = ["ollama", "keyword"] + [p for p in OPENAI_COMPATIBLE if p != "groq"]  # Groq has no embeddings API


def _float_env(name, default):
    try:
        return float(os.getenv(name, default))
    except ValueError:
        return float(default)


def _int_env(name):
    value = os.getenv(name, "").strip()
    return int(value) if value.isdigit() else None


def _import(module, pip_name=None):
    try:
        return __import__(module)
    except ImportError as exc:
        raise ProviderError(
            f"The '{module}' package is not installed. Run: pip install {pip_name or module}"
        ) from exc


def _openai_settings(prefix, provider):
    """Resolve API key and base URL for an OpenAI-compatible provider."""
    preset = OPENAI_COMPATIBLE[provider]
    base_url = os.getenv(f"{prefix}_BASE_URL") or preset["base_url"]
    api_key = (
        os.getenv(f"{prefix}_API_KEY")
        or (os.getenv(preset["key_env"]) if preset["key_env"] else None)
        or preset.get("default_key")
    )
    if provider == "custom" and not base_url:
        raise ProviderError(f"{prefix}_PROVIDER=custom needs {prefix}_BASE_URL in .env")
    if not api_key:
        needed = f"{prefix}_API_KEY" + (f" (or {preset['key_env']})" if preset["key_env"] else "")
        if provider == "custom":
            api_key = "not-needed"  # many self-hosted servers don't check the key
        else:
            raise ProviderError(f"{provider} needs an API key: set {needed} in .env")
    return api_key, base_url


# ===========================================================================
# CHAT
# ===========================================================================
class OllamaChat:
    def __init__(self, model, host, timeout):
        self.ollama = _import("ollama")
        self.model = model
        self.client = self.ollama.Client(host=host or None, timeout=timeout)

    def chat(self, system, messages):
        msgs = [{"role": "system", "content": system}] + messages
        try:
            # Thinking off = much faster for models like qwen3.
            resp = self.client.chat(model=self.model, messages=msgs, think=False)
        except TypeError:  # older ollama library without `think`
            resp = self.client.chat(model=self.model, messages=msgs)
        except self.ollama.ResponseError as exc:
            if "think" not in str(exc).lower():
                raise
            resp = self.client.chat(model=self.model, messages=msgs)  # model lacks the option
        return resp["message"]["content"] or ""


class OpenAICompatibleChat:
    def __init__(self, provider, model, api_key, base_url, timeout, max_tokens):
        openai = _import("openai")
        self.provider = provider
        self.model = model
        self.max_tokens = max_tokens
        self.client = openai.OpenAI(
            api_key=api_key, base_url=base_url, timeout=timeout, max_retries=2
        )

    def chat(self, system, messages):
        kwargs = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}] + messages,
        }
        if self.max_tokens:
            # OpenAI's newer models only accept max_completion_tokens; others still use max_tokens.
            key = "max_completion_tokens" if self.provider == "openai" else "max_tokens"
            kwargs[key] = self.max_tokens
        resp = self.client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""


class AnthropicChat:
    def __init__(self, model, api_key, base_url, timeout, max_tokens):
        anthropic = _import("anthropic")
        self.model = model
        self.max_tokens = max_tokens or 600  # required by the Anthropic API
        self.client = anthropic.Anthropic(
            api_key=api_key, base_url=base_url, timeout=timeout, max_retries=2
        )

    def chat(self, system, messages):
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,  # Anthropic takes the system prompt as a separate parameter
            messages=messages,
        )
        return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")


def build_chat_provider():
    """Create the chat provider from CHAT_PROVIDER / CHAT_MODEL / ... in .env."""
    provider = os.getenv("CHAT_PROVIDER", "ollama").strip().lower()
    timeout = _float_env("CHAT_TIMEOUT_SECONDS", _float_env("OLLAMA_TIMEOUT_SECONDS", 90))
    max_tokens = _int_env("CHAT_MAX_TOKENS")
    model = os.getenv("CHAT_MODEL", "").strip()

    if provider not in CHAT_PROVIDERS:
        raise ProviderError(
            f"Unknown CHAT_PROVIDER '{provider}'. Choose one of: {', '.join(CHAT_PROVIDERS)}"
        )

    if provider == "ollama":
        return OllamaChat(model or "qwen3:4b", os.getenv("OLLAMA_HOST"), timeout), \
            f"ollama / {model or 'qwen3:4b'}"

    if not model:
        raise ProviderError(f"CHAT_PROVIDER={provider} needs CHAT_MODEL set in .env")

    if provider == "anthropic":
        api_key = os.getenv("CHAT_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ProviderError("anthropic needs an API key: set CHAT_API_KEY (or ANTHROPIC_API_KEY) in .env")
        return AnthropicChat(model, api_key, os.getenv("CHAT_BASE_URL") or None, timeout, max_tokens), \
            f"anthropic / {model}"

    api_key, base_url = _openai_settings("CHAT", provider)
    return OpenAICompatibleChat(provider, model, api_key, base_url, timeout, max_tokens), \
        f"{provider} / {model}"


# ===========================================================================
# EMBEDDINGS
# ===========================================================================
class Embedder:
    """Base class: handles the prefix some models want, and batching."""

    def __init__(self, provider, model):
        self.provider = provider
        self.model = model

    def _prefix(self, text, kind):
        # nomic-embed-text works best with a task prefix ("document" or "query").
        if "nomic-embed-text" in self.model:
            return f"search_{kind}: {text}"
        return text

    def embed(self, texts, kind="document"):
        return self._embed([self._prefix(t, kind) for t in texts])

    def _embed(self, texts):
        raise NotImplementedError


class OllamaEmbedder(Embedder):
    def __init__(self, model, host, timeout):
        super().__init__("ollama", model)
        ollama = _import("ollama")
        self.client = ollama.Client(host=host or None, timeout=timeout)

    def _embed(self, texts):
        return list(self.client.embed(model=self.model, input=texts)["embeddings"])


class OpenAICompatibleEmbedder(Embedder):
    def __init__(self, provider, model, api_key, base_url, timeout):
        super().__init__(provider, model)
        openai = _import("openai")
        self.client = openai.OpenAI(
            api_key=api_key, base_url=base_url, timeout=timeout, max_retries=2
        )

    def _embed(self, texts):
        resp = self.client.embeddings.create(model=self.model, input=texts)
        return [d.embedding for d in sorted(resp.data, key=lambda d: d.index)]


# Sensible default embedding models. Other providers: set EMBED_MODEL yourself.
DEFAULT_EMBED_MODELS = {"ollama": "nomic-embed-text", "openai": "text-embedding-3-small"}


def default_embed_provider():
    """Local Ollama users keep Ollama embeddings; everyone else starts with keyword search,
    which needs no extra setup (Anthropic, for example, has no embeddings API)."""
    return "ollama" if os.getenv("CHAT_PROVIDER", "ollama").strip().lower() == "ollama" else "keyword"


def embed_settings():
    """Returns (provider, model). Model is '' for keyword search."""
    provider = (os.getenv("EMBED_PROVIDER", "").strip().lower() or default_embed_provider())
    if provider not in EMBED_PROVIDERS:
        raise ProviderError(
            f"Unknown EMBED_PROVIDER '{provider}'. Choose one of: {', '.join(EMBED_PROVIDERS)}"
        )
    if provider == "keyword":
        return provider, ""
    model = os.getenv("EMBED_MODEL", "").strip() or DEFAULT_EMBED_MODELS.get(provider, "")
    if not model:
        raise ProviderError(f"EMBED_PROVIDER={provider} needs EMBED_MODEL set in .env")
    return provider, model


def build_embedder():
    """Returns (embedder_or_None, label). None means keyword search (no AI model needed)."""
    provider, model = embed_settings()
    if provider == "keyword":
        return None, "keyword search (no embedding model)"

    timeout = _float_env("EMBED_TIMEOUT_SECONDS", _float_env("OLLAMA_TIMEOUT_SECONDS", 90))
    if provider == "ollama":
        return OllamaEmbedder(model, os.getenv("OLLAMA_HOST"), timeout), f"ollama / {model}"

    api_key, base_url = _openai_settings("EMBED", provider)
    return OpenAICompatibleEmbedder(provider, model, api_key, base_url, timeout), f"{provider} / {model}"
