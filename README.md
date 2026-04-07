---
title: AgentAPIBench
emoji: 🔌
colorFrom: indigo
colorTo: indigo     
sdk: docker
pinned: true
tags:
  - openenv
  - benchmark
  - tool-use
  - api-integration
  - evaluation
  - real-world
---

# AgentAPIBench

**The benchmark for evaluating AI agents on real-world API integration tasks.**

AgentAPIBench tests the #1 enterprise AI capability: reading API documentation
and making correct authenticated REST API calls to complete business workflows.

---

## Why This Benchmark

Every enterprise AI deployment requires agents that can:
- Read API docs and make correct authenticated calls
- Chain multiple API calls where each depends on the last
- Recover from errors and fix broken integrations

No public standard benchmark existed for this. AgentAPIBench fills that gap.

---

## Environment Description

AgentAPIBench runs a mock REST API server simulating a realistic SaaS business
API (customers, invoices, payments). The agent receives:

- A task description telling it what to accomplish
- Full API documentation (endpoints, auth, parameters, response schema)
- Feedback from each API call (HTTP status, response body, errors)

The agent must make correct API calls to complete the task. Grading is
**100% deterministic** — based on HTTP responses from the mock API, not
LLM output parsing.

---

## Tasks

### Task 1 — Single API Call (Easy)

**Objective:** Read API documentation and make one correct authenticated call.

**What is tested:** Instruction following, parameter extraction, auth headers.

**Example task:** *"List up to 5 active customers."*

**Correct action:**
```json
{
  "method": "GET",
  "url": "http://api/v1/customers",
  "headers": {"Authorization": "Bearer sk-bench-4921x"},
  "params": {"status": "active", "limit": 5}
}
```

**Baseline score (gemini-2.5-flash):** 1.000

---

### Task 2 — Multi-Step Workflow (Medium)

**Objective:** Chain 3-4 API calls where each call depends on the previous response.

**What is tested:** Planning, JSON response parsing, stateful multi-turn execution.

**Example task:** *"Find all unpaid invoices for customer cust_4821, then send
an email reminder for each one."*

**Required sequence:**
1. `GET /invoices?customer_id=cust_4821&status=unpaid` → get invoice IDs
2. `POST /invoices/inv_001/remind` with `{"channel": "email"}`
3. `POST /invoices/inv_002/remind` with `{"channel": "email"}`

**Baseline score (gemini-2.5-flash):** 1.000

---

### Task 3 — Debug Broken Integration (Hard)

**Objective:** Fix a broken API client by reading error responses and
submitting corrected calls until achieving HTTP 200.

**What is tested:** Iterative error recovery, API debugging, error interpretation.

**Pre-injected errors the agent sees:**
- `401 Unauthorized` — wrong auth format (missing Bearer prefix)
- `405 Method Not Allowed` — wrong HTTP method
- `422 Unprocessable Entity` — missing required field

**Agent must make one corrected call that passes all validations.**

**Baseline score (gemini-2.5-flash):** 1.000

---

## Action Space

At each step, the agent submits a JSON object:

```json
{
  "method":    "GET | POST | PUT | PATCH | DELETE",
  "url":       "http://127.0.0.1:7861/v1/resource",
  "headers":   {"Authorization": "Bearer sk-bench-4921x"},
  "params":    {"key": "value"},
  "body":      {"field": "value"},
  "reasoning": "brief explanation (logged but not scored)"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| method | string | Yes | HTTP method |
| url | string | Yes | Full URL including base URL from docs |
| headers | object | Yes | Must include Authorization header |
| params | object | No | URL query parameters |
| body | object | No | Request body for POST/PUT |
| reasoning | string | No | Agent's explanation — not used in scoring |

---

## Observation Space

At each step, the agent receives:

| Field | Type | Description |
|---|---|---|
| task_description | string | What the agent must accomplish |
| api_base_url | string | Base URL for the mock API |
| api_docs | object | Full endpoint documentation |
| step_number | integer | Current step (1-indexed) |
| max_steps | integer | Maximum steps allowed |
| previous_responses | array | All previous API call results |
| current_errors | array | Error messages from last call |

---

## Reward Function

Reward is computed entirely from HTTP responses recorded by the mock API server.
**No LLM output is parsed for scoring.**

### Task 1 reward breakdown
- `0.40` — correct endpoint was called
- `0.30` — call returned HTTP 200 (correct auth)
- `0.30` — required query parameters present and correct

### Task 2 reward breakdown
- `0.40` — first step (fetch data) completed correctly
- `0.30` — each subsequent step completed correctly (split per item)

### Task 3 reward breakdown
- `0.30` — got past 401 (auth fixed)
- `0.30` — got past 405 (method fixed)
- `0.40` — achieved HTTP 200 (all bugs fixed)

Reward is **partial** — agent earns credit for each sub-task completed,
providing dense signal across the full episode trajectory.

---

## Baseline Scores

Evaluated using `gemini-2.5-flash` via OpenAI-compatible endpoint.

| Task | Difficulty | Score | Steps used |
|---|---|---|---|
| Task 1 — single API call | Easy | 1.000 | 1 |
| Task 2 — multi-step workflow | Medium | 1.000 | 3 |
| Task 3 — debug broken client | Hard | 1.000 | 1 |
| **Average** | | **1.000** | |

---

## Setup & Running Locally

### Prerequisites
- Python 3.11+
- Docker (optional)

### Install

```bash
git clone https://github.com/YOUR_USERNAME/agentapibench
cd agentapibench
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Run the environment

```bash
# Terminal 1 — start mock API server
uvicorn mock_api.server:app --host 0.0.0.0 --port 7861

# Terminal 2 — start OpenEnv wrapper
uvicorn server.app:app --host 0.0.0.0 --port 7860
```

### Run baseline inference

```bash
export HF_TOKEN="your-api-key"
export API_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/"
export MODEL_NAME="gemini-2.0-flash"

python inference.py
```

### Run with Docker

```bash
docker build -t agentapibench .
docker run -p 7860:7860 \
  -e HF_TOKEN="your-api-key" \
  -e API_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/" \
  -e MODEL_NAME="gemini-2.0-flash" \
  agentapibench
```

---

## API Endpoints

The OpenEnv wrapper exposes:

| Endpoint | Method | Description |
|---|---|---|
| `/reset?task_id=task1` | POST | Start new episode |
| `/step` | POST | Execute one action |
| `/state` | GET | Current episode state |
| `/health` | GET | Health check |

---

## Mock API Endpoints (what agents call)

| Endpoint | Method | Description |
|---|---|---|
| `/v1/customers` | GET | List customers |
| `/v1/customers/{id}` | GET | Get customer by ID |
| `/v1/invoices` | GET | List invoices |
| `/v1/invoices/{id}/remind` | POST | Send payment reminder |
| `/v1/payments` | POST | Create payment record |

---

## Environment Variables

| Variable | Required | Description | Example |
|---|---|---|---|
| `HF_TOKEN` | Yes | API key for LLM | `AIza...` or HF token |
| `API_BASE_URL` | Yes | LLM API endpoint | `https://generativelanguage.googleapis.com/v1beta/openai/` |
| `MODEL_NAME` | Yes | Model to use | `gemini-2.0-flash` |

---

## License

Apache 2.0

---

## Citation

```bibtex
@misc{agentapibench2026,
  title  = {AgentAPIBench: Evaluating LLM Tool Use on Real-World API Integration},
  year   = {2026},
  url    = {https://huggingface.co/spaces/YOUR_USERNAME/agentapibench}
}
```