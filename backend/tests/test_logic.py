from app.logic import is_precision_question


def test_precision_gate_matches_original_predicate():
    # level >= 4 AND (decimal answer OR mechanics skill)
    assert is_precision_question(5, "1.05", "decimal division") is True   # decimal
    assert is_precision_question(4, "1.05", "addition") is True           # decimal, level 4
    assert is_precision_question(4, "8", "dialogue punctuation") is True  # mechanic skill
    assert is_precision_question(5, "8", "pronoun order") is True         # mechanic skill

    # excluded cases
    assert is_precision_question(4, "8", "addition") is False             # integer, not mechanic
    assert is_precision_question(3, "1.05", "decimal division") is False  # level < 4
    assert is_precision_question(1, "1.05", "dialogue punctuation") is False
    assert is_precision_question(None, None, None) is False
