"""
Prompt Templates — Safety Reasoning Agent (Agent 1)
Aligned with base paper: LLM-Empowered Functional Safety & Security for SDVs
Novel Points: Temporal Intelligence, Real-Time Validation, GenAI Threat Reasoning

All prompts are engineered for structured JSON or plain-text output.
No values are hardcoded — all inputs injected at runtime.
"""


def get_requirement_parse_prompt(requirement: str) -> str:
    """
    Novel Point 2: Temporal Intelligence
    GenAI understands natural language requirements and extracts
    timing constraints, triggers, components — like the paper's
    VSS/CAN signal extraction step, but for requirement-level semantics.
    """
    return f"""
You are a safety requirements engineer for Software-Defined Vehicles (SDVs).
Your task is Temporal Intelligence: extract precise, measurable safety constraints
from a natural language requirement.

Requirement: "{requirement}"

Extract the following with high precision:
- The safety-critical EVENT the system must perform (e.g. brake, steer, alert)
- The MAX DELAY in milliseconds (convert units if needed — e.g. 0.1s = 100ms)
- The TRIGGER condition that initiates the event
- The SDV COMPONENT responsible (e.g. braking_system, steering_ecu, alert_module)
- The REQUIREMENT TYPE: timing | threshold | behavioral
- The ISO STANDARD relevant: ISO_26262 (functional safety) | ISO_21434 (cybersecurity) | both
- A formal EVENT CHAIN: ordered list of steps from trigger to actuation
  (following the paper's sense → detect → decide → actuate model)

Output STRICT JSON only. No markdown. No explanation. No extra text.

{{
    "event": "<action>",
    "max_delay_ms": <integer or null>,
    "trigger": "<trigger condition>",
    "component": "<SDV component>",
    "requirement_type": "<timing|threshold|behavioral>",
    "iso_standard": "<ISO_26262|ISO_21434|both>",
    "event_chain": [
        "<step 1: sense>",
        "<step 2: detect>",
        "<step 3: decide>",
        "<step 4: actuate>"
    ]
}}
"""


def get_scenario_generation_prompt(parsed: dict, scenario_type: str, memory: list) -> str:
    """
    Novel Point 3: Real-Time Validation Instead of Static Check
    Generates dynamic runtime simulation scenarios — normal, edge, stress.
    Inspired by paper's event-chain construction for functional safety validation.
    Memory of past delays ensures agent explores untested regions.
    """
    past_delays = [m["actual_delay_ms"] for m in memory] if memory else []
    avoid_hint = (
        f"These delays have already been tested: {past_delays}. "
        f"Generate a DIFFERENT delay to explore new test space."
        if past_delays else ""
    )

    type_instructions = {
        "normal":  "Typical operating condition. System should respond well within the time limit.",
        "edge":    "Boundary condition. Delay should be very close to (just under or at) the max limit.",
        "stress":  "Worst-case, high-load condition. Delay will likely EXCEED the limit — simulate a violation.",
    }

    event_chain_str = " → ".join(parsed.get("event_chain", ["sense", "detect", "decide", "actuate"]))

    return f"""
You are an SDV safety simulation engine generating realistic runtime scenarios.

Safety Requirement:
- Event: {parsed.get('event')}
- Max allowed delay: {parsed.get('max_delay_ms')} ms
- Trigger: {parsed.get('trigger')}
- Component: {parsed.get('component')}
- ISO Standard: {parsed.get('iso_standard')}
- Event chain: {event_chain_str}

Scenario type: {scenario_type.upper()}
Instruction: {type_instructions.get(scenario_type, type_instructions['normal'])}
{avoid_hint}

Generate a realistic simulation of this scenario at runtime.
The event_chain_timing must map each step of the event chain to a time in ms.
The actual_delay_ms is the TOTAL time from trigger to actuation.

Output STRICT JSON only. No markdown. No explanation.

{{
    "scenario_id": <unique random integer>,
    "type": "{scenario_type}",
    "parameters": {{
        "vehicle_speed_kmh": <integer>,
        "distance_to_hazard_m": <integer>,
        "road_condition": "<dry|wet|icy|foggy>",
        "sensor_load": "<low|medium|high>",
        "ecu_cpu_load_pct": <integer 0-100>
    }},
    "event_chain_timing": [
        {{"step": "<chain step name>", "time_ms": <integer>}}
    ],
    "actual_delay_ms": <total integer ms from trigger to actuation>,
    "simulated_violation": <true|false>
}}
"""


def get_threat_reasoning_prompt(parsed: dict, scenario: dict, evaluation: dict) -> str:
    """
    Novel Point 4: GenAI-Driven Threat Reasoning
    Generates cyber-physical attack chains and severity/risk assessment.
    Aligned with paper's security analysis + TARA (Threat Analysis & Risk Assessment).
    """
    return f"""
You are a cybersecurity and functional safety expert for SDV systems.
Perform GenAI-Driven Threat Reasoning based on this test result.

System Under Test:
- Component: {parsed.get('component')}
- Event: {parsed.get('event')}
- ISO Standard: {parsed.get('iso_standard')}

Test Result:
- Expected delay: {evaluation.get('expected_delay_ms')} ms
- Actual delay: {evaluation.get('actual_delay_ms')} ms
- Violation: {'YES' if evaluation.get('violation') else 'NO'}
- Risk score: {evaluation.get('risk_score')}
- Road condition: {scenario.get('parameters', {}).get('road_condition')}
- ECU CPU load: {scenario.get('parameters', {}).get('ecu_cpu_load_pct')}%

Generate:
1. A plausible CYBER-PHYSICAL ATTACK CHAIN that could cause or worsen this delay
2. How a software threat could impact physical safety
3. SEVERITY: CRITICAL | HIGH | MEDIUM | LOW
4. RISK ASSESSMENT aligned with ISO 26262 / ISO 21434

Output STRICT JSON only. No markdown. No explanation.

{{
    "attack_chain": [
        "<step 1>",
        "<step 2>",
        "<step 3>"
    ],
    "software_to_physical_impact": "<how software threat leads to physical harm>",
    "severity": "<CRITICAL|HIGH|MEDIUM|LOW>",
    "risk_assessment": "<1-2 sentence TARA-aligned risk summary>",
    "mitigation": "<recommended defensive action>"
}}
"""


def get_explanation_prompt(parsed: dict, scenarios: list, evaluations: list, threats: list, memory: list) -> str:
    """
    Novel Point 5: Intelligent Dashboard Layer — Real-time GenAI explanations
    Operator-friendly safety analysis across all iterations.
    """
    history_delays = [m["actual_delay_ms"] for m in memory]
    violation_count = sum(1 for e in evaluations if e["violation"])

    scenario_lines = "\n".join([
        f"  [{s['type'].upper()}] delay={e['actual_delay_ms']}ms | "
        f"risk={e['risk_score']} | "
        f"violation={'YES' if e['violation'] else 'NO'} | "
        f"road={s.get('parameters',{}).get('road_condition')} | "
        f"severity={t.get('severity','N/A')}"
        for s, e, t in zip(scenarios, evaluations, threats)
    ])

    return f"""
You are an SDV safety analyst generating an operator-friendly explanation
for a real-time safety validation session.

Requirement: "{parsed.get('event')} within {parsed.get('max_delay_ms')}ms"
Component: {parsed.get('component')}
ISO Standard: {parsed.get('iso_standard')}

Test Results This Session:
{scenario_lines}

Full delay history across all iterations: {history_delays}
Total violations: {violation_count} out of {len(evaluations)} tests

Write a concise, operator-friendly safety report:
1. Overall PASS / FAIL verdict with justification
2. Severity level: CRITICAL / HIGH / MEDIUM / LOW
3. Key timing patterns observed (use actual numbers)
4. Most dangerous scenario identified and why
5. Recommendation for the safety engineering team

Plain text only. Max 6 sentences. Use clear, non-technical language where possible.
"""


def get_next_action_prompt(parsed: dict, evaluations: list, threats: list, memory: list) -> str:
    """
    Agentic Decision Logic — autonomous next test selection.
    Agent reasons about untested regions, boundary conditions, and threat patterns.
    """
    past_delays = [m["actual_delay_ms"] for m in memory]
    severities = [t.get("severity", "LOW") for t in threats]
    violation_count = sum(1 for e in evaluations if e["violation"])
    avg_risk = round(sum(e["risk_score"] for e in evaluations) / len(evaluations), 2) if evaluations else 0

    return f"""
You are an autonomous safety test agent for SDV systems.
Make an intelligent decision about what to test next.

Current Test Session:
- Requirement: {parsed.get('event')} within {parsed.get('max_delay_ms')} ms
- Component: {parsed.get('component')}
- Delays tested so far: {past_delays}
- Violations found: {violation_count}
- Severities observed: {severities}
- Average risk score: {avg_risk}
- Max delay seen: {max(past_delays) if past_delays else 'N/A'} ms
- Min delay seen: {min(past_delays) if past_delays else 'N/A'} ms

Think like an autonomous agent:
- What timing region is UNEXPLORED?
- Should you stress test further or confirm boundary behavior?
- Are there road/load conditions not yet tested?
- Is enough data collected to conclude?

Output STRICT JSON only. No markdown. No explanation.

{{
    "next_action": "<clear one-line instruction for next test>",
    "target_delay_ms": <suggested delay in ms as integer>,
    "scenario_type": "<normal|edge|stress>",
    "focus_condition": "<road condition or system load to focus on>",
    "reason": "<why this is the most valuable next test>",
    "should_continue": <true if more testing needed, false if sufficient data>
}}
"""