"""Facade tests for src/ai_helper.py over the shared llm-backends package.

Covers: the preserved public surface, fake-LLM dispatch, legacy (dead) model
name remapping, and the formerly-NameError Claude path now dispatching against
a fake Anthropic client. No live calls anywhere (see conftest.py).
"""

import pytest

from llm_backends import multi_provider_llm

from src import ai_helper


# ---- capturing fakes ---------------------------------------------------------------

class _CapturingOpenAIClient:
    """Mimics the OpenAI SDK surface used by send_prompt_openai_meta."""

    def __init__(self, text="openai fake text"):
        captured = self.captured = {}

        class _Message:
            content = text

        class _Choice:
            message = _Message()
            finish_reason = "stop"

        class _Response:
            choices = [_Choice()]

        class _Completions:
            def create(self, **kwargs):
                captured.update(kwargs)
                return _Response()

        class _Chat:
            completions = _Completions()

        self.chat = _Chat()


class _CapturingAnthropicClient:
    """Mimics the Anthropic SDK surface used by send_prompt_claude_meta."""

    def __init__(self, text="claude fake text"):
        captured = self.captured = {}

        class _Block:
            pass

        block = _Block()
        block.text = text

        class _Response:
            content = [block]
            stop_reason = "end_turn"

        class _Messages:
            def create(self, **kwargs):
                captured.update(kwargs)
                return _Response()

        self.messages = _Messages()


@pytest.fixture
def fake_openai(monkeypatch):
    client = _CapturingOpenAIClient()
    monkeypatch.setattr(multi_provider_llm, "_get_openai_client", lambda: client)
    return client


@pytest.fixture
def fake_anthropic(monkeypatch):
    client = _CapturingAnthropicClient()
    monkeypatch.setattr(multi_provider_llm, "_get_anthropic_client", lambda: client)
    return client


# ---- facade surface ----------------------------------------------------------------

def test_facade_keeps_original_public_surface():
    for name in ("send_prompt", "get_supported_models", "send_prompt_oai",
                 "send_prompt_o1", "send_prompt_gemini", "send_prompt_claude"):
        assert callable(getattr(ai_helper, name)), name


def test_get_supported_models_lists_legacy_and_package_primaries():
    supported = ai_helper.get_supported_models()
    # Every old CAB registry key still validates...
    for legacy in ("gpt-4o", "o1", "o1-mini", "o3", "o4-mini",
                   "gemini-1.5-pro-latest", "gemini-2.0-pro-exp-02-05",
                   "gemini-2.5-pro-exp-03-25",
                   "claude-3-5-sonnet", "claude-3-7-sonnet"):
        assert legacy in supported, legacy
    # ...and the package primaries are selectable too.
    for primary in ("gpt-5.5", "gpt-5.4-mini", "gemini-2.5-pro",
                    "claude-sonnet-4-6"):
        assert primary in supported, primary


def test_reporter_default_models_still_validate():
    # AIMarketReporter(default_model="o3") and the alt reporter ("o4-mini")
    # raise ValueError at construction if their default is unsupported.
    supported = ai_helper.get_supported_models()
    assert "o3" in supported
    assert "o4-mini" in supported


# ---- fake-LLM dispatch and dead-name remapping ---------------------------------------

@pytest.mark.parametrize(
    ("legacy", "expected_api_model"),
    [
        ("gpt-4o", "gpt-5.5"),
        ("o1", "gpt-5.5"),
        ("o3", "gpt-5.5"),
        ("o1-mini", "gpt-5.4-mini"),
        ("o4-mini", "gpt-5.4-mini"),
    ],
)
def test_send_prompt_remaps_dead_openai_names(fake_openai, legacy, expected_api_model):
    assert ai_helper.send_prompt("hello", model=legacy) == "openai fake text"
    assert fake_openai.captured["model"] == expected_api_model


def test_send_prompt_passes_package_primaries_through(fake_openai):
    assert ai_helper.send_prompt("hello", model="gpt-5.5") == "openai fake text"
    assert fake_openai.captured["model"] == "gpt-5.5"


@pytest.mark.parametrize(
    "legacy",
    ["gemini-1.5-pro-latest", "gemini-2.0-pro-exp-02-05", "gemini-2.5-pro-exp-03-25"],
)
def test_send_prompt_remaps_dead_gemini_names(monkeypatch, legacy):
    calls = {}

    def fake_gemini_meta(prompt, model_name, max_output_tokens, timeout=None, **kw):
        calls.update(prompt=prompt, model_name=model_name)
        return "gemini fake text", "STOP"

    monkeypatch.setattr(multi_provider_llm, "send_prompt_gemini_meta", fake_gemini_meta)
    assert ai_helper.send_prompt("hello", model=legacy) == "gemini fake text"
    assert calls["model_name"] == "gemini-2.5-pro"


def test_send_prompt_unknown_model_raises_valueerror_with_supported_list():
    with pytest.raises(ValueError, match="Unsupported model: not-a-model"):
        ai_helper.send_prompt("hello", model="not-a-model")


def test_send_prompt_oai_remaps_hardcoded_gpt4o_and_forwards_kwargs(fake_openai):
    # The reporters hardcode send_prompt_oai(model="gpt-4o", temperature=0.3,
    # role_description=<crypto analyst>) at their call sites.
    role = "You are a professional cryptocurrency market analyst."
    text = ai_helper.send_prompt_oai(
        prompt="analyse BTC", model="gpt-4o", max_tokens=4096,
        temperature=0.3, role_description=role,
    )
    assert text == "openai fake text"
    captured = fake_openai.captured
    assert captured["model"] == "gpt-5.5"
    assert captured["max_tokens"] == 4096
    assert captured["temperature"] == 0.3
    assert captured["messages"][0] == {"role": "system", "content": role}
    assert captured["messages"][1] == {"role": "user", "content": "analyse BTC"}


@pytest.mark.parametrize(
    ("legacy", "expected_api_model"),
    [("o3", "gpt-5.5"), ("o4-mini", "gpt-5.4-mini"), ("o1-mini", "gpt-5.4-mini")],
)
def test_send_prompt_o1_remaps_dead_o_series(fake_openai, legacy, expected_api_model):
    assert ai_helper.send_prompt_o1("hello", model=legacy) == "openai fake text"
    assert fake_openai.captured["model"] == expected_api_model


def test_send_prompt_gemini_old_surface_accepts_top_p_top_k(monkeypatch):
    calls = {}

    def fake_gemini_meta(prompt, model_name, max_output_tokens, temperature=0.9,
                         timeout=None):
        calls.update(model_name=model_name, max_output_tokens=max_output_tokens,
                     temperature=temperature)
        return "gemini fake text", "STOP"

    monkeypatch.setattr(multi_provider_llm, "send_prompt_gemini_meta", fake_gemini_meta)
    text = ai_helper.send_prompt_gemini(
        "hello", model_name="gemini-1.5-pro", max_output_tokens=8192,
        temperature=0.7, top_p=1, top_k=40,   # old signature, still accepted
    )
    assert text == "gemini fake text"
    assert calls == {"model_name": "gemini-2.5-pro", "max_output_tokens": 8192,
                     "temperature": 0.7}


def test_send_prompt_gemini_returns_none_on_error(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("provider down")

    monkeypatch.setattr(multi_provider_llm, "send_prompt_gemini_meta", boom)
    assert ai_helper.send_prompt_gemini("hello") is None


# ---- the formerly-dead Claude path ---------------------------------------------------

@pytest.mark.parametrize("legacy", ["claude-3-5-sonnet", "claude-3-7-sonnet"])
def test_previously_nameerror_claude_keys_now_dispatch(fake_anthropic, legacy):
    """Old module: these registry keys raised NameError (undefined
    anthropic_client). Facade: they dispatch to claude-sonnet-4-6 through the
    package against the injected fake client."""
    assert ai_helper.send_prompt("hello", model=legacy) == "claude fake text"
    captured = fake_anthropic.captured
    assert captured["model"] == "claude-sonnet-4-6"
    assert captured["max_tokens"] == 4096
    assert captured["messages"] == [{"role": "user", "content": "hello"}]


def test_send_prompt_claude_direct_keeps_crypto_analyst_system_prompt(fake_anthropic):
    text = ai_helper.send_prompt_claude("hello")
    assert text == "claude fake text"
    captured = fake_anthropic.captured
    assert captured["model"] == "claude-sonnet-4-6"  # dated 2024 id remapped
    assert captured["system"].startswith(
        "You are a professional cryptocurrency market analyst"
    )
    assert captured["temperature"] == 0.7


def test_send_prompt_claude_returns_none_on_error(monkeypatch):
    def boom():
        raise RuntimeError("no client")

    monkeypatch.setattr(multi_provider_llm, "_get_anthropic_client", boom)
    assert ai_helper.send_prompt_claude("hello") is None
