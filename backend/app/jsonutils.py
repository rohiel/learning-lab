"""Robust JSON extraction/recovery for model output.

Direct port of extractJSON / recoverJSON / remainingClosers / salvageQuestions
from tutor_app.html. Even though pre-generation isn't latency-bound, the model
can still emit fenced or slightly-truncated JSON, so we keep the same recovery
chain as a safety net.
"""
import json
import re


def extract_json(text: str):
    t = text.strip()
    # strip code fences
    t = re.sub(r"^```json\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"^```\s*", "", t)
    t = re.sub(r"```\s*$", "", t)

    # jump to first opening bracket/brace
    start = t.find("{")
    start_a = t.find("[")
    s = start
    if start_a != -1 and (start == -1 or start_a < start):
        s = start_a
    if s > 0:
        t = t[s:]

    # First try: clean parse on the slice up to the last closing bracket
    last_b = t.rfind("}")
    last_a = t.rfind("]")
    e = max(last_b, last_a)
    candidate = t[: e + 1] if e != -1 else t
    try:
        return json.loads(candidate)
    except Exception:
        pass

    return recover_json(t)


def recover_json(t: str):
    """Recover a truncated/garbled JSON object or array by tracking bracket
    depth and string state, then closing what's open."""
    in_str = False
    esc = False
    stack = []
    last_good_element_end = -1

    for i, c in enumerate(t):
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
            continue
        if c in "{[":
            stack.append(c)
        elif c in "}]":
            if stack:
                stack.pop()
        # closing an object that sits directly inside an array => complete element
        if c == "}" and len(stack) >= 1 and stack[-1] == "[":
            last_good_element_end = i + 1

    # Strategy A: truncate to the last complete array element, then close brackets.
    if last_good_element_end != -1:
        head = t[:last_good_element_end]
        repaired = head + remaining_closers(head)
        try:
            return json.loads(repaired)
        except Exception:
            pass

    # Strategy B: close whatever is open at the very end.
    try:
        return json.loads(t + remaining_closers(t))
    except Exception:
        pass

    # Strategy C: salvage individual complete objects.
    salvaged = salvage_questions(t)
    if salvaged:
        return {"questions": salvaged}

    raise ValueError("Could not parse questions from the tutor response. Please try again.")


def remaining_closers(s: str) -> str:
    in_str = False
    esc = False
    stack = []
    for c in s:
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
            continue
        if c in "{[":
            stack.append(c)
        elif c == "}":
            if stack and stack[-1] == "{":
                stack.pop()
        elif c == "]":
            if stack and stack[-1] == "[":
                stack.pop()
    out = '"' if in_str else ""
    for x in reversed(stack):
        out += "}" if x == "{" else "]"
    return out


def salvage_questions(t: str):
    """Scan for complete {...} objects and json.loads each individually."""
    out = []
    depth = 0
    in_str = False
    esc = False
    start_idx = -1
    for i, c in enumerate(t):
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
            continue
        if c == "{":
            if depth == 0:
                start_idx = i
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0 and start_idx != -1:
                chunk = t[start_idx : i + 1]
                try:
                    obj = json.loads(chunk)
                    if obj and obj.get("question"):
                        out.append(obj)
                except Exception:
                    pass
                start_idx = -1
    return out
