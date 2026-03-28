import random


# ==============================
# 1. SIMULATOR
# ==============================
def simulate(delay, max_delay):
    actual_delay = delay

    violation = 1 if actual_delay > max_delay else 0
    delay_score = round(actual_delay / max_delay, 2)

    return {
        "actual_delay": actual_delay,
        "violation": violation,
        "delay_score": delay_score
    }


# ==============================
# 2. ADAPTIVE RL POLICY
# ==============================
def adaptive_policy(current_delay, violation, max_delay):

    explore_prob = 0.4

    if violation == 1:
        # move toward boundary
        next_delay = current_delay - random.choice([10, 20])
    else:
        if random.random() < explore_prob:
            # explore risky region
            next_delay = max_delay + random.choice([10, 20])
        else:
            next_delay = current_delay + random.choice([-10, -5, 5])

    return max(0, next_delay)


# ==============================
# 3. SINGLE STEP
# ==============================
def run_simulation(input_data):

    delay = input_data["delay"]
    max_delay = input_data["max_delay"]

    sim_result = simulate(delay, max_delay)

    next_delay = adaptive_policy(delay, sim_result["violation"], max_delay)

    return {
        "input_delay": delay,
        "actual_delay": sim_result["actual_delay"],
        "violation": sim_result["violation"],
        "delay_score": sim_result["delay_score"],
        "next_delay": next_delay
    }


# ==============================
# 4. RL OVER AGENT1 OUTPUT
# ==============================
def apply_adaptive_learning(agent1_output, steps_per_scenario=3):

    max_delay = agent1_output["max_delay_ms"]
    scenarios = agent1_output["scenarios"]

    adaptive_results = []

    for scenario in scenarios:

        delay = scenario["delay_ms"]

        for step in range(steps_per_scenario):

            result = run_simulation({
                "delay": delay,
                "max_delay": max_delay
            })

            adaptive_results.append({
                "scenario_type": scenario["type"],
                "original_delay": scenario["delay_ms"],
                "iteration": step + 1,
                **result
            })

            delay = result["next_delay"]

    return adaptive_results