"""
diagram_generator.py — Event Chain Diagram Generator
══════════════════════════════════════════════════════════════════
Generates PlantUML activity diagrams from scenario event chains.
Matches the paper's Fig. 3 style: activity diagrams with safety flaw markers.

Novel: automated diagram generation from GenAI-produced event chains.
Paper reference: PlantUML activity diagram notation (Section III-A),
event chain extraction module.
"""

import json
import os
from pathlib import Path
from llm_client import query_llm


# ──────────────────────────────────────────────────────────────────────
# PlantUML Templates
# ──────────────────────────────────────────────────────────────────────

_PLANTUML_HEADER = """@startuml
skinparam activity {{
  BackgroundColor #F8F9FA
  BorderColor #343A40
  FontSize 12
}}
skinparam activityDiamond {{
  BackgroundColor #FFF3CD
  BorderColor #856404
}}
title {title}
start
"""

_PLANTUML_FOOTER = """
stop
@enduml
"""


def _step_to_plantuml(step: str, is_violation: bool = False, is_decision: bool = False) -> str:
    """Convert a single event chain step to PlantUML activity notation."""
    step_clean = step.replace("_", " ").title()

    if is_violation:
        return f"#FFCCCC:{step_clean} ⚠️ VIOLATION;↓"
    if is_decision:
        return f"if ({step_clean}?) then (yes)\n  :{step_clean} = true;\nelse (no)\n  :{step_clean} = false;\nendif"
    return f":{step_clean};"


def generate_plantuml_from_chain(
    event_chain: list,
    title: str = "SDV Event Chain",
    violations: list = None,
    timing: list = None
) -> str:
    """
    Generate PlantUML activity diagram from event chain list.
    
    Args:
        event_chain: list of step strings
        title: diagram title
        violations: list of step names that are violations (marked red)
        timing: list of {step, time_ms} dicts for annotations
    """
    violations = violations or []
    timing_map = {t["step"]: t["time_ms"] for t in (timing or [])}

    lines = [_PLANTUML_HEADER.format(title=title)]

    for step in event_chain:
        step_lower = step.lower()
        is_viol = any(v.lower() in step_lower or step_lower in v.lower() for v in violations)
        is_dec  = any(kw in step_lower for kw in ["detect", "check", "decide", "found", "detected"])

        time_note = f" [{timing_map[step]}ms]" if step in timing_map else ""
        step_label = step.replace("_", " ").title() + time_note

        if is_viol:
            lines.append(f"#FFCCCC:{step_label} ⚠️;")
        elif is_dec:
            lines.append(f"if ({step_label}?) then (yes)")
            lines.append(f"  :{step_label} = true;")
            lines.append("else (no)")
            lines.append(f"  :{step_label} = false;")
            lines.append("endif")
        else:
            lines.append(f":{step_label};")
        lines.append("↓")

    lines.append(_PLANTUML_FOOTER)
    return "\n".join(lines)


def llm_generate_plantuml(
    event_chain: list,
    scenario_type: str,
    violation: bool,
    component: str
) -> str:
    """
    Use LLM to generate a richer PlantUML diagram matching the paper's Fig. 3 style.
    """
    chain_str = " → ".join(event_chain)
    violation_note = "MARK any safety-violating steps in RED using #FFCCCC:step_name;" if violation else ""

    prompt = f"""
You are generating a PlantUML activity diagram for an SDV safety event chain.
Follow the exact style from the TUM paper (LLM-Empowered Functional Safety for SDVs).

Event chain: {chain_str}
Scenario type: {scenario_type}
Component: {component}
Has safety violation: {violation}

{violation_note}

Rules:
- Use @startuml / @enduml
- Use skinparam to style the diagram
- Use if/else for detection decisions
- Mark violation steps with #FFCCCC: background color
- Add note for each step showing input/output format
- Title: "SDV {component} — {scenario_type.title()} Scenario"

Output ONLY valid PlantUML code. No explanation. No markdown fences.
"""
    return query_llm(prompt, temperature=0.3)


def generate_mermaid_from_chain(event_chain: list, title: str = "Event Chain") -> str:
    """
    Generate Mermaid flowchart from event chain (for dashboard use).
    Mermaid renders directly in browser without PlantUML server.
    """
    lines = [f"flowchart TD", f'    title["{title}"]']
    nodes = []

    for i, step in enumerate(event_chain):
        node_id   = f"S{i}"
        step_clean = step.replace("_", " ").title()
        is_dec     = any(kw in step.lower() for kw in ["detect", "decide", "check"])
        shape      = f'{{{{{step_clean}}}}}' if is_dec else f'[{step_clean}]'
        nodes.append((node_id, shape))
        lines.append(f"    {node_id}{shape}")

    for i in range(len(nodes) - 1):
        lines.append(f"    {nodes[i][0]} --> {nodes[i+1][0]}")

    return "\n".join(lines)


def save_diagram(content: str, filename: str, output_dir: str = "outputs/diagrams") -> str:
    """Save diagram to file."""
    os.makedirs(output_dir, exist_ok=True)
    path = Path(output_dir) / filename
    path.write_text(content, encoding="utf-8")
    return str(path)


def generate_all_scenario_diagrams(agent_output: dict) -> list:
    """
    Generate PlantUML diagrams for all scenarios in agent output.
    Returns list of saved file paths.
    """
    saved = []
    event_chain = agent_output.get("event_chain", [])

    for i, scenario in enumerate(agent_output.get("scenarios", [])):
        stype     = scenario.get("type", f"scenario_{i}")
        violation = scenario.get("violation", False)
        component = agent_output.get("event", "brake")

        # Identify violated steps
        violated_steps = []
        if violation and "attack_chain" in scenario:
            violated_steps = scenario.get("attack_chain", [])[:1]

        # Generate timing annotations
        timing = []
        if "attack_chain" in scenario:
            pass  # could enrich with timing data here

        plantuml = generate_plantuml_from_chain(
            event_chain=event_chain,
            title=f"SDV {component.title()} — {stype.title()} Scenario",
            violations=violated_steps,
            timing=timing
        )

        filename = f"diagram_{stype}_{i}.puml"
        path = save_diagram(plantuml, filename)
        saved.append({"scenario": stype, "path": path, "violation": violation})
        print(f"  [Diagram] Saved: {path}")

    return saved


# ──────────────────────────────────────────────────────────────────────
# CLI test
# ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    chain = [
        "camera_sense_start",
        "pedestrian_detected",
        "sensor_fusion_complete",
        "brake_decide",
        "brake_actuate"
    ]

    print("=== PlantUML ===")
    puml = generate_plantuml_from_chain(
        chain,
        title="Emergency Brake — Stress Scenario",
        violations=["brake_decide"],
        timing=[{"step": "camera_sense_start", "time_ms": 12},
                {"step": "pedestrian_detected",  "time_ms": 55},
                {"step": "brake_actuate",         "time_ms": 145}]
    )
    print(puml)

    print("\n=== Mermaid ===")
    print(generate_mermaid_from_chain(chain, "Emergency Brake"))