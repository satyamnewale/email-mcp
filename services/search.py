
from datetime import datetime, date, time, timedelta
from tzlocal import get_localzone
from googleapiclient.errors import HttpError


# --------------------------------------------------
# 1. TIMEZONE
# --------------------------------------------------

def get_user_timezone():
    """
    Detect the timezone configured on the machine
    running this MCP server.
    """
    return get_localzone()


# --------------------------------------------------
# 2. CONVERT LOCAL DATE/TIME TO UNIX TIMESTAMP
# --------------------------------------------------

def local_datetime_to_timestamp(local_datetime):
    """
    Convert a naive local datetime into a Unix timestamp.
    The machine's detected timezone is applied automatically.
    """
    timezone = get_user_timezone()
    aware_datetime = local_datetime.replace(tzinfo=timezone)

    return int(aware_datetime.timestamp())


# --------------------------------------------------
# 3. BUILD SENDER / RECIPIENT / SUBJECT QUERY
# --------------------------------------------------

def build_search_query(
    sender=None,
    recipient=None,
    subject=None,
    keyword=None,
    has_attachment=None,
    is_unread=None,
):
    """Build a Gmail-compatible search query."""

    query_parts = []

    if sender:
        query_parts.append(f"from:{sender}")

    if recipient:
        query_parts.append(f"to:{recipient}")

    if subject:
        query_parts.append(f"subject:{subject}")

    if keyword:
        query_parts.append(keyword)

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
# 4. BUILD DATE-RANGE QUERY
# --------------------------------------------------

def build_date_query(start_date=None, end_date=None):
    """
    Build a date query using the machine's local timezone.

    Input format: YYYY-MM-DD
    Both start_date and end_date are inclusive calendar dates.
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

        # Subtract one second to include the start boundary.
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

        # before: excludes the next day's midnight.
        query_parts.append(f"before:{end_timestamp}")

    return " ".join(query_parts)


# --------------------------------------------------
# 5. BUILD TIME-RANGE QUERY
# --------------------------------------------------

def build_time_query(
    start_date,
    start_time,
    end_time,
):
    """
    Build a local-time query for one date.

    Date format: YYYY-MM-DD
    Time format: HH:MM (24-hour clock)

    If end_time is earlier than or equal to start_time,
    the interval is treated as crossing midnight.
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

    # Example: 22:00 to 02:00 means the next day at 02:00.
    if end_dt <= start_dt:
        end_dt += timedelta(days=1)

    start_timestamp = int(start_dt.timestamp()) - 1
    end_timestamp = int(end_dt.timestamp())

    return (
        f"after:{start_timestamp} "
        f"before:{end_timestamp}"
    )


# --------------------------------------------------
# 6. SEARCH EMAILS
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
    Search emails using Gmail search operators.

    date_filters example:
        {
            "after": "2026-10-23",
            "before": "2026-10-25"
        }

    time_filters example:
        {
            "date": "2026-10-23",
            "start_time": "08:00",
            "end_time": "12:00"
        }
    """

    try:
        query_parts = []

        max_results = min(max(1, max_results), 500)

        # Sender, recipient, subject and keyword.
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

        # Date range.
        if date_filters:
            date_query = build_date_query(
                start_date=date_filters.get("after"),
                end_date=date_filters.get("before"),
            )

            if date_query:
                query_parts.append(date_query)

        # Specific time range on a particular date.
        if time_filters:
            time_query = build_time_query(
                start_date=time_filters["date"],
                start_time=time_filters["start_time"],
                end_time=time_filters["end_time"],
            )

            query_parts.append(time_query)

        # Gmail accepts search conditions through one q parameter.
        params = {
            "userId": "me",
            "maxResults": max_results,
        }

        query = " ".join(query_parts).strip()

        if query:
            params["q"] = query

        if page_token:
            params["pageToken"] = page_token

        response = (
            service.users()
            .messages()
            .list(**params)
            .execute()
        )

        return {
            "messages": response.get("messages", []),
            "next_page_token": response.get("nextPageToken"),
            "result_size_estimate": response.get(
                "resultSizeEstimate", 0
            ),
            "query": params.get("q", ""),
            "timezone": str(get_user_timezone()),
        }

    except HttpError as err:
        raise