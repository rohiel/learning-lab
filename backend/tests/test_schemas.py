from types import SimpleNamespace

from app.schemas import QuestionPublic


def _row(**kw):
    base = dict(
        id=1, type="fill", passage=None, question="q", choices=None,
        level=5, skill="decimal division", retention=False, connection=False,
        answer="1.05", solution="divide then round", distractor_note=None,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_public_question_omits_answer_key():
    pub = QuestionPublic.from_row(_row())
    dumped = pub.model_dump()
    assert "answer" not in dumped
    assert "solution" not in dumped
    assert "distractor_note" not in dumped


def test_precision_flag_computed_server_side():
    # level 5 + decimal answer -> gate fires
    assert QuestionPublic.from_row(_row()).precision is True
    # plain integer, non-mechanic -> no gate
    assert QuestionPublic.from_row(_row(answer="8", skill="addition")).precision is False
