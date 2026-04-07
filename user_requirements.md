# User Requirements for AgentAPIBench

To fully run and test the AgentAPIBench locally and deploy it, you will need to provide the following:

1. **OpenAI API Key (`OPENAI_API_KEY` or `API_KEY`)**: Required to run the baseline agent in `inference.py`. The baseline uses `gpt-4o-mini` by default.
2. **HuggingFace Token (`HF_TOKEN`)**: If you are deploying to HuggingFace Spaces or pulling restricted models.
3. **HuggingFace Space**: To complete the Phase 1 Gate, you will need to create a HuggingFace Space and push this code there.
4. **Docker**: Ensure Docker is installed and running on your machine to build and run the evaluation environment container.
5. **Python 3.11+**: For running the tests and the evaluation locally without Docker.

### Environment Variables for local execution
When running `inference.py`, you can configure it via:
- `API_KEY` or `OPENAI_API_KEY` or `HF_TOKEN`
- `API_BASE_URL` (default: `https://api.openai.com/v1`)
- `MODEL_NAME` (default: `gpt-4o-mini`)
- `ENV_URL` (default: `http://localhost:7860`)
