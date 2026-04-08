---
title: AgentAPIBench
emoji: 🔌
colorFrom: indigo
colorTo: purple
sdk: docker
pinned: true
tags:
  - openenv
  - benchmark
  - tool-use
  - api-integration
  - evaluation
  - real-world
  - rl-environment
  - function-calling
---

<div align="center">

# 🔌 AgentAPIBench

### The First Open Benchmark for LLM API Integration & Tool Use

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![OpenEnv](https://img.shields.io/badge/OpenEnv-Compatible-green.svg)](https://github.com/meta-pytorch/OpenEnv)
[![HuggingFace](https://img.shields.io/badge/🤗-HuggingFace_Space-yellow)](https://huggingface.co/spaces/balrampandey/AgentApiBench)
[![GitHub](https://img.shields.io/badge/GitHub-pandey019%2FAgentApiBench-black)](https://github.com/pandey019/AgentApiBench)

**Built for the Meta × PyTorch OpenEnv Hackathon 2026**

</div>

---

## 🎯 What is AgentAPIBench?

AgentAPIBench is a fully open-source RL environment that evaluates AI agents
on the most important enterprise AI capability: **reading REST API documentation
and making correct authenticated API calls** to complete real business workflows.

No game. No toy problem. This is what enterprise AI actually does every day.

```
Agent receives:  Task description + API documentation
Agent action:    A structured API call (method, url, headers, params, body)
Environment:     Executes the call against a mock REST API server
Reward:          Determined by HTTP response codes — 100% deterministic
```

---

## 🏆 Baseline Scores

Evaluated using `gemini-2.5-flash` via OpenAI-compatible endpoint.

| Task | Difficulty | Score | Avg Steps |
|------|-----------|-------|-----------|
| Task 1 — Single API call | 🟢 Easy | **1.000** | 1 |
| Task 2 — Multi-step workflow | 🟡 Medium | **1.000** | 3 |
| Task 3 — Debug broken client | 🔴 Hard | **1.000** | 1 |
| **Overall Average** | | **1.000** | |

---

## 📋 Tasks

### 🟢 Task 1 — Single API Call (Easy)

The agent reads API docs and makes **one correct authenticated call**.

Tests: instruction following, parameter extraction, auth header construction.

**Example:**
```
Task:   "List up to 5 active customers."
Action: GET /v1/customers?status=active&limit=5
        Authorization: Bearer sk-bench-4921x
Result: HTTP 200 → reward = 1.0
```

---

### 🟡 Task 2 — Multi-Step Workflow (Medium)

The agent chains **3-4 API calls** where each depends on the previous response.

Tests: planning, JSON parsing, stateful multi-turn execution.

**Example:**
```
Task:   "Find all unpaid invoices for customer cust_4821,
         then send an email reminder for each one."

Step 1: GET /v1/invoices?customer_id=cust_4821&status=unpaid
        → returns [inv_001, inv_002]

Step 2: POST /v1/invoices/inv_001/remind  {"channel": "email"}
Step 3: POST /v1/invoices/inv_002/remind  {"channel": "email"}
        → reward = 1.0
```

---

### 🔴 Task 3 — Debug Broken Integration (Hard)

The agent sees **pre-injected broken API calls** and must fix all bugs
by reading error responses and submitting corrected calls.

Tests: iterative reasoning, error interpretation, API debugging.

**Pre-injected failures the agent sees:**
```
Call 1: Authorization: sk-bench-4921x      → 401 (missing Bearer prefix)
Call 2: GET /v1/payments                   → 405 (wrong method, must be POST)
Call 3: {"customer_id": "x", "amount": 1}  → 422 (missing currency field)
```

**Agent must submit one call that passes all validations → HTTP 200 → reward = 1.0**

---

## 🔁 Action Space

At each step the agent submits a JSON object:

```json
{
  "method":    "GET | POST | PUT | PATCH | DELETE",
  "url":       "http://localhost:7861/v1/customers/cust_4821",
  "headers":   {"Authorization": "Bearer sk-bench-4921x"},
  "params":    {"include": "subscription"},
  "body":      null,
  "reasoning": "Retrieving customer details including subscription"
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `method` | string | ✅ Yes | HTTP verb |
| `url` | string | ✅ Yes | Full URL with base URL from docs |
| `headers` | object | ✅ Yes | Must include `Authorization` |
| `params` | object | No | URL query parameters |
| `body` | object/null | No | Request body for POST/PUT |
| `reasoning` | string | No | Logged only — **not used in scoring** |

---

## 👁️ Observation Space

At each step the agent receives:

| Field | Type | Description |
|-------|------|-------------|
| `task_description` | string | Exact task the agent must complete |
| `api_base_url` | string | Base URL for the mock API |
| `api_docs` | object | Full endpoint documentation |
| `step_number` | integer | Current step (1-indexed) |
| `max_steps` | integer | Maximum steps for this task |
| `previous_responses` | array | All previous API call results with status codes |
| `current_errors` | array | Error messages from the last call |

---

## 🎁 Reward Function

**Reward is computed entirely from HTTP status codes in the mock API call log.**
No LLM output is parsed. No text matching. Pure task performance.

### Task 1 Reward Breakdown
| Component | Reward | Condition |
|-----------|--------|-----------|
| Correct endpoint called | +0.40 | Path matches ground truth |
| HTTP 200 returned | +0.30 | Auth correct + request valid |
| Correct params | +0.30 | Required query params present |

### Task 2 Reward Breakdown
| Component | Reward | Condition |
|-----------|--------|-----------|
| Data fetch step | +0.40 | GET with correct filters → 200 |
| Each reminder sent | +0.30 | POST remind with correct channel → 200 |

### Task 3 Reward Breakdown
| Component | Reward | Condition |
|-----------|--------|-----------|
| Auth bug fixed | +0.30 | Got past 401 error |
| Method bug fixed | +0.30 | Got past 405 error |
| Full success | +0.40 | Achieved HTTP 200 |

Reward is **dense** — partial credit is awarded for each sub-task completed,
providing meaningful signal throughout the entire episode trajectory.

---

## 🌐 API Endpoints

### OpenEnv Wrapper (port 7860 — what judges call)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/reset?task_id=task1` | POST | Start new episode |
| `/step` | POST | Execute one action |
| `/state` | GET | Current episode state |
| `/health` | GET | Health check |

### Mock Business API (port 7861 — what agents call)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /v1/customers` | GET | List customers with filters |
| `GET /v1/customers/{id}` | GET | Get customer by ID |
| `GET /v1/invoices` | GET | List invoices with filters |
| `POST /v1/invoices/{id}/remind` | POST | Send payment reminder |
| `POST /v1/payments` | POST | Create payment record |

---

## 🚀 Quick Start

### Run Locally

```bash
# Clone
git clone https://github.com/pandey019/AgentApiBench.git
cd AgentApiBench

# Install
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Terminal 1 — Mock API server
uvicorn mock_api.server:app --host 0.0.0.0 --port 7861

# Terminal 2 — OpenEnv wrapper
uvicorn server.app:app --host 0.0.0.0 --port 7860

# Terminal 3 — Test it works
curl -X POST http://localhost:7860/reset
curl -X GET  http://localhost:7860/health
```

### Run Inference

```bash
export HF_TOKEN="your-google-api-key"
export API_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/"
export MODEL_NAME="gemini-2.0-flash"

python inference.py
```

### Run with Docker

```bash
docker build -t agentapibench .

docker run -p 7860:7860 \
  -e HF_TOKEN="your-google-api-key" \
  -e API_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/" \
  -e MODEL_NAME="gemini-2.0-flash" \
  agentapibench
```

---

## 🔧 Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `HF_TOKEN` | ✅ Yes | Google or HuggingFace API key | `AIzaSy...` |
| `API_BASE_URL` | ✅ Yes | OpenAI-compatible LLM endpoint | `https://generativelanguage.googleapis.com/v1beta/openai/` |
| `MODEL_NAME` | ✅ Yes | Model identifier | `gemini-2.0-flash` |

---

## 📁 Project Structure

```
AgentApiBench/
├── inference.py                    ← Baseline inference script
├── openenv.yaml                    ← OpenEnv spec
├── Dockerfile                      ← Container definition
├── requirements.txt
├── README.md
│
├── server/
│   ├── app.py                      ← OpenEnv FastAPI wrapper
│   ├── agentapi_environment.py     ← Environment logic
│   └── graders/
│       ├── task1_grader.py         ← Deterministic HTTP-based grader
│       ├── task2_grader.py
│       └── task3_grader.py
│
├── scenarios/
│   ├── task1/                      ← Easy task scenario JSONs
│   ├── task2/                      ← Medium task scenario JSONs
│   └── task3/                      ← Hard task scenario JSONs
│
└── mock_api/
    ├── server.py                   ← Mock business REST API
    ├── call_logger.py              ← Records all API calls for grading
    └── data/
        ├── customers.json
        ├── invoices.json
        └── payments.json
```

---

## 🔬 Why Deterministic Grading Matters

Most benchmarks grade LLM output using another LLM — introducing bias,
inconsistency, and the possibility of gaming the evaluator.

AgentAPIBench grades **only from HTTP responses**:

```
Agent makes a call → Mock API returns HTTP status → Grader reads status code
```

Same input always produces the same score. No randomness. No LLM-as-judge.
Fully reproducible across any hardware, any time.

---

## 📊 Scoring Logic (Simplified)

```python
# Task 1: Did the agent hit the right endpoint and get 200?
score = 0.0
if correct_endpoint_in_call_log:      score += 0.40
if http_200_in_call_log:              score += 0.30
if correct_params_in_call_log:        score += 0.30

# Task 3: Which errors did the agent fix?
if agent_got_past_401:                score += 0.30
if agent_got_past_405:                score += 0.30
if agent_achieved_200:                score += 0.40
```

No text parsing. No keyword matching. Just HTTP status codes.

---

## 🤝 Contributing

Contributions welcome! Open areas:

- **New scenarios** — More task variations for each difficulty level
- **New domains** — Healthcare APIs, financial APIs, logistics APIs
- **New tasks** — Task 4 (pagination), Task 5 (OAuth flow)
- **New models** — Run against GPT-4o, Claude 3.5, Llama 3.1 and submit scores

See [CONTRIBUTING.md](CONTRIBUTING.md) or open an issue to discuss.

---

## 📜 License

Apache 2.0 — free to use, modify, and build upon commercially.

---

## 🔗 Links

- **HuggingFace Space:** https://huggingface.co/spaces/balrampandey/AgentApiBench
- **GitHub:** https://github.com/pandey019/AgentApiBench
- **OpenEnv:** https://github.com/meta-pytorch/OpenEnv

---

## 📖 Citation

```bibtex
@misc{agentapibench2026,
  title  = {AgentAPIBench: Evaluating LLM Tool Use on Real-World API Integration Tasks},
  author = {Balram Pandey},
  year   = {2026},
  url    = {https://huggingface.co/spaces/balrampandey/AgentApiBench},
  note   = {OpenEnv-compatible RL benchmark for API integration evaluation}
}
```

---

<div align="center">

Built with ❤️ for the **Meta × PyTorch OpenEnv Hackathon 2026**

**[🔌 Try it on HuggingFace](https://huggingface.co/spaces/balrampandey/AgentApiBench)** · **[⭐ Star on GitHub](https://github.com/pandey019/AgentApiBench)**

</div>