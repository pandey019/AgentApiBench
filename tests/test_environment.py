import pytest
import asyncio
from env.environment import AgentAPIEnv
from env.models import ApiCallAction, HttpMethod
import uvicorn
import multiprocessing
import time
from mock_api.server import app as mock_app


def run_mock_api():
    uvicorn.run(mock_app, host="127.0.0.1", port=7861)


@pytest.fixture(scope="module")
def mock_api_server():
    p = multiprocessing.Process(target=run_mock_api)
    p.start()
    time.sleep(2)  # Wait for server to start
    yield
    p.terminate()
    p.join()


@pytest.mark.asyncio
async def test_full_episode_flow_task1(mock_api_server):
    env = AgentAPIEnv("task1")
    reset_result = await env.reset()
    assert reset_result.observation.task_id == "task1"

    action = ApiCallAction(
        method=HttpMethod.GET,
        url="http://127.0.0.1:7861/v1/customers/cust_4821",
        headers={"Authorization": "Bearer sk-bench-4921x"},
        params={"include": "subscription"},
    )

    step_result = await env.step(action)

    assert step_result.reward > 0.0

    state = env.state()
    assert state.step == 1

    await env.close()
