from datetime import datetime

from pydantic import BaseModel

from app.models.submission import Language, SubmissionStatus, Verdict


class SubmissionCreate(BaseModel):
    problem_id: int
    language: Language
    source_code: str


class SubmissionOut(BaseModel):
    id: int
    user_id: int
    problem_id: int
    language: Language
    status: SubmissionStatus
    verdict: Verdict | None
    execution_time_ms: int | None
    stdout: str | None
    stderr: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
