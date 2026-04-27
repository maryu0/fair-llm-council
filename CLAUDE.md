# CLAUDE.md - Technical Notes for LLM Council

This file contains technical details, architectural decisions, and important implementation notes for future development sessions.

## Project Overview

FairCouncil is a 3-stage deliberation system where multiple LLMs collaboratively answer user questions. The key innovation is bias-aware adaptive chairperson selection: peer review still happens in Stage 2, but the final synthesizer is chosen using a fairness-adjusted score.

## Architecture

### Backend Structure (`backend/`)

**`config.py`**

- Contains `COUNCIL_MODELS` (provider/model configs for Gemini and Groq)
- Contains `CHAIRMAN_MODEL` (model that synthesizes final answer)
- Uses environment variables `GEMINI_API_KEY` and `GROQ_API_KEY` from `.env`
- Backend runs on **port 8001** (NOT 8000 - user had another app on 8000)

**`openrouter.py`**

- `call_gemini()`: Direct Gemini client with retry/backoff
- `call_groq()`: Direct Groq client with timeout handling
- Returns dict with `model`, `output`, and `latency_ms`
- Graceful degradation: returns None on failure, continues with successful responses

**`council.py`** - The Core Logic

- `stage1_collect_responses()`: Parallel queries to all council models
- `stage2_collect_rankings()`:
  - Anonymizes responses as "Response A, B, C, etc."
  - Creates `label_to_model` mapping for de-anonymization
  - Prompts models to evaluate and rank (with strict format requirements)
  - Returns tuple: (rankings_list, label_to_model_dict)
  - Each ranking includes both raw text and `parsed_ranking` list
- `evaluate_bias_scores()`: Prompt-based fairness scoring with heuristic fallback
- `calculate_aggregate_rankings()`: Computes average rank position and performance score
- `build_fairness_leaderboard()`: Combines performance and bias into a final adjusted score
- `select_chairperson()`: Chooses the final model from the fairness leaderboard
- `stage3_synthesize_final()`: Selected chairperson synthesizes from all responses + rankings
- `parse_ranking_from_text()`: Extracts "FINAL RANKING:" section, handles both numbered lists and plain format

**`storage.py`**

- JSON-based conversation storage in `data/conversations/`
- Each conversation: `{id, created_at, messages[]}`
- Assistant messages contain: `{role, stage1, stage2, stage3, metadata}`
- Metadata now includes the label mapping, aggregate rankings, bias scores, fairness leaderboard, and selected chairperson

**`main.py`**

- FastAPI app with CORS enabled for localhost:5173 and localhost:3000
- POST `/api/conversations/{id}/message` returns metadata in addition to stages
- Metadata includes: label_to_model mapping, aggregate rankings, bias scores, fairness leaderboard, and chairperson selection

### Frontend Structure (`frontend/src/`)

**`App.jsx`**

- Main orchestration: manages conversations list and current conversation
- Handles message sending and metadata storage
- Important: metadata is stored in the UI state for display but not persisted to backend JSON

**`components/ChatInterface.jsx`**

- Multiline textarea (3 rows, resizable)
- Enter to send, Shift+Enter for new line
- User messages wrapped in markdown-content class for padding

**`components/Stage1.jsx`**

- Tab view of individual model responses
- ReactMarkdown rendering with markdown-content wrapper

**`components/Stage2.jsx`**

- **Critical Feature**: Tab view showing RAW evaluation text from each model
- De-anonymization happens CLIENT-SIDE for display (models receive anonymous labels)
- Shows "Extracted Ranking" below each evaluation so users can validate parsing
- Fairness leaderboard shows average rank, performance score, bias score, and final adjusted score
- Selected chairperson is highlighted for transparency

**`components/Stage3.jsx`**

- Final synthesized answer from the selected chairperson
- Green-tinted background (#f0fff0) to highlight conclusion

**Styling (`*.css`)**

- Light mode theme (not dark mode)
- Primary color: #4a90e2 (blue)
- Global markdown styling in `index.css` with `.markdown-content` class
- 12px padding on all markdown content to prevent cluttered appearance

## Key Design Decisions

### Stage 2 Prompt Format

The Stage 2 prompt is very specific to ensure parseable output:

```
1. Evaluate each response individually first
2. Provide "FINAL RANKING:" header
3. Numbered list format: "1. Response C", "2. Response A", etc.
4. No additional text after ranking section
```

This strict format allows reliable parsing while still getting thoughtful evaluations.

Bias scoring is handled separately after Stage 2 using a prompt-based fairness auditor plus a heuristic fallback so the system can still produce a chairperson when the bias scorer fails.

### De-anonymization Strategy

- Models receive: "Response A", "Response B", etc.
- Backend creates mapping: `{"Response A": "openai/gpt-5.1", ...}`
- Frontend displays model names in **bold** for readability
- Users see explanation that original evaluation used anonymous labels
- This prevents bias while maintaining transparency

### Error Handling Philosophy

- Continue with successful responses if some models fail (gr
- If fairness scoring fails, fall back to a heuristic bias score and then select the chairperson from the best available adjusted scoreaceful degradation)
- Never fail the entire request due to single model failure
- Log errors but don't expose to user unless all models fail

### UI/UX Transparency

- All raw outputs are inspectable via tabs
- Parsed rankings shown below raw text for validation
- Users can verify system's interpretation of model outputs
- This builds trust and allows debugging of edge cases

## Important Implementation Details

### Relative Imports

All backend modules use relative imports (e.g., `from .config import ...`) not absolute imports. This is critical for Python's module system to work correctly when running as `python -m backend.main`.

### Port Configuration

- Backend: 8001 (changed from 8000 to avoid conflict)
- Frontend: 5173 (Vite default)
- Update both `backend/main.py` and `frontend/src/api.js` if changing

### Markdown Rendering

All ReactMarkdown components must be wrapped in `<div className="markdown-content">` for proper spacing. This class is defined globally in `index.css`.

### Model Configuration

Models are hardcoded in `backend/config.py`. Chairman can be same or different from council members. The current default is Gemini as chairman per user preference.

## Common Gotchas

1. **Module Import Errors**: Always run backend as `python -m backend.main` from project root, not from backend directory
2. **CORS Issues**: Frontend must match allowed origins in `main.py` CORS middleware
3. **Ranking Parse Failures**: If models don't follow format, fallback regex extracts any "Response X" patterns in order
4. **Missing Metadata**: Metadata is ephemeral (not persisted), only available in API responses

## Future Enhancement Ideas

- Configurable council/chairman via UI instead of config file
- Streaming responses instead of batch loading
- Export conversations to markdown/PDF
- Model performance analytics over time
- Custom ranking criteria (not just accuracy/insight)
- Support for reasoning models (o1, etc.) with special handling

## Testing Notes

Use `test_free_pipeline.py` to verify the Gemini and Groq provider paths, timeout handling, and Stage 1 orchestration.

## Data Flow Summary

```
User Query
    ↓
Stage 1: Parallel queries → [individual responses]
Bias Evaluation Layer → [bias scores per response]
    ↓
Fairness Leaderboard → [performance score - lambda x bias score]
    ↓
Stage 3: Selected chairperson synthesis with full context
    ↓
Return: {stage1, stage2, stage3, metadata}
    ↓
Frontend: Display with tabs + validation UI + fairness leaderboard
Return: {stage1, stage2, stage3, metadata}
    ↓
Frontend: Display with tabs + validation UI
```

The entire flow is async/parallel where possible to minimize latency.
