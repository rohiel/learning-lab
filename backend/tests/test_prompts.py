from app.prompts import (
    build_help_system_prompt,
    build_hint_prompts,
    build_question_system_prompt,
    build_question_user_prompt,
)


def test_math_prompt_preserves_core_rules():
    s = build_question_system_prompt("math", 1, 540, 1, [], [], 6, 4)
    assert "EVERY question is a WORD PROBLEM that hides the operation" in s
    assert "CRITICAL — NUMBER CONSISTENCY" in s
    assert '"solution"' in s
    assert "No confirmed weak spots yet" in s
    # the one deviation: per-level targeting
    assert "ALL at difficulty level 4" in s


def test_weak_spot_weighting_text():
    s = build_question_system_prompt("math", 1, 540, 1, ["decimal division"], [], 6, 2)
    assert "70% of questions should hit these" in s
    assert "decimal division" in s


def test_retention_note_included():
    s = build_question_system_prompt("math", 2, 570, 3, [], ["place value"], 6, 1)
    assert "LONG-TERM RETENTION CHECK" in s
    assert "place value" in s


def test_english_prompt_rules():
    s = build_question_system_prompt("english", 1, 540, 1, [], [], 6, 1)
    assert 'ALWAYS use "fill" type for these, NEVER "mc"' in s
    assert "pronoun case" in s
    assert "pronoun order" in s
    assert "Target Lexile ~540L" in s


def test_user_prompt_targets_level():
    u = build_question_user_prompt("math", 1, 6, 3)
    assert "level 3" in u
    assert "Week 1" in u


def test_help_prompt_anchors_to_solution_and_redirects():
    s = build_help_system_prompt(
        problem_context="2 + 2?", subject="math", off_topic_count=2,
        solution="add 2 and 2 to get 4", answer="4", choices=None,
    )
    assert "ANSWER KEY (hidden from her" in s
    assert "add 2 and 2 to get 4" in s
    assert "gone off-topic for 2+ messages" in s


def test_hint_prompt_handles_distractor():
    _system, _user = build_hint_prompts("q", "12", "8", True, "the $3.50 price is not needed")
    assert "the $3.50 price is not needed" in _system
    assert "DON'T reveal it" in _user
