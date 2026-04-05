"""
Central Prompt Templates for GenAI SDV Safety System
"""

# ─────────────────────────────
# REQUIREMENT PARSING
# ─────────────────────────────

def get_requirement_parse_prompt(requirement: str) -> str:
    return f"""
Extract structure (NOT timing):

Requirement: "{requirement}"

Output JSON:

{{
  "event": "",
  "trigger": "",
  "component": "",
  "event_chain": ["", "", "", ""]
}}
"""


# ─────────────────────────────
# TIMING EXTRACTION (MAIN)
# ─────────────────────────────

def get_timing_extraction_prompt(text: str, iso_context: str) -> str:
    return f"""
You are ISO 26262 expert.

Extract timing intelligently.

INPUT:
{text}

CONTEXT:
{iso_context}

Output JSON:

{{
  "event": "",
  "total_latency_ms": 0,
  "component": "",
  "asil_level": "",
  "breakdown_ms": {{
    "sensor_ms": 0,
    "decision_ms": 0,
    "actuator_ms": 0
  }},
  "confidence": "",
  "reasoning": ""
}}
"""


# ─────────────────────────────
# THREAT REASONING
# ─────────────────────────────

def get_threat_reasoning_prompt(parsed, scenario, evaluation) -> str:
    return f"""
Generate attack scenario.

Event: {parsed.get("event")}
Delay: {scenario.get("actual_delay_ms")}
Risk: {evaluation.get("risk_score")}

Output JSON:
{{
  "attack_chain": [],
  "severity": "",
  "mitigation": ""
}}
"""


# ─────────────────────────────
# EXPLANATION
# ─────────────────────────────

def get_explanation_prompt(parsed, scenarios, evaluations, threats, memory) -> str:
    return f"""
Explain system safety in 4 sentences.
"""


# ─────────────────────────────
# NEXT ACTION
# ─────────────────────────────

def get_next_action_prompt(parsed, evaluations, threats, memory) -> str:
    return f"""
Suggest next test.

Output JSON:
{{
  "next_action": "",
  "scenario_type": "",
  "should_continue": true
}}
"""
def get_scenario_generation_prompt(parsed: dict, scenario_type: str, memory: list) -> str:

    past_delays = [m["actual_delay_ms"] for m in memory] if memory else []

    avoid_hint = (
        f"These delays have already been tested: {past_delays}. Generate a DIFFERENT delay."
        if past_delays else ""
    )

    return f"""
You are a simulation engine for SDV systems.

Requirement:
- Event: {parsed.get('event')}
- Max delay: {parsed.get('max_delay_ms')}
- Component: {parsed.get('component')}

Scenario Type: {scenario_type}

{avoid_hint}

Generate realistic simulation.

Output JSON:

{{
  "scenario_id": 1,
  "type": "{scenario_type}",
  "parameters": {{
    "vehicle_speed_kmh": 50,
    "road_condition": "dry",
    "ecu_cpu_load_pct": 40
  }},
  "event_chain_timing": [
    {{"step": "sense", "time_ms": 10}},
    {{"step": "detect", "time_ms": 20}},
    {{"step": "decide", "time_ms": 30}},
    {{"step": "actuate", "time_ms": 40}}
  ],
  "actual_delay_ms": 100,
  "simulated_violation": false
}}
"""






