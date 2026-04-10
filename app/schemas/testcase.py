from datetime import datetime

from pydantic import BaseModel


class TestCaseCreate(BaseModel):
    input_data: str
    expected_output: str
    is_sample: bool = False


class TestCaseOut(BaseModel):
    id: int
    problem_id: int
    input_data: str
    expected_output: str
    is_sample: bool
    created_at: datetime

    model_config = {"from_attributes": True}
