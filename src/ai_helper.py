# ai_helper.py
#
# Facade over the shared llm-backends package (migration step 6,
# StoryDaemon docs/LLM_BACKENDS_INVENTORY.md section 7.4).
#
# The public surface of the old module is preserved exactly:
#   send_prompt, get_supported_models,
#   send_prompt_oai, send_prompt_o1, send_prompt_gemini, send_prompt_claude
# but all provider traffic now routes through llm_backends.multi_provider_llm
# (lazy client init, hardened SDK construction, per-request timeouts).
#
# Legacy model names. The old registry keys no longer exist upstream, so they
# are remapped here to current package primaries:
#
#   old CAB key                 -> package key
#   gpt-4o                      -> gpt-5.5
#   o1                          -> gpt-5.5
#   o3                          -> gpt-5.5
#   o1-mini                     -> gpt-5.4-mini
#   o4-mini                     -> gpt-5.4-mini  (old code silently sent o3-mini)
#   gemini-1.5-pro[-latest]     -> gemini-2.5-pro
#   gemini-2.0-pro-exp-02-05    -> gemini-2.5-pro
#   gemini-2.5-pro-exp-03-25    -> gemini-2.5-pro
#   claude-3-5-sonnet[-20241022]-> claude-sonnet-4-6
#   claude-3-7-sonnet[-20250219]-> claude-sonnet-4-6
#   claude-3-sonnet-20240229    -> claude-sonnet-4-6
#
# The Claude path used to be DEAD CODE: the old send_prompt_claude referenced
# an `anthropic_client` that was never imported or defined, so selecting
# "claude-3-5-sonnet" / "claude-3-7-sonnet" raised NameError. Through the
# package those keys now dispatch for real (to claude-sonnet-4-6). No CAB
# caller selects a Claude model (reporter defaults are "o3" / "o4-mini" and
# all hardcoded call sites are OpenAI), so this cannot start Claude spend
# unless a model is explicitly requested.
#
# Behavioural notes vs. the old module:
# - Clients are created lazily inside the package on first use, not eagerly
#   at import time.
# - send_prompt_o1 previously sent no system prompt; it now routes through the
#   package registry, which applies the package's neutral default system
#   prompt and temperature.
# - send_prompt_gemini accepts top_p/top_k for signature compatibility but no
#   longer forwards them (the package Gemini path does not take them).
# - send_prompt_gemini / send_prompt_claude keep the old contract of returning
#   None on error; send_prompt re-raises (the package wraps dispatch failures
#   in RuntimeError).

import os  # noqa: F401  (kept for consumers that reach through this module)

from dotenv import load_dotenv

load_dotenv()  # consumers historically relied on ai_helper loading .env

from llm_backends import DEFAULT_API_MODEL  # noqa: E402
from llm_backends.multi_provider_llm import (  # noqa: E402
    get_supported_models as _pkg_get_supported_models,
    send_prompt as _pkg_send_prompt,
    send_prompt_openai as _pkg_send_prompt_openai,
    send_prompt_gemini as _pkg_send_prompt_gemini,
    send_prompt_claude as _pkg_send_prompt_claude,
)

# Old CAB registry key (and the dated API ids the old lambdas used) -> current
# package primary. Anything not listed passes through to the package verbatim
# (package primaries, package aliases, "openrouter:<id>", "-latest" fallback).
# The old flagship/o-series keys map to the package's authoritative default
# (DEFAULT_API_MODEL, added in llm-backends 0.1.1) instead of a hardcoded
# literal, so a future default bump upstream carries through automatically.
LEGACY_MODEL_MAP = {
    "gpt-4o": DEFAULT_API_MODEL,
    "o1": DEFAULT_API_MODEL,
    "o1-mini": "gpt-5.4-mini",
    "o3": DEFAULT_API_MODEL,
    "o4-mini": "gpt-5.4-mini",
    "gemini-1.5-pro": "gemini-2.5-pro",
    "gemini-1.5-pro-latest": "gemini-2.5-pro",
    "gemini-2.0-pro-exp-02-05": "gemini-2.5-pro",
    "gemini-2.5-pro-exp-03-25": "gemini-2.5-pro",
    "claude-3-5-sonnet": "claude-sonnet-4-6",
    "claude-3-5-sonnet-20241022": "claude-sonnet-4-6",
    "claude-3-7-sonnet": "claude-sonnet-4-6",
    "claude-3-7-sonnet-20250219": "claude-sonnet-4-6",
    "claude-3-sonnet-20240229": "claude-sonnet-4-6",
}

# CAB-owned system prompt (assumption A5: system prompts stay app-owned; the
# package default is a neutral/creative-writing string, not a crypto analyst).
CRYPTO_ANALYST_ROLE = (
    "You are a professional cryptocurrency market analyst with expertise in "
    "technical analysis, market structure, and digital asset investment strategies."
)


def _resolve(model):
    """Map a legacy CAB model name to its package primary; pass others through."""
    return LEGACY_MODEL_MAP.get(model, model)


def get_supported_models():
    """Returns a list of supported model names.

    Package primaries plus the legacy CAB spellings that still resolve here,
    so existing defaults ("o3", "o4-mini", "gpt-4o", ...) keep validating.
    """
    return sorted(set(_pkg_get_supported_models()) | set(LEGACY_MODEL_MAP))


def send_prompt(prompt, model=DEFAULT_API_MODEL, max_tokens=4096):
    """Sends a prompt to the specified AI model (legacy names are remapped)."""
    resolved = _resolve(model)
    if resolved != model:
        print(f"Attempting to use model: {model} -> {resolved}")
    else:
        print(f"Attempting to use model: {model}")
    try:
        return _pkg_send_prompt(prompt, model=resolved, max_tokens=max_tokens)
    except ValueError:
        # Package raises ValueError for unknown models; re-raise with the
        # facade's (legacy-inclusive) list, matching the old message shape.
        supported_models = get_supported_models()
        raise ValueError(
            f"Unsupported model: {model}. Supported models are: {supported_models}"
        )


def send_prompt_oai(prompt, model=DEFAULT_API_MODEL, max_tokens=1500, temperature=0.7,
                    role_description=CRYPTO_ANALYST_ROLE):
    """OpenAI chat path (old surface). Hardcoded legacy ids like 'gpt-4o' remap.

    The old default role_description was a creative-writing string ("You are a
    helpful fiction writing assistant...") inherited from the library's origin
    apps; CAB is a market-analysis app, so the default is now the CAB-owned
    crypto analyst role (assumption A5: system prompts are app-owned). All
    reporter call sites pass role_description explicitly, so this only affects
    callers that omitted it.
    """
    return _pkg_send_prompt_openai(
        prompt=prompt,
        model=_resolve(model),
        max_tokens=max_tokens,
        temperature=temperature,
        role_description=role_description,
    )


def send_prompt_o1(prompt, model="o1-mini"):
    """Old o-series path. The o-series keys are gone; they remap to current
    GPT-5.x primaries and route through the package registry."""
    resolved = _resolve(model)
    print("Used model: ", resolved)
    return _pkg_send_prompt(prompt, model=resolved, max_tokens=4096)


def send_prompt_gemini(prompt, model_name="gemini-1.5-pro", max_output_tokens=1024,
                       temperature=0.9, top_p=1, top_k=1):
    """Gemini path (old surface). Returns the generated text, or None on error.

    top_p / top_k are accepted for signature compatibility but not forwarded.
    """
    try:
        return _pkg_send_prompt_gemini(
            prompt=prompt,
            model_name=_resolve(model_name),
            max_output_tokens=max_output_tokens,
            temperature=temperature,
        )
    except Exception as e:
        print(f"Error generating content: {e}")
        return None


def send_prompt_claude(prompt, model="claude-3-sonnet-20240229", max_tokens=4096,
                       temperature=0.7, role_description=CRYPTO_ANALYST_ROLE):
    """Claude path (old surface). Returns the generated text, or None on error.

    Previously dead code (undefined anthropic_client -> NameError); now a real
    call through the package. Legacy/dated Claude ids remap to claude-sonnet-4-6.
    """
    try:
        return _pkg_send_prompt_claude(
            prompt=prompt,
            model=_resolve(model),
            max_tokens=max_tokens,
            temperature=temperature,
            role_description=role_description,
        )
    except Exception as e:
        print(f"Error generating content with Claude: {e}")
        return None
