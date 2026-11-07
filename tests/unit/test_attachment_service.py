
import base64
import pytest

pytestmark = pytest.mark.unit

from services.attachment_service import (
    _safe_filename,
    _get_unique_path,
    _decode_attachment_data,
    download_attachment,
)


def test_safe_filename():
    result = _safe_filename(
        "../../secret/report.pdf"
    )

    assert result == "report.pdf"


def test_safe_filename_removes_windows_path():
    result = _safe_filename(
        r"C:\temp\report.pdf"
    )

    assert result == "report.pdf"


def test_unique_path(tmp_path):
    first = tmp_path / "report.pdf"
    first.write_text("existing")

    result = _get_unique_path(
        tmp_path,
        "report.pdf",
    )

    assert result.name == "report_1.pdf"


def test_decode_attachment_data():
    content = b"test attachment"

    encoded = base64.urlsafe_b64encode(
        content
    ).decode().rstrip("=")

    assert _decode_attachment_data(encoded) == content


def test_download_attachment(mock_gmail_service, tmp_path):
    content = b"hello attachment"

    encoded = base64.urlsafe_b64encode(
        content
    ).decode().rstrip("=")

    attachment = {
        "filename": "report.txt",
        "attachment_id": "att_123",
        "size_bytes": len(content),
    }

    from services import attachment_service

    mock_get = pytest.MonkeyPatch()
    mock_get.setattr(
        attachment_service,
        "get_attachment_data",
        lambda *args: {"data": encoded},
    )

    try:
        result = download_attachment(
            service=mock_gmail_service,
            message_id="msg_123",
            attachment=attachment,
            output_dir=tmp_path,
        )

        saved_file = tmp_path / "report.txt"

        assert saved_file.exists()
        assert saved_file.read_bytes() == content
        assert result["filename"] == "report.txt"
    finally:
        mock_get.undo()


def test_download_rejects_oversized_attachment(
    mock_gmail_service,
    tmp_path,
):
    attachment = {
        "filename": "large.bin",
        "attachment_id": "att_123",
        "size_bytes": 1000,
    }

    with pytest.raises(ValueError):
        download_attachment(
            service=mock_gmail_service,
            message_id="msg_123",
            attachment=attachment,
            output_dir=tmp_path,
            max_bytes=100,
        )
