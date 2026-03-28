"""
Scenario Generator — Novel Point 3: Real-Time Validation Instead of Static Check
Generates dynamic runtime simulation scenarios (normal, edge, stress).
Aligned with paper's event-chain construction for functional safety validation.
Memory ensures the agent explores untested timing regions autonomously.
"""
from llm_client import query_llm
from prompt_templates import get_scenario_generation_prompt
import json


def generate_scenario(parsed: dict, scenario_type: str, memory: list) -> dict:
    """Generate a single scenario of a given type, aware of past tests."""
    prompt = get_scenario_generation_prompt(parsed, scenario_type, memory)
    response = query_llm(prompt, temperature=0.95)  # high temp = diverse scenarios

    try:
        json_start = response.find("{")
        json_end = response.rfind("}") + 1
        scenario = json.loads(response[json_start:json_end])

        # Ensure actual_delay_ms exists
        if "actual_delay_ms" not in scenario:
            raise ValueError("Missing actual_delay_ms in scenario")

        return scenario

    except Exception as e:
        raise ValueError(f"Scenario generation failed ({scenario_type}): {e}\nRaw: {response}")


def generate_all_scenarios(parsed: dict, memory: list) -> list:
    """
    Generate normal + edge + stress scenarios per iteration.
    Represents the paper's multi-scenario validation approach.
    """
    scenarios = []
    for scenario_type in ["normal", "edge", "stress"]:
        print(f"        [{scenario_type.upper()}] generating...")
        try:
            scenario = generate_scenario(parsed, scenario_type, memory)
            scenarios.append(scenario)
        except ValueError as e:
            print(f"        Skipped {scenario_type}: {e}")
    return scenarios