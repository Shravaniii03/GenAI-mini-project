"""
Parser — Novel Point 2: Temporal Intelligence
Uses GenAI (not regex) to extract timing constraints, event chains,
and ISO standard alignment from natural language requirements.
Aligned with paper's VSS/CAN signal extraction concept at requirement level.
"""
from llm_client import query_llm
from prompt_templates import get_requirement_parse_prompt
import json


def parse_requirement(requirement: str) -> dict:
    """
    GenAI-powered requirement parser.
    Extracts: event, max_delay_ms, trigger, component,
              requirement_type, iso_standard, event_chain
    """
    prompt = get_requirement_parse_prompt(requirement)
    response = query_llm(prompt, temperature=0.1)  # very low temp — precision task

    try:
        json_start = response.find("{")
        json_end = response.rfind("}") + 1
        parsed = json.loads(response[json_start:json_end])

        # Validate required fields exist
        required = ["event", "max_delay_ms", "trigger", "component", "event_chain"]
        for field in required:
            if field not in parsed:
                raise ValueError(f"Missing field: {field}")

        return parsed

    except Exception as e:
        raise ValueError(f"Requirement parsing failed: {e}\nRaw LLM output: {response}")