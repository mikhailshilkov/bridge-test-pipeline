"""Test steps for bridge pipeline.

This module contains:
1. A simple code step (no agent) - runs Python code directly
2. An agent step - handled by Bridge via Core API (no sidecar needed)
3. A multi-turn API test step - verifies FORGE_API_URL/TOKEN injection and creates a session
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
# Step 3: Multi-turn API connectivity test
# =============================================================================

class MultiTurnTestInput(BaseModel):
    message: str


class MultiTurnTestOutput(BaseModel):
    api_url: str
    api_reachable: bool
    agents: list


@step()
def multi_turn_api_test(input_data: MultiTurnTestInput) -> MultiTurnTestOutput:
    """Verifies FORGE_API_URL and FORGE_API_TOKEN are injected and the API is reachable."""
    from bridge_sdk.multi_turn_client import MultiTurnClient

    api_url = os.environ.get("FORGE_API_URL", "")
    api_token = os.environ.get("FORGE_API_TOKEN", "")

    if not api_url:
        raise RuntimeError("FORGE_API_URL not set in environment")
    if not api_token:
        raise RuntimeError("FORGE_API_TOKEN not set in environment")

    print(f"FORGE_API_URL={api_url}")
    print(f"FORGE_API_TOKEN={'*' * 8}...{api_token[-4:]}")

    client = MultiTurnClient(api_url=api_url, api_token=api_token)

    # Test: list agents to verify connectivity and auth
    agents = client.list_agents()
    print(f"Found {len(agents)} agents")

    return MultiTurnTestOutput(
        api_url=api_url,
        api_reachable=True,
        agents=agents,
    )
