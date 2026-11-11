import re
from datetime import date, datetime, time, timedelta

from tzlocal import get_localzone


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


# --------------------------------------------------
# TIMEZONE
# --------------------------------------------------

def get_user_timezone():
    """Return the timezone configured on the MCP server machine."""
    return get_localzone()


def local_datetime_to_timestamp(local_datetime):
    """Convert a naive local datetime to a Unix timestamp."""

    timezone = get_user_timezone()
    aware_datetime = local_datetime.replace(tzinfo=timezone)

    return int(aware_datetime.timestamp())


# --------------------------------------------------
# SEARCH INPUT VALIDATION
# --------------------------------------------------

def _validate_identity(value, field_name):
    if value is None:
        return None

    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string.")

    value = value.strip()

    if not value:
        raise ValueError(f"{field_name} cannot be empty.")

    if EMAIL_PATTERN.fullmatch(value):
        return value

    if DISPLAY_NAME_PATTERN.fullmatch(value):
        return value

    raise ValueError(
        f"{field_name} must be a valid email address or simple display name. "
        "Gmail search operators are not allowed."
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


def _quote_phrase(value):
    """Quote a validated literal phrase for Gmail search."""
    return f'"{value}"'

MAX_KEYWORD_OR_TERMS = 5

def _build_keyword_query(keyword: str | None) -> str:
    """
    Build a safe Gmail keyword query.

    Examples:
        invoice
            -> "invoice"

        invoice OR payment receipt
            -> { "invoice" "payment receipt" }

        project OR meeting OR demo
            -> { "project" "meeting" "demo" }

    Only literal phrases are accepted as alternatives.
    Gmail search operators cannot be injected through a keyword.
    """

    if keyword is None:
        return ""

    alternatives = re.split(
        r"\s+OR\s+",
        keyword,
        flags=re.IGNORECASE,
    )

    if len(alternatives) > MAX_KEYWORD_OR_TERMS:
        raise ValueError(
            f"A keyword search can contain at most "
            f"{MAX_KEYWORD_OR_TERMS} OR alternatives."
        )

    validated_terms = []

    for term in alternatives:

        term = _validate_literal_phrase(
            term,
            "keyword",
        )

        validated_terms.append(term)

    quoted_terms = [
        _quote_phrase(term)
        for term in validated_terms
    ]

    if len(quoted_terms) == 1:
        return quoted_terms[0]

    return "{ " + " ".join(quoted_terms) + " }"

# --------------------------------------------------
# BUILD SENDER / RECIPIENT / SUBJECT QUERY
# --------------------------------------------------

def build_search_query(
    sender=None,
    recipient=None,
    subject=None,
    keyword=None,
    has_attachment=None,
    is_unread=None,
):
    """Build a Gmail query using validated user input."""

    query_parts = []

    sender = _validate_identity(sender, "sender")
    recipient = _validate_identity(recipient, "recipient")
    subject = _validate_literal_phrase(subject, "subject")

    if sender:
        if EMAIL_PATTERN.fullmatch(sender):
            query_parts.append(f"from:{sender}")
        else:
            query_parts.append(f"from:{_quote_phrase(sender)}")

    if recipient:
        if EMAIL_PATTERN.fullmatch(recipient):
            query_parts.append(f"to:{recipient}")
        else:
            query_parts.append(f"to:{_quote_phrase(recipient)}")

    if subject:
        query_parts.append(f"subject:{_quote_phrase(subject)}")

    keyword_query = _build_keyword_query(keyword)

    if keyword_query:
        query_parts.append(keyword_query)

    if has_attachment is True:
        query_parts.append("has:attachment")
    elif has_attachment is False:
        query_parts.append("-has:attachment")

    if is_unread is True:
        query_parts.append("is:unread")
    elif is_unread is False:
        query_parts.append("is:read")

    return " ".join(query_parts)


# --------------------------------------------------
# BUILD DATE-RANGE QUERY
# --------------------------------------------------

def build_date_query(start_date=None, end_date=None):
    """
    Build a Gmail date query using the local timezone.

    Both dates are inclusive calendar dates.
    """

    query_parts = []
    timezone = get_user_timezone()

    if start_date:
        first_day = date.fromisoformat(start_date)

        start_dt = datetime.combine(
            first_day,
            time.min,
            tzinfo=timezone,
        )

        start_timestamp = int(start_dt.timestamp()) - 1

        query_parts.append(f"after:{start_timestamp}")

    if end_date:
        last_day = date.fromisoformat(end_date)
        next_day = last_day + timedelta(days=1)

        end_dt = datetime.combine(
            next_day,
            time.min,
            tzinfo=timezone,
        )

        end_timestamp = int(end_dt.timestamp())

        query_parts.append(f"before:{end_timestamp}")

    return " ".join(query_parts)


# --------------------------------------------------
# BUILD TIME-RANGE QUERY
# --------------------------------------------------

def build_time_query(
    start_date,
    start_time,
    end_time,
):
    """
    Build a local-time query for one date.

    If end_time is earlier than or equal to start_time,
    the range is treated as crossing midnight.
    """

    timezone = get_user_timezone()
    local_day = date.fromisoformat(start_date)

    start_clock = time.fromisoformat(start_time)
    end_clock = time.fromisoformat(end_time)

    start_dt = datetime.combine(
        local_day,
        start_clock,
        tzinfo=timezone,
    )

    end_dt = datetime.combine(
        local_day,
        end_clock,
        tzinfo=timezone,
    )

    if end_dt <= start_dt:
        end_dt += timedelta(days=1)

    start_timestamp = int(start_dt.timestamp()) - 1
    end_timestamp = int(end_dt.timestamp())

    return f"after:{start_timestamp} before:{end_timestamp}"


# --------------------------------------------------
# SEARCH EMAILS
# --------------------------------------------------

def search_emails(
    service,
    sender=None,
    recipient=None,
    subject=None,
    keyword=None,
    date_filters=None,
    attachment_filters=None,
    time_filters=None,
    max_results=500,
    page_token=None,
):
    """
    Search Gmail using validated filters.

    User-provided text filters are inserted as literal phrases,
    not unrestricted Gmail search syntax.
    """

    if isinstance(max_results, bool) or not isinstance(max_results, int):
        raise ValueError("max_results must be an integer.")

    max_results = min(max(1, max_results), 500)

    query_parts = []

    text_query = build_search_query(
        sender=sender,
        recipient=recipient,
        subject=subject,
        keyword=keyword,
        has_attachment=(
            attachment_filters.get("hasAttachment")
            if attachment_filters else None
        ),
        is_unread=(
            attachment_filters.get("isUnread")
            if attachment_filters else None
        ),
    )

    if text_query:
        query_parts.append(text_query)

    # Date range
    if date_filters:
        date_query = build_date_query(
            start_date=date_filters.get("after"),
            end_date=date_filters.get("before"),
        )

        if date_query:
            query_parts.append(date_query)

    # Time range
    if time_filters:
        time_query = build_time_query(
            start_date=time_filters["date"],
            start_time=time_filters["start_time"],
            end_time=time_filters["end_time"],
        )

        query_parts.append(time_query)

    query = " ".join(query_parts).strip()

    params = {
        "userId": "me",
        "maxResults": max_results,
    }

    if query:
        params["q"] = query

    if page_token:
        if not isinstance(page_token, str) or not page_token.strip():
            raise ValueError("Invalid page_token.")

        params["pageToken"] = page_token.strip()

    response = (
        service.users()
        .messages()
        .list(**params)
        .execute()
    )

    return {
        "messages": response.get("messages", []),
        "next_page_token": response.get("nextPageToken"),
        "result_size_estimate": response.get("resultSizeEstimate", 0),
        "query": query,
        "timezone": str(get_user_timezone()),
    }