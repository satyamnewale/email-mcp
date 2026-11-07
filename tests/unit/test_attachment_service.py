import base64

import pytest

from services import attachment_service as attachments


@pytest.mark.unit
def test_filename_removes_directory_traversal():
    assert attachments._safe_filename("../../secret.txt") == "secret.txt"
    assert attachments._safe_filename(r"C:\temp\file.pdf") == "file.pdf"


@pytest.mark.unit
def test_download_inline_attachment(tmp_path):
    payload = base64.urlsafe_b64encode(b"PDF DATA").decode()
    result = attachments.download_attachment(
        service=None,
        message_id="msg-1",
        attachment={"filename": "report.pdf", "data": payload, "size_bytes": 8},
        output_dir=tmp_path,
    )
    assert result["saved"] is True
    assert (tmp_path / "report.pdf").read_bytes() == b"PDF DATA"


@pytest.mark.unit
def test_duplicate_name_gets_suffix(tmp_path):
    payload = base64.urlsafe_b64encode(b"abc").decode()
    attachment = {"filename": "a.txt", "data": payload}
    attachments.download_attachment(None, "msg-1", attachment, output_dir=tmp_path)
    result = attachments.download_attachment(
        None, "msg-1", attachment, output_dir=tmp_path
    )
    assert result["filename"] == "a_1.txt"


@pytest.mark.unit
def test_size_limit_rejected_before_write(tmp_path):
    with pytest.raises(ValueError, match="size limit"):
        attachments.download_attachment(
            None,
            "msg-1",
            {"filename": "huge.bin", "size_bytes": 100, "data": "YQ=="},
            output_dir=tmp_path,
            max_bytes=10,
        )
    assert list(tmp_path.iterdir()) == []


@pytest.mark.unit
def test_download_fetches_attachment_when_not_inline(mocker, tmp_path):
    encoded = base64.urlsafe_b64encode(b"data").decode()
    fetch = mocker.patch.object(
        attachments, "get_attachment_data", return_value={"data": encoded}
    )
    result = attachments.download_attachment(
        "service",
        "msg-1",
        {"filename": "file.txt", "attachment_id": "att-1"},
        output_dir=tmp_path,
    )
    fetch.assert_called_once_with("service", "msg-1", "att-1")
    assert result["size_bytes"] == 4
