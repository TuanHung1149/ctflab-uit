from datetime import datetime

from pydantic import BaseModel


class SubmissionCreate(BaseModel):
    challenge_id: int
    flag: str


class SubmissionResponse(BaseModel):
    id: int
    challenge_id: int
    is_correct: bool
    submitted_at: datetime

    model_config = {"from_attributes": True}


class ScoreboardEntry(BaseModel):
    username: str
    total_score: int
    solved_count: int
