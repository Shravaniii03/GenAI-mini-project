"""
Agent Memory — Simple stateful store for the agentic loop.
Tracks all past delays, violations, threats, and scenario types tested.
Enables the agent to make informed decisions across iterations —
avoiding retesting the same delays and focusing on unexplored regions.
Aligned with paper's iterative feedback loop concept.
"""


class AgentMemory:
    def __init__(self):
        self.history = []            # full records of every test
        self.delays_tested = []      # quick lookup: all actual delays seen
        self.violations = []         # only violation records
        self.severities_seen = []    # threat severity history

    def store(self, scenario: dict, evaluation: dict, threat: dict):
        record = {
            "iteration": len(self.history) + 1,
            "scenario_type": scenario.get("type"),
            "actual_delay_ms": evaluation["actual_delay_ms"],
            "violation": evaluation["violation"],
            "risk_score": evaluation["risk_score"],
            "road_condition": scenario.get("parameters", {}).get("road_condition"),
            "ecu_cpu_load": scenario.get("parameters", {}).get("ecu_cpu_load_pct"),
            "severity": threat.get("severity", "UNKNOWN"),
            "bottleneck": evaluation.get("bottleneck_step")
        }
        self.history.append(record)
        self.delays_tested.append(evaluation["actual_delay_ms"])
        self.severities_seen.append(threat.get("severity", "UNKNOWN"))
        if evaluation["violation"]:
            self.violations.append(record)

    def store_batch(self, scenarios: list, evaluations: list, threats: list):
        for s, e, t in zip(scenarios, evaluations, threats):
            self.store(s, e, t)

    def get_history(self) -> list:
        return self.history

    def summary(self) -> dict:
        if not self.history:
            return {}
        return {
            "total_tests": len(self.history),
            "total_violations": len(self.violations),
            "violation_rate_pct": round(len(self.violations) / len(self.history) * 100, 1),
            "delays_tested_ms": self.delays_tested,
            "max_delay_ms": max(self.delays_tested),
            "min_delay_ms": min(self.delays_tested),
            "avg_risk_score": round(sum(r["risk_score"] for r in self.history) / len(self.history), 3),
            "severities_observed": list(set(self.severities_seen)),
            "critical_violations": sum(1 for r in self.history if r["severity"] == "CRITICAL")
        }