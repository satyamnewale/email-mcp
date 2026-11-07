import pytest

from services import auth


@pytest.mark.unit
def test_missing_credentials_fails_without_oauth(mocker, tmp_path):
    mocker.patch.object(auth, "TOKEN_FILE", tmp_path / "token.json")
    mocker.patch.object(auth, "CREDENTIALS_FILE", tmp_path / "credentials.json")
    flow = mocker.patch.object(auth.InstalledAppFlow, "from_client_secrets_file")
    with pytest.raises(FileNotFoundError):
        auth.get_gmail_service()
    flow.assert_not_called()


@pytest.mark.unit
def test_valid_token_reused_without_browser(mocker, tmp_path):
    token = tmp_path / "token.json"
    token.write_text("{}")
    mocker.patch.object(auth, "TOKEN_FILE", token)
    creds = mocker.Mock(valid=True)
    mocker.patch.object(
        auth.Credentials, "from_authorized_user_file", return_value=creds
    )
    browser = mocker.patch.object(auth.InstalledAppFlow, "from_client_secrets_file")
    build = mocker.patch.object(auth, "build", return_value="gmail-client")
    assert auth.get_gmail_service() == "gmail-client"
    browser.assert_not_called()
    build.assert_called_once_with("gmail", "v1", credentials=creds)


@pytest.mark.unit
def test_expired_token_refreshes(mocker, tmp_path):
    token = tmp_path / "token.json"
    token.write_text("{}")
    mocker.patch.object(auth, "TOKEN_FILE", token)
    creds = mocker.Mock(valid=False, expired=True, refresh_token="refresh")
    creds.to_json.return_value = '{"token": "new"}'
    mocker.patch.object(
        auth.Credentials, "from_authorized_user_file", return_value=creds
    )
    mocker.patch.object(auth, "build", return_value="gmail-client")
    auth.get_gmail_service()
    creds.refresh.assert_called_once()
    assert token.read_text() == '{"token": "new"}'
