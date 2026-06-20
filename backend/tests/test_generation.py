import json

from app import generation

CANNED = json.dumps(
    {
        "questions": [
            {"type": "fill", "question": "A Venus flytrap caught 3 flies Monday and 5 Tuesday. How many total?",
             "answer": "8", "solution": "3 + 5 = 8", "level": 1, "skill": "addition"},
            {"type": "mc", "question": "Which rock is hardest?", "choices": ["talc", "quartz", "gypsum", "chalk"],
             "answer": "quartz", "solution": "Mohs scale", "level": 1, "skill": "reasoning"},
        ]
    }
)


def test_generate_level_enforces_level(monkeypatch):
    monkeypatch.setattr(generation, "call_claude", lambda *a, **k: CANNED)
    qs = generation.generate_level_questions("math", 1, 1, 3, 2, [], [])
    assert len(qs) == 2
    assert all(q["level"] == 3 for q in qs)  # level pinned regardless of model output


def test_generate_day_pool_spans_all_levels(monkeypatch):
    monkeypatch.setattr(generation, "call_claude", lambda *a, **k: CANNED)
    pool = generation.generate_day_pool("math", 1, 1, [], [], count_per_level=2)
    assert len(pool) == 10  # 5 levels x 2 questions
    assert sorted({q["level"] for q in pool}) == [1, 2, 3, 4, 5]


def test_generation_survives_unparseable_output(monkeypatch):
    monkeypatch.setattr(generation, "call_claude", lambda *a, **k: "the model rambled and produced no json")
    qs = generation.generate_level_questions("math", 1, 1, 2, 5, [], [])
    assert qs == []


def test_writing_prompt_fallback(monkeypatch):
    monkeypatch.setattr(generation, "call_claude", lambda *a, **k: "not json")
    p = generation.generate_writing_prompt(1, 1, [], [])
    assert "prompt" in p and len(p["targetWords"]) == 3 and p["lines"] == 5
