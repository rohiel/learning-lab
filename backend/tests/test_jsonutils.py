from app.jsonutils import extract_json, salvage_questions


def test_clean_object():
    assert extract_json('{"a": 1}') == {"a": 1}


def test_strips_code_fences():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_leading_prose_then_json():
    assert extract_json('Sure! Here you go:\n{"questions": []}') == {"questions": []}


def test_recovers_truncated_array():
    # last object is cut off mid-way (the original "Test" bug)
    txt = '{"questions":[{"question":"q1","answer":"1"},{"question":"q2","answer":'
    out = extract_json(txt)
    assert "questions" in out
    assert len(out["questions"]) >= 1
    assert out["questions"][0]["question"] == "q1"


def test_salvage_individual_objects():
    txt = 'junk {"question":"a","answer":"1"} mid {"question":"b","answer":"2"} tail {bad'
    salvaged = salvage_questions(txt)
    assert [o["question"] for o in salvaged] == ["a", "b"]
