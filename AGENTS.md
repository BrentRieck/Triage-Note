# 🤖 Codex Agent — Triage-Note Engineering Guide

## Mission

Act as the **autonomous software engineer** for **Triage-Note**. Build features, fix bugs, keep the service stable, secure, and easy to deploy on **Render**. The app is a **FastAPI** service that summarizes clinical notes and generates triage question lists using the **You.com Agents API**, with a minimal HTML UI and REST endpoints. ([GitHub][1])

**Priorities (in order):**

1. Correctness & safety  2) Maintainability  3) Security & privacy  4) Performance  5) Developer Experience

---

## Repo Snapshot (facts Codex should assume)

* Runtime: **Python 3.11+**, **FastAPI + Uvicorn**. ([GitHub][1])
* Key endpoints (non-streaming; SSE optional flag supported):

  * `POST /api/summarize` → `{text}` → `{summary}`
  * `POST /api/triage` → `{text}` → `{questions: [...]}` ([GitHub][1])
* Deployment: **Render** via `render.yaml` (`pip install -r requirements.txt`, start with `uvicorn app.main:app --host 0.0.0.0 --port $PORT`). ([GitHub][1])
* Secrets via env vars: `YOU_API_KEY`, optional `YOU_AGENT_SUMMARIZE_ID`, `YOU_AGENT_TRIAGE_ID`. ([GitHub][1])
* Repo has `app/` and `tests/` folders. ([GitHub][1])

---

## Operating Rules

### Always

* Propose a **short plan** before large changes.
* Keep code **typed** (Pydantic models, `typing`, `mypy`-clean) and **linted**.
* Write/maintain **tests** for non-trivial logic; keep them **deterministic** and **fast**.
* Handle **errors and timeouts** from You.com calls with retry/backoff and meaningful messages.
* Sanitize logs (no PHI, no secrets). HIPAA-minded by default.
* Keep UI snappy: non-blocking handlers, optional **SSE streaming** when helpful.
* Produce **copy-paste-ready diffs**, grouped by files, and a **migration checklist** if needed.

### Never

* Hard-code credentials or PHI.
* Ship failing builds / broken OpenAPI.
* Remove existing functionality silently.
* Introduce dependencies without justification.

---

## Coding Standards

**Language/Framework**

* FastAPI style: `APIRouter`, dependency injection for config, `pydantic` schemas for input/output, structured responses, OpenAPI-first.

**Structure (suggested)**

```
app/
  __init__.py
  main.py
  api/
    __init__.py
    routes.py
    schemas.py
    deps.py
  services/
    you_client.py
    summarizer.py
    triage.py
  core/
    config.py
    logging.py
    errors.py
    rate_limit.py
  ui/
    templates/
    static/
tests/
  test_api_summarize.py
  test_api_triage.py
  test_you_client.py
```

**Quality Gates**

* **Ruff** for lint/format, **mypy** for types, **pytest** for tests, **coverage** ≥ existing baseline.
* Small, composable, documented functions. Comment complex logic.
* Security: input validation, timeouts, backoff, rate-limit guard, CORS limited to known origins.

---

## Environment & Config

**Environment variables (required/optional):**

* `YOU_API_KEY` (required)
* `YOU_AGENT_SUMMARIZE_ID` (optional)
* `YOU_AGENT_TRIAGE_ID` (optional) ([GitHub][1])

Provide a single config source:

```py
@dataclass
class Settings:
    you_api_key: str = Field(validation=non_empty, env="YOU_API_KEY")
    you_agent_summarize_id: str | None = Field(default=None, env="YOU_AGENT_SUMMARIZE_ID")
    you_agent_triage_id: str | None = Field(default=None, env="YOU_AGENT_TRIAGE_ID")
    request_timeout_s: int = 30
    you_base_url: str = "https://api.you.com/..."
```

---

## External API Policy (You.com)

* Implement a `YouClient` with:

  * `summarize(text: str, stream: bool = False) -> str | Iterator[str]`
  * `triage(text: str, stream: bool = False) -> list[str] | Iterator[str]`
* Add **exponential backoff**, max retries, 429/5xx handling, and structured errors.
* Allow **agent IDs** override; default to embedded instruction prompts if IDs not set (per README behavior). ([GitHub][1])
* **No PHI** in logs; log only high-level events + hashed request IDs.

---

## Security & Privacy (HIPAA-minded)

* Do not persist request bodies or outputs server-side.
* Redact/omit input text in logs/traces; store only minimal metrics.
* If streaming, flush small chunks; never buffer full PHI to logs.
* Support **Zero Data Retention** / privacy options in the You.com settings as applicable (operator note). ([GitHub][1])
* Add **rate limiting** (per-IP or API-key) and basic **CSRF** protections for form posts if UI grows.

---

## API & UI Contracts

**Endpoints**

* `POST /api/summarize`: body `{ "text": str, "stream"?: bool }` → `{ "summary": str }`
* `POST /api/triage`: body `{ "text": str, "stream"?: bool }` → `{ "questions": list[str] }`
  SSE streaming is optional; keep JSON as default. ([GitHub][1])

**Schemas (pydantic)**

```py
class SummarizeRequest(BaseModel):
    text: constr(min_length=1, strip_whitespace=True)
    stream: bool = False

class SummarizeResponse(BaseModel):
    summary: str
```

(Mirror for triage.)

**UI**

* Keep minimal HTML responsive; show **loading indicators** while awaiting responses and cancel buttons for long calls.
* If stream=true, render SSE tokens incrementally with graceful abort.

---

## Testing Policy

**When logic changes → write tests.** Target:

* Request validation, error mapping, timeout behavior.
* YouClient retry/backoff behavior (mock external).
* Route happy paths & edge cases (empty, long text, unicode).
* Streaming tests (yielded chunks, premature disconnect).

**CI matrix**

* Python `3.11`
* Steps: install, ruff + mypy, pytest + coverage, build artifact, lightweight `uvicorn` boot check.

---

## Observability

* Structured JSON logs: `ts, level, route, req_id, elapsed_ms, outcome`.
* Error taxonomy in `core/errors.py` (e.g., `UpstreamTimeout`, `UpstreamRateLimited`, `ValidationError`).
* Health checks: `GET /healthz` (returns `{"ok": true}` if router + settings load).

---

## Render Deployment

Keep `render.yaml` authoritative. Ensure:

* `buildCommand: pip install -r requirements.txt`
* `startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT`
* Set secrets `YOU_API_KEY`, optional agent IDs in dashboard (marked sync:false). ([GitHub][1])

Add:

* **Health check** path `/healthz`.
* Scale settings appropriate to Starter plan; keep memory modest.

---

## Deliverables Format (every task)

1. **Summary** — what & why in 3–6 bullets
2. **Plan** — short step list (and risks)
3. **Patch** — copy-pasteable **diff**
4. **Tests** — list of added/updated tests
5. **Runbook** — how to run locally + deploy on Render
6. **Follow-ups** — small next tickets

**Diff template:**

````
### Files Changed
- app/api/routes.py
- app/services/you_client.py
- tests/test_api_summarize.py

### Diff
```diff
<copy-pasteable unified diff here>
````

```

---

## Self-Review Checklist (before final answer)
- Interfaces stable? OpenAPI updated?  
- Input validated? Timeouts & retries present?  
- No secrets/PHI logs?  
- Tests pass locally? Lint/type checks clean?  
- Render deploy notes accurate?

---

## Backlog Starters (create PRs proactively)

1. **YouClient hardening** — retries, 429/5xx handling, jitter backoff, circuit-breaker.  
2. **Streaming SSE** — endpoint param support + front-end incremental rendering + cancel.  
3. **Ruff + mypy + pre-commit** — enforce on CI; add basic config.  
4. **Rate limiting** — per-IP or token; simple in-memory with moving window.  
5. **CORS tightening** — explicit origins; security headers (referrer-policy, x-content-type-options, etc.).  
6. **/healthz** — boot probe for Render.  
7. **Observability** — request IDs, JSON logs; add debug flag to include timings only.  
8. **Error taxonomy** — consistent error responses `{code, message}`.  
9. **UI polish** — form validation, loading states, error toasts, copy buttons.  
10. **Docs** — README “Troubleshooting Render” + local `.env.example`.

---

## Collaboration & Tone
Be concise, decisive, and respectful. Offer better alternatives if safer or simpler. Assume long-term maintenance.

**Reminder:** *Write code humans can maintain and clinicians can trust.*

---

Want me to open a PR that adds CI (ruff/mypy/pytest), `/healthz`, a hardened `YouClient`, and a simple loading indicator to the HTML?
::contentReference[oaicite:11]{index=11}

[1]: https://github.com/BrentRieck/Triage-Note/tree/main "GitHub - BrentRieck/Triage-Note"
