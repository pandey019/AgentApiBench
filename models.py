# models.py — root level
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from openenv.core.env_server import Action, Observation, State


class APICallAction(Action):
    """
    The agent's action: a structured API call specification.
    Agent produces this as JSON — environment executes it against the mock API.
    Reward comes from what the mock API actually returns, NOT from the text content.
    """

    model_config = ConfigDict(extra="ignore")

    method: str = "GET"  # GET | POST | PUT | PATCH | DELETE
    url: str = ""  # Full URL including base URL
    headers: Dict[str, str] = Field(default_factory=dict)
    params: Dict[str, Any] = Field(default_factory=dict)
    body: Optional[Dict[str, Any]] = None
    reasoning: Optional[str] = None  # Logged but NOT used in scoring


class APIBenchObservation(Observation):
    """
    What the agent sees after each step.
    Contains task context, API docs, and results from previous calls.
    """

    model_config = ConfigDict(extra="ignore")

    task_id: str = ""
    task_description: str = ""
    api_base_url: str = ""
    api_docs: Dict[str, Any] = Field(default_factory=dict)
    step_number: int = 0
    max_steps: int = 0
    previous_responses: List[Dict[str, Any]] = Field(default_factory=list)
    current_errors: List[str] = Field(default_factory=list)


class APIBenchState(State):
    """
    Full internal episode state — returned by state() endpoint.
    Inheriting directly from State (which is a Pydantic BaseModel).
    """

    model_config = ConfigDict(extra="ignore")

    task_id: str = ""
    task_name: str = ""
    scenario_id: str = ""
    step: int = 0
    max_steps: int = 0
    call_log: List[Dict] = Field(default_factory=list)
    cumulative_reward: float = 0.0
    bugs_fixed: List[str] = Field(default_factory=list)  # Task 3 only
    workflow_progress: float = 0.0  # Task 2 only
    done: bool = False
