
from unittest.mock import patch
import pytest

pytestmark = pytest.mark.integration
import server


@patch("server.get_service")
@patch("server.search_service.search_emails")
@patch("server.gmail_api.get_message")
def test_search_emails_success(
    mock_get_message,
    mock_search,
    mock_get_service,
    sample_message,
):
    mock_get_service.return_value = object()

    mock_search.return_value = {
        "messages": [{"id": "message_123"}],
        "query": "from:sender@example.com",
        "timezone": "UTC",
        "result_size_estimate": 1,
        "next_page_token": None,
    }

    mock_get_message.return_value = sample_message

    result = server.search_emails(
        sender="sender@example.com",
    )

    assert result["ok"] is True
    assert result["returned_count"] == 1
    assert result["emails"][0]["message_id"] == "message_123"
    assert result["emails"][0]["subject"] == "Project Update"

    mock_search.assert_called_once()


@patch("server.get_service")
@patch("server.gmail_api.get_message")
def test_get_email_details_success(
    mock_get_message,
    mock_get_service,
    sample_message,
):
    mock_get_service.return_value = object()
    mock_get_message.return_value = sample_message

    result = server.get_email_details("message_123")

    assert result["ok"] is True
    assert result["email"]["message_id"] == "message_123"
    assert result["email"]["subject"] == "Project Update"


@patch("server.get_service")
@patch("server.gmail_api.get_message")
@patch("server.gmail_api.get_thread")
def test_get_email_conversation_success(
    mock_get_thread,
    mock_get_message,
    mock_get_service,
    sample_thread,
):

    mock_get_service.return_value = object()

    # The first Gmail request returns lightweight thread metadata.
    mock_get_thread.return_value = {
        "id": "thread_123",
        "messages": [
            {
                "id": "message_123",
                "threadId": "thread_123",
            },
            {
                "id": "message_456",
                "threadId": "thread_123",
            },
        ],
    }

    # The next requests retrieve selected full messages individually.
    mock_get_message.side_effect = sample_thread["messages"]

    result = server.get_email_conversation("thread_123")

    assert result["ok"] is True

    conversation = result["conversation"]

    assert conversation["thread_id"] == "thread_123"
    assert conversation["message_count"] == 2
    assert conversation["returned_count"] == 2
    assert conversation["truncated"] is False
    assert len(conversation["messages"]) == 2

    mock_get_thread.assert_called_once_with(
        mock_get_service.return_value,
        "thread_123",
        format="minimal",
    )

    assert mock_get_message.call_count == 2


@patch("server.get_service")
@patch("server.attachment_service.download_attachment")
@patch("server.gmail_api.get_message")
def test_get_attachment_success(
    mock_get_message,
    mock_download,
    mock_get_service,
):
    mock_get_service.return_value = object()

    mock_get_message.return_value = {
        "payload": {
            "mimeType": "multipart/mixed",
            "parts": [
                {
                    "filename": "report.pdf",
                    "mimeType": "application/pdf",
                    "partId": "1",
                    "body": {
                        "attachmentId": "att_123",
                        "size": 100,
                    },
                }
            ],
        }
    }

    mock_download.return_value = {
        "filename": "report.pdf",
        "path": "downloads/report.pdf",
    }

    result = server.get_attachment(
        "message_123",
        "att_123",
    )

    assert result["ok"] is True
    assert result["attachment"]["filename"] == "report.pdf"

    mock_download.assert_called_once()


def test_get_email_details_invalid_id():
    result = server.get_email_details("")

    assert result["ok"] is False
    assert result["error"]["code"] == "VALIDATION_ERROR"


@patch("server.get_service")
@patch("server.gmail_api.get_message")
def test_get_email_details_service_failure(
    mock_get_message,
    mock_get_service,
):
    mock_get_service.return_value = object()
    mock_get_message.side_effect = RuntimeError("Mock failure")

    result = server.get_email_details("message_123")

    assert result["ok"] is False
    assert result["error"]["code"] == "INTERNAL_ERROR"


@patch("server.get_service")
@patch("server.gmail_api.get_message")
def test_attachment_not_belonging_to_email(
    mock_get_message,
    mock_get_service,
):
    mock_get_service.return_value = object()

    mock_get_message.return_value = {
        "payload": {
            "mimeType": "multipart/mixed",
            "parts": [
                {
                    "filename": "report.pdf",
                    "mimeType": "application/pdf",
                    "body": {
                        "attachmentId": "different_id",
                        "size": 100,
                    },
                }
            ],
        }
    }

    result = server.get_attachment(
        "message_123",
        "att_123",
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "VALIDATION_ERROR"

@patch("server.get_service")
@patch("server.gmail_api.get_message")
@patch("server.gmail_api.get_thread")
def test_get_email_conversation_limits_full_message_requests(
    mock_get_thread,
    mock_get_message,
    mock_get_service,
    sample_message,
):

    mock_get_service.return_value = object()

    mock_get_thread.return_value = {
        "id": "thread_large",
        "messages": [
            {
                "id": f"message_{index}",
                "threadId": "thread_large",
            }
            for index in range(25)
        ],
    }

    mock_get_message.return_value = {
        **sample_message,
        "id": "message_latest",
        "threadId": "thread_large",
    }

    result = server.get_email_conversation("thread_large")

    assert result["ok"] is True

    conversation = result["conversation"]

    assert conversation["message_count"] == 25
    assert conversation["returned_count"] == 20
    assert conversation["messages_truncated"] is True
    assert conversation["truncated"] is True

    assert mock_get_message.call_count <= 20