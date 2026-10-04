"""Optional language model access through LlamaIndex.

The engine is fully functional with no language model. When one is configured it is used for
three things only: proposing extra failure scenarios from narrative text for human review,
writing natural language answers over retrieved evidence, and judging answers in RAGAS.
It is never asked for a rating or a number.
"""
from __future__ import annotations

from typing import Protocol

from aegis_rmf.settings import Settings


class TextLLM(Protocol):
    def complete(self, prompt: str) -> str: ...


class LlamaIndexLLM:
    """Adapter that exposes a LlamaIndex LLM through the minimal TextLLM protocol."""

    def __init__(self, llm) -> None:
        self.llm = llm

    def complete(self, prompt: str) -> str:
        return str(self.llm.complete(prompt))


def build_llm(settings: Settings) -> LlamaIndexLLM | None:
    """Return the configured language model, or None for offline operation."""
    provider = settings.llm_provider.strip().lower()
    if provider in ("", "none"):
        return None
    if provider == "anthropic":
        from llama_index.llms.anthropic import Anthropic

        return LlamaIndexLLM(Anthropic(model=settings.llm_model, temperature=0.0, max_tokens=1500))
    if provider == "openai":
        from llama_index.llms.openai import OpenAI

        return LlamaIndexLLM(OpenAI(model=settings.llm_model, temperature=0.0))
    raise ValueError(f"Unsupported llm_provider: {settings.llm_provider!r}")
