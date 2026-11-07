
import pytest

from services import auth


@pytest.mark.unit
def test_missing_credentials_fails_without_oauth(mocker, tmp_path):
    mocker.patch.object(
        auth,
        "TOKEN_FILE",
        tmp_path / "token.json",
    )

    mocker.patch.object(
        auth,
        "CREDENTIALS_FILE",
        tmp_path / "credentials.json",
    )

    flow = mocker.patch.object(
        auth.InstalledAppFlow,
        "from_client_secrets_file",
    )

    with pytest.raises(FileNotFoundError):
        auth.get_gmail_service()

    flow.assert_not_called()


@pytest.mark.unit
def test_valid_token_reused_without_browser(mocker, tmp_path):
    token = tmp_path / "token.json"
    token.write_text("{}", encoding="utf-8")

    mocker.patch.object(auth, "TOKEN_FILE", token)

    creds = mocker.Mock()
    creds.valid = True

    mocker.patch.object(
        auth.Credentials,
        "from_authorized_user_file",
        return_value=creds,
    )

    browser = mocker.patch.object(
        auth.InstalledAppFlow,
        "from_client_secrets_file",
    )

    build = mocker.patch.object(
        auth,
        "build",
        return_value="gmail-client",
    )

    result = auth.get_gmail_service()

    assert result == "gmail-client"

    browser.assert_not_called()

    build.assert_called_once_with(
        "gmail",
        "v1",
        credentials=creds,
    )


@pytest.mark.unit
def test_expired_token_refreshes(mocker, tmp_path):
    token = tmp_path / "token.json"
    token.write_text("{}", encoding="utf-8")

    mocker.patch.object(auth, "TOKEN_FILE", token)

    creds = mocker.Mock()
    creds.valid = False
    creds.expired = True
    creds.refresh_token = "refresh-token"
    creds.to_json.return_value = '{"token": "new"}'

    mocker.patch.object(
        auth.Credentials,
        "from_authorized_user_file",
        return_value=creds,
    )

    request = mocker.patch.object(auth, "Request")

    mocker.patch.object(
        auth,
        "build",
        return_value="gmail-client",
    )

    auth.get_gmail_service()

    creds.refresh.assert_called_once_with(request.return_value)

    assert token.read_text(encoding="utf-8") == '{"token": "new"}'
