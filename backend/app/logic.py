"""Adaptive-engine helpers ported from the React Quiz component.

These encode behavior the frontend relies on; we compute them server-side so
the browser never needs the answer key.
"""
import re


def is_precision_question(level, answer, skill) -> bool:
    """Port of `isPrecisionQuestion(q)` from tutor_app.html.

    The "read it back" gate fires ONLY on hard problems (level 4-5) where the
    answer contains a decimal place (e.g. 1.05 vs 1.5) OR the skill is a
    mechanics skill. NOTE: this is intentionally narrower than the loose
    "all level 4-5" summary — it matches the original CODE exactly.
    """
    if level is None:
        level = 1
    if (level or 1) < 4:
        return False
    ans = str(answer if answer is not None else "")
    sk = str(skill if skill is not None else "").lower()
    has_decimal = re.search(r"\d\.\d", ans) is not None
    mechanic = re.search(r"(punctuat|comma|capital|quotation|dialogue|pronoun|apostrophe)", sk) is not None
    return has_decimal or mechanic
