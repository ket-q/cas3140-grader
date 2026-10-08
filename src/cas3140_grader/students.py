from __future__ import annotations

import base64
import io
import os
import ssl
from typing import Any

import httpx

from .models import BestScoreResponse, ProcessResponse

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
_FUNCTION_TYPE = "dill_function"
_CIRCUIT_TYPE = "qiskit_qpy"


def _encoded_value(kind: str, payload: bytes) -> dict[str, str]:
    return {
        _SERIALIZED_TYPE: kind,
        _SERIALIZED_PAYLOAD: base64.b64encode(payload).decode("ascii"),
    }


def _pack_submission_value(value: Any) -> Any:
    """Encode values that JSON cannot represent for the isolated grader."""
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


def submit(lab: int, problem: int, value: Any, *, token: str) -> ProcessResponse | None:
    """Submit to the configured request server, print scores, and return its response."""
    return _submit(
        lab,
        problem,
        value,
        token=token,
        url=DEFAULT_SUBMISSION_URL,
    )


def _submit(
    lab: int,
    problem: int,
    value: Any,
    *,
    token: str,
    url: str,
    certificate: str = DEFAULT_CERTIFICATE,
) -> ProcessResponse | None:
    """Submit to an explicitly supplied URL, print its result, and return it."""
    if not token:
        raise ValueError("A submission token is required.")
    packed_value = _pack_submission_value(value)
    tls_context = ssl.create_default_context(cadata=certificate)
    # Grading may legitimately take longer than HTTPX's default 5-second timeout.
    with httpx.Client(verify=tls_context, timeout=None) as session:
        response = session.post(f"{url.rstrip('/')}/submit", json={"token": token, "lab": lab, "problem": problem, "value": packed_value})
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError:
        if response.status_code == 413:
            print("Submission rejected: the request is too large (HTTP 413). Reduce the submission size and try again.")
            return None
        try:
            message = response.json()["error"]["message"]
        except (KeyError, TypeError, ValueError):
            message = response.text
        print(message)
        return None
    result = ProcessResponse.model_validate(response.json())
    print(f"Score: {result.score} / (Best score: {result.best_score})")
    return result


def best_score(lab: int, problem: int, *, token: str) -> BestScoreResponse | None:
    """Print and return the token owner's best score for one lab problem."""
    return _best_score(
        lab,
        problem,
        token=token,
        url=DEFAULT_SUBMISSION_URL,
    )


def _best_score(
    lab: int,
    problem: int,
    *,
    token: str,
    url: str,
    certificate: str = DEFAULT_CERTIFICATE,
) -> BestScoreResponse | None:
    """Look up a best score at an explicit URL; used by local manual tests."""
    if not token:
        raise ValueError("A submission token is required.")
    tls_context = ssl.create_default_context(cadata=certificate)
    with httpx.Client(verify=tls_context, timeout=None) as session:
        response = session.post(
            f"{url.rstrip('/')}/best-score",
            json={"token": token, "lab": lab, "problem": problem},
        )
    if response.is_error:
        try:
            message = response.json()["error"]["message"]
        except (KeyError, TypeError, ValueError):
            message = response.text
        print(message)
        return None
    result = BestScoreResponse.model_validate(response.json())
    print(f"Best score: {result.best_score}")
    return result
