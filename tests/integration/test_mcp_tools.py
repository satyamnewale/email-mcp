
import pytest

import server


@pytest.mark.integration
def test_search_recent_emails_without_filters(
    mocker,
    mock_server_service,
    sample_message,
):
    search = mocker.patch.object(
        server.search_service,
        "search_emails",
        return_value={
            "messages": [{"id": "msg-1"}],
            "result_size_estimate": 1,
            "timezone": "UTC",
            "query": "",
            "next_page_token": None,
        },
    )

    mocker.patch.object(
        server.gmail_api,
        "get_message",
        return_value=sample_message,
    )

    result = server.search_emails()

    assert result["ok"] is True
    assert result["returned_count"] == 1
    assert result["emails"][0]["subject"] == "Update"

    assert search.call_args.kwargs["max_results"] == 10
    assert search.call_args.kwargs["page_token"] == ""


@pytest.mark.integration
def test_get_details_returns_parsed_email(
    mocker,
    mock_server_service,
    sample_message,
):
    get = mocker.patch.object(
        server.gmail_api,
        "get_message",
        return_value=sample_message,
    )

    result = server.get_email_details(" msg-1 ")

    assert result["ok"] is True
    assert result["email"]["body"] == "Hello"

    get.assert_called_once_with(
        mock_server_service.return_value,
        "msg-1",
        format="full",
    )


@pytest.mark.integration
def test_get_conversation_returns_messages(
    mocker,
    mock_server_service,
    sample_thread,
):
    get = mocker.patch.object(
        server.gmail_api,
        "get_thread",
        return_value=sample_thread,
    )

    result = server.get_email_conversation("thread-1")

    assert result["ok"] is True
    assert result["conversation"]["message_count"] == 1

    get.assert_called_once_with(
        mock_server_service.return_value,
        "thread-1",
        format="full",
    )


@pytest.mark.integration
def test_attachment_checks_membership_before_download(
    mocker,
    mock_server_service,
    sample_message,
):
    mocker.patch.object(
        server.gmail_api,
        "get_message",
        return_value=sample_message,
    )

    download = mocker.patch.object(
        server.attachment_service,
        "download_attachment",
    )

    result = server.get_attachment("msg-1", "not-present")

    assert result["ok"] is False
    assert result["error"]["code"] == "VALIDATION_ERROR"

    download.assert_not_called()


@pytest.mark.integration
def test_attachment_download_uses_gmail_metadata(
    mocker,
    mock_server_service,
    sample_message,
):
    sample_message["payload"]["parts"] = [
        {
            "filename": "invoice.pdf",
            "mimeType": "application/pdf",
            "body": {
                "attachmentId": "att-1",
                "size": 5,
            },
        }
    ]

    mocker.patch.object(
        server.gmail_api,
        "get_message",
        return_value=sample_message,
    )

    download = mocker.patch.object(
        server.attachment_service,
        "download_attachment",
        return_value={
            "saved": True,
            "filename": "invoice.pdf",
        },
    )

    result = server.get_attachment("msg-1", "att-1")

    assert result["ok"] is True

    kwargs = download.call_args.kwargs

    assert kwargs["message_id"] == "msg-1"
    assert kwargs["attachment"]["filename"] == "invoice.pdf"
    assert kwargs["attachment"]["attachment_id"] == "att-1"
    assert kwargs["attachment"]["size_bytes"] == 5


@pytest.mark.integration
def test_search_returns_api_failure_as_structured_error(
    mocker,
    mock_server_service,
):
    mocker.patch.object(
        server.search_service,
        "search_emails",
        side_effect=TimeoutError("Gmail timed out"),
    )

    result = server.search_emails(sender="alice@example.com")

    assert result["ok"] is False
    assert result["error"]["code"] == "NETWORK_ERROR"
    assert result["error"]["retryable"] is True
