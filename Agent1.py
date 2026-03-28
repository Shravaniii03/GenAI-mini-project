"""
Agent 1: Safety Reasoning Agent
═══════════════════════════════════════════════════════════════
Project  : GenAI-Based Real-Time Temporal Safety & Threat Detection for SDVs
Base Paper: LLM-Empowered Functional Safety & Security by Design (TUM, 2026)
Novel Points Implemented:
  [2] Temporal Intelligence       — GenAI extracts timing constraints + event chains
  [3] Real-Time Validation        — Compares expected vs actual delay dynamically
  [4] GenAI-Driven Threat Reasoning — Cyber-physical attack chains + TARA risk
  [5] Intelligent Dashboard Layer — Operator-friendly GenAI explanations

Agentic Loop:
  Understand → Generate Scenarios → Evaluate → Threat Reason → Decide Next → Repeat
═══════════════════════════════════════════════════════════════
"""

import json
from parser import parse_requirement
from scenario_generator import generate_all_scenarios
from reasoning_engine import (
    evaluate_all_scenarios,
    generate_all_threats,
    generate_explanation,
    decide_next_action
)
from memory import AgentMemory

MAX_ITERATIONS = 3  # agentic loop depth


def print_header(title: str, width: int = 60):
    print(f"\n{'═'*width}")
    print(f"  {title}")
    print(f"{'═'*width}")


def print_section(step: str, title: str):
    print(f"\n{'─'*55}")
    print(f"  {step}  {title}")
    print(f"{'─'*55}")


def run_agent(requirement: str) -> dict:
    memory = AgentMemory()

    print_header(" Agent 1 — SDV Safety Reasoning Agent")
    print(f"  Requirement : {requirement}")

    # ══════════════════════════════════════════════════════
    # STEP 1: Temporal Intelligence — GenAI Requirement Parsing
    # Novel Point 2: Extract timing, event chain, ISO standard
    # ══════════════════════════════════════════════════════
    print_section(" STEP 1:", "Temporal Intelligence — Parsing Requirement (GenAI)")

    parsed = parse_requirement(requirement)

    print(f"  Event        : {parsed.get('event')}")
    print(f"  Max Delay    : {parsed.get('max_delay_ms')} ms")
    print(f"  Trigger      : {parsed.get('trigger')}")
    print(f"  Component    : {parsed.get('component')}")
    print(f"  ISO Standard : {parsed.get('iso_standard')}")
    print(f"  Event Chain  : {' → '.join(parsed.get('event_chain', []))}")

    all_scenarios   = []
    all_evaluations = []
    all_threats     = []
    iteration_logs  = []

    # ══════════════════════════════════════════════════════
    # AGENTIC LOOP
    # ══════════════════════════════════════════════════════
    for iteration in range(1, MAX_ITERATIONS + 1):
        
        print(f"   AGENTIC LOOP — Iteration {iteration} / {MAX_ITERATIONS}")
        

        # ── STEP 2: Generate Scenarios (normal + edge + stress) ──
        print_section(" STEP 2:", "Real-Time Scenario Generation (GenAI)")
        scenarios = generate_all_scenarios(parsed, memory.get_history())
        if not scenarios:
            print("    No scenarios generated. Skipping iteration.")
            continue

        # ── STEP 3: Real-Time Evaluation ─────────────────────────
        print_section("🔹 STEP 3:", "Real-Time Validation — Expected vs Actual Delay")
        evaluations = evaluate_all_scenarios(parsed, scenarios)
        for s, e in zip(scenarios, evaluations):
            status = " VIOLATION" if e["violation"] else " PASS"
            bottleneck = e.get("bottleneck_step", {})
            print(
                f"  [{s['type'].upper():6}] "
                f"delay={e['actual_delay_ms']}ms / {e['expected_delay_ms']}ms  "
                f"risk={e['risk_score']}  "
                f"road={e.get('road_condition')}  "
                f"{status}"
            )
            if bottleneck:
                print(f"             Bottleneck: {bottleneck.get('step')} @ {bottleneck.get('time_ms')}ms")

        # ── STEP 4: GenAI Threat Reasoning ───────────────────────
        print_section(" STEP 4:", "GenAI-Driven Threat Reasoning (Cyber-Physical)")
        threats = generate_all_threats(parsed, scenarios, evaluations)
        for s, t in zip(scenarios, threats):
            print(f"  [{s['type'].upper():6}] severity={t.get('severity')}  |  {t.get('risk_assessment','')[:80]}")
            print(f"             Mitigation: {t.get('mitigation','N/A')[:70]}")

        # Store in memory
        memory.store_batch(scenarios, evaluations, threats)
        all_scenarios.extend(scenarios)
        all_evaluations.extend(evaluations)
        all_threats.extend(threats)

        # STEP 5: Agentic Next Action Decision 
        print_section(" STEP 5:", "Agentic Decision — Next Test Action (GenAI)")
        next_action = decide_next_action(parsed, evaluations, threats, memory.get_history())
        print(f"   Next Action  : {next_action.get('next_action')}")
        print(f"   Target Delay : {next_action.get('target_delay_ms')} ms")
        print(f"   Reason       : {next_action.get('reason')}")
        print(f"   Continue?    : {next_action.get('should_continue')}")

        iteration_logs.append({
            "iteration": iteration,
            "scenarios_count": len(scenarios),
            "violations": sum(1 for e in evaluations if e["violation"]),
            "next_action": next_action
        })

        # Early stop if agent decides sufficient data is collected
        if not next_action.get("should_continue", True) and iteration >= 2:
            print(f"\n   Agent concluded sufficient data collected after iteration {iteration}.")
            break

    
    # STEP 6: Intelligent Dashboard — Final Explanation
    
    print_section(" STEP 6:", "Intelligent Dashboard — Safety Explanation (GenAI)")
    explanation = generate_explanation(parsed, all_scenarios, all_evaluations, all_threats, memory.get_history())
    print(f"\n   {explanation}")

    
    # FINAL STRUCTURED OUTPUT 
    
    mem = memory.summary()
    output = {
        "requirement": requirement,
        "event": parsed.get("event"),
        "max_delay_ms": parsed.get("max_delay_ms"),
        "iso_standard": parsed.get("iso_standard"),
        "event_chain": parsed.get("event_chain"),
        "scenarios": [
            {
                "type": s["type"],
                "delay_ms": s["actual_delay_ms"],
                "road_condition": s.get("parameters", {}).get("road_condition"),
                "violation": bool(e["violation"]),
                "risk_score": e["risk_score"],
                "severity": t.get("severity"),
                "attack_chain": t.get("attack_chain"),
                "mitigation": t.get("mitigation")
            }
            for s, e, t in zip(all_scenarios, all_evaluations, all_threats)
        ],
        "next_action": iteration_logs[-1]["next_action"].get("next_action") if iteration_logs else None,
        "explanation": explanation,
        "memory_summary": mem
    }

    print_header(" FINAL OUTPUT")
    print(json.dumps(output, indent=2))
    return output



# ENTRY POINT

if __name__ == "__main__":
    print_header(" SDV Safety Reasoning Agent — Agent 1")
    print("""
  Example requirements:
    • Brake within 100ms if obstacle detected
    • Steer within 200ms if lane departure detected
    • Alert driver within 50ms if speed exceeds limit
    • Emergency stop within 150ms if camera detects pedestrian
    """)

    requirement = input("  Enter your safety requirement: ").strip()
    if not requirement:
        print("  No input. Using default.")
        requirement = "Brake within 100ms if obstacle detected"

    run_agent(requirement)