"""
main_pipeline.py — FINAL INTEGRATED PIPELINE
"""
import os, json, sys
from datetime import datetime
from Agent1 import run_agent
from simulator_rl import apply_adaptive_learning

try:
    from timing_extractor import extract_timing_from_requirement, enrich_with_iso_rules
    HAS_TIMING = True
except ImportError:
    HAS_TIMING = False

try:
    from rag_engine import build_rag_context, load_iso_rules, load_attack_patterns
    HAS_RAG = True
except ImportError:
    HAS_RAG = False

try:
    from threat_generator import generate_batch_threats
    HAS_THREAT = True
except ImportError:
    HAS_THREAT = False

try:
    from multi_lang_parser import parse_sdv_file
    HAS_PARSER = True
except ImportError:
    HAS_PARSER = False

try:
    from temporal_validator import validate_runtime_trace
    HAS_VALIDATOR = True
except ImportError:
    HAS_VALIDATOR = False

try:
    from diagram_generator import generate_all_scenario_diagrams, generate_mermaid_from_chain, save_diagram
    HAS_DIAGRAM = True
except ImportError:
    HAS_DIAGRAM = False

def _banner(t): print(f"\n══════════════════════════════════════\n {t}\n══════════════════════════════════════")
def _section(t): print(f"\n──────────────────────────────────────\n {t}\n──────────────────────────────────────")

def _infer_component(req):
    r = req.lower()
    if "brake" in r or "stop" in r: return "braking_system"
    if "steer" in r or "lane" in r: return "steering_ecu"
    if "alert" in r or "warn" in r: return "alert_module"
    return "unknown_component"

def save_output(data, label="pipeline"):
    os.makedirs("outputs", exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"outputs/{label}_{ts}.json"
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"\n  Output saved: {path}")
    return path

def summarize_results(adaptive_results):
    if not adaptive_results:
        print("\n No adaptive results generated.")
        return
    total = len(adaptive_results)
    violations = sum(1 for r in adaptive_results if r.get("violation"))
    delays = [r.get("actual_delay", 0) for r in adaptive_results]
    print(f"\n RL SUMMARY\nTotal tests        : {total}\nViolations         : {violations}\nMax delay observed : {max(delays)} ms\nMin delay observed : {min(delays)} ms")

def run_requirement_mode(requirement: str) -> dict:
    _banner("SDV SAFETY PIPELINE — Requirement Mode")
    print(f"  Input: {requirement}")

    timing_result = {}
    if HAS_TIMING:
        _section("STEP 0b: GenAI Timing Constraint Extraction (Novel Module 3)")
        try:
            timing_result = extract_timing_from_requirement(requirement)
            if HAS_RAG:
                timing_result = enrich_with_iso_rules(timing_result, load_iso_rules())
            print(f"  Max Latency: {timing_result.get('total_latency_ms')} ms | ASIL: {timing_result.get('asil_level')}")
        except Exception as e:
            print(f"  Timing extraction skipped: {e}")

    if HAS_RAG:
        _section("STEP 0: RAG Context Retrieval")
        try:
            print(build_rag_context(requirement, top_k=2))
        except Exception as e:
            print(f"  RAG skipped: {e}")

    _banner("RUNNING SDV SAFETY PIPELINE")
    agent_output = run_agent(requirement)
    if not agent_output:
        return {}

    _banner("RUNNING ADAPTIVE RL MODULE")
    adaptive_results = apply_adaptive_learning(agent_output)
    summarize_results(adaptive_results)

    topology_threats = []
    if HAS_THREAT and HAS_RAG:
        _section("STEP 3: Topology-Aware Threat Analysis (Novel Module 5)")
        try:
            attack_patterns = load_attack_patterns()
            parsed_for_threat = {
                "event": agent_output.get("event", "brake"),
                "max_delay_ms": agent_output.get("max_delay_ms", 100),
                "component": _infer_component(requirement),
                "iso_standard": agent_output.get("iso_standard", "ISO_26262")
            }
            scenarios_raw = agent_output.get("scenarios", [])
            scenarios_for_threat = [{"type": s.get("type","normal"), "parameters": {"road_condition": s.get("road_condition","dry"), "ecu_cpu_load_pct": 50}} for s in scenarios_raw]
            evals_for_threat = [{"violation": s.get("violation",False), "risk_score": s.get("risk_score",0.5), "actual_delay_ms": s.get("delay_ms",0), "expected_delay_ms": agent_output.get("max_delay_ms",100)} for s in scenarios_raw]
            topology_threats = generate_batch_threats(parsed_for_threat, scenarios_for_threat, evals_for_threat, attack_patterns)
        except Exception as e:
            print(f"  Threat generation skipped: {e}")

    diagram_paths = []
    if HAS_DIAGRAM:
        try:
            diagram_paths = generate_all_scenario_diagrams(agent_output)
        except Exception as e:
            print(f"  Diagram generation skipped: {e}")

    final_output = {
        "mode": "requirement",
        "requirement": requirement,
        "timing_extraction": timing_result,
        "agent_output": agent_output,
        "rl_summary": {
            "total_tests": len(adaptive_results),
            "violations": sum(1 for r in adaptive_results if r.get("violation")),
            "max_delay_ms": max((r.get("actual_delay",0) for r in adaptive_results), default=0),
            "min_delay_ms": min((r.get("actual_delay",0) for r in adaptive_results), default=0),
        },
        "topology_threats": topology_threats,
        "diagrams": diagram_paths,
        "adaptive_results": adaptive_results,
        "timestamp": datetime.now().isoformat()
    }

    _banner("FINAL PIPELINE OUTPUT")
    for r in adaptive_results[:10]:
        print(r)

    save_output(final_output, "requirement_pipeline")
    return final_output

def run_code_mode(filepath: str) -> dict:
    _banner("SDV PIPELINE — Code Analysis Mode")
    if not HAS_PARSER:
        return {"mode": "code", "error": "multi_lang_parser not found"}
    code_result = parse_sdv_file(filepath)
    print(f"  Language: {code_result['language']} | CAN IDs: {code_result['can_ids']}")
    attack_patterns = load_attack_patterns() if HAS_RAG else []
    matched = [p for p in attack_patterns if any(code_result["component"].lower() in t.lower() for t in p.get("target_components", []))]
    result = {"mode": "code", "filepath": filepath, "code_analysis": code_result, "matched_threats": matched[:3], "timestamp": datetime.now().isoformat()}
    save_output(result, "code_pipeline")
    return result

def run_trace_mode(trace_path: str) -> dict:
    _banner("SDV PIPELINE — Runtime Trace Validation Mode")
    if not os.path.exists(trace_path):
        return {"mode": "trace", "error": "file not found"}
    with open(trace_path) as f:
        trace = json.load(f)
    iso_rules = load_iso_rules() if HAS_RAG else []
    if HAS_VALIDATOR:
        val_result = validate_runtime_trace(trace, iso_rules)
    else:
        actual = trace.get("actual_delays", {}).get("total_ms", 0)
        expected = trace.get("expected_delays", {}).get("total_ms", 100)
        val_result = {"actual_ms": actual, "expected_ms": expected, "violation": actual > expected, "verdict": "FAIL" if actual > expected else "PASS", "risk_level": "HIGH" if actual > expected else "LOW"}
    print(f"  Verdict: {val_result.get('verdict')} | Actual: {val_result.get('actual_ms')}ms | Expected: {val_result.get('expected_ms')}ms")
    result = {"mode": "trace", "trace_path": trace_path, "validation": val_result, "timestamp": datetime.now().isoformat()}
    save_output(result, f"trace_{trace.get('scenario_id','x')}")
    return result

def main():
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        inp = sys.argv[2] if len(sys.argv) > 2 else ""
        if mode == "code":
            run_code_mode(inp or "datasets/code_samples/brake_python.py"); return
        if mode == "trace":
            run_trace_mode(inp or "datasets/runtime_traces/scenario_1_trace.json"); return

    requirement = input("Enter requirement: ").strip()
    if not requirement:
        requirement = "Brake within 100ms if obstacle detected"
    run_requirement_mode(requirement)

if __name__ == "__main__":
    main()