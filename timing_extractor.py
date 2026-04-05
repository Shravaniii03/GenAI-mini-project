"""
timing_extractor.py — MODULE 3: GenAI Timing Constraint Extractor
══════════════════════════════════════════════════════════════════
🔥 THIS IS THE MAIN NOVELTY of the project.

The base paper uses event chains but does NOT extract timing constraints
from requirements text, ISO 26262 rules, or code comments using GenAI.

This module does exactly that:
  Input:  "Braking must be immediate per ISO 26262"
  Output: {"sensor_latency_ms": 10, "decision_latency_ms": 50, "actuator_latency_ms": 40}

Also enriches with RAG-retrieved ISO 26262 rules for grounding.
Paper reference: Section I — "LLMs lack guarantees on timing determinism"
"""

import json
import re
from typing import Optional
from llm_client import query_llm


# ──────────────────────────────────────────────────────────────────────
# Heuristic keyword → timing budget mapping
# Used as fallback / cross-check against LLM output
# ──────────────────────────────────────────────────────────────────────
_KEYWORD_TIMING = {
    "immediate":      {"total_ms": 100,  "component": "braking_system"},
    "emergency":      {"total_ms": 100,  "component": "braking_system"},
    "brake":          {"total_ms": 100,  "component": "braking_system"},
    "braking":        {"total_ms": 100,  "component": "braking_system"},
    "steer":          {"total_ms": 200,  "component": "steering_ecu"},
    "steering":       {"total_ms": 200,  "component": "steering_ecu"},
    "lane":           {"total_ms": 200,  "component": "lane_departure_system"},
    "alert":          {"total_ms": 50,   "component": "alert_module"},
    "warn":           {"total_ms": 50,   "component": "alert_module"},
    "abs":            {"total_ms": 20,   "component": "abs_system"},
    "antilock":       {"total_ms": 20,   "component": "abs_system"},
    "traction":       {"total_ms": 30,   "component": "traction_control"},
    "esc":            {"total_ms": 50,   "component": "esc_system"},
    "stability":      {"total_ms": 50,   "component": "esc_system"},
    "pedestrian":     {"total_ms": 100,  "component": "braking_system"},
    "airbag":         {"total_ms": 15,   "component": "airbag_ecu"},
    "collision":      {"total_ms": 15,   "component": "airbag_ecu"},
    "accelerat":      {"total_ms": 300,  "component": "acc_system"},
    "cruise":         {"total_ms": 300,  "component": "acc_system"},
}

# Standard ISO 26262 breakdown ratios
_ISO_BREAKDOWN_RATIO = {
    "sensor_ms":    0.10,  # 10% of total
    "perception_ms": 0.30,  # 30%
    "decision_ms":  0.20,  # 20%
    "command_ms":   0.10,  # 10%
    "actuator_ms":  0.30,  # 30%
}


def _heuristic_timing(text: str) -> Optional[dict]:
    """Fast keyword-based timing extraction as fallback."""
    text_lower = text.lower()

    # Direct ms/s extraction: "within 100ms", "in 0.1s", "under 200 milliseconds"
    ms_match = re.search(r'(\d+)\s*ms', text_lower)
    s_match  = re.search(r'(\d+(?:\.\d+)?)\s*(?:seconds?|s\b)', text_lower)

    if ms_match:
        total = int(ms_match.group(1))
    elif s_match:
        total = int(float(s_match.group(1)) * 1000)
    else:
        # Use keyword lookup
        total = None
        for keyword, info in _KEYWORD_TIMING.items():
            if keyword in text_lower:
                total = info["total_ms"]
                break

    if total is None:
        return None

    return {
        "total_ms":     total,
        "breakdown_ms": {k: round(v * total) for k, v in _ISO_BREAKDOWN_RATIO.items()},
        "source":       "heuristic"
    }


def extract_timing_llm(text: str, source_type: str = "requirement") -> dict:
    """
    LLM-powered timing constraint extraction.
    source_type: "requirement" | "iso_rule" | "code_comment" | "architecture"
    """
    prompt = f"""
You are an ISO 26262 functional safety expert for Software-Defined Vehicles.
Your task is GenAI Timing Constraint Extraction — the main novelty of this system.

Source type: {source_type.upper()}
Input text: "{text}"

Extract precise timing constraints with ISO 26262 ASIL-level justification.

Rules:
- If the text says "immediate" for braking, map to 100ms (ISO 26262 ASIL-D)
- If a specific ms/s value is given, use it exactly
- Break down total latency into per-step budgets
- Map to the correct automotive component
- Identify applicable ASIL level

Output STRICT JSON only. No markdown. No explanation.

{{
    "event": "<safety action being timed>",
    "total_latency_ms": <integer>,
    "component": "<sdv component>",
    "asil_level": "<ASIL_A|ASIL_B|ASIL_C|ASIL_D>",
    "iso_rule_id": "<ISO rule like ISO26262-6-8.4.5 or null>",
    "breakdown_ms": {{
        "sensor_ms": <int>,
        "perception_ms": <int>,
        "decision_ms": <int>,
        "command_ms": <int>,
        "actuator_ms": <int>
    }},
    "confidence": "<HIGH|MEDIUM|LOW>",
    "reasoning": "<one line explanation>"
}}
"""
    response = query_llm(prompt, temperature=0.1)
    try:
        start = response.find("{")
        end   = response.rfind("}") + 1
        result = json.loads(response[start:end])
        result["source"] = "llm"
        return result
    except Exception:
        # Fallback to heuristic
        h = _heuristic_timing(text)
        if h:
            return {
                "event": "unknown",
                "total_latency_ms": h["total_ms"],
                "component": "braking_system",
                "asil_level": "ASIL_D",
                "iso_rule_id": None,
                "breakdown_ms": h["breakdown_ms"],
                "confidence": "LOW",
                "reasoning": "Heuristic fallback — LLM parse failed",
                "source": "heuristic_fallback"
            }
        raise ValueError(f"Timing extraction failed for: {text}")


def extract_timing_from_requirement(requirement: str) -> dict:
    """Extract timing from a natural language safety requirement."""
    return extract_timing_llm(requirement, source_type="requirement")


def extract_timing_from_iso_rule(rule_text: str) -> dict:
    """Extract timing from an ISO 26262 rule description."""
    return extract_timing_llm(rule_text, source_type="iso_rule")


def extract_timing_from_code_comment(comment: str) -> dict:
    """Extract timing from code comments/annotations."""
    return extract_timing_llm(comment, source_type="code_comment")


def extract_timing_from_architecture(arch_text: str) -> dict:
    """Extract timing from architecture/design document text."""
    return extract_timing_llm(arch_text, source_type="architecture")


def enrich_with_iso_rules(timing_result: dict, iso_rules: list) -> dict:
    """
    Cross-reference extracted timing with loaded ISO 26262 rules from knowledge base.
    Adds canonical rule reference and validates extracted values.
    """
    component = timing_result.get("component", "")
    extracted_ms = timing_result.get("total_latency_ms", 0)

    for rule in iso_rules:
        if rule.get("component", "") in component or component in rule.get("component", ""):
            canonical_ms = rule.get("max_latency_ms", 0)
            timing_result["iso_canonical_ms"] = canonical_ms
            timing_result["iso_rule_id"]       = rule.get("rule_id")
            timing_result["asil_level"]         = rule.get("asil_level", timing_result.get("asil_level"))

            if extracted_ms > canonical_ms:
                timing_result["iso_warning"] = (
                    f"Extracted {extracted_ms}ms exceeds ISO canonical {canonical_ms}ms — "
                    f"requirement may be unsafe"
                )
            else:
                timing_result["iso_compliant"] = True
            break

    return timing_result


# ──────────────────────────────────────────────────────────────────────
# CLI test
# ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    test_inputs = [
        "Braking must be immediate per ISO 26262",
        "The vehicle shall steer within 200ms of lane departure",
        "Alert driver within 50ms if speed limit is exceeded",
        "Emergency stop within 150ms if camera detects pedestrian",
    ]

    text = sys.argv[1] if len(sys.argv) > 1 else test_inputs[0]
    print(f"\n[TimingExtractor] Input: {text}")
    result = extract_timing_from_requirement(text)
    print(json.dumps(result, indent=2))