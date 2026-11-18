"""Student submission interface for the CAS3140 server."""

from ._version import __version__
from .accounts import delete_account, save_account, saved_account
from .students import best_score, best_scores, check_versions, submit, verify_variable
from .models import BestScoreResponse, BestScoresResponse, ProblemBestScore, ProcessResponse, VersionCheckResponse

__all__ = [
    "__version__",
    "BestScoreResponse", 
    "BestScoresResponse", 
    "ProblemBestScore", 
    "ProcessResponse", 
    "VersionCheckResponse",
    "best_score", 
    "best_scores", 
    "check_versions",
    "delete_account",
    "save_account",
    "saved_account",
    "submit",
    "verify_variable"
]
