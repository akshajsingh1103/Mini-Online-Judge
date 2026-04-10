from datetime import datetime

from pydantic import BaseModel

from app.models.problem import Difficulty
from app.schemas.testcase import TestCaseOut


class ProblemCreate(BaseModel):
    title: str
    statement: str
    difficulty: Difficulty
    time_limit_ms: int = 2000
    memory_limit_mb: int = 256


class ProblemOut(BaseModel):
    id: int
    title: str
    statement: str
    difficulty: Difficulty
    time_limit_ms: int
    memory_limit_mb: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ProblemDetail(ProblemOut):
    """ProblemOut with sample testcases (is_sample=True only)."""

    sample_testcases: list[TestCaseOut] = []
