
# attachment_service.py

import base64
import re
from pathlib import Path

from .gmail_service import get_attachment_data


# Maximum allowed attachment size: 25 MB.
DEFAULT_MAX_BYTES = 25 * 1024 * 1024


def _decode_attachment_data(encoded_data):
    """Decode Gmail's Base64URL-encoded attachment data."""

    if not encoded_data:
        raise ValueError("Attachment data is empty.")

    # Gmail may omit Base64URL padding.
    encoded_data += "=" * (-len(encoded_data) % 4)

    return base64.urlsafe_b64decode(encoded_data)


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


def _get_unique_path(directory, filename):
    """Avoid overwriting an existing file."""

    path = directory / filename

    if not path.exists():
        return path

    original = Path(filename)
    counter = 1

    while True:
        new_name = f"{original.stem}_{counter}{original.suffix}"
        path = directory / new_name

        if not path.exists():
            return path

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
        raise ValueError(
            f"Attachment exceeds the {max_bytes}-byte size limit."
        )

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
        raise ValueError(
            "Attachment has neither inline data nor an attachment_id."
        )

    # Convert Base64URL text into the original binary file contents.
    file_bytes = _decode_attachment_data(encoded_data)

    # Check actual decoded size as well.
    actual_size = len(file_bytes)

    if actual_size > max_bytes:
        raise ValueError(
            f"Decoded attachment exceeds the {max_bytes}-byte size limit."
        )

    # Create the output directory if it does not exist.
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)

    # Never overwrite an existing attachment.
    file_path = _get_unique_path(directory, filename)

    # Save binary bytes. This works for PDFs, images, documents, etc.
    file_path.write_bytes(file_bytes)

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
        "saved": True,
    }