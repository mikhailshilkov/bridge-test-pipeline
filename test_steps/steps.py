"""Test steps for bridge pipeline.

This module contains:
1. A simple code step (no agent) - runs Python code directly
2. An agent step - handled by Bridge via Core API (no sidecar needed)
3. A multi-turn step - creates an agent session, sends prompts, validates output, retries
"""

import json
import os

from pydantic import BaseModel
from bridge_sdk import step


# =============================================================================
# Step 1: Simple Code Step (no agent)
# =============================================================================

class HelloCodeInput(BaseModel):
    message: str


class HelloCodeOutput(BaseModel):
    result: str


@step()
def hello_code_step(input_data: HelloCodeInput) -> HelloCodeOutput:
    """Simple code step that transforms input - no agent involved."""
    transformed = f"Code step received: {input_data.message}"
    print(f"hello_code_step executed with: {input_data.message}")
    return HelloCodeOutput(result=transformed)


# =============================================================================
# Step 2: Agent Step (handled by Bridge directly via Core API)
# =============================================================================

class HelloAgentInput(BaseModel):
    prompt: str


class HelloAgentOutput(BaseModel):
    result: str


@step(metadata={"type": "agent"})
def hello_agent_step(input_data: HelloAgentInput) -> HelloAgentOutput:
    """Agent step - executed by Bridge via Core API, not this function."""
    ...


# =============================================================================
# Step 3: Multi-turn validated JSON generation
# =============================================================================

class ValidatedJsonInput(BaseModel):
    agent_name: str = "default"
    sandbox_definition_id: str = ""


class ValidatedJsonOutput(BaseModel):
    session_id: str
    result_json: dict
    attempts: int


@step()
def validated_json_generation(input_data: ValidatedJsonInput) -> ValidatedJsonOutput:
    """Creates an agent session, asks it to produce valid JSON, validates, retries if needed."""
    from bridge_sdk.multi_turn_client import MultiTurnClient

    client = MultiTurnClient()

    # Find agent
    agents = client.list_agents(name=input_data.agent_name)
    if not agents:
        raise RuntimeError(f"No agent found with name '{input_data.agent_name}'")
    agent_id = agents[0]["id"]
    print(f"Using agent: {agent_id} ({input_data.agent_name})")

    # Create session with initial prompt
    sandbox_def_id = input_data.sandbox_definition_id or None
    session = client.create_session(
        agent_id=agent_id,
        prompt='Write a valid JSON file at /tmp/result.json with these fields: "name" (a string), "age" (an integer), "hobbies" (an array of strings). Do not include any other text in the file, only valid JSON.',
        sandbox_definition_id=sandbox_def_id,
    )
    session_id = session["id"]
    print(f"Created session: {session_id}")

    # Wait for session to become running (initial prompt completes)
    print("Waiting for session to be running...")
    client.wait_for_state(session_id, {"running"}, timeout=300)
    print("Session is running")

    # Validate and retry loop
    max_retries = 2
    last_error = None
    for attempt in range(1, max_retries + 2):
        print(f"Attempt {attempt}: reading /tmp/result.json")
        result = client.exec(session_id, ["cat", "/tmp/result.json"])

        if result.get("exit_code", -1) != 0:
            last_error = f"cat failed: exit_code={result.get('exit_code')}, stderr={result.get('stderr', '')}"
            print(f"  {last_error}")
        else:
            try:
                data = json.loads(result["stdout"])
                assert isinstance(data.get("name"), str), "'name' must be a string"
                assert isinstance(data.get("age"), int), "'age' must be an integer"
                assert isinstance(data.get("hobbies"), list), "'hobbies' must be a list"
                print(f"  Valid JSON: {data}")
                client.finish(session_id)
                return ValidatedJsonOutput(
                    session_id=session_id,
                    result_json=data,
                    attempts=attempt,
                )
            except (json.JSONDecodeError, AssertionError) as e:
                last_error = str(e)
                print(f"  Validation failed: {last_error}")

        if attempt <= max_retries:
            print(f"  Sending retry prompt...")
            cmd_id = client.prompt(
                session_id,
                f"The file /tmp/result.json is not valid. Error: {last_error}. "
                "Please fix it. The file must contain only valid JSON with fields: "
                '"name" (string), "age" (integer), "hobbies" (array of strings).',
            )
            client.wait_for_command(session_id, cmd_id, timeout=300)

    client.finish(session_id)
    raise RuntimeError(f"Failed after {max_retries + 1} attempts. Last error: {last_error}")
