"""Parent review + writing review (parentReview / reviewWriting in the HTML).

HTTP endpoints land in Phase 3; prompts + parsing ported verbatim here.
"""
import json

from .anthropic_client import call_claude
from .prompts import build_parent_review_system_prompt, build_writing_review_system_prompt


def parent_review(log: dict) -> str:
    system = build_parent_review_system_prompt()
    user = f"Here is Anam's recent session log (JSON):\n{json.dumps(log)[:6000]}\n\nGive me the parent review."
    return call_claude([{"role": "user", "content": user}], system, max_tokens=1000)


def review_writing(text: str, prompt: str, target_words, weak_spots) -> dict:
    """Returns {"feedback": str, "meta": dict}. Splits the hidden ###json tail."""
    system = build_writing_review_system_prompt(weak_spots, target_words)
    user = f"Prompt was: {prompt}\n\nHer paragraph:\n{text}"
    raw = call_claude([{"role": "user", "content": user}], system, max_tokens=700)

    feedback, meta = raw, {}
    idx = raw.rfind("###")
    if idx != -1:
        feedback = raw[:idx].strip()
        try:
            meta = json.loads(raw[idx + 3:].strip())
        except Exception:
            meta = {}
    return {"feedback": feedback, "meta": meta}
