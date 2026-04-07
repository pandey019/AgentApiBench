import asyncio
import os
import sys

# Ensure root directory is in sys.path BEFORE imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI
from openenv.core.env_server import create_app
from models import APICallAction, APIBenchObservation
from server.agentapi_environment import AgentAPIBenchEnvironment
import uvicorn

app = create_app(AgentAPIBenchEnvironment, APICallAction, APIBenchObservation)


def main():
    port = int(os.getenv("PORT", 7860))
    uvicorn.run(
        "server.app:app", host="0.0.0.0", port=port, log_level="info", reload=False
    )


if __name__ == "__main__":
    main()
