# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Local dev
python main.py                          # Start server on :8080

# Docker (production)
docker build -t 3hmind:latest .         # Build image
docker compose -f docker-compose-new.yml up -d  # Full stack with Caddy

# Deploy to remote (47.101.212.254)
# Uses sshpass/plink to sync code + restart container:
# 1. tar czf /tmp/3hmind_deploy.tar.gz . (excluding data/.git/__pycache__/.venv/uploads/node_modules)
# 2. scp to remote
# 3. docker compose -f docker-compose-new.yml down 3hmind && docker compose up -d 3hmind

# Test endpoints
curl http://localhost:8080/                                      # Health check
curl -X POST http://localhost:8080/api/auth/login -H "Content-Type: application/json" -d '{"username":"admin","password":"<pw>"}'  # Login
curl -X POST http://localhost:8080/api/voice/refine -H "Content-Type: application/json" -H "Authorization: Bearer <token>" -d '{"text":"..."}'  # Voice refine

# Kill process on :8080 (Windows)
$p = Get-NetTCPConnection -LocalPort 8080 | Select-Object -First 1; if ($p) { Stop-Process -Id $p.OwningProcess -Force }

# No tests/lint configured — no Makefile, pytest config, or linting setup
```

## Architecture Overview

### 5-Layer Cognitive Pipeline (agent.py → UnifiedAgent)

```
Layer 1: Input     (input_layer/input_parser.py + document_processor.py)
  → Normalizes text, voice, document, video, camera input into unified format

Layer 2: Intent    (intent_layer/intent_parser.py)
  → Two-level intent parsing: surface command + LLM deep motivation inference
  → 6 growth scenario templates (goal decomposition, emotional awareness, habit, decisions, learning, career)
  → Ambiguity detection for fuzzy input

Layer 3: Memory    (mind_layer/memory_orchestrator.py)
  → Central memory coordinator: SQLite (8 tables) + ChromaDB vector store + topic memory
  → User-per-user isolation: data/{username}/memory.db + chroma_db/
  → 8 topic domains auto-detected (tech, career, deep thinking, learning, health, relationships, daily, english)
  → Auto profile extraction from conversation
  → Session context buffer + periodic consolidation

Layer 4: Dispatch  (dispatch_layer/dispatcher.py + thinking_guide.py + progress_tracker.py + assessment_engine.py)
  → Intent-driven task execution
  → Thinking scaffolds (decomposition, pros/cons, review, planning)
  → Goal progress monitoring (stale detection, celebration)
  → Assessment engine: 4-dimension scoring (knowledge, progress, review, deep thinking) with expert rules + LLM

Layer 5: Output    (output_layer/output_adapter.py + response_builder.py)
  → Multi-format adaptation (text/voice/display)
  → Unified response construction
```

### Key Data Flow

```
User Input → input_parser → intent_parser (with memory context) 
  → reasoning_layer (LLM analysis) → dispatcher → response_builder → output_adapter
```

### Backend Schedule

`AutonomousScheduler` (scheduler.py) runs two background loops per user:
- **Reflection** every 60 min (configurable via `AUTO_REFLECT_INTERVAL_MIN`)
- **Nudge** every 120 min (configurable via `AUTO_NUDGE_INTERVAL_MIN`)
Results stored in `_pending` dict, polled via `GET /api/poll`

### Database (per-user SQLite)

8 tables in `data/{username}/memory.db`: profile, goals, abilities, history, insights, gaps, plans, topic_entries, plus goal_dimensions, assessment_records, learning_sessions.

### Assessment Engine (dispatch_layer/assessment_engine.py)

Closed-loop learning assessment system:
- Baseline → Learn → Question → Feedback → Verify → Iterate
- 4 weighted dimensions: knowledge(40%) + progress(30%) + review(20%) + deep thinking(10%)
- Composite score = Σ(dimension_score × weight)
- LLM provides domain-specific suggestions with concrete knowledge points and resource recommendations

### Voice Pipeline

Browser recording → Whisper-compatible API (aliyun DashScope) → `refine_voice_text()` (LLM corrects homophone errors) → normal process → browser TTS playback

### Legacy Compatibility

- `reasoning/` directory is the LLM engine (used by agent.py via `ReasoningLayer`)
- `memory/`, `perception/`, `interaction/` are legacy stubs — real logic is in `mind_layer/`, `dispatch_layer/`
- `legacy/` directory has bridge classes for backward compatibility

### Frontend (Single-page app, zero build)

7 JS modules in `web/static/js/`: api, auth, state, ui, voice, chat, app
No build step — served directly by FastAPI. Use `curl` to verify cache headers on static assets.

### Key Config (config.py → Settings)

All via `.env` file, pydantic-settings backed. Must set: `LLM_API_KEY`, `JWT_SECRET_KEY`, `DEFAULT_ADMIN_PASSWORD`. Default LLM is `deepseek-v4-pro` at `api.deepseek.com/v1`.
