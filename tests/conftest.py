"""Test setup for CryptoAlertBot.

- Puts the repo root on sys.path so `from src.ai_helper import ...` works the
  same way it does for main.py / the reporters (src/ is a namespace package).
- An autouse fixture guarantees NO live LLM calls: every provider client
  getter in llm_backends.multi_provider_llm is replaced with one that raises,
  and any cached client is cleared. Individual tests then monkeypatch in their
  own capturing fakes on top of this.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from llm_backends import multi_provider_llm  # noqa: E402


def _refuse(name):
    def getter(*args, **kwargs):
        raise AssertionError(
            f"Test tried to construct a real provider client via {name}. "
            "All LLM traffic in tests must go through fakes."
        )
    return getter


@pytest.fixture(autouse=True)
def no_live_llm_clients(monkeypatch):
    """Fail loudly if any code path reaches for a real SDK client."""
    for cache_attr in ("_openai_client", "_anthropic_client", "_hosted_llm_client",
                      "_openrouter_client", "_venice_client"):
        monkeypatch.setattr(multi_provider_llm, cache_attr, None)
    monkeypatch.setattr(multi_provider_llm, "_gemini_configured", False)
    for getter_attr in ("_get_openai_client", "_get_anthropic_client",
                        "_get_hosted_llm_client", "_get_openrouter_client",
                        "_get_venice_client"):
        monkeypatch.setattr(multi_provider_llm, getter_attr, _refuse(getter_attr))
    # Gemini has no client getter; block configuration + model construction.
    monkeypatch.setattr(multi_provider_llm, "_ensure_gemini_configured",
                        _refuse("_ensure_gemini_configured"))
    yield
