"""Public response models returned by the CAS3140 student interface.

This module is deliberately independent of :mod:`cas3140_protocol`: it is
part of the student-facing API and can be published without
also publishing the request, grading, and internal-service models.
"""

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
