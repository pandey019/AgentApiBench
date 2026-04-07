# How to Run and Test AgentAPIBench Locally

Your entire environment is now perfectly configured, utilizing the official `openenv-core` base classes, deterministic graders, and proper background process daemonization for macOS. 

You can test and run the benchmark in two different ways:

## 1. The Automated End-to-End Script (Easiest)

I have built a robust testing script `run_test.sh` that handles everything for you. It automatically:
1. Cleans up any zombie server processes from previous runs.
2. Activates your Python virtual environment.
3. Starts the **Mock API Server** on port `7861` in the background.
4. Starts the **OpenEnv Server** on port `7860` in the background.
5. Verifies the servers are healthy.
6. Executes the LLM agent (`inference.py`) to run through `task1`, `task2`, and `task3`.
7. Gracefully shuts down both servers when finished.

To run it, simply open your terminal and execute:

```bash
# 1. Ensure your Gemini API Key is set in your terminal (or loaded from .env)
export GEMINI_API_KEY="your-api-key-here"

# 2. Run the script
./run_test.sh
```

You will see the `[START]`, `[STEP]`, and `[END]` logs stream to your console as the LLM navigates the tasks!

---

## 2. Manual Execution (For Debugging or cURL Testing)

If you want to manually interact with the environment (e.g., using `curl` to act as the agent yourself to test the graders), you can start the servers manually in your terminal.

**Terminal Window 1 (Start the Servers):**
```bash
# Activate your environment
source venv/bin/activate
export PYTHONPATH="$(pwd):$PYTHONPATH"

# Start the Mock API
python -m uvicorn mock_api.server:app --host 127.0.0.1 --port 7861 &

# Start the OpenEnv Server
python -m uvicorn server.app:app --host 127.0.0.1 --port 7860 &
```

**Terminal Window 2 (Play the Game via cURL):**
```bash
# 1. Reset the environment and get the first task observation
curl -X POST "http://127.0.0.1:7860/reset" -H "Content-Type: application/json" -d '{"task_id": "task1"}'

# 2. Submit an action (acting as the LLM)
curl -X POST "http://127.0.0.1:7860/step" -H "Content-Type: application/json" -d '{
  "action": {
    "method": "GET",
    "url": "http://127.0.0.1:7861/v1/customers",
    "headers": {"Authorization": "Bearer sk-bench-4921x"},
    "params": {"status": "active", "limit": 5},
    "body": null,
    "reasoning": "I am manually testing the endpoint."
  }
}'

# 3. Check the internal state of the environment
curl "http://127.0.0.1:7860/state"
```

## 3. How to Build & Run in Docker (Production/HF Spaces)

This is how the application will run when deployed to HuggingFace.

```bash
# 1. Build the image
docker build -t agentapibench .

# 2. Run the container (exposing the necessary ports)
docker run -p 7860:7860 -p 7861:7861 agentapibench

# 3. In a separate terminal, run the inference script against it
source venv/bin/activate
export GEMINI_API_KEY="your-api-key"
python inference.py
```