
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ActionEvent(BaseModel):
    """A structured record of an AI agent's attempted action."""

    model_config = ConfigDict(extra="forbid")

    step: int = Field(ge=1)
    task_id: str
    objective_id: str = "default-objective"
    agent_id: str
    parent_agent_id: str | None = None

    tool: str
    action: str
    resource: str
    canonical_resource: str

    status: Literal["requested", "allowed", "denied", "blocked"]
    reason: str | None = None
