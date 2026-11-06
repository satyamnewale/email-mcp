from pydantic import BaseModel, Field , field_validator, ConfigDict
from datetime import date, time, datetime
from pathlib import PurePath
import re

# search email request

from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
    field_validator,
    model_validator,
)
from datetime import date, time, datetime
import re


class SearchEmailsRequest(BaseModel):

    # --------------------------------------------------
    # 1. MODEL CONFIGURATION
    # --------------------------------------------------

    model_config = ConfigDict(
        extra="forbid",
    )

    # --------------------------------------------------
    # 2. SEARCH FILTERS
    # --------------------------------------------------

    sender: str | None = Field(
        default=None,
        min_length=1,
        max_length=320,
        description=(
            "Sender's email address or name. "
            "Use when the user wants emails from a particular person."
        ),
    )

    recipient: str | None = Field(
        default=None,
        min_length=1,
        max_length=320,
        description=(
            "Recipient's email address or name. "
            "Use when the user wants emails sent to a particular person."
        ),
    )

    subject: str | None = Field(
        default=None,
        min_length=1,
        max_length=500,
        description=(
            "Full or partial email subject to search for."
        ),
    )

    keyword: str | None = Field(
        default=None,
        min_length=1,
        max_length=1000,
        description=(
            "Keyword or phrase to search within matching emails."
        ),
    )

    # --------------------------------------------------
    # 3. DATE FILTERS
    # --------------------------------------------------

    start_date: date | None = Field(
        default=None,
        description=(
            "Inclusive beginning of the date range. "
            "Must use YYYY-MM-DD format."
        ),
    )

    end_date: date | None = Field(
        default=None,
        description=(
            "Inclusive ending of the date range. "
            "Must use YYYY-MM-DD format."
        ),
    )

    # --------------------------------------------------
    # 4. TIME FILTERS
    # --------------------------------------------------

    time_date: date | None = Field(
        default=None,
        description=(
            "Calendar date for the time-based search. "
            "Must be provided together with start_time and end_time. "
            "Format: YYYY-MM-DD."
        ),
    )

    start_time: time | None = Field(
        default=None,
        description=(
            "Beginning of the time range in HH:MM 24-hour format. "
            "Requires time_date and end_time."
        ),
    )

    end_time: time | None = Field(
        default=None,
        description=(
            "End of the time range in HH:MM 24-hour format. "
            "Requires time_date and start_time. "
            "An earlier or equal end time represents the following day."
        ),
    )

    # --------------------------------------------------
    # 5. BOOLEAN FILTERS
    # --------------------------------------------------

    has_attachment: bool | None = Field(
        default=None,
        description=(
            "True to find emails with attachments; "
            "False to find emails without attachments; "
            "None to apply no attachment filter."
        ),
    )

    is_unread: bool | None = Field(
        default=None,
        description=(
            "True to find unread emails; "
            "False to find read emails; "
            "None to apply no read-status filter."
        ),
    )

    # --------------------------------------------------
    # 6. PAGINATION
    # --------------------------------------------------

    max_results: int = Field(
        default=10,
        ge=1,
        le=50,
        description=(
            "Maximum number of emails to return. "
            "Defaults to 10. Allowed range: 1-50."
        ),
    )

    page_token: str | None = Field(
        default=None,
        min_length=1,
        description=(
            "Pagination token returned by a previous search. "
            "Use only when retrieving the next page of that search."
        ),
    )

    # --------------------------------------------------
    # 7. STRING VALIDATION
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
            return None

        value = value.strip()

        if not value:
            raise ValueError(
                "Search values cannot be empty or whitespace."
            )

        return value

    # --------------------------------------------------
    # 8. DATE VALIDATION
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
            return None

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

        except ValueError as exc:
            raise ValueError(
                "Invalid calendar date."
            ) from exc

    # --------------------------------------------------
    # 9. TIME VALIDATION
    # --------------------------------------------------

    @field_validator(
        "start_time",
        "end_time",
        mode="before",
    )
    @classmethod
    def validate_times(cls, value):

        if value is None:
            return None

        if isinstance(value, time):

            if value.tzinfo is not None:
                raise ValueError(
                    "Timezone-aware times are not supported."
                )

            if value.second != 0 or value.microsecond != 0:
                raise ValueError(
                    "Time must use HH:MM format."
                )

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

        except ValueError as exc:
            raise ValueError(
                "Invalid time."
            ) from exc

    # --------------------------------------------------
    # 10. MODEL-LEVEL VALIDATION
    # --------------------------------------------------

    @model_validator(mode="after")
    def validate_search_parameters(self):

        # Validate date range.
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.start_date > self.end_date
        ):
            raise ValueError(
                "start_date must not be after end_date."
            )

        # Validate time filter dependencies.
        time_fields = (
            self.time_date,
            self.start_time,
            self.end_time,
        )

        provided_time_fields = sum(
            value is not None for value in time_fields
        )

        if provided_time_fields not in (0, 3):
            raise ValueError(
                "time_date, start_time, and end_time "
                "must all be provided together."
            )

        return self



class GetEmailDetailsInput(BaseModel):

    model_config = ConfigDict(
        extra="forbid",
    )

    message_id: str = Field(
        min_length=1,
        max_length=256,
        description=(
            "Gmail message ID of the specific email to retrieve. "
            "Obtain this ID from search_emails results. "
            "Required to retrieve the complete email details."
        ),
    )

    @field_validator("message_id")
    @classmethod
    def validate_message_id(cls, value):

        value = value.strip()

        if not value:
            raise ValueError(
                "message_id cannot be empty."
            )

        return value

# get email conversation

class GetEmailConversationInput(BaseModel):

    model_config = ConfigDict(
        extra="forbid",
    )

    thread_id: str = Field(
        min_length=1,
        max_length=256,
        description=(
            "Gmail conversation/thread ID identifying the "
            "conversation to retrieve. Obtain this ID from "
            "search_emails results or email details. "
            "Returns all messages belonging to that thread."
        ),
    )

    @field_validator("thread_id")
    @classmethod
    def validate_thread_id(cls, value):

        value = value.strip()

        if not value:
            raise ValueError(
                "thread_id cannot be empty."
            )

        return value


# get email attachments
class GetAttachmentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message_id: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Gmail message ID containing the attachment. Obtain this from search_emails or get_email_details.",
    )

    attachment_id: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Attachment ID obtained from the attachment metadata returned by get_email_details.",
    )

    @field_validator("message_id", "attachment_id")
    @classmethod
    def validate_ids(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("ID cannot be empty.")

        return value