"""Student submission interface for the CAS3140 example server."""

from .students import best_score, submit
from .models import BestScoreResponse, ProcessResponse

__all__ = ["BestScoreResponse", "ProcessResponse", "best_score", "submit"]
