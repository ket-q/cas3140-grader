from pydantic import BaseModel, ConfigDict, StrictFloat, StrictInt, StrictStr


class StudentModel(BaseModel):
    """Base class for strict models exposed to students."""

    model_config = ConfigDict(extra="forbid")


class ProcessResponse(StudentModel):
    """Result of a submitted solution."""

    score: StrictFloat
    msg: StrictStr
    best_score: StrictFloat | None = None


class BestScoreResponse(StudentModel):
    """Best recorded score for a lab problem."""

    lab: StrictInt
    problem: StrictInt
    best_score: StrictFloat | None


__all__ = ["BestScoreResponse", "ProcessResponse", "StudentModel"]
