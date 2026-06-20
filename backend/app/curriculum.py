"""The 8-week math + english curriculum, interest themes, and pacing helpers.

Every literal in this file is lifted VERBATIM from `tutor_app.html`
(MATH_WEEKS, ENGLISH_WEEKS, LEXILE_BY_WEEK, passageLines, INTEREST_THEMES,
MODES, practiceCount). Do not paraphrase — the tutoring behavior depends on
this exact text.
"""
import math

# --- MATH_WEEKS (verbatim) ---
MATH_WEEKS = {
    1: {"title": "Number & Operations", "focus": "Decimals: division into decimals, decimal addition & subtraction. Multi-step word problems hiding the operation.", "level": "decimals"},
    2: {"title": "Number & Operations II", "focus": "Decimal multiplication & division mastery. Place value with decimals. Two-operation word problems.", "level": "decimals"},
    3: {"title": "Fractions, Decimals & %", "focus": "Converting between fractions, decimals, percentages. Fraction addition & subtraction.", "level": "fractions"},
    4: {"title": "Fractions II", "focus": "Fraction multiplication & division. Mixed numbers. Word problems combining fractions and decimals.", "level": "fractions"},
    5: {"title": "Ratios & Proportions", "focus": "Ratios, proportions, unit rates. The heaviest 6th-grade concept — depends on fraction/decimal mastery.", "level": "ratios"},
    6: {"title": "Operations & Algebraic Thinking", "focus": "Order of operations (PEMDAS), properties, writing basic expressions. Her 'Low' MAP area.", "level": "algebra"},
    7: {"title": "Geometry, Area & Volume", "focus": "Coordinate planes, area of complex shapes, intro to volume.", "level": "geometry"},
    8: {"title": "Data & Diagnostic", "focus": "Mean, median, mode, range. Comprehensive review and readiness test.", "level": "data"},
}

# --- ENGLISH_WEEKS (verbatim) ---
ENGLISH_WEEKS = {
    1: {"title": "Foundation & Mechanics", "focus": "Prefix/suffix decoding, context clues, pronoun rules, dialogue punctuation.", "lexile": "515-550"},
    2: {"title": "Mechanics II", "focus": "Sentence-level mechanics, capitalization, periods, punctuation execution. Catching rushing errors.", "lexile": "550-580"},
    3: {"title": "Root Words & Sentence Combining", "focus": "Greek & Latin roots. Combining simple sentences into complex ones using conjunctions.", "lexile": "580-620"},
    4: {"title": "Roots II & Complex Sentences", "focus": "More roots, eliminating choppy writing, informational text comprehension.", "lexile": "620-660"},
    5: {"title": "Advanced Editing & Paragraphs", "focus": "Tier-2 academic words, outlining, writing one flawless paragraph at a time.", "lexile": "660-700"},
    6: {"title": "Paragraph Structure II", "focus": "Multi-paragraph structure, main idea, supporting detail across subjects.", "lexile": "700-730"},
    7: {"title": "6th Grade Readiness Stamina", "focus": "Speed drills on roots/prefixes. Reading science/history articles, highlighting main ideas.", "lexile": "730-760"},
    8: {"title": "Readiness Stamina II", "focus": "Heavy proofreading challenges — she edits highly flawed texts. Stretch toward 780L.", "lexile": "760-780"},
}

# Lexile target by week (English reading) — verbatim
LEXILE_BY_WEEK = {1: 540, 2: 570, 3: 600, 4: 640, 5: 680, 6: 715, 7: 745, 8: 780}

# Session modes — verbatim
MODES = {
    "practice": {"label": "Practice", "count": 12, "icon": "🌱", "desc": "daily practice"},
    "test": {"label": "Weekly Test", "count": 15, "icon": "🏆", "desc": "once a week"},
}

# Anam's interest universe — shared across math + reading (verbatim)
INTEREST_THEMES = """Anam's interests (weave these into every passage and word problem):
- Nature: trees, grass, flowers, plant biology
- Insects, bugs, flies (entomology)
- Rocks, minerals, precious stones, gem formation (earth science / geology)
- Fiction tone she loves: thriller + comedy + MILD gore (never extreme), in the voice of Raina Telgemeier graphic novels (Smile, Guts, Sisters) — personal, funny, a little gross, real emotions.
Math word problems and reading passages should share the SAME world when possible (e.g. a passage about Venus flytraps pairs with a math problem about how many flies it catches)."""


def _js_round(x: float) -> int:
    """Match JavaScript's Math.round (round half UP) for positive inputs,
    so pacing matches the original app exactly."""
    return math.floor(x + 0.5)


def practice_count(day: int) -> int:
    """Daily practice grows in length across the week (verbatim logic).
    Day 1 -> 10 questions, +~0.8/day, capped at 15 by end of week."""
    return min(10 + _js_round((day - 1) * 0.83), 15)


def passage_lines(week: int, day: int) -> int:
    """Passage line length: starts low each week, grows. (verbatim logic)"""
    week_floor = {1: 5, 2: 8, 3: 10, 4: 12, 5: 14, 6: 16, 7: 18, 8: 20}
    floor = week_floor.get(week, 5)
    return min(floor + (day - 1) * 2, floor + 12)
