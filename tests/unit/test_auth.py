
from unittest.mock import MagicMock, patch

from services.auth import get_gmail_service


@patch("services.auth.build")
@patch("services.auth.Credentials")
@patch("services.auth.TOKEN_FILE")
def test_existing_valid_token(
    mock_token_file,
    mock_credentials,
    mock_build,
):
    mock_token_file.exists.return_value = True

    credentials = MagicMock()
    credentials.valid = True

    mock_credentials.from_authorized_user_file.return_value = (
        credentials
    )

    mock_build.return_value = "mock-gmail-service"

    result = get_gmail_service()

    assert result == "mock-gmail-service"

    mock_build.assert_called_once_with(
        "gmail",
        "v1",
        credentials=credentials,
    )


@patch("services.auth.build")
@patch("services.auth.InstalledAppFlow")
@patch("services.auth.TOKEN_FILE")
@patch("services.auth.CREDENTIALS_FILE")
@patch("services.auth.Credentials")
def test_oauth_flow_when_token_missing(
    mock_credentials,
    mock_credentials_file,
    mock_token_file,
    mock_flow,
    mock_build,
):
    mock_token_file.exists.return_value = False
    mock_credentials_file.exists.return_value = True

    credentials = MagicMock()
    credentials.valid = True
    credentials.to_json.return_value = '{"token": "fake"}'

    flow = mock_flow.from_client_secrets_file.return_value
    flow.run_local_server.return_value = credentials

    mock_build.return_value = "mock-gmail-service"

    result = get_gmail_service()

    assert result == "mock-gmail-service"

    flow.run_local_server.assert_called_once_with(port=0)
    mock_token_file.write_text.assert_called_once()


@patch("services.auth.CREDENTIALS_FILE")
@patch("services.auth.TOKEN_FILE")
def test_missing_oauth_credentials(
    mock_token_file,
    mock_credentials_file,
):
    mock_token_file.exists.return_value = False
    mock_credentials_file.exists.return_value = False

    import pytest

    with pytest.raises(FileNotFoundError):
        get_gmail_service()
