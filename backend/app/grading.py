"""Server-side grading + Socratic help (checkAnswer / getHint / askHelp).

These run on the server so the `solution` and `answer` never reach the browser.
HTTP endpoints wiring these up land in Phase 3; the logic + prompts are ported
verbatim here now.
"""
import re

from .anthropic_client import call_claude
from .jsonutils import extract_json
from .prompts import (
    build_check_answer_prompts,
    build_help_system_prompt,
    build_hint_prompts,
)

# Skills where punctuation/capitalization ARE the answer (grammar grading is strict).
_GRAMMAR_RE = re.compile(
    r"(punctuat|comma|capital|quotation|dialogue|pronoun|apostrophe|grammar|sentence)"
)


def is_grammar_skill(skill) -> bool:
    return bool(_GRAMMAR_RE.search(str(skill or "").lower()))


def _norm_numeric(s) -> str:
    # numeric/other normalized compare (matches the HTML submit() path)
    return re.sub(r"[^a-z0-9./\-]", "", re.sub(r"[\s$,]", "", str(s).lower()))


def grade_answer(subject, question, expected, given, skill) -> dict:
    """Grade one answer: exact/normalized match first, model grader only if needed.

    Returns {"correct": bool, "reason": str}.
    """
    is_grammar = is_grammar_skill(skill)

    if is_grammar:
        # punctuation/capitalization matters — don't strip it; collapse whitespace only
        exact = re.sub(r"\s+", " ", str(given)).strip() == re.sub(r"\s+", " ", str(expected)).strip()
        if exact:
            return {"correct": True, "reason": "exact match"}
    else:
        if _norm_numeric(given) == _norm_numeric(expected):
            return {"correct": True, "reason": "match"}

    return check_answer(subject, question, expected, given, is_grammar)


def check_answer(subject, question, expected, given, is_grammar: bool) -> dict:
    """Model-graded fallback (checkAnswer in the HTML)."""
    system, user = build_check_answer_prompts(question, expected, given, is_grammar)
    try:
        txt = call_claude([{"role": "user", "content": user}], system, max_tokens=200, timeout=18.0, retries=1)
        return extract_json(txt)
    except Exception:
        # never hang: loose string compare fallback
        norm = lambda s: re.sub(r"[^a-z0-9.]", "", str(s).lower())
        return {"correct": norm(expected) == norm(given), "reason": ""}


def get_hint(subject, question, given, expected, has_distractor=False, distractor_note="") -> str:
    """Socratic nudge when wrong — never reveals the answer (getHint)."""
    system, user = build_hint_prompts(question, given, expected, has_distractor, distractor_note)
    return call_claude([{"role": "user", "content": user}], system, max_tokens=150, timeout=15.0, retries=1)


def ask_help(problem_context, subject, history, off_topic_count, solution, answer, choices) -> str:
    """The 'I'm stuck' chat — anchored to the answer key (askHelp)."""
    system = build_help_system_prompt(problem_context, subject, off_topic_count, solution, answer, choices)
    msgs = [{"role": h["role"], "content": h["content"]} for h in history]
    return call_claude(msgs, system, max_tokens=300)
