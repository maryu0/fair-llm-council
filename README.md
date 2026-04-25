# FairCouncil

![llmcouncil](header.jpg)

FairCouncil is a bias-aware adaptive LLM council.
It extends the original council pattern by selecting the final decision-maker dynamically based on both response quality and bias, instead of using a permanently fixed chairperson.

The system is designed for free-tier model APIs and Google Cloud friendly operation.
Instead of routing through OpenRouter, it calls providers directly:

- Gemini (Google AI Studio API)
- Groq (OpenAI-compatible chat API)

## Core Idea

FairCouncil computes an adjusted leadership score for each candidate model:

$$
	ext{Final Score} = \text{Performance Score} - \lambda \times \text{Bias Score}
$$

Where:

- Performance Score: response quality, correctness, and reasoning ability
- Bias Score: measured social, cultural, or linguistic bias in the response
- $\lambda$: fairness weighting factor that controls how strongly bias penalizes selection

The model with the best adjusted score becomes the adaptive chairperson for final synthesis.

## System Workflow

1. Input Processing: accept user query and optionally classify query type.
2. Stage 1 (Multi-Model Generation): collect independent responses in parallel.
3. Stage 2 (Peer Review and Ranking): models evaluate anonymized candidate answers.
4. Bias Evaluation Layer: score each response for bias signals.
5. Adaptive Chairperson Selection: choose final model via fairness-aware scoring.
6. Stage 3 (Final Response): selected chairperson synthesizes the final answer.

## Key Features

- Bias-aware aggregation: fairness is integrated into selection, not only post-processing.
- Dynamic leadership: different queries can produce different chairperson models.
- Model-agnostic routing: unified provider layer supports multiple backends.
- Transparent evaluation: intermediate outputs (responses, rankings, bias scores) can be surfaced.

## Current Default Models

Configured in `backend/config.py`:

```python
COUNCIL_MODELS = [
    {"provider": "gemini", "model": "gemini-2.5-flash"},
    {"provider": "groq", "model": "llama-3.1-8b-instant"},
]

CHAIRMAN_MODEL = "gemini-2.5-flash"
```

## Project Structure

- `backend/`: FastAPI API, council orchestration, provider transports, local JSON storage
- `frontend/`: React + Vite UI
- `test_free_pipeline.py`: free-tier integration tests for Gemini/Groq router paths

## Setup

### 1. Install Dependencies

Backend (Python):

```bash
uv sync
python -m pip install google-generativeai groq python-dotenv pytest
```

Frontend:

```bash
cd frontend
npm install
cd ..
```

### 2. Configure Environment

Create `.env` in the project root (or copy from `.env.example`):

```bash
GEMINI_API_KEY=your_google_ai_studio_key
GROQ_API_KEY=your_groq_key
```

Notes:

- Free-tier quotas apply per provider project/account.
- Rotate keys immediately if exposed.
- Do not commit `.env`.

### 3. Optional Model Customization

Edit `backend/config.py` and keep the same shape:

```python
COUNCIL_MODELS = [
    {"provider": "gemini", "model": "gemini-2.5-flash"},
    {"provider": "groq", "model": "llama-3.1-8b-instant"},
]
```

## Running the Application

### Option 1: Start Script (Unix-like shells)

```bash
./start.sh
```

### Option 2: Manual Start (recommended on Windows)

Terminal 1 (Backend):

```bash
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8001
```

Terminal 2 (Frontend):

```bash
cd frontend
npm run dev -- --host 0.0.0.0 --port 5173
```

Open http://localhost:5173.

## Quick Integration Check (Parallel Provider Calls)

Run from repo root:

```bash
python -c "
import asyncio
from backend.llm_router import call_llm
from backend.config import COUNCIL_MODELS

async def test():
    prompt = 'Explain bias in AI in one sentence.'
    tasks = [call_llm(cfg, prompt) for cfg in COUNCIL_MODELS]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for r in results:
        print(r if isinstance(r, dict) else f'Error: {r}')

asyncio.run(test())
"
```

Expected: two response dicts (Gemini + Groq), typically within a few seconds total.

## Tests

Run free-tier integration tests:

```bash
python -m pytest -q test_free_pipeline.py
```

These tests validate:

- direct Gemini call path
- direct Groq call path
- stage timeout handling and graceful failure isolation

## Google Cloud Deployment Notes

This codebase is suitable for Google Cloud deployment (for example Cloud Run for backend + static/frontend hosting).
Minimum production recommendations:

- store API keys in Secret Manager (not in files)
- inject secrets as environment variables
- enable request logging/monitoring
- apply egress and quota safeguards for free-tier model usage

## Tech Stack

- Backend: FastAPI, asyncio, httpx, google-generativeai, groq
- Frontend: React + Vite
- Storage: JSON files in `data/conversations/`
- Tooling: uv (Python), npm (frontend), pytest (tests)
