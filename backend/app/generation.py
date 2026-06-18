"""Question-pool generation — the heart of the pre-generated bank.

For each day we generate 5-7 questions PER difficulty level (1-5), ~25-35 total,
weighted ~70% toward weak spots via the prompt's weak-note (exactly as the
original app weighted its live batches). Unlike the live app there's no latency
pressure, so we generate one calm call per level instead of parallel batches —
but we keep the same JSON-recovery safety net.
"""
import random

from .anthropic_client import call_claude
from .config import settings
from .curriculum import LEXILE_BY_WEEK
from .jsonutils import extract_json
from .prompts import (
    build_question_system_prompt,
    build_question_user_prompt,
    build_writing_prompt_system,
)


def _safe_parse_questions(txt: str) -> list:
    try:
        parsed = extract_json(txt)
    except Exception:
        return []
    arr = parsed.get("questions", []) if isinstance(parsed, dict) else parsed
    return arr if isinstance(arr, list) else []


def generate_level_questions(subject, week, day, level, count, weak_spots, retention_queue) -> list[dict]:
    """Generate `count` questions all pinned to `level`."""
    lexile = LEXILE_BY_WEEK[week]
    system = build_question_system_prompt(
        subject, week, lexile, day, weak_spots, retention_queue, count, level
    )
    user = build_question_user_prompt(subject, week, count, level)
    txt = call_claude([{"role": "user", "content": user}], system, max_tokens=4000, timeout=40.0, retries=1)

    out: list[dict] = []
    for q in _safe_parse_questions(txt):
        if not isinstance(q, dict) or not q.get("question"):
            continue
        q["level"] = level  # enforce the target level regardless of what the model set
        out.append(q)
    return out


def generate_day_pool(subject, week, day, weak_spots, retention_queue, count_per_level=None) -> list[dict]:
    """Generate a full day's pool: levels 1..5, 5-7 questions each."""
    pool: list[dict] = []
    for level in range(1, 6):
        n = count_per_level if count_per_level is not None else random.randint(
            settings.per_level_min, settings.per_level_max
        )
        pool.extend(generate_level_questions(subject, week, day, level, n, weak_spots, retention_queue))
    return pool


def generate_writing_prompt(week, day, practiced_words, weak_spots) -> dict:
    """Port of generateWritingPrompt() — picks 3 target words and a line count."""
    lines = min(5 + (day - 1) // 2, 8)
    word_list = practiced_words[-12:] if practiced_words else ["mineral", "specimen", "fragile", "ancient", "burrow"]
    pool = list(word_list)
    targets: list[str] = []
    for _ in range(3):
        if not pool:
            break
        targets.append(pool.pop(random.randrange(len(pool))))

    system = build_writing_prompt_system(lines, targets)
    txt = call_claude([{"role": "user", "content": "Make today's writing prompt."}], system, max_tokens=500)
    try:
        p = extract_json(txt)
        if not p.get("targetWords"):
            p["targetWords"] = targets
        if not p.get("lines"):
            p["lines"] = lines
        return p
    except Exception:
        return {
            "prompt": f"Write {lines} sentences about a strange rock you found that might be alive. Use these words: {', '.join(targets)}.",
            "targetWords": targets,
            "lines": lines,
        }
