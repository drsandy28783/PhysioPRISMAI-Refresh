# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

# PhysiologicPRISM — Project Overview

A HIPAA-compliant physiotherapy clinical decision-support SaaS (Flask/Python). Clinicians use it to manage patients, run AI-assisted assessments, and generate treatment plans. Key constraints: all data handling must respect HIPAA BAA compliance; PHI must never leave Azure-backed services.

## Architecture

| Concern | Technology |
|---|---|
| Web framework | Flask 3.x + Gunicorn (3 gthread workers) |
| Database | Azure Cosmos DB (`azure_cosmos_db.py`) |
| Auth | Firebase Auth (token verification) + Flask-Login sessions |
| AI | Azure OpenAI GPT-4o (`azure_openai_client.py`) |
| Voice | Azure Speech Services (`azure_speech_client.py`) |
| Payments | Razorpay (`razorpay_integration.py`) |
| Email | Resend (`email_service.py`) |
| Messaging | Twilio SMS/WhatsApp (`messaging_service.py`) |
| Rate limiting | Flask-Limiter + Redis (`rate_limiter.py`) |
| Validation | Marshmallow schemas (`schemas.py`) |
| Security headers | Flask-Talisman |
| Error tracking | Sentry SDK |
| Deployment | Azure Container Apps via GitHub Actions (push to `main`) |

**`main.py`** is the primary Flask app — the majority of web routes live here. Two Flask Blueprints extend it:
- `mobile_api.py` — REST endpoints for the mobile app (`/api/*`), registered in `main.py`
- `mobile_api_ai.py` — AI suggestion endpoints for the mobile app (`/api/ai_suggestion/*`), also registered in `main.py`

Key module roles:
- `app_auth.py` — `require_firebase_auth` / `require_auth` decorators
- `quota_middleware.py` — `require_ai_quota`, `require_patient_quota`, `require_voice_quota` decorators (atomic, race-condition safe)
- `ai_cache.py` — caches Azure OpenAI responses
- `ai_prompts.py` — all clinical AI prompt templates
- `schemas.py` — Marshmallow schemas + `validate_data` / `validate_json` helpers
- `azure_cosmos_db.py` — Cosmos DB client wrapper; `SERVER_TIMESTAMP`, `DELETE_FIELD`, `Increment` are sentinel values
- `subscription_manager.py` — subscription state and quota tracking
- `quick_mode_service.py` — AI pre-fills for Quick Mode assessment screens; every public function returns a plain `dict` and never raises (empty dict signals failure so callers fall back to a blank form)
- `notification_service.py` — in-app notifications stored in Cosmos DB
- `appointment_reminder_scheduler.py` — triggered on-demand (not a daemon) to send SMS/WhatsApp reminders via `messaging_service.py`

## Commands

**Run locally:**
```bash
cp .env.example .env   # fill in values first
python main.py
```

**Run with Gunicorn (production-like):**
```bash
gunicorn -w 3 -k gthread -b 0.0.0.0:8080 --timeout 120 main:app
```

**Run tests:**
```bash
pip install -r requirements-test.txt
pytest                          # all tests
pytest -m unit                  # unit tests only
pytest -m "not integration"     # skip tests that hit external services
pytest tests/test_foo.py::test_bar  # single test
```

Available pytest markers: `unit`, `integration`, `slow`, `critical`, `api`. Playwright e2e tests live under `tests/playwright/` and have their own `pytest.ini`.

**Build Docker image:**
```bash
docker build -t physiologicprism-app .
docker run --env-file .env -p 8080:8080 physiologicprism-app
```

**Deployment** happens automatically on push to `main` via `.github/workflows/azure-container-app.yml` — it builds, pushes to ACR (`physiologicprismacr`), and updates the `physiologicprism-app` Container App in `rg-physiologicprism-prod`.

## Environment Setup

Copy `.env.example` to `.env`. Required vars the app validates at startup: `SECRET_KEY`, `RESEND_API_KEY`. Additional required in practice: `COSMOS_DB_*`, `AZURE_OPENAI_*`, `FIREBASE_PROJECT_ID`, `RAZORPAY_*`, `REDIS_HOST`. Redis can be absent (rate limiter degrades gracefully). See `.env.example` for the full list.

## Critical Invariants

**Append-only assessment sections.** Assessment records (subjective, objective, provisional diagnosis, etc.) are accumulated as separate Cosmos DB documents — they are never overwritten. When reading the latest assessment for a section, always order by `timestamp` DESC and take the first result. Overwriting instead of appending will silently corrupt the clinical history.

**Load-bearing `timezone` import in `main.py:92`.** The `timezone` symbol is imported via `from datetime import datetime, timedelta, timezone` on line 92 and referenced at ~10 call sites throughout `main.py`. Don't remove it when editing nearby imports because linters may flag it as "unused" on that line.

**`TOS_VERSION` must stay in sync.** `TOS_VERSION = '1.0'` is defined in both `main.py` and `mobile_api.py`. Bumping one without the other will break ToS acceptance flows in the other client.

**Cosmos DB partition key is `/id`.** All containers are created with `PartitionKey(path="/id")`. Every document is in its own logical partition, which means any query that doesn't filter on `id` is a cross-partition (fan-out) query. This is intentional for the current scale but relevant when adding new query patterns.

## HIPAA / Security Constraints

- PHI must only flow to Azure-backed services (Cosmos DB, Azure OpenAI, Azure Speech). Never Sentry, logs, or third-party APIs.
- `data_sanitization.py` sanitizes events before they reach Sentry.
- `geo_restriction.py` enforces geographic access controls.
- `consent_manager.py` tracks patient consent.
- All quota enforcement in `quota_middleware.py` uses atomic Cosmos DB operations — do not bypass or replicate quota logic outside that module.
- CSRF protection (Flask-WTF) is active on all mutating endpoints.

## CSP Nonce Rule (Critical)

Flask-Talisman is configured with `content_security_policy_nonce_in=['script-src']`, which means **every `<script>` tag in every template must have `nonce="{{ csp_nonce() }}"`** — no exceptions. This includes:

- Inline scripts: `<script nonce="{{ csp_nonce() }}">...</script>`
- External scripts: `<script src="..." nonce="{{ csp_nonce() }}"></script>`
- JSON-LD structured data: `<script type="application/ld+json" nonce="{{ csp_nonce() }}">...</script>`
- Third-party snippets (Google Analytics, Razorpay, Firebase, GTM, etc.)

Missing a nonce silently blocks the script at runtime and can break login, payments, or analytics. When adding any `<script>` tag — especially when copy-pasting from third-party docs — always add the nonce before committing.

---

# Behavioral Guidelines

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
