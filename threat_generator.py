"""
threat_generator.py — MODULE 5: GenAI Topology-Aware Threat Generator
══════════════════════════════════════════════════════════════════════
Extends the base paper's basic threat reasoning to topology-aware
cyber-physical attack chain generation with TARA risk scoring.

Novel: uses system architecture + known attack patterns (RAG) to generate
realistic attack chains like: Infotainment → CAN → Brake ECU = spoofing risk.

Paper reference: Security Analysis of System Topology (Section III-B),
ISO 21434 TARA methodology.
"""

import json
from llm_client import query_llm


# ──────────────────────────────────────────────────────────────────────
# TARA severity scoring
# ──────────────────────────────────────────────────────────────────────

def compute_tara_score(
    timing_violation: bool,
    risk_score: float,
    road_condition: str,
    cpu_load_pct: int,
    attack_patterns_matched: list
) -> dict:
    """
    Compute ISO 21434-aligned TARA risk score.
    Combines timing risk + environmental factors + known attack patterns.
    """
    base_score = risk_score  # already normalized (actual/expected)

    # Environmental multipliers
    road_mult = {"icy": 1.4, "wet": 1.2, "foggy": 1.3, "dry": 1.0}.get(road_condition, 1.0)
    cpu_mult  = 1.0 + (cpu_load_pct / 200.0)  # 0% CPU = 1.0x, 100% CPU = 1.5x
    viol_mult = 1.3 if timing_violation else 1.0

    # Known attack pattern bonus
    pattern_mult = 1.0 + (0.1 * len(attack_patterns_matched))

    raw_score  = base_score * road_mult * cpu_mult * viol_mult * pattern_mult
    final_score = min(round(raw_score, 3), 1.0)  # cap at 1.0

    severity = (
        "CRITICAL" if final_score >= 0.85 else
        "HIGH"     if final_score >= 0.65 else
        "MEDIUM"   if final_score >= 0.40 else
        "LOW"
    )

    return {"tara_score": final_score, "severity": severity}


def match_attack_patterns(component: str, can_ids: list, attack_db: list) -> list:
    """
    Match known attack patterns from knowledge base to current scenario.
    Returns list of relevant attack pattern IDs and names.
    """
    matches = []
    component_lower = component.lower()

    for pattern in attack_db:
        targets = [t.lower() for t in pattern.get("target_components", [])]
        target_ids = pattern.get("target_can_ids", [])

        # Check component match
        comp_match = any(component_lower in t or t in component_lower for t in targets)
        # Check CAN ID match
        id_match = any(cid in target_ids for cid in can_ids)

        if comp_match or id_match:
            matches.append({
                "id":       pattern.get("id"),
                "name":     pattern.get("name"),
                "severity": pattern.get("severity"),
                "vector":   pattern.get("attack_vector")
            })

    return matches


def generate_topology_threat(
    component: str,
    event: str,
    parsed: dict,
    evaluation: dict,
    scenario: dict,
    attack_patterns: list = None
) -> dict:
    """
    Generate a topology-aware cyber-physical threat assessment.
    Uses system topology context to construct realistic attack chains.
    """
    road_condition = scenario.get("parameters", {}).get("road_condition", "dry")
    cpu_load       = scenario.get("parameters", {}).get("ecu_cpu_load_pct", 50)
    timing_viol    = evaluation.get("violation", False)
    risk_score     = evaluation.get("risk_score", 0.5)

    # Match known attack patterns
    matched_attacks = []
    if attack_patterns:
        matched_attacks = match_attack_patterns(component, [], attack_patterns)

    # Compute TARA score
    tara = compute_tara_score(timing_viol, risk_score, road_condition, cpu_load, matched_attacks)

    # LLM topology-aware threat generation
    matched_names = [m["name"] for m in matched_attacks[:3]]
    attack_db_hint = f"Known relevant attacks: {matched_names}" if matched_names else ""

    prompt = f"""
You are an automotive cybersecurity expert performing ISO 21434 TARA analysis.
Generate a topology-aware cyber-physical attack chain for this SDV scenario.

System Topology Context:
- Target component: {component}
- Safety event: {event}
- ISO standard: {parsed.get('iso_standard', 'ISO_26262')}

Runtime Context:
- Expected latency: {evaluation.get('expected_delay_ms')} ms
- Actual latency: {evaluation.get('actual_delay_ms')} ms
- Timing violation: {'YES' if timing_viol else 'NO'}
- Road condition: {road_condition}
- ECU CPU load: {cpu_load}%
- Risk score: {risk_score}

{attack_db_hint}

Generate a REALISTIC attack scenario following the vehicle architecture:
External → Infotainment/OTA/OBD → CAN Gateway → Safety ECU → Physical Effect

Output STRICT JSON only. No markdown. No explanation.

{{
    "topology_path": ["<entry point>", "<intermediate>", "<target ECU>", "<physical impact>"],
    "attack_type": "<spoofing|tampering|replay|DoS|escalation|injection>",
    "attack_chain": ["<step 1>", "<step 2>", "<step 3>", "<step 4>"],
    "software_to_physical_impact": "<how software attack causes physical harm>",
    "severity": "{tara['severity']}",
    "tara_score": {tara['tara_score']},
    "risk_assessment": "<TARA-aligned 1-2 sentence risk summary>",
    "mitigation": "<specific technical countermeasure>",
    "iso_21434_ref": "<relevant ISO 21434 clause>"
}}
"""
    response = query_llm(prompt, temperature=0.5)
    try:
        start = response.find("{")
        end   = response.rfind("}") + 1
        result = json.loads(response[start:end])
        # Ensure TARA score is included
        result["tara_score"]       = tara["tara_score"]
        result["severity"]         = tara["severity"]
        result["matched_patterns"] = matched_attacks
        return result
    except Exception:
        return {
            "topology_path":              ["External", "Infotainment", component, "Physical"],
            "attack_type":                "unknown",
            "attack_chain":               ["Fallback: attack chain parse failed"],
            "software_to_physical_impact": "Unknown — manual review required",
            "severity":                   tara["severity"],
            "tara_score":                 tara["tara_score"],
            "risk_assessment":            "Fallback threat assessment",
            "mitigation":                 "Consult cybersecurity engineer",
            "iso_21434_ref":              "ISO_21434",
            "matched_patterns":           matched_attacks
        }


def generate_batch_threats(
    parsed: dict,
    scenarios: list,
    evaluations: list,
    attack_patterns: list = None
) -> list:
    """Generate threats for all scenarios in batch."""
    component = parsed.get("component", "braking_system")
    event     = parsed.get("event", "unknown")
    threats   = []

    for s, e in zip(scenarios, evaluations):
        print(f"        [THREAT] {s.get('type','?').upper()} → topology analysis...")
        t = generate_topology_threat(component, event, parsed, e, s, attack_patterns)
        threats.append(t)

    return threats


# ──────────────────────────────────────────────────────────────────────
# CLI test
# ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_parsed = {
        "event": "brake",
        "max_delay_ms": 100,
        "component": "braking_system",
        "iso_standard": "ISO_26262"
    }
    test_eval = {
        "violation": True,
        "risk_score": 1.45,
        "actual_delay_ms": 145,
        "expected_delay_ms": 100
    }
    test_scenario = {
        "type": "stress",
        "parameters": {"road_condition": "icy", "ecu_cpu_load_pct": 82}
    }

    result = generate_topology_threat(
        "braking_system", "brake", test_parsed, test_eval, test_scenario
    )
    print(json.dumps(result, indent=2))