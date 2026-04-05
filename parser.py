"""
parser.py — Requirement Understanding (GenAI)

Role:
✔ Extract semantic structure (event, trigger, component, event_chain)
❌ DOES NOT extract timing anymore (handled by timing_extractor)

This separation improves:
- modularity
- novelty clarity
- paper justification
"""

from llm_client import query_llm
import json


def parse_requirement(requirement: str) -> dict:
    """
    Extract semantic structure from requirement.
    """

    prompt = f"""
You are an automotive safety analyst.

Extract the STRUCTURE of this requirement (NOT timing values).

Requirement:
"{requirement}"

OUTPUT STRICT JSON:

{{
  "event": "<main action>",
  "trigger": "<what triggers the event>",
  "component": "<system component>",
  "event_chain": ["<step1>", "<step2>", "<step3>", "<step4>"]
}}

RULES:
- DO NOT include timing values
- Focus only on semantic understanding
- Keep event_chain logical and sequential
"""

    response = query_llm(prompt, temperature=0.1)

    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        parsed = json.loads(response[start:end])

        required = ["event", "trigger", "component", "event_chain"]

        for field in required:
            if field not in parsed:
                raise ValueError(f"Missing field: {field}")

        return parsed

    except Exception:
        return {
            "event": "unknown",
            "trigger": "unknown",
            "component": "unknown",
            "event_chain": [],
            "source": "fallback"
        }