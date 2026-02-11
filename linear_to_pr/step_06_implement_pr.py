"""Step 6: Implement the solution and create a GitHub PR, then finish the session."""

from typing import Annotated

from bridge_sdk import step, step_result
from bridge_sdk.multi_turn_client import MultiTurnClient

from linear_to_pr.models import DesignResult, ImplementResult
from linear_to_pr.step_05_design_solution import design_solution

OUTPUT_PATH = "/tmp/implement_result.json"

IMPLEMENT_PROMPT = """\
Now implement the designed solution and create a pull request.

Follow the implementation plan you designed. For each step:
1. Create a new branch: `git checkout -b {branch_name}`
2. Make the code changes according to your plan
3. Run any existing tests to verify your changes don't break anything
4. Commit your changes with a descriptive message referencing the issue
5. Push the branch: `git push origin {branch_name}`
6. Create a pull request using the GitHub CLI or MCP tools

The PR should:
- Reference the Linear issue in the title and description
- Include a summary of what was changed and why
- List the files modified

After creating the PR, write the results as JSON to {output_path}:
{{
    "pr_url": "https://github.com/owner/repo/pull/123",
    "pr_number": 123,
    "pr_title": "Fix: issue title",
    "branch_name": "{branch_name}",
    "files_changed": ["path/to/file1.py", "path/to/file2.py"]
}}

Write ONLY valid JSON, no markdown or extra text.
"""


@step()
def implement_and_create_pr(
    design_result: Annotated[DesignResult, step_result(design_solution)],
) -> ImplementResult:
    """Implement the solution, create a PR, and finish the agent session."""
    client = MultiTurnClient()
    session_id = design_result.session_id

    prompt = IMPLEMENT_PROMPT.format(
        branch_name=design_result.branch_name,
        output_path=OUTPUT_PATH,
    )
    print(f"Implementing solution in session {session_id}...")

    from linear_to_pr import run_prompt_and_read_json

    parsed = run_prompt_and_read_json(client, session_id, prompt, OUTPUT_PATH, _ImplementOutput)

    # This is the final agent step — finish the session
    print(f"Finishing session {session_id}...")
    client.finish(session_id)

    result = ImplementResult(
        pr_url=parsed.pr_url,
        pr_number=parsed.pr_number,
        pr_title=parsed.pr_title,
        branch_name=parsed.branch_name,
        files_changed=parsed.files_changed,
    )
    print(f"PR created: {result.pr_url}")
    return result


from pydantic import BaseModel, Field


class _ImplementOutput(BaseModel):
    pr_url: str = ""
    pr_number: int = 0
    pr_title: str = ""
    branch_name: str = ""
    files_changed: list[str] = Field(default_factory=list)
