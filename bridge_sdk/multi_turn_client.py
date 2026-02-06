"""HTTP client for driving multi-turn agent sessions via the Core API."""

import os
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import json


class MultiTurnClient:
    """Drives multi-turn agent sessions via Core API HTTP calls.

    Reads FORGE_API_URL and FORGE_API_TOKEN from environment by default.
    """

    def __init__(self, api_url: str | None = None, api_token: str | None = None):
        self.api_url = api_url or os.environ["FORGE_API_URL"]
        self.api_token = api_token or os.environ["FORGE_API_TOKEN"]

    def _request(
        self,
        method: str,
        path: str,
        body: dict | None = None,
        timeout: int = 30,
    ) -> dict:
        url = f"{self.api_url}{path}"
        data = json.dumps(body).encode() if body else None
        req = Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self.api_token}")
        req.add_header("Content-Type", "application/json")
        try:
            with urlopen(req, timeout=timeout) as resp:
                resp_body = resp.read()
                if not resp_body:
                    return {}
                return json.loads(resp_body)
        except HTTPError as e:
            error_body = e.read().decode() if e.fp else ""
            raise RuntimeError(f"{method} {path} returned {e.code}: {error_body}") from e

    def list_agents(self, name: str | None = None) -> list[dict]:
        """GET /v0/agents, optionally filtered by name."""
        path = "/v0/agents"
        if name:
            path += f"?name={name}"
        resp = self._request("GET", path)
        return resp.get("agents", resp) if isinstance(resp, dict) else resp

    def create_session(
        self,
        agent_id: str,
        prompt: str | None = None,
        sandbox_definition_id: str | None = None,
    ) -> dict:
        """POST /v0/agents/{agent_id}/sessions → session dict with id."""
        body: dict = {"type": "remote"}
        if prompt:
            body["prompt"] = prompt
        if sandbox_definition_id:
            body["sandbox_definition_id"] = sandbox_definition_id
        return self._request("POST", f"/v0/agents/{agent_id}/sessions", body)

    def get_session(self, session_id: str) -> dict:
        """GET /v0/sessions/{session_id}."""
        return self._request("GET", f"/v0/sessions/{session_id}")

    def wait_for_state(
        self,
        session_id: str,
        target_states: set[str],
        timeout: int = 300,
        poll_interval: float = 3.0,
    ) -> dict:
        """Poll session until it reaches one of target_states."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            session = self.get_session(session_id)
            state = session.get("state", "")
            print(f"  session {session_id}: state={state}")
            if state in target_states:
                return session
            if state in ("failed", "cancelled"):
                raise RuntimeError(f"Session {session_id} reached terminal state: {state}")
            time.sleep(poll_interval)
        raise TimeoutError(f"Session {session_id} did not reach {target_states} within {timeout}s")

    def prompt(self, session_id: str, message: str) -> str:
        """POST /v0/sessions/{session_id}/prompt → command_id."""
        resp = self._request("POST", f"/v0/sessions/{session_id}/prompt", {"message": message})
        return resp["command_id"]

    def get_command(self, session_id: str, command_id: str) -> dict:
        """GET /v0/sessions/{session_id}/commands/{command_id}."""
        return self._request("GET", f"/v0/sessions/{session_id}/commands/{command_id}")

    def wait_for_command(
        self,
        session_id: str,
        command_id: str,
        timeout: int = 600,
        poll_interval: float = 3.0,
    ) -> dict:
        """Poll command until it completes."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            result = self.get_command(session_id, command_id)
            status = result.get("status", "")
            print(f"  command {command_id}: status={status}")
            if status in ("completed", "error"):
                return result
            time.sleep(poll_interval)
        raise TimeoutError(f"Command {command_id} did not complete within {timeout}s")

    def exec(
        self,
        session_id: str,
        command: list[str],
        cwd: str | None = None,
    ) -> dict:
        """POST /v0/sessions/{session_id}/exec → {exit_code, stdout, stderr}."""
        body: dict = {"command": command}
        if cwd:
            body["cwd"] = cwd
        # Exec is synchronous and may take a while
        return self._request("POST", f"/v0/sessions/{session_id}/exec", body, timeout=300)

    def finish(self, session_id: str) -> None:
        """POST /v0/sessions/{session_id}/finish."""
        self._request("POST", f"/v0/sessions/{session_id}/finish")

    def get_trajectory(self, session_id: str) -> dict:
        """GET /v0/sessions/{session_id}/trajectory."""
        return self._request("GET", f"/v0/sessions/{session_id}/trajectory")
