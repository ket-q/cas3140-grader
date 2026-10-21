from __future__ import annotations

import base64
import io
import os
import re
import ssl
import sys
import pickle
from importlib.metadata import PackageNotFoundError, version
from typing import Any
from beartype.door import die_if_unbearable
from beartype.roar import BeartypeDoorHintViolation

import httpx

from .accounts import resolve_token
from .models import BestScoreResponse, BestScoresResponse, ProcessResponse, VersionCheckResponse

DEFAULT_SUBMISSION_URL = os.environ.get("CAS3140_SUBMISSION_URL", "https://165.132.172.120")
DEFAULT_CERTIFICATE = """-----BEGIN CERTIFICATE-----
MIIBozCCAUmgAwIBAgIQVDXf+u/fHwvisTvgdM/mQzAKBggqhkjOPQQDAjAwMS4w
LAYDVQQDEyVDYWRkeSBMb2NhbCBBdXRob3JpdHkgLSAyMDI2IEVDQyBSb290MB4X
DTI2MTAwNzAzMjE0N1oXDTM2MDgxNTAzMjE0N1owMDEuMCwGA1UEAxMlQ2FkZHkg
TG9jYWwgQXV0aG9yaXR5IC0gMjAyNiBFQ0MgUm9vdDBZMBMGByqGSM49AgEGCCqG
SM49AwEHA0IABGxpaAKPvaQB1ioNWOALtPR8/WpNKF9hJenjte1ju0W03VE6SXrZ
/xx4Z93BcQO8vVPHaMKeTtx6y57d5jcWaQOjRTBDMA4GA1UdDwEB/wQEAwIBBjAS
BgNVHRMBAf8ECDAGAQH/AgEBMB0GA1UdDgQWBBR6FntwTeFk1uLdYCd5fcq+oMtz
njAKBggqhkjOPQQDAgNIADBFAiB0VWQHbtRwflDSqaln0rGKmfr9i5mOArqlQLUY
40rDUwIhAIMfugi58BraZRV4FU0GIURd/XzuiJSCAO4d8370DbPf
-----END CERTIFICATE-----
"""

_SERIALIZED_TYPE = "_cas3140_serialized_type"
_SERIALIZED_PAYLOAD = "payload"
_PICKLE_TYPE = "pickle_value"
_FUNCTION_TYPE = "dill_function"
_CIRCUIT_TYPE = "qiskit_qpy"
_LAB_NAME_RE = re.compile(r"lab(\d{2})")


def _submission_versions() -> dict[str, str | None]:
    """Collect installed versions without importing the packages."""
    versions: dict[str, str | None] = {"python": ".".join(map(str, sys.version_info[:3]))}
    for package in ("qiskit", "dill"):
        try:
            versions[package] = version(package)
        except PackageNotFoundError:
            raise ValueError(
                f"The '{package}' package is not installed. "
                "Please follow the setup instructions to install the required packages."
            ) from None
    return versions


def _server_error_message(response: httpx.Response) -> str:
    """Read the public error message supplied by the request server."""
    try:
        return response.json()["error"]["message"]
    except (KeyError, TypeError, ValueError):
        return response.text


def _encoded_value(kind: str, payload: bytes) -> dict[str, str]:
    return {
        _SERIALIZED_TYPE: kind,
        _SERIALIZED_PAYLOAD: base64.b64encode(payload).decode("ascii"),
    }


def _pack_submission_value(value: Any) -> Any:
    """Encode values that JSON cannot represent for the isolated grader."""
    try:
        import numpy as np
    except ImportError:
        is_numpy = False
    else:
        is_numpy = isinstance(value, (np.generic, np.ndarray, np.dtype)) or (
            type(value).__module__.split(".", 1)[0] == "numpy"
        )
    if isinstance(value, complex) or is_numpy:
        try:
            return _encoded_value(_PICKLE_TYPE, pickle.dumps(value, protocol=5))
        except Exception as error:
            raise ValueError(
                f"Submission value of type {type(value).__name__} cannot be serialized with pickle."
            ) from error
    if isinstance(value, (list, tuple)):
        return [_pack_submission_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _pack_submission_value(item) for key, item in value.items()}
    if callable(value):
        try:
            import dill
        except ImportError as error:
            raise RuntimeError("Function submissions require the 'dill' package.") from error
        return _encoded_value(_FUNCTION_TYPE, dill.dumps(value))
    try:
        from qiskit import QuantumCircuit
    except ImportError:
        return value
    if isinstance(value, QuantumCircuit):
        from qiskit import qpy

        buffer = io.BytesIO()
        qpy.dump(value, buffer)
        return _encoded_value(_CIRCUIT_TYPE, buffer.getvalue())
    return value


def submit(lab: str, slug: str, value: Any, *, token: str | None = None) -> ProcessResponse | None:
    """Submit to the configured request server, print scores, and return its response.
    
    Use ``token`` saved by ``save_account()``.
    """
    return _submit(
        lab,
        slug,
        value,
        token=resolve_token(token),
        url=DEFAULT_SUBMISSION_URL,
    )


def _submit(
    lab: str,
    slug: str,
    value: Any,
    *,
    token: str,
    url: str,
    certificate: str = DEFAULT_CERTIFICATE,
) -> ProcessResponse | None:
    """Submit to an explicitly supplied URL, print its result, and return it."""
    if not token:
        raise ValueError("A submission token is required.")
    match = _LAB_NAME_RE.fullmatch(lab)
    if match is None:
        raise ValueError("lab must have the format 'labXX', where XX is a two-digit integer.")
    lab_number = int(match.group(1))
    versions = _submission_versions()
    packed_value = _pack_submission_value(value)
    tls_context = ssl.create_default_context(cadata=certificate)
    # Grading may legitimately take longer than HTTPX's default 5-second timeout.
    with httpx.Client(verify=tls_context, timeout=None) as session:
        response = session.post(
            f"{url.rstrip('/')}/submit",
            json={"token": token, "lab": lab_number, "slug": slug,
                  "value": packed_value, "versions": versions},
        )
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError:
        if response.status_code == 413:
            print("Submission rejected: the request is too large (HTTP 413). Reduce the submission size and try again.")
            return None
        print(_server_error_message(response))
        return None
    result = ProcessResponse.model_validate(response.json())
    #  If version mismatch found, it is reported here
    print(result.msg)
    print(f"Score: {result.score} / (Best score: {result.best_score})")
    return result


def check_versions(*, token: str | None = None) -> VersionCheckResponse | None:
    """Check this environment against the grading environment."""
    return _check_versions(token=resolve_token(token), url=DEFAULT_SUBMISSION_URL)


def _check_versions(
    *, token: str, url: str, certificate: str = DEFAULT_CERTIFICATE,
) -> VersionCheckResponse | None:
    if not token:
        raise ValueError("A submission token is required.")
    versions = _submission_versions()
    print(f"Python version: {versions['python']}")
    print(f"Qiskit version: {versions['qiskit']}")
    tls_context = ssl.create_default_context(cadata=certificate)
    with httpx.Client(verify=tls_context, timeout=None) as session:
        response = session.post(
            f"{url.rstrip('/')}/check-versions",
            json={"token": token, "versions": versions},
        )
    if response.status_code == 401:
        print(_server_error_message(response))
        return None
    # Service failures are HTTP errors, not version mismatches
    response.raise_for_status()
    result = VersionCheckResponse.model_validate(response.json())
    if not result.compatible:
        raise ValueError(result.msg)
    print("Version check passed. Your Python and Qiskit versions are compatible with the grading environment.")
    return result


def best_score(lab: str, slug: str, *, token: str | None = None) -> BestScoreResponse | None:
    """Print and return the token owner's best score for one lab problem."""
    return _best_score(
        lab,
        slug,
        token=resolve_token(token),
        url=DEFAULT_SUBMISSION_URL,
    )


def _best_score(
    lab: str,
    slug: str,
    *,
    token: str,
    url: str,
    certificate: str = DEFAULT_CERTIFICATE,
) -> BestScoreResponse | None:
    """Look up a best score at an explicit URL; used by local manual tests."""
    if not token:
        raise ValueError("A submission token is required.")
    match = _LAB_NAME_RE.fullmatch(lab)
    if match is None:
        raise ValueError("lab must have the format 'labXX', where XX is a two-digit integer.")
    lab_number = int(match.group(1))
    tls_context = ssl.create_default_context(cadata=certificate)
    with httpx.Client(verify=tls_context, timeout=None) as session:
        response = session.post(
            f"{url.rstrip('/')}/best-score",
            json={"token": token, "lab": lab_number, "slug": slug},
        )
    if response.is_error:
        print(_server_error_message(response))
        return None
    result = BestScoreResponse.model_validate(response.json())
    print(f"Best score: {result.best_score}")
    return result


def best_scores(lab: str, *, token: str | None = None) -> BestScoresResponse | None:
    """Print and return the token owner's best score for every problem of one lab."""
    return _best_scores(
        lab, 
        token=resolve_token(token), 
        url=DEFAULT_SUBMISSION_URL
    )


def _best_scores(
    lab: str,
    *,
    token: str,
    url: str,
    certificate: str = DEFAULT_CERTIFICATE,
) -> BestScoresResponse | None:
    """Look up all best scores of a lab at an explicit URL."""
    if not token:
        raise ValueError("A submission token is required.")
    match = _LAB_NAME_RE.fullmatch(lab)
    if match is None:
        raise ValueError("lab must have the format 'labXX', where XX is a two-digit integer.")
    lab_number = int(match.group(1))
    tls_context = ssl.create_default_context(cadata=certificate)
    with httpx.Client(verify=tls_context, timeout=None) as session:
        response = session.post(f"{url.rstrip('/')}/best-scores", json={"token": token, "lab": lab_number})
    if response.is_error:
        print(_server_error_message(response))
        return None
    result = BestScoresResponse.model_validate(response.json())
    print(f"Lab {result.lab} best scores")
    for item in result.scores:
        print(f"  {item.slug}: {'not submitted' if item.best_score is None else item.best_score}")
    print(f"  Total: {result.total}")
    return result

def verify_variable(variable_obj, target_type_obj):
    """Polymorphic helper that runs checks using the passed type object."""
    try:
        die_if_unbearable(variable_obj, target_type_obj)
        print("✅ Type check passed.")
    except BeartypeDoorHintViolation as e:
        # Re-raise as a clean, standardized TypeError for the student
        raise TypeError(f"Variable failed structural type contract. Details: {e}") from None