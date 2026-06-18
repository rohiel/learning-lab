"""Supernote handwriting analysis (analyzeWork in the HTML).

Relays an uploaded image to the Messages API with the verbatim vision prompt.
HTTP endpoint (multipart upload) lands in Phase 3.
"""
from .anthropic_client import call_claude
from .prompts import build_work_analysis_context, build_work_analysis_system_prompt


def analyze_work(image_base64: str, media_type: str, problem_context: str = "") -> str:
    system = build_work_analysis_system_prompt()
    ctx = build_work_analysis_context(problem_context)
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_base64}},
                {"type": "text", "text": ctx + "\n\nRead my work and help me."},
            ],
        }
    ]
    return call_claude(messages, system, max_tokens=700)
