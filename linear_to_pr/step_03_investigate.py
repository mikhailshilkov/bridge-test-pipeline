"""Step 3: Create a multi-turn agent session and investigate the root cause."""

import json
from typing import Annotated

from pydantic import ValidationError

from bridge_sdk import step, step_result
from bridge_sdk.multi_turn_client import MultiTurnClient

from linear_to_pr.models import FetchLinearIssueResult, RepoSelectionResult, InvestigateResult
from linear_to_pr.step_01_fetch_linear_issue import fetch_linear_issue
from linear_to_pr.step_02_select_repo import select_repo

OUTPUT_PATH = "/tmp/investigate_result.json"

INVESTIGATION_PROMPT = """\
You are investigating a software issue. Here are the details:

**Issue:** {title}
**Identifier:** {identifier}
**Description:**
{description}

**Repository:** {owner}/{repo_name} (branch: {branch})

Your task:
1. Clone the repository if not already present: `git clone {repo_url} /workspace/{repo_name} && cd /workspace/{repo_name}`
2. Explore the codebase to understand the relevant components
3. Identify the root cause of the issue
4. List the affected files

Write your findings as JSON to {output_path} with this exact schema:
{{
    "root_cause": "description of the root cause",
    "affected_files": ["path/to/file1.py", "path/to/file2.py"],
    "summary": "brief summary of investigation findings"
}}

Write ONLY valid JSON to the file, no markdown or extra text.
"""


@step()
def investigate_root_cause(
    issue: Annotated[FetchLinearIssueResult, step_result(fetch_linear_issue)],
    repo: Annotated[RepoSelectionResult, step_result(select_repo)],
    agent_name: str,
    sandbox_definition_id: str,
) -> InvestigateResult:
    """Create an agent session and investigate the issue's root cause."""
    client = MultiTurnClient()

    # Find agent
    agents = client.list_agents(name=agent_name)
    if not agents:
        raise RuntimeError(f"No agent found with name '{agent_name}'")
    agent_id = agents[0]["id"]
    print(f"Using agent: {agent_id} ({agent_name})")

    # Build prompt
    prompt = INVESTIGATION_PROMPT.format(
        title=issue.title,
        identifier=issue.identifier,
        description=issue.description,
        owner=repo.owner,
        repo_name=repo.repo_name,
        repo_url=repo.repo_url,
        branch=repo.branch,
        output_path=OUTPUT_PATH,
    )

    # Create session with initial prompt
    session = client.create_session(
        agent_id=agent_id,
        prompt=prompt,
        sandbox_definition_id=sandbox_definition_id,
    )
    session_id = session["id"]
    print(f"Created session: {session_id}")

    # Wait for initial prompt to complete
    print("Waiting for session to be running...")
    client.wait_for_state(session_id, {"running"}, timeout=600)
    print("Session is running, reading investigation results...")

    # Read and validate output (agent already ran the initial prompt)
    result = _read_output(client, session_id)

    # Session stays alive for subsequent steps
    print(f"Investigation complete. Root cause: {result.root_cause[:100]}...")
    return result


def _read_output(client: MultiTurnClient, session_id: str) -> InvestigateResult:
    """Read investigation output, retrying if the file isn't ready."""
    max_retries = 2
    error = None
    for attempt in range(1, max_retries + 2):
        result = client.exec(session_id, ["cat", OUTPUT_PATH])
        if result.get("exit_code", -1) == 0:
            try:
                data = json.loads(result["stdout"])
                return InvestigateResult(
                    session_id=session_id,
                    root_cause=data.get("root_cause", ""),
                    affected_files=data.get("affected_files", []),
                    summary=data.get("summary", ""),
                )
            except (json.JSONDecodeError, ValidationError) as e:
                error = str(e)
        else:
            error = result.get("stderr", "file not found")

        if attempt <= max_retries:
            print(f"  Attempt {attempt} failed ({error}), asking agent to fix...")
            retry_id = client.prompt(
                session_id,
                f"The output at {OUTPUT_PATH} is invalid: {error}. "
                "Please write valid JSON to that path with keys: root_cause, affected_files, summary.",
            )
            client.wait_for_command(session_id, retry_id, timeout=600)

    raise RuntimeError(f"Failed to read investigation output after {max_retries + 1} attempts: {error}")
