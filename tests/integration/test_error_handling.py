import json
from types import SimpleNamespace

import pytest
from googleapiclient.errors import HttpError

import server


def http_error(status, reason=None):
    body = {"error": {"errors": [{"reason": reason}] if reason else []}}
    return HttpError(
        SimpleNamespace(status=status, reason="test"), json.dumps(body).encode()
    )


@pytest.mark.integration
@pytest.mark.parametrize(
    "status,reason,code,retryable",
    [
        (400, None, "GMAIL_BAD_REQUEST", False),
        (401, None, "AUTHENTICATION_ERROR", False),
        (403, "rateLimitExceeded", "RATE_LIMIT_EXCEEDED", True),
        (403, "forbidden", "PERMISSION_DENIED", False),
        (404, None, "RESOURCE_NOT_FOUND", False),
        (429, None, "RATE_LIMIT_EXCEEDED", True),
        (500, None, "GMAIL_API_ERROR", True),
    ],
)
def test_http_error_classification(status, reason, code, retryable):
    result = server._classify_http_error(http_error(status, reason))
    assert result["code"] == code
    assert result["retryable"] is retryable


@pytest.mark.integration
def test_internal_error_is_sanitized():
    result = server._error_result(RuntimeError("private token 123"), "search_emails")
    assert result["ok"] is False
    assert result["error"]["code"] == "INTERNAL_ERROR"
    assert "private token" not in result["error"]["message"]


@pytest.mark.integration
def test_network_error_is_retryable():
    result = server._error_result(TimeoutError("timeout"), "search_emails")
    assert result["error"]["code"] == "NETWORK_ERROR"
    assert result["error"]["retryable"] is True
