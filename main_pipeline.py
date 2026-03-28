from Agent1 import run_agent
from simulator_rl import apply_adaptive_learning


# ==============================
# SUMMARY FUNCTION (IMPORTANT)
# ==============================
def summarize_results(adaptive_results, max_delay):

    total = len(adaptive_results)
    violations = sum(r["violation"] for r in adaptive_results)

    max_delay_seen = max(r["actual_delay"] for r in adaptive_results)
    min_delay_seen = min(r["actual_delay"] for r in adaptive_results)

    print("\n📊 RL SUMMARY")
    print(f"Total tests: {total}")
    print(f"Violations: {violations}")
    print(f"Max delay observed: {max_delay_seen}")
    print(f"Min delay observed: {min_delay_seen}")


def main():

    # Step 1: Input
    requirement = input("Enter requirement: ").strip()
    if not requirement:
        requirement = "Brake within 100ms if obstacle detected"

    # Step 2: Agent 1
    agent1_output = run_agent(requirement)

    # Step 3: YOUR RL MODULE
    adaptive_results = apply_adaptive_learning(agent1_output)

    # Step 4: Summary (IMPORTANT)
    summarize_results(adaptive_results, agent1_output["max_delay_ms"])

    # Step 5: Final structured output
    final_output = {
        "requirement": agent1_output["requirement"],
        "max_delay": agent1_output["max_delay_ms"],
        "adaptive_summary": {
            "total_tests": len(adaptive_results),
            "violations": sum(r["violation"] for r in adaptive_results),
        },
        "adaptive_results": adaptive_results
    }

    print("\n================ FINAL PIPELINE OUTPUT ================\n")
    for r in adaptive_results[:10]:
        print(r)

    return final_output


if __name__ == "__main__":
    main()