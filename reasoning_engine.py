"""
Reasoning Engine — Core GenAI + Logic layer
Covers:
- Novel Point 3: Real-time evaluation (expected vs actual delay)
- Novel Point 4: GenAI-Driven Threat Reasoning (cyber-physical attack chains)
- Novel Point 5: Intelligent Dashboard Layer (operator-friendly explanation)
- Agentic next-action decision
Aligned with paper's functional safety validation + TARA threat assessment.
"""
from llm_client import query_llm
from prompt_templates import (
    get_threat_reasoning_prompt,
    get_explanation_prompt,
    get_next_action_prompt
)
import json


def evaluate_scenario(parsed: dict, scenario: dict) -> dict:
    """
    Novel Point 3: Real-Time Validation — pure deterministic logic.
    Compares expected vs actual delay, computes risk score, flags violations.
    Mirrors the paper's event-chain rule checking (e1 before e2).
    """
    max_delay = parsed["max_delay_ms"]
    actual_delay = scenario["actual_delay_ms"]
    violation = actual_delay > max_delay
    risk_score = round(actual_delay / max_delay, 3)

    # Event chain timing breakdown (from scenario)
    chain_timing = scenario.get("event_chain_timing", [])
    bottleneck = None
    if chain_timing:
        # Find the slowest step in the chain
        bottleneck = max(chain_timing, key=lambda x: x.get("time_ms", 0))

    return {
        "violation": violation,
        "risk_score": risk_score,
        "actual_delay_ms": actual_delay,
        "expected_delay_ms": max_delay,
        "scenario_type": scenario.get("type"),
        "bottleneck_step": bottleneck,
        "road_condition": scenario.get("parameters", {}).get("road_condition"),
        "ecu_cpu_load": scenario.get("parameters", {}).get("ecu_cpu_load_pct")
    }


def evaluate_all_scenarios(parsed: dict, scenarios: list) -> list:
    return [evaluate_scenario(parsed, s) for s in scenarios]


def generate_threat_reasoning(parsed: dict, scenario: dict, evaluation: dict) -> dict:
    """
    Novel Point 4: GenAI-Driven Threat Reasoning.
    Generates cyber-physical attack chains + severity + TARA-aligned risk assessment.
    """
    prompt = get_threat_reasoning_prompt(parsed, scenario, evaluation)
    response = query_llm(prompt, temperature=0.6)

    try:
        json_start = response.find("{")
        json_end = response.rfind("}") + 1
        return json.loads(response[json_start:json_end])
    except Exception:
        return {
            "attack_chain": ["Unable to parse threat chain"],
            "software_to_physical_impact": "Unknown",
            "severity": "UNKNOWN",
            "risk_assessment": "Fallback: manual review required",
            "mitigation": "Consult safety engineer"
        }


def generate_all_threats(parsed: dict, scenarios: list, evaluations: list) -> list:
    threats = []
    for s, e in zip(scenarios, evaluations):
        print(f"      🔍 [{s.get('type','?').upper()}] threat reasoning...")
        threats.append(generate_threat_reasoning(parsed, s, e))
    return threats


def generate_explanation(parsed: dict, scenarios: list, evaluations: list,
                         threats: list, memory: list) -> str:
    """
    Novel Point 5: Intelligent Dashboard Layer — operator-friendly GenAI explanation.
    """
    prompt = get_explanation_prompt(parsed, scenarios, evaluations, threats, memory)
    return query_llm(prompt, temperature=0.4)


def decide_next_action(parsed: dict, evaluations: list, threats: list, memory: list) -> dict:
    """
    Agentic decision: autonomous reasoning about what to test next.
    """
    prompt = get_next_action_prompt(parsed, evaluations, threats, memory)
    response = query_llm(prompt, temperature=0.5)

    try:
        json_start = response.find("{")
        json_end = response.rfind("}") + 1
        return json.loads(response[json_start:json_end])
    except Exception:
        return {
            "next_action": "stress test at higher delay",
            "target_delay_ms": parsed.get("max_delay_ms", 100) + 30,
            "scenario_type": "stress",
            "focus_condition": "icy",
            "reason": "Fallback: explore boundary violations",
            "should_continue": True
        }