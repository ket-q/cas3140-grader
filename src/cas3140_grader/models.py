from pydantic import BaseModel, ConfigDict, StrictBool, StrictFloat, StrictInt, StrictStr

Slug = StrictStr


class StudentModel(BaseModel):
    """Base class for strict models exposed to students."""

    model_config = ConfigDict(extra="forbid")


class ProcessResponse(StudentModel):
    """Result of a submitted solution."""

    score: StrictFloat
    msg: StrictStr
    best_score: StrictFloat | None = None
    
class VersionCheckResponse(StudentModel):
    """Compatibility of the local environment with the grader."""
    
    compatible: StrictBool
    msg: StrictStr


class BestScoreResponse(StudentModel):
    """Best recorded score for a lab problem."""

    lab: StrictInt
    slug: Slug
    best_score: StrictFloat | None
    

class ProblemBestScore(StudentModel):
    """Best recorded score for one problem (None: no attempt yet)."""

    slug: Slug
    best_score: StrictFloat | None


class BestScoresResponse(StudentModel):
    """Best recorded score for every problem of a lab."""

    lab: StrictInt
    scores: list[ProblemBestScore]
    total: StrictFloat


__all__ = ["BestScoreResponse", "BestScoresResponse", "ProblemBestScore", "ProcessResponse", "StudentModel", "VersionCheckResponse"]
