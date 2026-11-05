from pydantic import BaseModel, Field , model_validator, field_validator, ConfigDict
from datetime import date, time, datetime
from pathlib import PurePath
import re

# search email request
class SearchEmailsRequest(BaseModel):

    # --------------------------------------------------
    # 1. MODEL CONFIGURATION
    # --------------------------------------------------

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "allOf": [
                {
                    "if": {
                        "anyOf": [
                            {
                                "required": ["start_time"],
                            },
                            {
                                "required": ["end_time"],
                            },
                        ]
                    },
                    "then": {
                        "required": ["time_date"],
                    },
                }
            ]
        },
    )

    # --------------------------------------------------
    # 2. MODEL FIELDS
    # --------------------------------------------------

    sender: str | None = Field(
        default=None,
        description="Email address of sender.",
    )

    recipient: str | None = Field(
        default=None,
        description="Email address of recipient.",
    )

    subject: str | None = Field(
        default=None,
        description="Subject line.",
    )

    keyword: str | None = Field(
        default=None,
        description="Search email content using a keyword.",
    )

    start_date: date | None = Field(
        default=None,
        description="Beginning of date range, YYYY-MM-DD.",
    )

    end_date: date | None = Field(
        default=None,
        description="End of date range, YYYY-MM-DD.",
    )

    time_date: date | None = Field(
        default=None,
        description=(
            "Calendar date on which the time-based search starts. "
            "Required when start_time or end_time is supplied. "
            "If only start_time is supplied, end_time defaults to 23:59. "
            "If only end_time is supplied, start_time defaults to 00:00. "
            "If neither is supplied, the search covers the entire date."
        ),
    )

    start_time: time | None = Field(
        default=None,
        description=(
            "Start time, HH:MM, 24-hour format. "
            "Requires time_date. Defaults to 00:00 when time_date is supplied."
        ),
    )

    end_time: time | None = Field(
        default=None,
        description=(
            "End time, HH:MM, 24-hour format. "
            "Requires time_date. Defaults to 23:59 when time_date is supplied. "
            "An earlier or equal end time represents an interval crossing midnight."
        ),
    )

    has_attachment: bool | None = Field(
        default=None,
        description="True to find emails with attachments; false for without.",
    )

    is_unread: bool | None = Field(
        default=None,
        description="True to find unread emails; false for read emails.",
    )

    max_results: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of emails to return, between 1 and 100.",
    )

    page_token: str | None = Field(
        default=None,
        min_length=1,
        description="Pagination token returned by a previous search.",
    )

    # --------------------------------------------------
    # 3. STRING VALIDATORS
    # --------------------------------------------------

    @field_validator(
        "sender",
        "recipient",
        "subject",
        "keyword",
        "page_token",
    )
    @classmethod
    def validate_search_strings(cls, value):

        if value is None:
            return value

        value = value.strip()

        if not value:
            raise ValueError("Search values cannot be empty.")

        return value

    # --------------------------------------------------
    # 4. DATE VALIDATORS
    # --------------------------------------------------

    @field_validator(
        "start_date",
        "end_date",
        "time_date",
        mode="before",
    )
    @classmethod
    def validate_dates(cls, value):

        if value is None:
            return value

        if isinstance(value, datetime):
            raise ValueError(
                "Date must use YYYY-MM-DD format, not datetime."
            )

        if isinstance(value, date):
            return value

        if not isinstance(value, str):
            raise ValueError(
                "Date must be a string in YYYY-MM-DD format."
            )

        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError(
                "Date must use YYYY-MM-DD format."
            )

        try:
            return date.fromisoformat(value)

        except ValueError:
            raise ValueError("Invalid calendar date.")

    # --------------------------------------------------
    # 5. TIME VALIDATORS
    # --------------------------------------------------

    @field_validator(
        "start_time",
        "end_time",
        mode="before",
    )
    @classmethod
    def validate_times(cls, value):

        if value is None:
            return value

        if isinstance(value, time):
            if value.tzinfo is not None:
                raise ValueError("Timezone-aware times are not supported.")
            if value.second != 0 or value.microsecond != 0:
                raise ValueError("Time must use HH:MM format.")
            return value

        if not isinstance(value, str):
            raise ValueError(
                "Time must be a string in HH:MM format."
            )

        if not re.fullmatch(r"\d{2}:\d{2}", value):
            raise ValueError(
                "Time must use HH:MM format."
            )

        try:
            return time.fromisoformat(value)

        except ValueError:
            raise ValueError("Invalid time.")


# get email details
class GetEmailDetailsInput(BaseModel):

    model_config = ConfigDict(extra="forbid")

    message_id: str = Field(
        min_length=1,
        max_length=256,
        description="Required Gmail message ID."
    )

    @field_validator("message_id")
    @classmethod
    def validate_message_id(cls, value):
        value = value.strip()

        if not value:
            raise ValueError("message_id cannot be empty.")

        return value

# get email conversation
class GetEmailConversationInput(BaseModel):

    model_config = ConfigDict(extra="forbid")

    thread_id: str = Field(
        min_length=1,
        max_length=256,
        description="Required Gmail conversation/thread ID."
    )

    @field_validator("thread_id")
    @classmethod
    def validate_thread_id(cls, value):
        value = value.strip()

        if not value:
            raise ValueError("thread_id cannot be empty.")

        return value

# get email attachments
class GetAttachmentInput(BaseModel):

    model_config = ConfigDict(extra="forbid")

    message_id: str = Field(
        description="Gmail message ID containing the attachment."
    )

    attachment_id: str = Field(
        description="Gmail attachment ID."
    )

    filename: str = Field(
        description="Attachment filename, not a filesystem path."
    )

    mime_type: str = Field(
        default="application/octet-stream",
        description="MIME type reported for the attachment."
    )

    size_bytes: int | None = Field(
        default=None,
        ge=0,
        strict=True,
        description="Attachment size in bytes, if known."
    )

    @field_validator("message_id", "attachment_id")
    @classmethod
    def validate_ids(cls, value):
        value = value.strip()

        if not value:
            raise ValueError("ID cannot be empty.")

        return value

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, value):
        value = value.strip()

        if not value:
            raise ValueError("Filename cannot be empty.")

        if value in {".", ".."}:
            raise ValueError("Invalid filename.")

        if PurePath(value).name != value:
            raise ValueError("Filename must not contain a path.")

        if "/" in value or "\\" in value:
            raise ValueError("Path separators are not allowed.")

        if ".." in value:
            raise ValueError("Filename cannot contain traversal patterns.")

        if any(ord(char) < 32 for char in value):
            raise ValueError("Control characters are not allowed.")

        return value

    @field_validator("mime_type")
    @classmethod
    def validate_mime_type(cls, value):
        value = value.strip()

        if not re.fullmatch(
            r"[A-Za-z0-9!#$&^_.+-]+/[A-Za-z0-9!#$&^_.+-]+",
            value,
        ):
            raise ValueError("Invalid MIME type.")

        return value
