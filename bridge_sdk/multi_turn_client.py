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

    def _request(self, method: str, path: str, body: dict | None = None) -> dict:
        url = f"{self.api_url}{path}"
        data = json.dumps(body).encode() if body else None
        req = Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self.api_token}")
        req.add_header("Content-Type", "application/json")
        try:
            with urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
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
        prompt: str,
        sandbox_definition_id: str | None = None,
    ) -> dict:
        """POST /v0/agents/{agent_id}/sessions → session dict with id."""
        body: dict = {
            "type": "remote",
            "prompt": prompt,
        }
        if sandbox_definition_id:
            body["sandbox_definition_id"] = sandbox_definition_id
        return self._request("POST", f"/v0/agents/{agent_id}/sessions", body)

    def get_session(self, agent_id: str, session_id: str) -> dict:
        """GET /v0/agents/{agent_id}/sessions/{session_id}."""
        return self._request("GET", f"/v0/agents/{agent_id}/sessions/{session_id}")

    def wait_for_state(
        self,
        agent_id: str,
        session_id: str,
        target_states: set[str],
        timeout: int = 300,
        poll_interval: float = 3.0,
    ) -> dict:
        """Poll session until it reaches one of target_states."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            session = self.get_session(agent_id, session_id)
            state = session.get("state", "")
            if state in target_states:
                return session
            if state in ("failed", "cancelled"):
                raise RuntimeError(f"Session {session_id} reached terminal state: {state}")
            time.sleep(poll_interval)
        raise TimeoutError(f"Session {session_id} did not reach {target_states} within {timeout}s")

    def send_command(self, session_id: str, command: str) -> dict:
        """POST /v0/sessions/{session_id}/commands."""
        return self._request("POST", f"/v0/sessions/{session_id}/commands", {"command": command})

    def get_trajectory(self, agent_id: str, session_id: str) -> dict:
        """GET /v0/agents/{agent_id}/sessions/{session_id}/trajectory."""
        return self._request("GET", f"/v0/agents/{agent_id}/sessions/{session_id}/trajectory")
