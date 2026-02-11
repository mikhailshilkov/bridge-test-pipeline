"""Pydantic models for linear_to_pr pipeline input/output types."""

from pydantic import BaseModel, Field


# Step 1: Fetch Linear Issue
class FetchLinearIssueInput(BaseModel):
    linear_issue_id: str = Field(description="Linear issue identifier, e.g. 'FD-107'")


class FetchLinearIssueResult(BaseModel):
    issue_id: str
    identifier: str
    title: str
    description: str = ""
    team_name: str = ""
    project_name: str = ""
    labels: list[str] = Field(default_factory=list)
    priority: int = 0
    url: str = ""
    state: str = ""


# Step 2: Select Repository
class RepoSelectionResult(BaseModel):
    owner: str
    repo_name: str
    repo_url: str
    branch: str = "main"


# Step 3: Investigate Root Cause
class InvestigateResult(BaseModel):
    session_id: str
    root_cause: str = ""
    affected_files: list[str] = Field(default_factory=list)
    summary: str = ""


# Step 4: Validate Specification
class ValidateSpecResult(BaseModel):
    session_id: str
    score: int = 0
    decision: str = ""
    questions: list[str] = Field(default_factory=list)
    summary: str = ""


# Step 5: Design Solution
class DesignResult(BaseModel):
    session_id: str
    approach: str = ""
    branch_name: str = ""
    files_to_modify: list[str] = Field(default_factory=list)
    plan: str = ""


# Step 6: Implement & Create PR
class ImplementResult(BaseModel):
    pr_url: str = ""
    pr_number: int = 0
    pr_title: str = ""
    branch_name: str = ""
    files_changed: list[str] = Field(default_factory=list)


# Step 7: Update Linear Issue
class UpdateLinearResult(BaseModel):
    comment_posted: bool = False
    state_updated: bool = False
