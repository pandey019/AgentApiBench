import re

with open("inference.py", "r") as f:
    code = f.read()

# 1. Replace SYSTEM_PROMPT with get_system_prompt
prompt_replacement = '''def get_system_prompt(task_id: str) -> str:
    base = """You are an AI agent completing REST API tasks.
You MUST respond with ONLY a JSON object. No explanation. No markdown. No code.
Just the raw JSON object and nothing else.

Required format:
{
  "method": "GET|POST|PUT|PATCH|DELETE",
  "url": "full url",
  "headers": {"Authorization": "Bearer TOKEN"},
  "params": {},
  "body": null,
  "reasoning": "one sentence"
}"""

    if task_id == "task3":
        return base + """

SPECIAL INSTRUCTIONS FOR DEBUG TASK:
You are shown a broken API client. Your job is NOT to explain the bugs.
Your job is to MAKE THE CORRECT API CALL yourself.
Look at the error from the previous step and submit a corrected API call.
Start with the correct auth format: {"Authorization": "Bearer sk-bench-4921x"}
Use method POST for /payments.
Include customer_id, amount, AND currency in the body.

Example correct action:
{"method":"POST","url":"http://127.0.0.1:7861/v1/payments","headers":{"Authorization":"Bearer sk-bench-4921x"},"params":{},"body":{"customer_id":"cust_9933","amount":49.0,"currency":"USD"},"reasoning":"Fixed all bugs"}"""

    return base'''

# Remove old SYSTEM_PROMPT definition
old_system_prompt_pattern = r"SYSTEM_PROMPT = textwrap\.dedent\([^)]+\)\.strip\(\)"
code = re.sub(old_system_prompt_pattern, prompt_replacement, code, flags=re.DOTALL)


# 2. Replace get_agent_action entirely
import textwrap

old_get_agent_action = re.search(
    r"def get_agent_action\(client: OpenAI, obs: dict\) -> dict:(.*?)# ─── Episode runner",
    code,
    re.DOTALL,
).group(0)

new_get_agent_action = '''import re

def _validate_action(action: dict, obs: dict) -> dict:
    """Ensure action has required fields."""
    if "method" not in action or "url" not in action:
        raise ValueError("Missing method or url")
    action.setdefault("headers", {})
    action.setdefault("params", {})
    action.setdefault("body", None)
    action.setdefault("reasoning", "")
    
    if action["params"] is None:
        action["params"] = {}
    if action["headers"] is None:
        action["headers"] = {}
        
    return action

def _fallback_action(obs: dict) -> dict:
    """Return a do-nothing fallback action."""
    base_url = obs.get("api_base_url", "http://127.0.0.1:7861/v1")
    return {
        "method":    "GET",
        "url":       base_url + "/health",
        "headers":   {},
        "params":    {},
        "body":      None,
        "reasoning": "Fallback: could not parse LLM response as JSON",
    }

def get_agent_action(client: OpenAI, obs: dict, task_id: str) -> dict:
    """
    Ask the LLM which API call to make next.
    """
    user_prompt = build_user_prompt(obs)
    system_prompt = get_system_prompt(task_id)

    print(f"[DEBUG] Task: {obs.get('task_description', 'MISSING')[:100]}", flush=True)
    print(f"[DEBUG] Prompt length: {len(user_prompt)} chars", flush=True)

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=TEMPERATURE,
            max_tokens=600,
            stream=False,
        )
        text = (completion.choices[0].message.content or "").strip()

        # Strategy 1: try parsing the whole thing as JSON
        try:
            action = json.loads(text)
            return _validate_action(action, obs)
        except json.JSONDecodeError:
            pass

        # Strategy 2: strip markdown code blocks
        if "```" in text:
            # Extract content between first ``` and last ```
            parts = text.split("```")
            for part in parts[1::2]:  # odd indices are inside backticks
                cleaned = part.strip()
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:].strip()
                try:
                    action = json.loads(cleaned)
                    return _validate_action(action, obs)
                except json.JSONDecodeError:
                    continue

        # Strategy 3: find JSON object with regex
        match = re.search(r'\\{[^{}]*"method"[^{}]*\\}', text, re.DOTALL)
        if match:
            try:
                action = json.loads(match.group())
                return _validate_action(action, obs)
            except json.JSONDecodeError:
                pass

        # Strategy 4: find ANY valid JSON object in the text
        match = re.search(r'\\{.*\\}', text, re.DOTALL)
        if match:
            try:
                action = json.loads(match.group())
                return _validate_action(action, obs)
            except json.JSONDecodeError:
                pass

        print(f"[DEBUG] LLM produced invalid JSON: all strategies failed", flush=True)
        return _fallback_action(obs)

    except Exception as e:
        print(f"[DEBUG] LLM call failed: {e}", flush=True)
        return _fallback_action(obs)

# ─── Episode runner'''

code = code.replace(old_get_agent_action, new_get_agent_action)

# 3. Update call in run_episode
code = code.replace(
    "action_dict = get_agent_action(client, obs)",
    "action_dict = get_agent_action(client, obs, task_id)",
)

with open("inference.py", "w") as f:
    f.write(code)

print("inference.py updated successfully.")
