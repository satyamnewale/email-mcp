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
| Codex CLI | AI assistant and local MCP client |

## 🧠 Architecture

```text
         AI Assistant / MCP Client
                    |
                    | MCP tool calls
                    v
              FastMCP Server
                 server.py
                    |
                    v
               Tool Functions
                    |
       +------------+-------------+
       |            |             |
       v            v             v
    Search       Email Read    Attachment
    Service      & Parser      Service
       |            |             |
       +------------+-------------+
                    |
                    v
                 Gmail API
                    |
                    v
                Gmail Account

           Supporting Components:
           - Google OAuth
           - Input Validation
           - Email Parsing
           - Attachment Handling
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
│
├── services/
│   ├── __init__.py
│   ├── auth.py
│   ├── gmail_service.py
│   ├── search.py
│   ├── email_parser.py
│   └── attachment_service.py
│
├── downloads/
│
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
- Git
- A Google account with Gmail
- A Google Cloud project with the Gmail API enabled
- An OAuth client configured for the application

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/gmail-mcp.git
cd gmail-mcp
```

Replace `YOUR_USERNAME` with your GitHub username.

### 2. Create the Virtual Environment

```bash
uv venv
```

Activate the environment in PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

If the repository contains `pyproject.toml` and `uv.lock`, run:

```bash
uv sync
```

## ☁️ Google Cloud Setup

### 1. Create a Google Cloud Project

1. Open the [Google Cloud Console](https://console.cloud.google.com/).
2. Create or select a project.
3. Navigate to **APIs & Services**.
4. Open **Library**.
5. Search for **Gmail API**.
6. Enable the API.

### 2. Configure OAuth Consent Screen

1. Open Google Auth Platform.
2. Configure the application information.
3. Select the appropriate audience.
4. Configure the required OAuth permissions.
5. Add test users if the application is in testing mode.

### 3. Create OAuth Credentials

1. Navigate to the OAuth client configuration.
2. Create an OAuth client suitable for a local desktop application.
3. Download the OAuth client JSON file.
4. Save it in the project root as `credentials.json`.

The application requests the following scope:

```python
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly"
]
```

For an OAuth application in testing mode, your Google account may need to be added as a test user.

**Security:** Never commit OAuth credentials or access tokens. If credentials are exposed, revoke them and rotate them as appropriate.

## 🔐 Google OAuth Authentication

The project uses two files for Google authentication:

| File | Purpose |
|---|---|
| `credentials.json` | Contains the OAuth client credentials downloaded from Google Cloud Console |
| `token.json` | Stores the authentication token generated after successful authorization |

### Authentication Flow

1. The MCP server starts.
2. The authentication module checks for an existing token.
3. If a valid token exists, it is reused.
4. Otherwise, the OAuth authorization flow is initiated.
5. After successful authorization, the token is generated and saved.
6. The authenticated credentials are used to access the Gmail API.

Each user should authorize the application using their own Google account. For an OAuth application in testing mode, the account must be added as a test user.

## ▶️ Running the MCP Server

Run the server from the project root:

```powershell
uv run fastmcp run server.py --transport stdio
```

The server uses STDIO transport. An MCP client can launch the local server process and communicate with it through standard input and output.

**Note:** The command above is intended for the FastMCP CLI execution setup used by this project.

## 🔌 Codex Integration

OpenAI Codex is an AI coding agent that can connect to external MCP servers and use their tools while working with a project.

### 1. Install Codex CLI

On Windows, open PowerShell and use the official installation instructions:

https://developers.openai.com/codex/cli/

Alternatively, install through npm if Node.js and npm are available:

```powershell
npm install -g @openai/codex
```

Verify the installation:

```powershell
codex --version
```

### 2. Register the Gmail MCP Server

Codex supports registering local MCP servers through its CLI.

Use the following command in PowerShell:

```powershell
codex mcp add gmail_readonly_mcp -- "PATH_TO_UV_EXE" run --directory "PATH_TO_GMAIL_MCP" fastmcp run server.py --transport stdio
```

Replace:

- `PATH_TO_UV_EXE` with the absolute path to your `uv.exe`.
- `PATH_TO_GMAIL_MCP` with the absolute path to your Gmail MCP project directory.

This configuration allows Codex to launch the FastMCP server locally using STDIO transport.

### 3. Verify the MCP Connection

```powershell
codex mcp list
```

The registered Gmail MCP server should appear in the list.

Navigate to the project directory and start Codex:

```powershell
cd PATH_TO_GMAIL_MCP
codex
```

Codex can now discover the registered Gmail MCP tools and invoke them when appropriate.

### 4. Example Instructions

```text
Find recent emails from a particular sender.
```

```text
Search for emails containing a specified keyword.
```

```text
Retrieve the complete details of a particular email.
```

```text
Show the messages belonging to a specific email conversation.
```

```text
Download an attachment from a selected email.
```

## 💻 ChatGPT for Windows

ChatGPT for Windows can be used alongside Codex during development.

Download the application:

https://chatgpt.com/download/

ChatGPT can assist with:

- Understanding the project architecture.
- Explaining FastMCP and MCP concepts.
- Reviewing Python code.
- Debugging authentication and API errors.
- Understanding Gmail API operations.
- Improving documentation.
- Planning additional MCP tools.

You can provide relevant source files, code, or error logs when asking questions.

**Note:** Installing the ChatGPT Windows application does not automatically connect it to the local Gmail MCP server. The local MCP integration described in this README is configured through Codex. Direct ChatGPT MCP integration requires a separately supported connection and configuration.

## 🔐 Security

Security is an important part of this project.

- Uses Gmail's read-only OAuth scope.
- Does not expose tools for sending, deleting, or modifying emails.
- Keeps OAuth credentials outside version control.
- Validates tool inputs before performing operations.
- Sanitizes attachment filenames before saving files.
- Limits attachment download size.
- Avoids overwriting files with the same filename.

Ensure that `.gitignore` includes:

```gitignore
# Python environment
.venv/

# Python cache
__pycache__/
*.py[cod]

# Testing cache
.pytest_cache/

# Google OAuth credentials
credentials.json
token.json

# Downloaded attachments
downloads/

# Environment variables
.env
```

Email messages and attachments should be treated as untrusted input. An AI assistant should not follow instructions embedded in an email that conflict with its system instructions or the user's actual request.

> Read-only API access limits what this application can do through the authorized Gmail API scope. It does not mean that downloaded email content or local files are automatically safe.

## 🤝 Contributing

Contributions, suggestions, and bug reports are welcome.

1. Fork the repository.
2. Create a feature branch.
3. Make your changes and add tests where appropriate.
4. Submit a pull request describing the changes.

**Written using AI and reviewed by the repository owner.**

**Built with Python, Gmail API, and Model Context Protocol (MCP).