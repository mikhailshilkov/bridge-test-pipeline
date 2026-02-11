"""Step 2: Select the GitHub repository based on Linear issue metadata."""

import json
from pathlib import Path
from typing import Annotated

from bridge_sdk import step, step_result

from linear_to_pr.models import FetchLinearIssueResult, RepoSelectionResult
from linear_to_pr.step_01_fetch_linear_issue import fetch_linear_issue

REPO_MAPPING_PATH = Path(__file__).parent / "repo_mapping.json"


def _load_mapping() -> dict:
    with open(REPO_MAPPING_PATH) as f:
        return json.load(f)


@step()
def select_repo(
    issue: Annotated[FetchLinearIssueResult, step_result(fetch_linear_issue)],
) -> RepoSelectionResult:
    """Match Linear issue to a GitHub repository via repo_mapping.json."""
    mapping = _load_mapping()
    projects = mapping.get("projects", {})

    # Extract project key from identifier (e.g. "FD" from "FD-107")
    project_key = issue.identifier.split("-")[0] if "-" in issue.identifier else ""
    project = projects.get(project_key, {})

    # Priority: label override → team override → project default → global default
    repo_config = None

    if not repo_config and issue.labels:
        label_overrides = project.get("label_overrides", {})
        for label in issue.labels:
            if label.lower() in label_overrides:
                repo_config = label_overrides[label.lower()]
                break

    if not repo_config and issue.team_name:
        team_overrides = project.get("team_overrides", {})
        repo_config = team_overrides.get(issue.team_name)

    if not repo_config:
        repo_config = project.get("default")

    if not repo_config:
        repo_config = mapping.get("default")

    if not repo_config:
        raise RuntimeError(
            f"No repository mapping found for issue {issue.identifier} "
            f"(project={project_key}, team={issue.team_name}, labels={issue.labels})"
        )

    result = RepoSelectionResult(
        owner=repo_config["owner"],
        repo_name=repo_config["repo_name"],
        repo_url=repo_config["repo_url"],
        branch=repo_config.get("branch", "main"),
    )
    print(f"Selected repo: {result.owner}/{result.repo_name} (branch: {result.branch})")
    return result
