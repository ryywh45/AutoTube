from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class StageStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class StageResult(BaseModel):
    """Result of running a pipeline stage."""

    status: StageStatus
    output: Any = None
    error: str | None = None


class Stage(ABC):
    """Abstract base class for a pipeline stage.

    Each stage receives input from the previous stage and produces output
    for the next stage.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of this stage."""

    @abstractmethod
    async def run(self, input_data: Any) -> StageResult:
        """Execute this stage.

        Args:
            input_data: Output from the previous stage (or initial input for the first stage).

        Returns:
            StageResult with status and output data.
        """
