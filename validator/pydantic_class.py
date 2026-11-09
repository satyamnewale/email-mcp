import re
from datetime import date, datetime, time

# search email request
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

EMAIL_PATTERN = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$"
)

GMAIL_OPERATOR_PATTERN = re.compile(
    r"^\s*-?(?:"
    r"from|to|cc|bcc|subject|after|before|newer|older|"
    r"newer_than|older_than|has|filename|label|category|"
    r"is|in|deliveredto|list|larger|smaller|size|rfc822msgid"
    r")\s*:",
    re.IGNORECASE,
)

DISPLAY_NAME_PATTERN = re.compile(r"^[\w][\w .'-]{0,79}$")


def _validate_identity(value: str, field_name: str) -> str:
    """
    Accept either a simple email address or a display name.

    Examples:
        user@example.com
        John
        John Smith

    Gmail search operators and arbitrary query syntax are rejected.
    """

    value = value.strip()

    if not value:
        raise ValueError(f"{field_name} cannot be empty.")

    if EMAIL_PATTERN.fullmatch(value):
        return value

    if DISPLAY_NAME_PATTERN.fullmatch(value):
        return value

    raise ValueError(
        f"{field_name} must be a valid email address or a simple display name. "
        "Gmail search operators and special query syntax are not allowed."
    )


def _validate_literal_phrase(value, field_name):
    if value is None:
        return None

    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string.")

    value = value.strip()

    if not value:
        raise ValueError(f"{field_name} cannot be empty.")

    if '"' in value or "\\" in value:
        raise ValueError(
            f'{field_name} cannot contain double quotes or backslashes.'
        )

    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError(
            f"{field_name} cannot contain control characters."
        )

    # Reject values beginning with Gmail search operators.
    if GMAIL_OPERATOR_PATTERN.match(value):
        raise ValueError(
            f"{field_name} cannot contain Gmail search operators. "
            "Provide a literal search phrase instead."
        )

    return value

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
        description=("Full or partial email subject to search for."),
    )

    keyword: str | None = Field(
        default=None,
        min_length=1,
        max_length=1000,
        description=("Keyword or phrase to search within matching emails."),
    )

    # --------------------------------------------------
    # 3. DATE FILTERS
    # --------------------------------------------------

    start_date: date | None = Field(
        default=None,
        description=(
            "Inclusive beginning of the date range. Must use YYYY-MM-DD format."
        ),
    )

    end_date: date | None = Field(
        default=None,
        description=("Inclusive ending of the date range. Must use YYYY-MM-DD format."),
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
            "Maximum number of emails to return. Defaults to 10. Allowed range: 1-50."
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

    @field_validator("sender", "recipient")
    @classmethod
    def validate_identity_fields(cls, value, info):
        if value is None:
            return None

        return _validate_identity(value, info.field_name)

    @field_validator("subject", "keyword")
    @classmethod
    def validate_literal_search_fields(cls, value, info):
        if value is None:
            return None

        return _validate_literal_phrase(value, info.field_name)

    @field_validator("page_token")
    @classmethod
    def validate_page_token(cls, value):

        if value is None:
            return None

        value = value.strip()

        if not value:
            raise ValueError("page_token cannot be empty.")

        if any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise ValueError("page_token cannot contain control characters.")

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
            raise TypeError("Date must use YYYY-MM-DD format, not datetime.")

        if isinstance(value, date):
            return value

        if not isinstance(value, str):
            raise TypeError("Date must be a string in YYYY-MM-DD format.")

        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise TypeError("Date must use YYYY-MM-DD format.")

        try:
            return date.fromisoformat(value)

        except ValueError as exc:
            raise ValueError("Invalid calendar date.") from exc

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
                raise ValueError("Timezone-aware times are not supported.")

            if value.second != 0 or value.microsecond != 0:
                raise ValueError("Time must use HH:MM format.")

            return value

        if not isinstance(value, str):
            raise ValueError("Time must be a string in HH:MM format.")

        if not re.fullmatch(r"\d{2}:\d{2}", value):
            raise ValueError("Time must use HH:MM format.")

        try:
            return time.fromisoformat(value)

        except ValueError as exc:
            raise ValueError("Invalid time.") from exc

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
            raise ValueError("start_date must not be after end_date.")

        # Validate time filter dependencies.
        time_fields = (
            self.time_date,
            self.start_time,
            self.end_time,
        )

        provided_time_fields = sum(value is not None for value in time_fields)

        if provided_time_fields not in (0, 3):
            raise ValueError(
                "time_date, start_time, and end_time must all be provided together."
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
            raise ValueError("message_id cannot be empty.")

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

    max_messages: int = Field(
        default=20,
        ge=1,
        le=20,
        description=(
            "Maximum number of latest messages to retrieve. "
            "Allowed range: 1-20."
        ),
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
        min_length=1,
        max_length=256,
        description="Gmail message ID containing the attachment. Obtain this from search_emails or get_email_details.",
    )

    attachment_id: str = Field(
        min_length=1,
        max_length=256,
        description="Attachment ID obtained from the attachment metadata returned by get_email_details.",
    )

    @field_validator("message_id", "attachment_id")
    @classmethod
    def validate_ids(cls, value: str) :
        value = value.strip()

        if not value:
            raise ValueError("ID cannot be empty.")

        return value
