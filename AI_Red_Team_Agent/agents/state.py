"""
Agent State Management - The memory and context of the autonomous Red Team Agent.
This is the backbone of the LangGraph state machine.
"""
from typing import TypedDict, List, Optional
from pydantic import BaseModel


class AttackAttempt(BaseModel):
    """Record of a single attack attempt."""
    iteration: int
    strategy: str
    payload: str
    target_response: str
    is_vulnerable: bool
    vulnerability_score: int
    analysis_details: str
    reasoning: str  # Why the planner chose this strategy


class AgentState(TypedDict):
    """The state object passed between all nodes in the LangGraph."""
    # Mission parameters
    objective: str
    target_url: str
    target_model: str

    # Agent reasoning
    current_strategy: str
    current_payload: str
    planner_reasoning: str

    # Target interaction
    target_response: str
    working_schema_id: str

    # Analysis
    is_vulnerable: bool
    vulnerability_score: int
    analysis_details: str
    objective_achieved: bool

    # Memory
    history: List[dict]
    strategies_tried: List[str]

    # Control flow
    iteration: int
    max_iterations: int
    status: str  # "running", "success", "max_iterations_reached", "error"

    # Full agent log (for the UI)
    agent_log: List[dict]
