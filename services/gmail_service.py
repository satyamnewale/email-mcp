from googleapiclient.errors import HttpError

def list_messages(service, query=None, max_results=10, page_token=None, label_ids=None):
    """List matching emails and return their IDs and thread IDs."""
    try:
        params = {
            "userId": "me",
            "maxResults": max_results,
        }

        if query:
            params["q"] = query

        if page_token:
            params["pageToken"] = page_token

        if label_ids:
            params["labelIds"] = label_ids

        response = service.users().messages().list(**params).execute()

        return {
            "messages": response.get("messages", []),
            "next_page_token": response.get("nextPageToken"),
            "resultSizeEstimate": response.get("resultSizeEstimate", 0),
        }

    except HttpError as err:
        raise

def get_message(service, message_id, format="full"):

    try:
        return(
            service.users()
            .messages()
            .get(
                userId = "me",
                id = message_id,
                format = format
            ).execute()
        )
    except HttpError as err:
        raise

def get_thread( service, thread_id, format="full"):
    try:
        return(
            service.users()
            .threads()
            .get(
                userId = "me",
                id = thread_id,
                format = format
            ).execute()
        )
    except HttpError as err:
        raise

def get_attachment_data(service, message_id, attachment_id):
    try :
        return(
            service.users()
            .messages()
            .attachments()
            .get(
                userId = "me",
                messageId = message_id,
                id = attachment_id
            ).execute()
        )
    except HttpError as err:
        raise