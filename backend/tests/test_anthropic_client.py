import pytest

from app import anthropic_client


# Class name is what is_timeout_error() keys on.
class APITimeoutError(Exception):
    pass


def _status_err(code):
    e = Exception(f"status {code}")
    e.status_code = code
    return e


def test_error_classifiers():
    assert anthropic_client.is_timeout_error(APITimeoutError())
    assert anthropic_client.is_retryable_error(APITimeoutError())
    assert anthropic_client.is_retryable_error(_status_err(429))   # rate limit -> retry
    assert anthropic_client.is_retryable_error(_status_err(503))   # 5xx -> retry
    assert not anthropic_client.is_retryable_error(_status_err(401))  # auth -> fail fast
    assert not anthropic_client.is_retryable_error(_status_err(400))  # bad request -> fail fast


class _Block:
    type = "text"
    text = "ok"


class _Resp:
    content = [_Block()]


def test_retries_transient_then_succeeds(monkeypatch):
    calls = {"n": 0}

    class FakeMessages:
        @staticmethod
        def create(**kw):
            calls["n"] += 1
            if calls["n"] < 3:
                raise APITimeoutError("slow")
            return _Resp()

    class FakeClient:
        messages = FakeMessages()

    monkeypatch.setattr(anthropic_client, "_get_client", lambda: FakeClient())
    out = anthropic_client.call_claude([{"role": "user", "content": "x"}], retries=3, backoff=0)
    assert out == "ok"
    assert calls["n"] == 3  # failed twice, succeeded on the third


def test_does_not_retry_on_auth_error(monkeypatch):
    calls = {"n": 0}

    class FakeMessages:
        @staticmethod
        def create(**kw):
            calls["n"] += 1
            raise _status_err(401)

    class FakeClient:
        messages = FakeMessages()

    monkeypatch.setattr(anthropic_client, "_get_client", lambda: FakeClient())
    with pytest.raises(Exception):
        anthropic_client.call_claude([{"role": "user", "content": "x"}], retries=3, backoff=0)
    assert calls["n"] == 1  # no retries on 401
