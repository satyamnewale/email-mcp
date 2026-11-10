# attachment_service.py
import binascii
import base64
import re
from pathlib import Path

from .gmail_service import get_attachment_data

# Maximum allowed attachment size: 25 MB.
DEFAULT_MAX_BYTES = 25 * 1024 * 1024


def _decode_attachment_data(encoded_data: str) -> bytes:
    """Strictly decode Gmail Base64URL attachment data."""

    if not encoded_data:
        raise ValueError("Attachment data is empty.")

    if not isinstance(encoded_data, str):
        raise TypeError("Attachment data must be a string.")

    try:
        encoded_bytes = encoded_data.encode("ascii")

        encoded_bytes += b"=" * (-len(encoded_bytes) % 4)

        return base64.b64decode(
            encoded_bytes,
            altchars=b"-_",
            validate=True,
        )

    except (ValueError, UnicodeEncodeError, binascii.Error) as exc:
        raise ValueError("Invalid Base64URL attachment data.") from exc


def _safe_filename(filename):
    """Remove path components and unsafe filename characters."""

    # Handle both Windows and Unix-style paths.
    filename = str(filename or "attachment").replace("\\", "/")
    filename = Path(filename).name

    # Replace characters that are unsafe or invalid in filenames.
    filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", filename)
    filename = filename.strip(" .")

    if not filename:
        filename = "attachment"

    return filename


def _write_unique_file(directory, filename, content):
    original = Path(filename)

    counter = 0

    while True:
        if counter == 0:
            candidate = directory / filename
        else:
            candidate = directory / (f"{original.stem}_{counter}{original.suffix}")

        try:
            with candidate.open("xb") as file:
                file.write(content)

            return candidate

        except FileExistsError:
            counter += 1


def download_attachment(
    service,
    message_id,
    attachment,
    output_dir="downloads",
    max_bytes=DEFAULT_MAX_BYTES,
):
    """
    Download and save one Gmail attachment.

    Parameters:
        service: Authenticated Gmail API service.
        message_id: Gmail ID of the email containing the attachment.
        attachment: Metadata dictionary from email_parser.attachments().
        output_dir: Directory where the file will be saved.
        max_bytes: Maximum permitted decoded file size.

    Returns:
        Dictionary containing the saved file's path and metadata.
    """

    if not message_id:
        raise ValueError("message_id is required.")

    if not isinstance(attachment, dict):
        raise TypeError("attachment must be a dictionary.")

    if max_bytes <= 0:
        raise ValueError("max_bytes must be greater than zero.")

    filename = _safe_filename(attachment.get("filename"))
    attachment_id = attachment.get("attachment_id")
    inline_data = attachment.get("data")

    # Check the reported size before retrieving or decoding the file.
    reported_size = attachment.get("size_bytes")

    if reported_size is not None and int(reported_size) > max_bytes:
        raise ValueError(f"Attachment exceeds the {max_bytes}-byte size limit.")

    # Use data already supplied, or fetch it from Gmail.
    if inline_data:
        encoded_data = inline_data

    elif attachment_id:
        response = get_attachment_data(
            service,
            message_id,
            attachment_id,
        )
        encoded_data = response.get("data", "")

    else:
        raise ValueError("Attachment has neither inline data nor an attachment_id.")

    # Convert Base64URL text into the original binary file contents.
    file_bytes = _decode_attachment_data(encoded_data)

    # Check actual decoded size as well.
    actual_size = len(file_bytes)

    if actual_size > max_bytes:
        raise ValueError(f"Decoded attachment exceeds the {max_bytes}-byte size limit.")

    # Create the output directory if it does not exist.
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)

    # Never overwrite an existing attachment.
    file_path = _write_unique_file(
        directory,
        filename,
        file_bytes,
    )

    return {
        "filename": file_path.name,
        "path": str(file_path.resolve()),
        "mime_type": attachment.get(
            "mime_type",
            "application/octet-stream",
        ),
        "size_bytes": actual_size,
        "message_id": message_id,
        "attachment_id": attachment_id,
        "part_id": attachment.get("part_id"),
        "saved": True,
    }
