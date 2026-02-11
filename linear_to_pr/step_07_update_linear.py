"""Step 7: Post results back to Linear (comment + state update)."""

import json
import os
from typing import Annotated
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from bridge_sdk import step, step_result

from linear_to_pr.models import (
    FetchLinearIssueResult,
    ImplementResult,
    UpdateLinearResult,
)
from linear_to_pr.step_01_fetch_linear_issue import fetch_linear_issue
from linear_to_pr.step_06_implement_pr import implement_and_create_pr

LINEAR_API_URL = "https://api.linear.app/graphql"

CREATE_COMMENT_MUTATION = """
mutation CreateComment($issueId: String!, $body: String!) {
    commentCreate(input: { issueId: $issueId, body: $body }) {
        success
    }
}
"""

UPDATE_STATE_QUERY = """
query GetInReviewState($teamName: String!) {
    workflowStates(filter: { name: { eq: "In Review" }, team: { name: { eq: $teamName } } }) {
        nodes { id name }
    }
}
"""

UPDATE_ISSUE_MUTATION = """
mutation UpdateIssue($issueId: String!, $stateId: String!) {
    issueUpdate(id: $issueId, input: { stateId: $stateId }) {
        success
    }
}
"""


def _graphql_request(query: str, variables: dict | None = None) -> dict:
    api_key = os.environ["LINEAR_API_KEY"]
    payload = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = Request(LINEAR_API_URL, data=payload, method="POST")
    req.add_header("Authorization", api_key)
    req.add_header("Content-Type", "application/json")
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        body = e.read().decode() if e.fp else ""
        raise RuntimeError(f"Linear API error {e.code}: {body}") from e


@step(credential_bindings={"LINEAR_API_KEY_SECRET": "LINEAR_API_KEY"})
def update_linear_issue(
    issue: Annotated[FetchLinearIssueResult, step_result(fetch_linear_issue)],
    pr_result: Annotated[ImplementResult, step_result(implement_and_create_pr)],
) -> UpdateLinearResult:
    """Post a comment with PR details and update issue state to 'In Review'."""
    files_list = "\n".join(f"- `{f}`" for f in pr_result.files_changed) if pr_result.files_changed else "N/A"
    comment_body = (
        f"**Pull Request Created**\n\n"
        f"**PR:** [{pr_result.pr_title}]({pr_result.pr_url})\n"
        f"**Branch:** `{pr_result.branch_name}`\n\n"
        f"**Files Changed:**\n{files_list}\n\n"
        f"_Automated by linear-to-pr pipeline_"
    )

    # Stub mode: just print what we'd do when LINEAR_API_KEY is not set
    if not os.environ.get("LINEAR_API_KEY"):
        print(f"[STUB] Would post comment to {issue.identifier}:\n{comment_body}")
        print(f"[STUB] Would update state to 'In Review'")
        return UpdateLinearResult(comment_posted=True, state_updated=True)

    comment_posted = False
    state_updated = False

    # Post comment
    print(f"Posting comment to Linear issue {issue.identifier}...")
    result = _graphql_request(CREATE_COMMENT_MUTATION, {
        "issueId": issue.issue_id,
        "body": comment_body,
    })
    if "errors" not in result:
        comment_posted = result.get("data", {}).get("commentCreate", {}).get("success", False)
    if comment_posted:
        print("Comment posted successfully")
    else:
        print(f"Failed to post comment: {result}")

    # Update state to "In Review"
    if issue.team_name:
        print(f"Looking up 'In Review' state for team '{issue.team_name}'...")
        state_result = _graphql_request(UPDATE_STATE_QUERY, {"teamName": issue.team_name})
        states = state_result.get("data", {}).get("workflowStates", {}).get("nodes", [])
        if states:
            state_id = states[0]["id"]
            update_result = _graphql_request(UPDATE_ISSUE_MUTATION, {
                "issueId": issue.issue_id,
                "stateId": state_id,
            })
            if "errors" not in update_result:
                state_updated = update_result.get("data", {}).get("issueUpdate", {}).get("success", False)
            if state_updated:
                print(f"Issue state updated to 'In Review'")
            else:
                print(f"Failed to update state: {update_result}")
        else:
            print(f"No 'In Review' state found for team '{issue.team_name}'")
    else:
        print("Skipping state update: no team_name available")

    return UpdateLinearResult(comment_posted=comment_posted, state_updated=state_updated)
