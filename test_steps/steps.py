"""Simple test steps for bridge sidecar elimination prototype.

This module contains:
1. A simple code step (no agent) - runs Python code directly
2. An agent step - uses the sidecar to run an agent
"""

from pydantic import BaseModel
from bridge_sdk import step
from bridge_sdk.bridge_sidecar_client import BridgeSidecarClient


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
# Step 2: Agent Step (uses sidecar)
# =============================================================================

class HelloAgentInput(BaseModel):
    prompt: str


class HelloAgentOutput(BaseModel):
    session_id: str
    result: str


@step(
    metadata={"type": "agent"},
)
def hello_agent_step(input_data: HelloAgentInput) -> HelloAgentOutput:
    """Agent step that uses the sidecar to run an agent.

    This step:
    1. Connects to the Bridge sidecar on localhost:50052
    2. Calls StartAgent with the provided prompt
    3. Returns the session ID and result
    """
    print(f"hello_agent_step starting with prompt: {input_data.prompt}")

    with BridgeSidecarClient() as client:
        agent_name, session_id, exit_result = client.start_agent(
            prompt=input_data.prompt,
            agent_name="default",  # Use default agent
        )
        print(f"Agent completed: session_id={session_id}, result={exit_result}")

    return HelloAgentOutput(
        session_id=session_id,
        result=exit_result,
    )
