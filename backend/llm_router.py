"""Unified LLM routing for FairCouncil providers."""

from typing import Any, Dict

from .openrouter import call_gemini, call_groq


class FairCouncilError(Exception):
    """Raised when FairCouncil cannot complete an LLM call."""


async def call_llm(model_config: Dict[str, str], prompt: str) -> Dict[str, Any]:
    """
    Route a prompt to a provider-specific LLM client.

    Args:
        model_config: Dict in the format:
            {"provider": "gemini"|"groq", "model": "..."}
        prompt: User prompt to send to the model

    Returns:
        Dict with transport-normalized response data:
            {"model": str, "output": str, "latency_ms": int}

    Raises:
        FairCouncilError: If config is invalid or model call fails.
    """
    provider = (model_config or {}).get("provider")
    model = (model_config or {}).get("model")

    if provider not in {"gemini", "groq"}:
        raise FairCouncilError(f"Unsupported provider: {provider}")
    if not model:
        raise FairCouncilError("Missing model in model_config")
    if not prompt:
        raise FairCouncilError("Prompt cannot be empty")

    try:
        if provider == "gemini":
            result = await call_gemini(prompt=prompt, model=model)
        else:
            result = await call_groq(prompt=prompt, model=model)
    except Exception as e:
        raise FairCouncilError(
            f"LLM call failed for provider={provider} model={model}: {e}"
        ) from e

    if not result:
        raise FairCouncilError(
            f"LLM call returned no response for provider={provider} model={model}"
        )

    latency_ms = int(result.get("latency_ms", 0))
    print(f"provider={provider} model={model} latency_ms={latency_ms}")

    return result


# Example usage with the same shape as config.py's COUNCIL_MODELS
# COUNCIL_MODELS = [
#     {"provider": "gemini", "model": "gemini-2.0-flash"},
#     {"provider": "groq", "model": "llama3-8b-8192"},
# ]
#
# import asyncio
#
# async def _example() -> None:
#     response = await call_llm(
#         {"provider": "gemini", "model": "gemini-2.0-flash"},
#         "Summarize fairness in two sentences.",
#     )
#     print(response["output"])
#
# if __name__ == "__main__":
#     asyncio.run(_example())
