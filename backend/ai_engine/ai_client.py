"""
Optional LLM layer. When settings.ANTHROPIC_API_KEY is configured, the AI
engine can call the real Claude API to produce richer natural-language
output layered on top of the deterministic static-analysis results
(analyzers.py / generators.py). Without a key, the platform runs fully
on the offline rule-based engine — every feature still works.
"""
import json

from django.conf import settings

try:
    import anthropic
except ImportError:  # pragma: no cover - optional dependency
    anthropic = None


def is_llm_available() -> bool:
    return bool(settings.ANTHROPIC_API_KEY) and anthropic is not None


def enrich_with_llm(feature: str, code: str, language: str, heuristic_result: dict, extra_instruction: str = "") -> dict:
    """
    Sends the code + the heuristic engine's structured findings to Claude and
    asks it to produce a short natural-language write-up. Falls back silently
    to the heuristic result if the API call fails for any reason (network,
    quota, missing key) so the feature never breaks.
    """
    if not is_llm_available():
        return heuristic_result

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    system_prompt = (
        "You are a senior software engineer assisting inside a code-intelligence platform. "
        "You are given source code, a feature name, and structured findings already computed "
        "by a static-analysis engine. Add a concise, accurate natural-language write-up. "
        "Do not contradict the structured findings; explain and prioritize them. "
        "Keep it under 200 words unless generating code/tests/docs/SQL, in which case return only the artifact."
    )
    user_prompt = (
        f"Feature: {feature}\nLanguage: {language}\n{extra_instruction}\n\n"
        f"Static analysis findings (JSON):\n{json.dumps(heuristic_result)[:4000]}\n\n"
        f"Source code:\n```{language}\n{code[:6000]}\n```"
    )

    try:
        response = client.messages.create(
            model=settings.AI_MODEL,
            max_tokens=1200,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text_parts = [block.text for block in response.content if getattr(block, "type", "") == "text"]
        narrative = "\n".join(text_parts).strip()
        enriched = dict(heuristic_result)
        enriched["ai_narrative"] = narrative
        enriched["engine_used"] = "llm"
        return enriched
    except Exception as exc:  # noqa: BLE001 - never break the feature because of the LLM layer
        fallback = dict(heuristic_result)
        fallback["llm_error"] = str(exc)
        return fallback
