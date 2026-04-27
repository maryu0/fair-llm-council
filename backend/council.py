"""3-stage LLM Council orchestration."""

import asyncio
import json
import re
from collections import defaultdict
from typing import List, Dict, Any, Tuple, Optional

from .config import (
    BIAS_EVALUATOR_MODEL,
    BIAS_EVALUATOR_PROVIDER,
    CHAIRMAN_MODEL,
    COUNCIL_MODELS,
    FAIRNESS_LAMBDA,
)
from .llm_router import call_llm


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _normalize_performance_score(average_rank: float, total_candidates: int) -> float:
    if total_candidates <= 1:
        return 1.0
    score = 1.0 - ((average_rank - 1.0) / (total_candidates - 1.0))
    return round(_clamp(score, 0.0, 1.0), 3)


def _normalize_bias_score(raw_bias_score: float) -> float:
    return round(_clamp(raw_bias_score / 10.0, 0.0, 1.0), 3)


def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None

    trimmed = text.strip()
    if trimmed.startswith("```"):
        trimmed = re.sub(r"^```(?:json)?\s*", "", trimmed, flags=re.IGNORECASE)
        trimmed = re.sub(r"\s*```$", "", trimmed)

    json_match = re.search(r"\{.*\}", trimmed, re.DOTALL)
    candidate = json_match.group(0) if json_match else trimmed

    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        return None

    return None


def _heuristic_bias_score(text: str, user_query: str) -> Dict[str, Any]:
    combined = f"{user_query}\n{text}".lower()
    score = 0.0
    signals: List[str] = []

    patterns = [
        (r"\b(all|always|never|every)\b.*\b(women|men|girls|boys|immigrants|poor people|rich people|minorities)\b", 2.5, "broad stereotype"),
        (r"\b(inferior|superior|lazy|dangerous|untrustworthy|fraudulent)\b", 1.5, "loaded language"),
        (r"\bshould not be trusted\b|\bcan't be trusted\b", 1.2, "blanket exclusion"),
        (r"\bbecause of their gender\b|\bbecause of race\b|\bbecause they are\b", 1.5, "protected attribute causal claim"),
    ]

    for pattern, weight, description in patterns:
        if re.search(pattern, combined, re.IGNORECASE):
            score += weight
            signals.append(description)

    if "fairness" in combined or "bias" in combined:
        score += 0.1

    score = _clamp(score, 0.0, 10.0)
    return {
        "bias_score": round(score, 2),
        "bias_level": "low" if score < 3 else "medium" if score < 6 else "high",
        "rationale": ", ".join(signals) if signals else "No strong heuristic bias signals detected.",
        "source": "heuristic",
    }


def _resolve_model_config(model_name: Optional[str]) -> Dict[str, str]:
    for cfg in COUNCIL_MODELS:
        if cfg.get("model") == model_name:
            return cfg

    return {"provider": "gemini", "model": CHAIRMAN_MODEL}


async def stage1_collect_responses(user_query: str) -> List[Dict[str, Any]]:
    """
    Stage 1: Collect individual responses from all council models.

    Args:
        user_query: The user's question

    Returns:
        List of dicts with 'model' and 'response' keys
    """
    async def _run_with_timeout(model_config: Dict[str, Any]) -> Dict[str, Any]:
        return await asyncio.wait_for(
            call_llm(model_config, user_query),
            timeout=30.0,
        )

    valid_configs = []
    for cfg in COUNCIL_MODELS:
        if not isinstance(cfg, dict) or "provider" not in cfg or "model" not in cfg:
            print(f"Stage1 error invalid model_config: {cfg}")
            continue
        valid_configs.append(cfg)

    tasks = [_run_with_timeout(cfg) for cfg in valid_configs]
    responses = await asyncio.gather(*tasks, return_exceptions=True)

    # Keep pipeline running: drop failed calls, log errors, keep successful ones.
    stage1_results = []
    for cfg, response in zip(valid_configs, responses):
        provider = cfg.get("provider")
        model_name = cfg.get("model")

        if isinstance(response, Exception):
            print(
                f"Stage1 error provider={provider} model={model_name}: {response}"
            )
            continue

        stage1_results.append({
            "provider": provider,
            "model": model_name,
            "response": response.get("output", ""),
            "latency_ms": int(response.get("latency_ms", 0)),
        })

    return stage1_results


async def stage2_collect_rankings(
    user_query: str,
    stage1_results: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Stage 2: Each model ranks the anonymized responses.

    Args:
        user_query: The original user query
        stage1_results: Results from Stage 1

    Returns:
        Tuple of (rankings list, label_to_model mapping)
    """
    # Create anonymized labels for responses (Response A, Response B, etc.)
    labels = [chr(65 + i) for i in range(len(stage1_results))]  # A, B, C, ...

    # Create mapping from label to model name
    label_to_model = {
        f"Response {label}": result['model']
        for label, result in zip(labels, stage1_results)
    }

    # Build the ranking prompt
    responses_text = "\n\n".join([
        f"Response {label}:\n{result['response']}"
        for label, result in zip(labels, stage1_results)
    ])

    ranking_prompt = f"""You are evaluating different responses to the following question:

Question: {user_query}

Here are the responses from different models (anonymized):

{responses_text}

Your task:
1. First, evaluate each response individually. For each response, explain what it does well and what it does poorly.
2. Then, at the very end of your response, provide a final ranking.

IMPORTANT: Your final ranking MUST be formatted EXACTLY as follows:
- Start with the line "FINAL RANKING:" (all caps, with colon)
- Then list the responses from best to worst as a numbered list
- Each line should be: number, period, space, then ONLY the response label (e.g., "1. Response A")
- Do not add any other text or explanations in the ranking section

Example of the correct format for your ENTIRE response:

Response A provides good detail on X but misses Y...
Response B is accurate but lacks depth on Z...
Response C offers the most comprehensive answer...

FINAL RANKING:
1. Response C
2. Response A
3. Response B

Now provide your evaluation and ranking:"""

    async def _run_with_timeout(model_config: Dict[str, Any]) -> Dict[str, Any]:
        return await asyncio.wait_for(
            call_llm(model_config, ranking_prompt),
            timeout=30.0,
        )

    valid_configs = []
    for cfg in COUNCIL_MODELS:
        if not isinstance(cfg, dict) or "provider" not in cfg or "model" not in cfg:
            print(f"Stage2 error invalid model_config: {cfg}")
            continue
        valid_configs.append(cfg)

    tasks = [_run_with_timeout(cfg) for cfg in valid_configs]
    responses = await asyncio.gather(*tasks, return_exceptions=True)

    stage2_results = []
    for cfg, response in zip(valid_configs, responses):
        provider = cfg.get("provider")
        model_name = cfg.get("model")

        if isinstance(response, Exception):
            print(
                f"Stage2 error provider={provider} model={model_name}: {response}"
            )
            continue

        full_text = response.get("output", "")
        parsed = parse_ranking_from_text(full_text)
        stage2_results.append({
            "provider": provider,
            "model": model_name,
            "ranking": full_text,
            "parsed_ranking": parsed,
        })

    return stage2_results, label_to_model


async def evaluate_bias_scores(
    user_query: str,
    stage1_results: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Evaluate each response for bias using a prompt-based scorer with a heuristic fallback.

    Args:
        user_query: The original user query
        stage1_results: Stage 1 responses

    Returns:
        List of bias-score dicts keyed by model.
    """

    async def _score_response(result: Dict[str, Any]) -> Dict[str, Any]:
        prompt = f"""You are a fairness auditor for an LLM council.

Task: Score the candidate response for bias, stereotype risk, and unfair generalization.

User question:
{user_query}

Candidate response:
{result['response']}

Return ONLY valid JSON with these keys:
- bias_score: number from 0 to 10 where 0 means no detectable bias and 10 means severe bias
- bias_level: one of low, medium, high
- rationale: short explanation of the score

Be concrete and base the score on the response text, not on the model name.
"""

        evaluator_config = {
            "provider": BIAS_EVALUATOR_PROVIDER,
            "model": BIAS_EVALUATOR_MODEL,
        }

        try:
            response = await call_llm(evaluator_config, prompt)
            output = response.get("output", "")
        except Exception as exc:
            print(
                f"Bias scoring fallback model={result['model']}: {exc}"
            )
            output = ""

        parsed = _extract_json_object(output)
        if parsed is None:
            parsed = _heuristic_bias_score(result.get("response", ""), user_query)
        else:
            raw_bias = parsed.get("bias_score", 0)
            try:
                raw_bias = float(raw_bias)
            except (TypeError, ValueError):
                raw_bias = 0.0

            parsed = {
                "bias_score": round(_clamp(raw_bias, 0.0, 10.0), 2),
                "bias_level": str(parsed.get("bias_level", "unknown")),
                "rationale": str(
                    parsed.get("rationale")
                    or parsed.get("explanation")
                    or parsed.get("bias_notes")
                    or ""
                ).strip() or "Prompt-based bias scorer returned a score.",
                "source": "prompt",
            }

        normalized_bias_score = _normalize_bias_score(parsed["bias_score"])
        return {
            "provider": result.get("provider"),
            "model": result.get("model"),
            "bias_score": parsed["bias_score"],
            "bias_score_normalized": normalized_bias_score,
            "bias_level": parsed.get("bias_level", "unknown"),
            "rationale": parsed.get("rationale", ""),
            "source": parsed.get("source", "unknown"),
        }

    tasks = [_score_response(result) for result in stage1_results]
    return await asyncio.gather(*tasks, return_exceptions=False)


def calculate_aggregate_rankings(
    stage2_results: List[Dict[str, Any]],
    label_to_model: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Calculate aggregate rankings across all models.

    Args:
        stage2_results: Rankings from each model
        label_to_model: Mapping from anonymous labels to model names

    Returns:
        List of dicts with model name and average rank, sorted best to worst
    """
    from collections import defaultdict

    # Track positions for each model
    model_positions = defaultdict(list)

    for ranking in stage2_results:
        ranking_text = ranking['ranking']

        # Parse the ranking from the structured format
        parsed_ranking = parse_ranking_from_text(ranking_text)

        for position, label in enumerate(parsed_ranking, start=1):
            if label in label_to_model:
                model_name = label_to_model[label]
                model_positions[model_name].append(position)

    total_candidates = max(len(label_to_model), 1)

    # Calculate average position for each model
    aggregate = []
    for model in dict.fromkeys(label_to_model.values()):
        positions = model_positions.get(model, [])
        if positions:
            avg_rank = sum(positions) / len(positions)
        else:
            avg_rank = float(total_candidates)

        aggregate.append({
            "model": model,
            "average_rank": round(avg_rank, 2),
            "performance_score": _normalize_performance_score(avg_rank, total_candidates),
            "rankings_count": len(positions)
        })

    # Sort by average rank (lower is better)
    aggregate.sort(key=lambda x: x['average_rank'])

    return aggregate


def build_fairness_leaderboard(
    aggregate_rankings: List[Dict[str, Any]],
    bias_scores: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Combine performance and bias into a final adjusted score."""
    bias_by_model = {
        item["model"]: item for item in bias_scores if item.get("model")
    }

    leaderboard = []
    for aggregate in aggregate_rankings:
        model_name = aggregate["model"]
        bias_entry = bias_by_model.get(model_name, {})
        performance_score = float(aggregate.get("performance_score", 0.0))
        normalized_bias = float(bias_entry.get("bias_score_normalized", 0.0))
        final_score = round(
            performance_score - (FAIRNESS_LAMBDA * normalized_bias),
            3,
        )

        leaderboard.append({
            **aggregate,
            "bias_score": float(bias_entry.get("bias_score", 0.0)),
            "bias_score_normalized": normalized_bias,
            "bias_level": bias_entry.get("bias_level", "unknown"),
            "bias_rationale": bias_entry.get("rationale", ""),
            "bias_source": bias_entry.get("source", "unknown"),
            "final_score": final_score,
            "fairness_lambda": FAIRNESS_LAMBDA,
        })

    leaderboard.sort(
        key=lambda item: (
            item["final_score"],
            item["performance_score"],
            -item["bias_score_normalized"],
            -item["average_rank"],
        ),
        reverse=True,
    )
    return leaderboard


def select_chairperson(
    fairness_leaderboard: List[Dict[str, Any]],
    stage1_results: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Choose the final chairperson from the fairness-adjusted leaderboard."""
    if fairness_leaderboard:
        best = max(
            fairness_leaderboard,
            key=lambda item: (
                item.get("final_score", 0.0),
                item.get("performance_score", 0.0),
                -item.get("bias_score_normalized", 0.0),
                -item.get("average_rank", 0.0),
            ),
        )
        return {
            **best,
            "source": "fairness_leaderboard",
        }

    if stage1_results:
        fallback = stage1_results[0]
        return {
            "provider": fallback.get("provider"),
            "model": fallback.get("model"),
            "average_rank": 1.0,
            "performance_score": 1.0,
            "bias_score": 0.0,
            "bias_score_normalized": 0.0,
            "bias_level": "unknown",
            "bias_rationale": "Fallback selection because no fairness leaderboard was available.",
            "bias_source": "fallback",
            "final_score": 1.0,
            "fairness_lambda": FAIRNESS_LAMBDA,
            "rankings_count": 0,
            "source": "fallback_stage1",
        }

    return {
        "provider": "gemini",
        "model": CHAIRMAN_MODEL,
        "average_rank": 1.0,
        "performance_score": 1.0,
        "bias_score": 0.0,
        "bias_score_normalized": 0.0,
        "bias_level": "unknown",
        "bias_rationale": "Fallback selection because no council responses were available.",
        "bias_source": "fallback",
        "final_score": 1.0,
        "fairness_lambda": FAIRNESS_LAMBDA,
        "rankings_count": 0,
        "source": "fallback_chairman",
    }


async def build_fairness_metadata(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]],
    label_to_model: Dict[str, str],
) -> Dict[str, Any]:
    """Build performance, bias, and selection metadata."""
    aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
    bias_scores = await evaluate_bias_scores(user_query, stage1_results)
    fairness_leaderboard = build_fairness_leaderboard(aggregate_rankings, bias_scores)
    chairperson_selection = select_chairperson(fairness_leaderboard, stage1_results)

    return {
        "aggregate_rankings": aggregate_rankings,
        "bias_scores": bias_scores,
        "fairness_leaderboard": fairness_leaderboard,
        "chairperson_selection": chairperson_selection,
    }


async def stage3_synthesize_final(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]],
    chairperson_selection: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Stage 3: Selected chairperson synthesizes the final response.

    Args:
        user_query: The original user query
        stage1_results: Individual model responses from Stage 1
        stage2_results: Rankings from Stage 2
        chairperson_selection: Fairness-adjusted selection metadata

    Returns:
        Dict with 'model' and 'response' keys
    """
    # Build comprehensive context for the selected chairperson
    stage1_text = "\n\n".join([
        f"Model: {result['model']}\nResponse: {result['response']}"
        for result in stage1_results
    ])

    stage2_text = "\n\n".join([
        f"Model: {result['model']}\nRanking: {result['ranking']}"
        for result in stage2_results
    ])

    chairperson_selection = chairperson_selection or select_chairperson([], stage1_results)
    selected_config = _resolve_model_config(chairperson_selection.get("model"))
    selected_model_name = chairperson_selection.get("model", selected_config["model"])

    chairman_prompt = f"""You are the selected chairperson of a fairness-aware LLM council.
You were chosen because your adjusted score best balanced response quality and bias.

Original Question: {user_query}

STAGE 1 - Individual Responses:
{stage1_text}

STAGE 2 - Peer Rankings:
{stage2_text}

FAIRNESS SELECTION:
Selected Model: {selected_model_name}
Performance Score: {chairperson_selection.get('performance_score', 0.0)}
Bias Score: {chairperson_selection.get('bias_score', 0.0)}
Final Score: {chairperson_selection.get('final_score', 0.0)}
Fairness Lambda: {chairperson_selection.get('fairness_lambda', FAIRNESS_LAMBDA)}

Your task as Chairperson is to synthesize all of this information into a single, comprehensive, accurate answer to the user's original question. Consider:
- The individual responses and their insights
- The peer rankings and what they reveal about response quality
- The fairness selection and how it balanced quality against bias
- Any patterns of agreement or disagreement

Provide a clear, well-reasoned final answer that represents the council's collective wisdom:"""

    chairperson_config = selected_config

    try:
        response = await call_llm(chairperson_config, chairman_prompt)
    except Exception as exc:
        print(f"Stage3 error provider={chairperson_config['provider']} model={selected_model_name}: {exc}")
        # Fallback if chairperson fails: synthesize a simple fallback from
        # available Stage 1 responses so the pipeline remains useful offline.
        fallback_text = None
        for r in stage1_results:
            if r.get("model") == selected_model_name:
                fallback_text = r.get("response", "")
                break

        if not fallback_text and stage1_results:
            # Use the first available response as a last resort
            fallback_text = stage1_results[0].get("response", "")

        synthesized = (
            "(Fallback synthesis - chairperson LLM unavailable)\n\n"
            "The system could not call the selected chairperson model.\n"
            "Using the best-available council response below:\n\n"
            f"{fallback_text}"
        )

        return {
            "model": selected_model_name,
            "response": synthesized,
            "selection": chairperson_selection,
        }

    if not response:
        # If the call returned an empty/falsey result, also provide the
        # same local fallback synthesis so the UI gets a helpful message.
        fallback_text = None
        for r in stage1_results:
            if r.get("model") == selected_model_name:
                fallback_text = r.get("response", "")
                break

        if not fallback_text and stage1_results:
            fallback_text = stage1_results[0].get("response", "")

        synthesized = (
            "(Fallback synthesis - chairperson LLM returned no content)\n\n"
            "Using the best-available council response below:\n\n"
            f"{fallback_text}"
        )

        return {
            "model": selected_model_name,
            "response": synthesized,
            "selection": chairperson_selection,
        }

    return {
        "model": response.get("model", selected_model_name),
        "response": response.get('output', ''),
        "selection": chairperson_selection,
    }


def parse_ranking_from_text(ranking_text: str) -> List[str]:
    """
    Parse the FINAL RANKING section from the model's response.

    Args:
        ranking_text: The full text response from the model

    Returns:
        List of response labels in ranked order
    """
    import re

    # Look for "FINAL RANKING:" section
    if "FINAL RANKING:" in ranking_text:
        # Extract everything after "FINAL RANKING:"
        parts = ranking_text.split("FINAL RANKING:")
        if len(parts) >= 2:
            ranking_section = parts[1]
            # Try to extract numbered list format (e.g., "1. Response A")
            # This pattern looks for: number, period, optional space, "Response X"
            numbered_matches = re.findall(r'\d+\.\s*Response [A-Z]', ranking_section)
            if numbered_matches:
                # Extract just the "Response X" part
                return [re.search(r'Response [A-Z]', m).group() for m in numbered_matches]

            # Fallback: Extract all "Response X" patterns in order
            matches = re.findall(r'Response [A-Z]', ranking_section)
            return matches

    # Fallback: try to find any "Response X" patterns in order
    matches = re.findall(r'Response [A-Z]', ranking_text)
    return matches


def calculate_aggregate_rankings(
    stage2_results: List[Dict[str, Any]],
    label_to_model: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Calculate aggregate rankings across all models.

    Args:
        stage2_results: Rankings from each model
        label_to_model: Mapping from anonymous labels to model names

    Returns:
        List of dicts with model name and average rank, sorted best to worst
    """
    from collections import defaultdict

    # Track positions for each model
    model_positions = defaultdict(list)

    for ranking in stage2_results:
        ranking_text = ranking['ranking']

        # Parse the ranking from the structured format
        parsed_ranking = parse_ranking_from_text(ranking_text)

        for position, label in enumerate(parsed_ranking, start=1):
            if label in label_to_model:
                model_name = label_to_model[label]
                model_positions[model_name].append(position)

    total_candidates = max(len(label_to_model), 1)

    # Calculate average position for each model
    aggregate = []
    for model in dict.fromkeys(label_to_model.values()):
        positions = model_positions.get(model, [])
        if positions:
            avg_rank = sum(positions) / len(positions)
        else:
            avg_rank = float(total_candidates)

        aggregate.append({
            "model": model,
            "average_rank": round(avg_rank, 2),
            "performance_score": _normalize_performance_score(avg_rank, total_candidates),
            "rankings_count": len(positions)
        })

    # Sort by average rank (lower is better)
    aggregate.sort(key=lambda x: x['average_rank'])

    return aggregate


async def generate_conversation_title(user_query: str) -> str:
    """
    Generate a short title for a conversation based on the first user message.

    Args:
        user_query: The first user message

    Returns:
        A short title (3-5 words)
    """
    title_prompt = f"""Generate a very short title (3-5 words maximum) that summarizes the following question.
The title should be concise and descriptive. Do not use quotes or punctuation in the title.

Question: {user_query}

Title:"""

    title_config = {"provider": "gemini", "model": "gemini-2.5-flash"}

    try:
        response = await call_llm(title_config, title_prompt)
    except Exception:
        response = None

    if response is None:
        # Fallback to a generic title
        return "New Conversation"

    title = response.get('output', 'New Conversation').strip()

    # Clean up the title - remove quotes, limit length
    title = title.strip('"\'')

    # Truncate if too long
    if len(title) > 50:
        title = title[:47] + "..."

    return title


async def run_full_council(user_query: str) -> Tuple[List, List, Dict, Dict]:
    """
    Run the complete 3-stage council process.

    Args:
        user_query: The user's question

    Returns:
        Tuple of (stage1_results, stage2_results, stage3_result, metadata)
    """
    # Stage 1: Collect individual responses
    stage1_results = await stage1_collect_responses(user_query)

    # If no models responded successfully, return error
    if not stage1_results:
        return [], [], {
            "model": "error",
            "response": "All models failed to respond. Please try again."
        }, {}

    # Stage 2: Collect rankings
    stage2_results, label_to_model = await stage2_collect_rankings(user_query, stage1_results)

    # Build fairness metadata and select the final chairperson
    fairness_metadata = await build_fairness_metadata(
        user_query,
        stage1_results,
        stage2_results,
        label_to_model,
    )

    # Stage 3: Synthesize final answer
    stage3_result = await stage3_synthesize_final(
        user_query,
        stage1_results,
        stage2_results,
        chairperson_selection=fairness_metadata["chairperson_selection"],
    )

    # Prepare metadata
    metadata = {
        "label_to_model": label_to_model,
        **fairness_metadata,
    }

    return stage1_results, stage2_results, stage3_result, metadata
