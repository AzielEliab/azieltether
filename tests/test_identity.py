"""Public identity is Aziel Eliab only."""

from __future__ import annotations

from pathlib import Path

from azieltether import __author__


ROOT = Path(__file__).resolve().parents[1]


def _flat(text: str) -> str:
    return " ".join(text.split())


def test_package_author() -> None:
    assert __author__ == "Aziel Eliab"


AI_CLIENT_MARKERS = (
    "ChatGPT (GPT Actions / OpenAI)",
    "Grok (xAI)",
    "Venice",
    "Claude (Anthropic)",
    "Cursor (MCP)",
    "Glama (MCP)",
    "Perplexity",
    "Microsoft Copilot / Bing",
    "Google Gemini / Vertex",
    "Mistral",
    "Meta AI",
    "Apple Intelligence surfaces",
    "Amazon Q tooling",
    "DuckAssist",
    "You.com",
    "Cohere",
    "MCP/OpenAPI-capable assistants",
)

EXCLUSIVE_THREE_CLIENT = "Grok: import"


def test_readme_author_only() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Aziel Eliab" in text
    assert "Horton" not in text
    assert "Altman" not in text
    assert "GodLock.AZ" not in text


def test_readme_uses_full_ai_client_list() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    flat = _flat(text)
    assert "## Use with AI assistants" in text
    assert "## Use with Grok, ChatGPT, Venice" not in text
    for marker in AI_CLIENT_MARKERS:
        assert marker in flat
    assert EXCLUSIVE_THREE_CLIENT not in text


def test_skill_and_worker_use_full_ai_client_list() -> None:
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    runtime = (ROOT / "workers/download-tracker/src/runtime.js").read_text(encoding="utf-8")
    for text in (skill, runtime):
        flat = _flat(text)
        assert "Aziel Eliab" in text
        assert EXCLUSIVE_THREE_CLIENT not in text
        assert "use with Grok, ChatGPT, Venice" not in text
        for marker in AI_CLIENT_MARKERS:
            assert marker in flat
