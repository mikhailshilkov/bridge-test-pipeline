"""Step 4: Validate the specification completeness using the ongoing agent session."""

from typing import Annotated

from bridge_sdk import step, step_result
from bridge_sdk.multi_turn_client import MultiTurnClient

from linear_to_pr.models import InvestigateResult, ValidateSpecResult
from linear_to_pr.step_03_investigate import investigate_root_cause

OUTPUT_PATH = "/tmp/validate_spec_result.json"

VALIDATION_PROMPT = """\
Now validate whether the issue specification is complete enough to implement a solution.

Score the specification on these 7 criteria (0-100 each):
1. **Problem clarity** — Is the problem clearly described?
2. **Reproduction steps** — Can the issue be reproduced?
3. **Expected behavior** — Is the desired outcome clear?
4. **Scope** — Is the scope of the change well-defined?
5. **Acceptance criteria** — Are success conditions defined?
6. **Technical context** — Is enough technical context provided?
7. **Edge cases** — Are edge cases considered?

Write your assessment as JSON to {output_path}:
{{
    "score": <average score 0-100>,
    "decision": "proceed" or "needs_clarification",
    "questions": ["question 1", "question 2"],
    "summary": "brief assessment summary"
}}

Rules:
- If average score >= 50: set decision to "proceed"
- If average score < 50: set decision to "needs_clarification" and list questions that need answers
- Write ONLY valid JSON, no markdown or extra text
"""


@step()
def validate_specification(
    investigate_result: Annotated[InvestigateResult, step_result(investigate_root_cause)],
) -> ValidateSpecResult:
    """Validate whether the issue spec is complete enough to proceed."""
    client = MultiTurnClient()
    session_id = investigate_result.session_id

    prompt = VALIDATION_PROMPT.format(output_path=OUTPUT_PATH)
    print(f"Validating spec in session {session_id}...")

    from linear_to_pr import run_prompt_and_read_json

    parsed = run_prompt_and_read_json(client, session_id, prompt, OUTPUT_PATH, _ValidationOutput)

    result = ValidateSpecResult(
        session_id=session_id,
        score=parsed.score,
        decision=parsed.decision,
        questions=parsed.questions,
        summary=parsed.summary,
    )
    print(f"Spec validation: score={result.score}, decision={result.decision}")
    return result


from pydantic import BaseModel, Field


class _ValidationOutput(BaseModel):
    score: int = 0
    decision: str = ""
    questions: list[str] = Field(default_factory=list)
    summary: str = ""
