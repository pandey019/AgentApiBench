"""
AgentAPIBench Environment

Extends openenv.core Environment base class — the correct pattern
from the official reference implementations (coding_env, calendar_env).

step() returns Observation with reward embedded.
Reward comes ENTIRELY from graders reading mock API call_log.
LLM reasoning field is logged but never used in scoring.
"""

import json
import uuid
import httpx
from pathlib import Path
from openenv.core.env_server import Environment
from openenv.core.env_server.types import State

from models import APICallAction, APIBenchObservation, APIBenchState
from server.graders import task1_grader, task2_grader, task3_grader
from scenarios.loader import ScenarioLoader

SCENARIOS_DIR = Path(__file__).parent.parent / "scenarios"
MOCK_API_URL = "http://127.0.0.1:7861/v1"
MOCK_API_TOKEN = "sk-bench-4921x"

TASK_CONFIGS = {
    "task1": {"name": "single-api-call", "max_steps": 3},
    "task2": {"name": "multi-step-workflow", "max_steps": 6},
    "task3": {"name": "debug-broken-integration", "max_steps": 8},
}

GLOBAL_ENV_STATE = {"task_id": "task1", "scenario": None, "state": None}


class AgentAPIBenchEnvironment(Environment):
    def __init__(self, task_id: str = "task1"):
        super().__init__()
        self._http = httpx.Client(base_url=MOCK_API_URL, timeout=15.0)

    @property
    def task_id(self):
        return GLOBAL_ENV_STATE.get("task_id", "task1")

    @property
    def config(self):
        return TASK_CONFIGS[self.task_id]

    @property
    def _scenario(self):
        return GLOBAL_ENV_STATE["scenario"]

    @_scenario.setter
    def _scenario(self, val):
        GLOBAL_ENV_STATE["scenario"] = val

    @property
    def _state(self) -> APIBenchState:
        return GLOBAL_ENV_STATE["state"]

    @_state.setter
    def _state(self, val):
        GLOBAL_ENV_STATE["state"] = val

    # ─── OpenEnv required methods ─────────────────────────────────────────────

    def reset(self, **kwargs) -> APIBenchObservation:
        task_id = kwargs.get("task_id", "task1")
        if task_id in TASK_CONFIGS:
            GLOBAL_ENV_STATE["task_id"] = task_id

        loader = ScenarioLoader(SCENARIOS_DIR / self.task_id)

        # Load scenario from backend (JSON files, not UI)
        self._scenario = loader.load_random()

        # Reset internal state
        self._state = APIBenchState(
            episode_id=str(uuid.uuid4()),
            task_id=self.task_id,
            task_name=self.config["name"],
            scenario_id=self._scenario["id"],
            step=0,
            step_count=0,
            max_steps=self.config["max_steps"],
            call_log=[],
            cumulative_reward=0.0,
            bugs_fixed=[],
            workflow_progress=0.0,
            done=False,
        )

        print(
            f"[ENV] Reset: task={self.task_id} max_steps={self._state.max_steps}",
            flush=True,
        )

        # Clear mock API call log for this episode
        self._clear_mock_api_log()

        # For task3: pre-inject broken calls so agent sees real errors
        if self.task_id == "task3":
            self._inject_broken_calls()

        # Fetch the call log after injection so the initial observation has the errors
        try:
            log_resp = self._http.get(
                "/_internal/call_log",
                headers={"Authorization": f"Bearer {MOCK_API_TOKEN}"}
            )
            if log_resp.status_code == 200:
                self._state.call_log = log_resp.json().get("calls", [])
        except Exception:
            pass

        return self._build_observation()

    def step(self, action: APICallAction) -> APIBenchObservation:
        if not self._state:
            self.reset()

        self._state.step_count += 1
        self._state.step += 1

        print(
            f"[ENV DEBUG] step={self._state.step_count} max={self._state.max_steps}",
            flush=True,
        )

        # Log the agent's reasoning (for transparency) — NOT for scoring
        if action.reasoning:
            print(f"[ENV] Agent reasoning: {action.reasoning[:200]}", flush=True)

        # Execute the action against the mock API
        self._execute_api_call(action)

        # Fetch updated call_log from mock API
        try:
            log_resp = self._http.get(
                "/_internal/call_log",
                headers={"Authorization": f"Bearer {MOCK_API_TOKEN}"},
            )
            if log_resp.status_code == 200:
                self._state.call_log = log_resp.json().get("calls", [])
                print(
                    f"[ENV] call_log size after step: {len(self._state.call_log)}",
                    flush=True,
                )
        except Exception as e:
            print(f"[ENV] Failed to fetch call log: {e}", flush=True)

        # ── DETERMINISTIC GRADING FROM CALL_LOG ──────────────────────────────
        gt = self._scenario.get("ground_truth", {})

        if self.task_id == "task1":
            total_score = task1_grader.grade(self._state.call_log, gt)

        elif self.task_id == "task2":
            total_score = task2_grader.grade(self._state.call_log, gt)
            self._state.workflow_progress = total_score

        elif self.task_id == "task3":
            total_score = task3_grader.grade(self._state.call_log, gt)
            self._state.bugs_fixed = self._detect_fixed_bugs(gt)
        else:
            total_score = 0.0

        # Step reward = new progress since last step (incremental)
        prev_reward = self._state.cumulative_reward
        step_reward = max(0.0, total_score - prev_reward)
        self._state.cumulative_reward = total_score

        # Check if episode is done
        done = (
            self._state.step_count >= self._state.max_steps or self._is_task_complete()
        )
        self._state.done = done

        obs = self._build_observation()
        obs.reward = round(step_reward, 4)
        obs.done = done
        return obs

    @property
    def state(self) -> APIBenchState:
        return self._state

    # ─── Private helpers ──────────────────────────────────────────────────────

    def _execute_api_call(self, action: APICallAction):
        """Send the agent's API call to the mock server."""
        try:
            url = action.url

            # Strip domain prefixes and the /v1 namespace entirely because httpx base_url ALREADY includes /v1
            for prefix in [
                "https://mock-api.agentapibench.io/v1",
                "http://mock-api.agentapibench.io/v1",
                "http://127.0.0.1:7861/v1",
                "http://localhost:7861/v1",
                "https://mock-api.agentapibench.io",
                "http://mock-api.agentapibench.io",
                "http://127.0.0.1:7861",
                "http://localhost:7861",
            ]:
                if url.startswith(prefix):
                    url = url[len(prefix):]
                    break

            if not url.startswith("/"):
                url = "/" + url

            response = self._http.request(
                method=action.method.upper()
                if hasattr(action, "method")
                else action.get("method", "GET").upper(),
                url=url,
                headers=action.headers
                if hasattr(action, "headers")
                else action.get("headers", {}),
                params=action.params
                if hasattr(action, "params")
                else action.get("params", {}),
                json=action.body if hasattr(action, "body") else action.get("body"),
            )

            print(f"[ENV] {action.method} {url} → {response.status_code}", flush=True)
            return response

        except Exception as e:
            print(f"[ENV] API call error: {e}", flush=True)

    def _build_observation(self) -> APIBenchObservation:
        s = self._scenario or {}
        # Get errors from the most recent call
        recent_errors = []
        if self._state.call_log:
            last_call = self._state.call_log[-1]
            if last_call.get("status") not in [200, 201]:
                body = last_call.get("response", {})
                if isinstance(body, dict):
                    err = (
                        body.get("detail")
                        or body.get("error")
                        or body.get("message", "")
                    )
                    if err:
                        recent_errors = [f"HTTP {last_call.get('status')}: {err}"]

        # Ensure we pass the broken_client code if we are task3
        obs = APIBenchObservation(
            task_id=self.task_id,
            task_description=s.get("task_description", ""),
            api_base_url=s.get("api_docs", {}).get("base_url", ""),
            api_docs=s.get("api_docs", {}),
            step_number=self._state.step_count,
            max_steps=self._state.max_steps,
            previous_responses=[
                {
                    "path": c.get("path"),
                    "status": c.get("status"),
                    "response": c.get("response"),
                }
                for c in self._state.call_log
            ],
            current_errors=recent_errors,
        )

        import json
        # Inject broken_client directly to the observation model's extra kwargs conceptually if present
        if "broken_client" in s:
            obs.task_description += "\n\n=== BROKEN CLIENT ===\n" + json.dumps(
                s.get("broken_client", {}), indent=2
            )

        # Must populate parent class values needed by openenv-core
        obs.reward = 0.0
        obs.done = self._state.done

        return obs

    def _is_task_complete(self) -> bool:
        """Early termination if task is fully solved."""
        call_log = self._state.call_log
        if self.task_id in ("task1", "task3"):
            return any(c.get("status") == 200 for c in call_log)
        elif self.task_id == "task2":
            gt = self._scenario.get("ground_truth", {})
            return task2_grader.grade(call_log, gt) >= 0.99
        return False

    def _detect_fixed_bugs(self, gt: dict) -> list:
        """For task3: detect which bugs have been fixed from call_log."""
        fixed = []
        call_log = self._state.call_log
        target = gt.get("target_path", "/payments")
        calls = [c for c in call_log if target in c.get("path", "")]
        statuses = [c.get("status") for c in calls]

        if any(s != 401 for s in statuses):
            fixed.append("bug_auth")
        non_auth_calls = [c for c in calls if c.get("status") != 401]
        if any(c.get("status") != 405 for c in non_auth_calls):
            fixed.append("bug_method")
        if any(s == 200 for s in statuses):
            fixed.append("bug_currency")
        return fixed

    def _inject_broken_calls(self):
        """Make the 3 buggy calls so agent sees real error responses."""
        # Bug 1: wrong auth → 401
        self._http.post("/payments",
            headers={"Authorization": "sk-bench-4921x"},  # missing Bearer
            json={"customer_id": "cust_123", "amount": 100.0}
        )
        # Bug 2: wrong method → 405  
        self._http.put("/payments",
            headers={"Authorization": f"Bearer {MOCK_API_TOKEN}"},
            json={"customer_id": "cust_123", "amount": 100.0}
        )
        # Bug 3: missing currency → 422
        self._http.post("/payments",
            headers={"Authorization": f"Bearer {MOCK_API_TOKEN}"},
            json={"customer_id": "cust_123", "amount": 100.0}
        )

    def _clear_mock_api_log(self):
        """Clear the mock API call log at the start of each episode."""
        try:
            r = self._http.delete(
                "http://127.0.0.1:7861/v1/_internal/call_log",
                headers={"Authorization": f"Bearer {MOCK_API_TOKEN}"}
            )
            print(f"[ENV] Call log cleared: {r.status_code}", flush=True)
            
            # Verify it's actually empty
            r2 = self._http.get(
                "http://127.0.0.1:7861/v1/_internal/call_log",
                headers={"Authorization": f"Bearer {MOCK_API_TOKEN}"}
            )
            count = len(r2.json().get("calls", []))
            print(f"[ENV] Call log after clear: {count} entries", flush=True)
            
            if count > 0:
                print("[ENV] WARNING: Call log not empty after clear!", flush=True)
        except Exception as e:
            print(f"[ENV] Clear failed: {e}", flush=True)
