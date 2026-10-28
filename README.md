# Gmail Read-Only MCP Server

A Model Context Protocol (MCP) server that enables AI assistants to securely search, read, and retrieve Gmail messages and download email attachments through structured tools.

Built with Python, the Gmail API, and FastMCP, this project connects an AI assistant to Gmail without exposing the entire mailbox as a single context.

## ✨ Features

- **Email Search** — Search messages using sender, recipient, subject, keywords, date ranges, time ranges, attachment presence, and unread status.
- **Email Details** — Retrieve the full content and metadata of a specific email.
- **Conversation Retrieval** — Fetch messages belonging to a Gmail conversation, including their content and timestamps.
- **Attachment Downloads** — Retrieve email attachments and save them locally.
- **Read-Only OAuth Access** — Uses Gmail's `gmail.readonly` permission scope.
- **Input Validation** — Validate search parameters, dates, times, message IDs, and result limits.
- **Attachment Safety** — Apply filename sanitization, file-size limits, and unique filenames to avoid overwriting existing files.
- **Structured Responses** — Return readable results and structured errors to MCP clients.

## 🛠️ Tech Stack

| Technology | Purpose |
|---|---|
| Python | Core implementation |
| Model Context Protocol (MCP) | Exposes Gmail functionality as tools |
| FastMCP | MCP server and tool registration |
| Gmail API | Email search, retrieval, and attachment access |
| Google OAuth 2.0 | User authentication and authorization |
| `uv` | Python project and dependency management |

## 🧠 Architecture

```text
AI Assistant / MCP Client
          |
          | MCP tool calls
          v
   FastMCP Server
          |
          v
    Tool Functions
          |
     +----+------------------+
     |           |           |
     v           v           v
   Search     Email Read   Attachment
   Service    & Parser     Service
     |           |           |
     +-----------+-----------+
                 |
                 v
             Gmail API
                 |
                 v
            Gmail Account
```

The MCP server exposes a small set of focused tools. The assistant selects the appropriate tool based on the user's request, while the server handles Gmail API operations, parsing, validation, and attachment saving.

## 🔧 Available MCP Tools

### 1. `search_emails`

Search Gmail using supported search conditions.

**Parameters include:**

- `sender`
- `recipient`
- `subject`
- `keyword`
- `start_date`
- `end_date`
- `time_date`
- `start_time`
- `end_time`
- `has_attachment`
- `is_unread`
- `max_results`

The tool returns matching messages and relevant metadata. Date values use `YYYY-MM-DD`, and times use the 24-hour `HH:MM` format.

### 2. `get_email_details`

Retrieve a specific email using its Gmail message ID.

Returns message headers, body text, timestamps, labels, conversation ID, and attachment metadata.

### 3. `get_email_conversation`

Retrieve a Gmail conversation using its thread ID.

Returns the messages in the conversation with their headers, content, timestamps, and attachment metadata.

### 4. `get_attachment`

Retrieve an attachment using its message ID and attachment ID, then save it in the local `downloads/` directory.

The attachment service includes filename sanitization, a default maximum size of 25 MB, and protection against overwriting existing files.

## 📁 Project Structure

```text
gmail-mcp/
├── server.py
├── services/
│   ├── __init__.py
│   ├── auth.py
│   ├── gmail_service.py
│   ├── search.py
│   ├── email_parser.py
│   └── attachment_service.py
├── downloads/
├── credentials.json
├── token.json
├── pyproject.toml
├── uv.lock
├── .gitignore
└── README.md
```

`credentials.json`, `token.json`, and `downloads/` are local runtime files and should not be committed to a public repository.

## 🚀 Getting Started

### Prerequisites

- Python 3.10 or later
- [`uv`](https://docs.astral.sh/uv/)
- A Google account with Gmail
- A Google Cloud project with the Gmail API enabled
- An OAuth client configured for the application

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/gmail-mcp.git
cd gmail-mcp
```

Replace `YOUR_USERNAME` with your GitHub username.

### 2. Install dependencies

If the repository contains `pyproject.toml` and `uv.lock`, run:

```bash
uv sync
```

### 3. Configure Google OAuth

1. Open the [Google Cloud Console](https://console.cloud.google.com/).
2. Create or select a project.
3. Enable the Gmail API.
4. Configure the OAuth consent screen.
5. Create an OAuth client suitable for a local desktop application.
6. Download the OAuth client JSON file and save it locally as `credentials.json`.

The application requests this scope:

```python
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly"
]
```

For an OAuth application in testing mode, your Google account may need to be added as a test user.

**Security:** Never commit OAuth credentials or access tokens. If credentials are exposed, revoke them and rotate them as appropriate.

### 4. Run the MCP server

Run the server from the project root:

```bash
uv run python server.py
```

The server uses the MCP transport configured by FastMCP. For an MCP client that launches local processes, configure it to start this command using the appropriate executable and working directory.

## 🔌 MCP Client Configuration

For an MCP client that supports local STDIO servers, use a configuration similar to the following:

```json
{
  "mcpServers": {
    "gmail-readonly": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "C:\\path\\to\\gmail-mcp",
        "python",
        "server.py"
      ]
    }
  }
}
```

Replace `C:\\path\\to\\gmail-mcp` with the absolute path to your project directory.

Restart or refresh your MCP client after saving the configuration. The exact configuration location depends on the client.

## 🔐 Security

Security is an important part of this project.

- Uses Gmail's read-only OAuth scope.
- Does not expose tools for sending, deleting, or modifying emails.
- Keeps OAuth credentials outside version control.
- Validates tool inputs before performing operations.
- Sanitizes attachment filenames before saving files.
- Limits attachment download size.
- Avoids overwriting files with the same filename.

Email messages and attachments should be treated as untrusted input. An AI assistant should not follow instructions embedded in an email that conflict with its system instructions or the user's actual request.

> Read-only API access limits what this application can do through the authorized Gmail API scope. It does not mean that downloaded email content or local files are automatically safe.


## 🤝 Contributing

Contributions, suggestions, and bug reports are welcome.

1. Fork the repository.
2. Create a feature branch.
3. Make your changes and add tests where appropriate.
4. Submit a pull request describing the changes.

**Written using AI and verified my repo-owner**

**Built with Python, Gmail API, and Model Context Protocol (MCP).**