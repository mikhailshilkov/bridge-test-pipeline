"""Linear-to-PR pipeline: automates Linear issue → GitHub PR via multi-turn agent sessions."""

import json

from pydantic import ValidationError

from linear_to_pr.step_01_fetch_linear_issue import fetch_linear_issue
from linear_to_pr.step_02_select_repo import select_repo
from linear_to_pr.step_03_investigate import investigate_root_cause
from linear_to_pr.step_04_validate_spec import validate_specification
from linear_to_pr.step_05_design_solution import design_solution
from linear_to_pr.step_06_implement_pr import implement_and_create_pr
from linear_to_pr.step_07_update_linear import update_linear_issue

__all__ = [
    "fetch_linear_issue",
    "select_repo",
    "investigate_root_cause",
    "validate_specification",
    "design_solution",
    "implement_and_create_pr",
    "update_linear_issue",
    "run_prompt_and_read_json",
]


def run_prompt_and_read_json(client, session_id, prompt, output_path, model_class, max_retries=2):
    """Send prompt, wait for completion, read JSON output, validate with Pydantic, retry on failure."""
    cmd_id = client.prompt(session_id, prompt)
    client.wait_for_command(session_id, cmd_id, timeout=600)

    error = None
    for attempt in range(1, max_retries + 2):
        result = client.exec(session_id, ["cat", output_path])
        if result.get("exit_code", -1) == 0:
            try:
                return model_class.model_validate(json.loads(result["stdout"]))
            except (json.JSONDecodeError, ValidationError) as e:
                error = str(e)
        else:
            error = result.get("stderr", "file not found")

        if attempt <= max_retries:
            retry_id = client.prompt(
                session_id,
                f"The output at {output_path} is invalid: {error}. "
                "Please fix the file so it contains valid JSON matching the required schema.",
            )
            client.wait_for_command(session_id, retry_id, timeout=600)

    raise RuntimeError(f"Failed to read valid output from {output_path} after {max_retries + 1} attempts: {error}")
