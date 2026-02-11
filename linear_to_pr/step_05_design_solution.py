"""Step 5: Design the solution approach using the ongoing agent session."""

from typing import Annotated

from bridge_sdk import step, step_result
from bridge_sdk.multi_turn_client import MultiTurnClient

from linear_to_pr.models import ValidateSpecResult, DesignResult
from linear_to_pr.step_04_validate_spec import validate_specification

OUTPUT_PATH = "/tmp/design_result.json"

DESIGN_PROMPT = """\
Now design the implementation approach for this issue.

Based on your investigation and the validated specification:
1. Propose 2-3 possible approaches
2. Select the best approach and justify your choice
3. Plan the implementation steps
4. Determine the branch name and list of files to modify

Write your design as JSON to {output_path}:
{{
    "approach": "description of the chosen approach",
    "branch_name": "fix/issue-identifier-short-description",
    "files_to_modify": ["path/to/file1.py", "path/to/file2.py"],
    "plan": "step-by-step implementation plan"
}}

Write ONLY valid JSON, no markdown or extra text.
"""


@step()
def design_solution(
    validate_result: Annotated[ValidateSpecResult, step_result(validate_specification)],
) -> DesignResult:
    """Design the implementation approach for the issue."""
    client = MultiTurnClient()
    session_id = validate_result.session_id

    prompt = DESIGN_PROMPT.format(output_path=OUTPUT_PATH)
    print(f"Designing solution in session {session_id}...")

    from linear_to_pr import run_prompt_and_read_json

    parsed = run_prompt_and_read_json(client, session_id, prompt, OUTPUT_PATH, _DesignOutput)

    result = DesignResult(
        session_id=session_id,
        approach=parsed.approach,
        branch_name=parsed.branch_name,
        files_to_modify=parsed.files_to_modify,
        plan=parsed.plan,
    )
    print(f"Design complete. Branch: {result.branch_name}, files: {len(result.files_to_modify)}")
    return result


from pydantic import BaseModel, Field


class _DesignOutput(BaseModel):
    approach: str = ""
    branch_name: str = ""
    files_to_modify: list[str] = Field(default_factory=list)
    plan: str = ""
