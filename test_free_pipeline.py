"""Free-tier pipeline tests for FairCouncil."""

import asyncio
import os

import pytest
from dotenv import load_dotenv

from backend import council
from backend.llm_router import call_llm

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TEST_QUERY = "What is 2+2?"

pytestmark = [pytest.mark.free_tier]


def _has_real_key(value: str | None) -> bool:
    if not value:
        return False
    normalized = value.strip()
    if normalized == "":
        return False
    if normalized.startswith("FREE_API_KEY"):
        return False
    if normalized.lower().startswith("your_"):
        return False
    return True


def _assert_valid_response(response: dict) -> None:
    assert isinstance(response, dict)
    assert response.get("model")

    output = response.get("output")
    assert isinstance(output, str)
    assert output.strip() != ""

    latency_ms = response.get("latency_ms")
    assert isinstance(latency_ms, int)
    assert latency_ms > 0


@pytest.mark.skipif(
    not _has_real_key(GEMINI_API_KEY),
    reason="GEMINI_API_KEY missing/placeholder in environment",
)
def test_call_llm_gemini_free_tier() -> None:
    response = asyncio.run(
        call_llm(
            {"provider": "gemini", "model": "gemini-2.5-flash"},
            TEST_QUERY,
        )
    )
    _assert_valid_response(response)


@pytest.mark.skipif(
    not _has_real_key(GROQ_API_KEY),
    reason="GROQ_API_KEY missing/placeholder in environment",
)
def test_call_llm_groq_free_tier() -> None:
    response = asyncio.run(
        call_llm(
            {"provider": "groq", "model": "llama-3.1-8b-instant"},
            TEST_QUERY,
        )
    )
    _assert_valid_response(response)


def test_stage1_timeout_handling_graceful(monkeypatch: pytest.MonkeyPatch) -> None:
    async def slow_call_llm(model_config: dict, prompt: str) -> dict:
        await asyncio.sleep(40)
        return {
            "model": model_config.get("model", "unknown"),
            "output": "delayed",
            "latency_ms": 40000,
        }

    original_wait_for = asyncio.wait_for

    async def fast_wait_for(awaitable, timeout=None):
        return await original_wait_for(awaitable, timeout=0.01)

    monkeypatch.setattr(council, "call_llm", slow_call_llm)
    monkeypatch.setattr(
        council,
        "COUNCIL_MODELS",
        [{"provider": "gemini", "model": "gemini-2.0-flash"}],
    )
    monkeypatch.setattr(council.asyncio, "wait_for", fast_wait_for)

    stage1_results = asyncio.run(council.stage1_collect_responses(TEST_QUERY))

    # Timeout should be isolated and Stage 1 should return successful responses only.
    assert stage1_results == []


def test_select_chairperson_prefers_adjusted_score() -> None:
    fairness_leaderboard = [
        {
            "provider": "gemini",
            "model": "model-a",
            "average_rank": 1.0,
            "performance_score": 0.95,
            "bias_score": 3.5,
            "bias_score_normalized": 0.35,
            "final_score": 0.775,
            "rankings_count": 2,
        },
        {
            "provider": "groq",
            "model": "model-b",
            "average_rank": 1.5,
            "performance_score": 0.90,
            "bias_score": 0.2,
            "bias_score_normalized": 0.02,
            "final_score": 0.89,
            "rankings_count": 2,
        },
    ]

    selection = council.select_chairperson(fairness_leaderboard)

    assert selection["model"] == "model-b"
    assert selection["final_score"] == pytest.approx(0.89)


def test_calculate_aggregate_rankings_includes_missing_models() -> None:
    stage2_results = [
        {
            "provider": "gemini",
            "model": "evaluator-a",
            "ranking": "FINAL RANKING:\n1. Response A\n2. Response B",
            "parsed_ranking": ["Response A", "Response B"],
        }
    ]
    label_to_model = {
        "Response A": "model-a",
        "Response B": "model-b",
    }

    aggregate = council.calculate_aggregate_rankings(stage2_results, label_to_model)

    assert [entry["model"] for entry in aggregate] == ["model-a", "model-b"]
    assert aggregate[0]["performance_score"] >= aggregate[1]["performance_score"]
