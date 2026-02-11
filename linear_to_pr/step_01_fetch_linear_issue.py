"""Step 1: Fetch a Linear issue by identifier via the GraphQL API."""

import json
import os
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from bridge_sdk import step

from linear_to_pr.models import FetchLinearIssueInput, FetchLinearIssueResult

LINEAR_API_URL = "https://api.linear.app/graphql"

ISSUE_QUERY = """
query GetIssue($id: String!) {
    issue(id: $id) {
        id
        identifier
        title
        description
        team { name }
        project { name }
        labels { nodes { name } }
        priority
        url
        state { name }
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


_STUB_ISSUES = {
    "FD-107": FetchLinearIssueResult(
        issue_id="stub-fd-107",
        identifier="FD-107",
        title="Fix flaky timeout in sandbox health check",
        description=(
            "The sandbox health check probe occasionally times out after 5s, "
            "causing pods to restart unnecessarily. The root cause appears to be "
            "a blocking DNS lookup in the health handler. We should switch to an "
            "async resolver or increase the probe timeout."
        ),
        team_name="Forward Deployed",
        project_name="FD",
        labels=["bug", "sandbox"],
        priority=2,
        url="https://linear.app/poolside/issue/FD-107",
        state="In Progress",
    ),
}


@step(credential_bindings={"LINEAR_API_KEY_SECRET": "LINEAR_API_KEY"})
def fetch_linear_issue(input_data: FetchLinearIssueInput) -> FetchLinearIssueResult:
    """Fetch issue metadata from Linear via GraphQL API."""
    identifier = input_data.linear_issue_id
    print(f"Fetching Linear issue: {identifier}")

    # Stub mode: return hard-coded data when LINEAR_API_KEY is not set
    if not os.environ.get("LINEAR_API_KEY"):
        if identifier in _STUB_ISSUES:
            print(f"[STUB] Returning hard-coded data for {identifier}")
            return _STUB_ISSUES[identifier]
        # Return a generic stub for any identifier
        print(f"[STUB] Returning generic stub for {identifier}")
        return FetchLinearIssueResult(
            issue_id=f"stub-{identifier.lower()}",
            identifier=identifier,
            title=f"Stub issue for {identifier}",
            description="This is a stub issue for local testing.",
            team_name="Forward Deployed",
            project_name=identifier.split("-")[0] if "-" in identifier else "",
        )

    result = _graphql_request(ISSUE_QUERY, {"id": identifier})

    if "errors" in result:
        raise RuntimeError(f"Linear GraphQL errors: {result['errors']}")

    issue = result["data"]["issue"]
    labels = [node["name"] for node in (issue.get("labels", {}).get("nodes", []))]

    output = FetchLinearIssueResult(
        issue_id=issue["id"],
        identifier=issue["identifier"],
        title=issue["title"],
        description=issue.get("description") or "",
        team_name=(issue.get("team") or {}).get("name", ""),
        project_name=(issue.get("project") or {}).get("name", ""),
        labels=labels,
        priority=issue.get("priority", 0),
        url=issue.get("url", ""),
        state=(issue.get("state") or {}).get("name", ""),
    )
    print(f"Fetched: [{output.identifier}] {output.title}")
    return output
