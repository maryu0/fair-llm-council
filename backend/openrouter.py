"""OpenRouter API client for making LLM requests."""

import asyncio
import os
import time
import httpx
import google.generativeai as genai
from groq import AsyncGroq
from typing import List, Dict, Any, Optional
from .config import OPENROUTER_API_KEY, OPENROUTER_API_URL

try:
    from google.api_core.exceptions import ResourceExhausted, TooManyRequests
    RATE_LIMIT_ERRORS = (ResourceExhausted, TooManyRequests)
except Exception:
    RATE_LIMIT_ERRORS = ()


async def call_gemini(
    prompt: str,
    model: str = "gemini-2.5-flash"
) -> Optional[Dict[str, Any]]:
    """
    Query Gemini directly via Google AI Studio free-tier API.

    Returns:
        Dict with provider tag, output text, and latency in milliseconds,
        or None if the request fails.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error querying model gemini: GEMINI_API_KEY is not set")
        return None

    genai.configure(api_key=api_key)
    max_retries = 3

    for attempt in range(max_retries + 1):
        start = time.perf_counter()
        try:
            def _generate_content():
                client = genai.GenerativeModel(model)
                return client.generate_content(prompt)

            response = await asyncio.to_thread(_generate_content)
            output = (getattr(response, "text", "") or "").strip()

            latency_ms = int((time.perf_counter() - start) * 1000)
            return {
                "model": "gemini",
                "output": output,
                "latency_ms": latency_ms,
            }

        except Exception as e:
            error_text = str(e).lower()
            is_rate_limited = (
                (bool(RATE_LIMIT_ERRORS) and isinstance(e, RATE_LIMIT_ERRORS))
                or "429" in error_text
                or "rate limit" in error_text
                or "resource_exhausted" in error_text
            )

            if is_rate_limited and attempt < max_retries:
                await asyncio.sleep(2 ** attempt)
                continue

            print(f"Error querying model gemini: {e}")
            return None


async def call_groq(
    prompt: str,
    model: str = "llama-3.1-8b-instant"
) -> Optional[Dict[str, Any]]:
    """
    Query Groq directly via free-tier API.

    Returns:
        Dict with provider tag, output text, and latency in milliseconds,
        or None if the request fails.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("Error querying model groq: GROQ_API_KEY is not set")
        return None

    client = AsyncGroq(api_key=api_key, timeout=30.0)
    start = time.perf_counter()

    try:
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
            ),
            timeout=30.0,
        )

        output = response.choices[0].message.content or ""
        latency_ms = int((time.perf_counter() - start) * 1000)

        return {
            "model": "groq",
            "output": output,
            "latency_ms": latency_ms,
        }

    except Exception as e:
        print(f"Error querying model groq: {e}")
        return None
    finally:
        await client.close()


async def query_model(
    model: str,
    messages: List[Dict[str, str]],
    timeout: float = 120.0
) -> Optional[Dict[str, Any]]:
    """
    Query a single model via OpenRouter API.

    Args:
        model: OpenRouter model identifier (e.g., "openai/gpt-4o")
        messages: List of message dicts with 'role' and 'content'
        timeout: Request timeout in seconds

    Returns:
        Response dict with 'content' and optional 'reasoning_details', or None if failed
    """
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                OPENROUTER_API_URL,
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            data = response.json()
            message = data['choices'][0]['message']

            return {
                'content': message.get('content'),
                'reasoning_details': message.get('reasoning_details')
            }

    except Exception as e:
        print(f"Error querying model {model}: {e}")
        return None


async def query_models_parallel(
    models: List[str],
    messages: List[Dict[str, str]]
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Query multiple models in parallel.

    Args:
        models: List of OpenRouter model identifiers
        messages: List of message dicts to send to each model

    Returns:
        Dict mapping model identifier to response dict (or None if failed)
    """
    import asyncio

    # Create tasks for all models
    tasks = [query_model(model, messages) for model in models]

    # Wait for all to complete
    responses = await asyncio.gather(*tasks)

    # Map models to their responses
    return {model: response for model, response in zip(models, responses)}
