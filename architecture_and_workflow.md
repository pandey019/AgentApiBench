# AgentAPIBench: End-to-End Architecture & Workflow

This document explains exactly how AgentAPIBench works under the hood, detailing the flow of data, how the components interact, and how scoring is calculated.

---

## 1. High-Level Architecture

The system consists of three distinct components running simultaneously:

1. **The Agent / Inference Script (`inference.py`)**: The script that runs the LLM, feeds it observations, parses its JSON actions, and logs the standard output required by the benchmark.
2. **The OpenEnv Server (`server/app.py` & `env/environment.py`)**: A FastAPI server running on port `7860` that acts as the referee. It manages the episode state, loads scenarios, executes the agent's actions, and calculates the score.
3. **The Mock API (`mock_api/server.py`)**: A FastAPI server running on port `7861` that simulates a real-world SaaS backend. It handles authentication, validation, state (customers, invoices, payments), and critically, **logs every API call made to it**.

```text
┌─────────────────┐       JSON via HTTP       ┌──────────────────┐
│                 │      POST /step           │                  │
│  inference.py   ├──────────────────────────►│  OpenEnv Server  │
│  (LLM Agent)    │◄──────────────────────────┤  (port 7860)     │
│                 │   Observation + Reward    │   AgentAPIEnv    │
└─────────────────┘                           └────────┬─────────┘
                                                       │
                                  Executes HTTP Call   │ 
                                  & Fetches Call Log   │
                                                       ▼
                                              ┌──────────────────┐
                                              │                  │
                                              │    Mock API      │
                                              │  (port 7861)     │
                                              │   CallLogger     │
                                              └──────────────────┘
```

---

## 2. Step-by-Step Workflow

Here is exactly what happens during a single episode (e.g., running `task1`):

### Phase 1: Initialization
1. `inference.py` starts and sends a `POST /reset?task_id=task1` request to the OpenEnv server.
2. `AgentAPIEnv` receives the request:
   - It instantiates a `ScenarioLoader` and randomly selects one of the 5 JSON scenarios for `task1` (e.g., `scenario_01.json`).
   - It sends a `DELETE /v1/_internal/call_log` request to the Mock API to clear out any logs from previous episodes.
   - It formats the `task_description` and `api_docs` into an `ApiCallObservation`.
3. The OpenEnv server returns the initial observation to the agent.

### Phase 2: The Action Loop
4. `inference.py` takes the observation, injects it into a prompt, and calls the OpenAI API (e.g., `gpt-4o-mini`).
5. The LLM generates a JSON response representing an API call (Method, URL, Headers, Body).
6. `inference.py` parses this JSON and sends it via `POST /step` to the OpenEnv server.
7. `AgentAPIEnv` processes the step:
   - It takes the URL, method, headers, and body provided by the agent.
   - **Execution:** It makes a real HTTP request to the Mock API (`http://localhost:7861`) using those exact parameters.
   - **Mock API Side:** The Mock API receives the call. It checks the `Authorization` header, validates the payload, updates its internal JSON state if necessary, and logs the precise details of the call into its thread-safe `CallLogger`.
   - **Response:** The Mock API returns a response (e.g., `200 OK` or `422 Unprocessable Entity`) back to `AgentAPIEnv`.
8. `AgentAPIEnv` prepares for grading:
   - It immediately sends a `GET /v1/_internal/call_log` request to the Mock API to retrieve the updated list of all API calls made so far.
   - It passes the Agent's original action, the scenario's `ground_truth`, and the complete `call_log` to the specific task grader (e.g., `task1_grader.py`).

### Phase 3: Grading & Reward
9. **The Grader** evaluates the action deterministically:
   - *Example (Task 1):* Did the URL contain the right path? Did the headers have the correct "Bearer" token? Did the method match? 
   - It calculates a step reward between `0.0` and `1.0`.
10. `AgentAPIEnv` checks termination conditions (is the task complete? or did we hit `max_steps`?).
11. `AgentAPIEnv` returns a `StepResult` to `inference.py` containing:
    - The new `observation` (including the HTTP response and any error messages from the Mock API).
    - The `reward`.
    - `done` (True/False).

### Phase 4: Episode End
12. `inference.py` logs the `[STEP]` to standard output.
13. If `done` is True, `inference.py` calculates the final score (sum of rewards / max steps) and logs `[END]`.
14. It calls `POST /close` to tear down the environment.

---

## 3. Component Deep Dive

### A. The Scenarios (`env/scenarios/`)
Scenarios are the heart of the benchmark. They define what the agent needs to do.
Each scenario JSON contains:
- `task_description`: The prompt given to the LLM.
- `api_docs`: The "fake" documentation the LLM must read to know how to format its requests.
- `ground_truth`: The exact criteria the grader looks for (e.g., `required_params`, expected sequence of calls, or bugs to fix).

### B. The Mock API & Call Logger (`mock_api/`)
Why do we need a mock API instead of just checking the LLM's JSON?
- **Realism:** Agents need to handle real HTTP error codes. If they format a token wrong, they get a real `401 Unauthorized`. If they miss a required body field, they get a `422 Unprocessable Entity` with a descriptive message. Task 3 entirely relies on the agent reading these dynamic error messages to debug its code.
- **The Call Logger:** This is a hidden backdoor. Every time a request hits the Mock API, the `CallLogger` records the method, path, params, status code, and response. The OpenEnv server uses this log to verify if a sequence of calls *actually* succeeded on the backend, rather than just guessing if the agent's intent was correct.

### C. The Graders (`env/graders/`)
Graders are completely deterministic (no LLM-as-a-judge).
- **Task 1 Grader (Single Call):** Awards partial credit based on how well the single API call was formed (25% method, 25% path, 25% auth, 25% params).
- **Task 2 Grader (Multi-Step):** Loops through the `expected_sequence` in the ground truth. It checks the `call_log` to see if the agent successfully made Call 1, then Call 2, etc. It awards partial credit per completed step in the chain.
- **Task 3 Grader (Debug):** Checks the agent's actions to see if it successfully corrected the 3 planted bugs (e.g., Did it finally submit an action with the `Bearer` prefix? Did it switch `PUT` to `POST`?).

### D. The `inference.py` Baseline
This script uses a low temperature (`0.1`) to ensure deterministic JSON formatting. It traps errors locally so that if the LLM hallucinates non-JSON output, the script sends a fallback API call rather than crashing, ensuring the benchmark finishes and logs the episode correctly.