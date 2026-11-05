from pydantic import BaseModel, Field , model_validator, field_validator, ConfigDict
from datetime import date, time
from pathlib import PurePath
import re

# search email request
class SearchEmailsRequest(BaseModel):

    # 1. model configs
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "allOf" :[
                {
                    "if": {
                        "anyOf" :[
                            {
                                "required":["time_date"],
                                "properties":{
                                    "time_date":{"type":"string"}
                                },
                            },
                            {
                                "required": ["start_time"],
                                "properties": {
                                    "start_time": {"type": "string"}
                                },
                            },
                            {
                                "required": ["end_time"],
                                "properties": {
                                    "end_time": {"type": "string"}
                                },
                            }
                        ]
                    },
                    "then" :{
                        "required":[
                            "time_date",
                            "start_time",
                            "end_time",
                        ],
                        "properties":{
                            "time_date":{"type":"string"},
                            "start_time":{"type":"string"},
                            "end_time":{"type":"string"},
                        },
                    }
                }
            ]
        }
    )

    # 2. model fields

    sender: str | None = Field(None, description="Email address of sender.")
    recipient: str | None = Field(None, description="Email address of recipient.")
    subject: str | None = Field(None, description="Subject line.")

    keyword: str | None = Field(
        default=None,
        description="Search email content using a keyword."
    )

    start_date: date | None = Field(
        default=None,
        description="Beginning of date range, YYYY-MM-DD."
    )

    end_date: date | None = Field(
        default=None,
        description="End of date range, YYYY-MM-DD."
    )

    time_date: date | None = Field(
        default=None,
        description="Date for time-based search, YYYY-MM-DD."
    )

    start_time: time | None = Field(
        default=None,
        description="Start time, HH:MM, 24-hour format."
    )

    end_time: time |None = Field(
        default=None,
        description="End time, HH:MM, 24-hour format."
    )

    has_attachment: bool | None = Field(
        default=None,
        description="True to find emails with attachments; false for without."
    )

    is_unread: bool | None = Field(
        default=None,
        description="True to find unread emails; false for read emails."
    )

    max_results: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of emails to return, between 1 and 100."
    )

    page_token: str | None = Field(
        default=None,
        min_length=1,
        description="Pagination token returned by a previous search."
    )

    # field validators
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

    @field_validator("start_date", "end_date", "time_date", mode="before")
    @classmethod
    def validate_dates(cls, value):

        if value is None:
            return value

        if isinstance(value, date):
            return value

        if not isinstance(value, str):
            raise ValueError("Date must be a string in YYYY-MM-DD format.")

        try:
            return date.fromisoformat(value)
        except ValueError:
            raise ValueError("Date must use YYYY-MM-DD format.")


    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def validate_times(cls, value):

        if value is None:
            return value

        if isinstance(value, time):
            return value

        if not isinstance(value, str):
            raise ValueError("Time must be a string in HH:MM format.")

        if not re.fullmatch(r"\d{2}:\d{2}", value):
            raise ValueError("Time must use HH:MM format.")

        try:
            return time.fromisoformat(value)
        except ValueError:
            raise ValueError("Invalid time.")

    # model validators

    @model_validator(mode="after")
    def validate_search_conditions(self):

        # Date range validation
        if (
            self.start_date
            and self.end_date
            and self.start_date > self.end_date
        ):
            raise ValueError(
                "start_date cannot be after end_date."
            )

        # Time fields must be supplied together
        time_values = [
            self.time_date,
            self.start_time,
            self.end_time,
        ]

        supplied = [value is not None for value in time_values]

        if any(supplied) and not all(supplied):
            raise ValueError(
                "time_date, start_time and end_time "
                "must be provided together."
            )

        # Start time must be earlier than end time
        if self.start_time and self.end_time:
            if self.start_time >= self.end_time:
                raise ValueError(
                    "start_time must be earlier than end_time."
                )

        # Do not combine date-range and time-range filters
        if self.time_date and (self.start_date or self.end_date):
            raise ValueError(
                "Use either date-range filtering or "
                "time-range filtering, not both."
            )

        # Require at least one actual search condition
        search_conditions = [
            self.sender,
            self.recipient,
            self.subject,
            self.keyword,
            self.start_date,
            self.end_date,
            self.time_date,
            self.has_attachment,
            self.is_unread,
        ]

        if not any(value is not None for value in search_conditions):
            raise ValueError(
                "Provide at least one search condition."
            )

        return self

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
