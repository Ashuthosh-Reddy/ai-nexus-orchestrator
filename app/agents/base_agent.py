from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class AgentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentResult:
    agent_name: str
    status: AgentStatus
    output: str = ""
    artifacts: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    started_at: str = ""
    completed_at: str = ""
    duration_seconds: float = 0.0


class BaseAgent(ABC):
    """Base class for all AI tool agents in the pipeline."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    async def execute(self, input_data: dict[str, Any]) -> AgentResult:
        start = datetime.now()
        result = AgentResult(
            agent_name=self.name,
            status=AgentStatus.RUNNING,
            started_at=start.isoformat(),
        )
        try:
            output, artifacts = await self.run(input_data)
            result.status = AgentStatus.COMPLETED
            result.output = output
            result.artifacts = artifacts
        except Exception as e:
            import traceback
            result.status = AgentStatus.FAILED
            result.error = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
        finally:
            end = datetime.now()
            result.completed_at = end.isoformat()
            result.duration_seconds = round((end - start).total_seconds(), 2)
        return result

    @abstractmethod
    async def run(self, input_data: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """Run the agent logic. Returns (summary_text, artifacts_dict)."""
        ...
