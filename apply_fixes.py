import re
import os

# --- 1. Fix inference.py ---
with open("inference.py", "r") as f:
    inference_code = f.read()

# Fix score formula
inference_code = re.sub(
    r"score = min\(1\.0, max\(0\.0, sum\(rewards\) / max_reward\)\) if rewards else 0\.0",
    r"score = min(1.0, max(0.0, sum(rewards)))",
    inference_code,
)

# Fix System Prompt
old_prompt = r'SYSTEM_PROMPT = textwrap\.dedent\(\s*"""(.*?)"""\s*\)\.strip\(\)'
new_prompt = r'''SYSTEM_PROMPT = textwrap.dedent(
    """
You are an AI agent completing REST API tasks.

RULES:
1. Read YOUR TASK carefully — it tells you exactly what to do
2. Your FIRST call must directly address the task
3. If the task says "customer cust_4821" — call /customers/cust_4821 NOT /customers
4. Use the exact IDs mentioned in the task description
5. Only make calls needed for THIS task

Return ONLY this JSON:
{
  "method": "GET|POST|PUT|PATCH|DELETE",
  "url": "full URL using base_url from docs",
  "headers": {"Authorization": "Bearer TOKEN"},
  "params": {},
  "body": null,
  "reasoning": "one sentence"
}
"""
).strip()'''
inference_code = re.sub(old_prompt, new_prompt, inference_code, flags=re.DOTALL)

# Add debug print to get_agent_action
debug_injection = """    user_prompt = build_user_prompt(obs)
    
    print(f"[DEBUG] Task: {obs.get('task_description', 'MISSING')[:100]}", flush=True)
    print(f"[DEBUG] Prompt length: {len(user_prompt)} chars", flush=True)
"""
inference_code = inference_code.replace(
    "    user_prompt = build_user_prompt(obs)", debug_injection
)

with open("inference.py", "w") as f:
    f.write(inference_code)


# --- 2. Fix server/agentapi_environment.py ---
with open("server/agentapi_environment.py", "r") as f:
    env_code = f.read()

# Fix call log clearing (absolute URLs to bypass httpx relative join bugs)
old_clear = r'''    def _clear_mock_api_log\(self\):
        """Clear the mock API call log at the start of each episode\."""
        try:
            self\._http\.delete\(
                "/_internal/call_log",
                headers=\{"Authorization": f"Bearer \{MOCK_API_TOKEN\}"\}
            \)
        except Exception:
            pass'''

new_clear = '''    def _clear_mock_api_log(self):
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
            print(f"[ENV] Clear failed: {e}", flush=True)'''

env_code = re.sub(old_clear, new_clear, env_code, flags=re.DOTALL)

# Fix getting call log (absolute URLs to bypass httpx relative join bugs)
old_get_log = r"""        try:
            log_resp = self\._http\.get\(
                "/_internal/call_log",
                headers=\{"Authorization": f"Bearer \{MOCK_API_TOKEN\}"\}
            \)
            if log_resp\.status_code == 200:
                self\._state\.call_log = log_resp\.json\(\)\.get\("calls", \[\]\)
                print\(f"\[ENV\] call_log size after step: \{len\(self\._state\.call_log\)\}", flush=True\)
        except Exception as e:
            print\(f"\[ENV\] Failed to fetch call log: \{e\}", flush=True\)"""

new_get_log = """        try:
            log_resp = self._http.get(
                "http://127.0.0.1:7861/v1/_internal/call_log",
                headers={"Authorization": f"Bearer {MOCK_API_TOKEN}"}
            )
            if log_resp.status_code == 200:
                self._state.call_log = log_resp.json().get("calls", [])
                print(f"[ENV] call_log size after step: {len(self._state.call_log)}", flush=True)
        except Exception as e:
            print(f"[ENV] Failed to fetch call log: {e}", flush=True)"""

env_code = re.sub(old_get_log, new_get_log, env_code, flags=re.DOTALL)


with open("server/agentapi_environment.py", "w") as f:
    f.write(env_code)

print("Fixes applied.")
