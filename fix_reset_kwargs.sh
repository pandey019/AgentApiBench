#!/bin/bash

export API_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/"
export MODEL_NAME="gemini-2.5-flash"
export ENV_URL="http://127.0.0.1:7860"

# Fix: Reset passing task IDs properly into kwargs so the framework actually switches to task 2 & 3 correctly.
# openenv-core strictly requires `"task_id": ...` mapped natively in `json={"task_id": task_id}`
