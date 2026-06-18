# Anam's Learning Lab — Backend (Phase 1)

FastAPI + SQLAlchemy backend that holds the Anthropic API key, stores progress,
and pre-generates the daily question bank. All tutoring prompts, the curriculum,
and the question schema are lifted **verbatim** from `../tutor_app.html`.

> **Phase 1 scope:** project scaffold, all 6 data models, the generation module
> (prompts ported), and a working `generate-day` admin endpoint + seed so you can
> test pre-generation immediately. The nightly scheduler (Phase 2), the gameplay
> endpoints + React port (Phase 3), and Docker/deploy (Phase 4) come next.

## Layout

```
backend/
  app/
    config.py          settings (env): keys, DB url, model, tz
    curriculum.py      MATH_WEEKS / ENGLISH_WEEKS / lexile / themes  (verbatim)
    prompts.py         every system/user prompt                      (verbatim)
    jsonutils.py       extractJSON/recoverJSON port (truncation-safe)
    anthropic_client.py call_claude() — the key lives here only
    generation.py      generate_day_pool(): 5-7 questions x level 1-5
    grading.py         grade_answer / get_hint / ask_help (server-side)
    vision.py          analyze_work (Supernote image)
    review.py          parent_review / review_writing
    models.py          students, question_pool, sessions, answers,
                       weak_spots, progress_flags
    schemas.py         QuestionPublic (NO answer/solution) vs internal
    auth.py            X-API-Key shared secret
    routers/admin.py   /api/health, /api/admin/generate-day, /api/admin/pool
    main.py            app factory
  seed.py              create student "Anam"
  tests/               run without an API key (Anthropic is mocked)
```

## Run locally

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env            # then edit .env: set ANTHROPIC_API_KEY + API_SHARED_SECRET
python seed.py                  # creates student "Anam" (prints the student_id)
uvicorn app.main:app --reload   # http://127.0.0.1:8000  (docs at /docs)
```

### Smoke-test pre-generation

```bash
# liveness
curl -s localhost:8000/api/health

# build Week 1 / Day 1 math pool for the seeded student (id likely 1)
curl -s -X POST localhost:8000/api/admin/generate-day \
  -H "X-API-Key: $API_SHARED_SECRET" -H "Content-Type: application/json" \
  -d '{"student_id":1,"subject":"math","week":1,"day":1}'
# -> {"...":"...","total":31,"per_level":{"1":6,"2":7,"3":6,"4":6,"5":6}}

# inspect what's stored (note: solutions are NOT returned)
curl -s "localhost:8000/api/admin/pool?student_id=1&subject=math&week=1&day=1" \
  -H "X-API-Key: $API_SHARED_SECRET"
```

`generate-day` is **idempotent** — a day's pool is built once and is otherwise
static. Pass `"force": true` to rebuild. `"count_per_level": N` overrides the
5-7 default (handy for a quick cheap test).

> Real generation needs `ANTHROPIC_API_KEY` set and outbound access to
> `api.anthropic.com`. The test suite mocks the client, so it needs neither.

## Tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

Covers: JSON-recovery, the precision-gate predicate, prompt invariants (incl.
the 70% weak-spot weighting and the per-level deviation), generation level-
pinning, `solution`/`answer` exclusion from `QuestionPublic`, and the full
`generate-day` HTTP flow with auth + idempotency.

## Environment variables

| Var | Default | Notes |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | **required** to generate. Server-only. |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | preserved from the HTML |
| `ANTHROPIC_TIMEOUT` | `40` | seconds per call |
| `ANTHROPIC_MAX_RETRIES` | `1` | transient-error retries |
| `API_SHARED_SECRET` | `change-me` | the `X-API-Key` the frontend sends |
| `DATABASE_URL` | `sqlite:///./data/tutor.db` | swap to Postgres with no code change |
| `SCHEDULER_TZ` | `America/New_York` | DST-aware Eastern (Phase 2) |
| `SCHEDULER_HOUR` | `20` | nightly run hour, local (Phase 2) |
| `FRONTEND_ORIGIN` | `*` | comma-separated CORS origins |
| `PER_LEVEL_MIN` / `PER_LEVEL_MAX` | `5` / `7` | pool size per level |

## Security notes

- The Anthropic key is read only in `anthropic_client.py` from the env; it is
  never returned or logged.
- `QuestionPublic` (the only question shape sent to the browser) omits `answer`,
  `solution`, and `distractor_note`. A precomputed `precision` flag drives the
  read-it-back gate without leaking the answer.
- All `/api` routes except `/health` require the `X-API-Key` header.
