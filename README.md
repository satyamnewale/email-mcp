# Gmail Read-Only MCP Server

A Model Context Protocol (MCP) server that enables AI assistants to search, read, and retrieve Gmail messages and download email attachments through structured tools.

Built with Python, the Gmail API, and FastMCP, this project provides an agent-friendly interface to Gmail without requiring an AI assistant to load an entire mailbox into its context.

The server exposes focused tools with descriptive input schemas, Pydantic validation, and structured responses. The MCP client or AI agent decides which tool to invoke and supplies its arguments, while the server handles validation, authentication, Gmail API operations, parsing, and attachment management.

## ✨ Features

- **Email Search** — Search messages by sender, recipient, subject, keywords, date ranges, time ranges, attachment presence, and read status.
- **Email Details** — Retrieve the complete content and metadata of a specific email.
- **Conversation Retrieval** — Fetch messages belonging to a Gmail conversation, including content, headers, and timestamps.
- **Attachment Downloads** — Retrieve email attachments and save them locally.
- **Read-Only OAuth Access** — Uses Google's `gmail.readonly` permission scope.
- **Input Validation** — Validate tool arguments using Pydantic, including dates, times, message IDs, and result limits.
- **Agent-Friendly Tool Schemas** — Provide descriptive parameters, types, constraints, defaults, and tool instructions for MCP clients.
- **Attachment Safety** — Sanitize filenames, enforce attachment size limits, and prevent overwriting existing files.
- **Structured Responses** — Return predictable success and error responses to MCP clients.
- **Automated Testing** — Include unit, integration, and contract testing.
- **Continuous Integration** — Run automated checks through GitHub Actions.

## 🛠️ Tech Stack

| Technology | Purpose |
|---|---|
| Python 3.13+ | Core implementation |
| Model Context Protocol (MCP) | Exposes Gmail functionality as tools |
| FastMCP | MCP server and tool registration |
| Gmail API | Email search, retrieval, and attachment access |
| Google OAuth 2.0 | User authentication and authorization |
| Pydantic | Input validation and schema constraints |
| `uv` | Python project and dependency management |
| pytest | Automated testing |
| pytest-cov | Test coverage reporting |
| GitHub Actions | Continuous integration |
| Codex CLI | Local AI coding agent and MCP client |

## 🧠 Architecture

```text
                AI Assistant / MCP Client
                           |
                           | MCP requests
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

                  Supporting Components
                  ---------------------
                  Google OAuth
                  Pydantic Validation
                  Email Parsing
                  Attachment Handling
                  Structured Error Handling
```

### Request Processing

1. The AI assistant receives a user's request.
2. The MCP client selects an appropriate tool and provides its arguments.
3. FastMCP exposes the tool interface and input schema.
4. Pydantic validates and normalizes the received arguments.
5. The tool function calls the appropriate service.
6. The service communicates with the Gmail API.
7. Email content is parsed or attachments are retrieved as required.
8. The server returns a structured response to the MCP client.

The server is independent of any particular agent framework. An external client or orchestration system can consume its tools without requiring LangChain, LangGraph, or another agent framework inside the MCP server.

## 🔧 Available MCP Tools

The server exposes four focused tools.

### 1. `search_emails`

Search Gmail messages using optional filters.

**Supported parameters:**

| Parameter | Type | Description |
|---|---|---|
| `sender` | `str \| None` | Filter by sender name or email address |
| `recipient` | `str \| None` | Filter by recipient |
| `subject` | `str \| None` | Search by full or partial subject |
| `keyword` | `str \| None` | Search by keyword or phrase |
| `start_date` | `str \| None` | Inclusive starting date |
| `end_date` | `str \| None` | Inclusive ending date |
| `time_date` | `str \| None` | Date for a time-based search |
| `start_time` | `str \| None` | Starting time |
| `end_time` | `str \| None` | Ending time |
| `has_attachment` | `bool \| None` | Filter by attachment presence |
| `is_unread` | `bool \| None` | Filter by read status |
| `max_results` | `int` | Number of results, from 1 to 50; default 10 |
| `page_token` | `str \| None` | Token for continuing a previous search |

**Date and time formats:**

- Dates: `YYYY-MM-DD`
- Times: `HH:MM` using the 24-hour format.

**Search behavior:**

- Multiple supplied filters are combined.
- When no filters are supplied, the tool returns the most recent emails.
- Time-based searches require `time_date`, `start_time`, and `end_time` together.
- Time ranges crossing midnight are supported.
- Pagination uses the `next_page_token` returned by a previous search.
- The server uses its configured local timezone for time-based searches.

**Response includes:**

- Email message IDs
- Conversation/thread IDs
- Sender and recipient
- Subject
- Date
- Snippet
- Attachment presence
- Labels
- Result count and estimated matching count
- Search query and timezone
- Next pagination token

The search tool returns email metadata rather than complete email bodies. Use `get_email_details` or `get_email_conversation` to retrieve full content.

### 2. `get_email_details`

Retrieve a specific email using its Gmail message ID.

Returns:

- Message ID and conversation ID
- Sender and recipient
- Subject and date
- Email body
- Labels
- Attachment metadata

### 3. `get_email_conversation`

Retrieve a Gmail conversation using its thread ID.

Returns the messages belonging to the conversation, including their headers, content, timestamps, and attachment metadata.

### 4. `get_attachment`

Retrieve an email attachment using:

- `message_id`
- `attachment_id`

The attachment is saved locally in the configured download directory.

**Attachment safeguards:**

- Filename sanitization
- Default maximum attachment size of 25 MB
- Validation of decoded attachment size
- Unique filename generation
- Prevention of accidental overwrites

## 📁 Project Structure

```text
email-mcp/
│
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
├── validator/
│   ├── __init__.py
│   └── pydantic_class.py
│
├── tests/
│   ├── unit/
│   │   ├── test_auth.py
│   │   ├── test_attachment_service.py
│   │   ├── test_email_parser.py
│   │   ├── test_gmail_service.py
│   │   ├── test_search.py
│   │   └── test_validators.py
│   │
│   ├── integration/
│   │   └── test_mcp_tools.py
│   │
│   └── contracts/
│       └── test_tool_contracts.py
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── downloads/               # Runtime attachment downloads
├── credentials.json         # Local OAuth client credentials
├── token.json               # Local OAuth token
│
├── pyproject.toml
├── uv.lock
├── .gitignore
└── README.md
```

The `tests/contracts/` directory is the planned location for MCP tool contract tests. Create it and add the contract test module before enabling that CI stage.

**Important:** `credentials.json`, `token.json`, and downloaded attachments are local runtime files. They must not be committed to a public repository.

## 🚀 Getting Started

### Prerequisites

- Python 3.13 or later
- [`uv`](https://docs.astral.sh/uv/)
- Git
- A Google account with Gmail
- A Google Cloud project with Gmail API enabled
- An OAuth client configured for a local desktop application

### 1. Clone the Repository

```bash
git clone https://github.com/satyamnewale/email-mcp.git
cd email-mcp
```

### 2. Create a Virtual Environment

```bash
uv venv
```

Activate it in PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

Install the project dependencies using the existing lockfile:

```bash
uv sync --locked
```

To install development dependencies, including testing tools:

```bash
uv sync --locked --group dev
```

## ☁️ Google Cloud Setup

The Gmail MCP server uses Google OAuth 2.0 to authorize access to a Gmail account.

### 1. Create a Google Cloud Project

1. Open the [Google Cloud Console](https://console.cloud.google.com/).
2. Create or select a project.
3. Navigate to **APIs & Services**.
4. Open **Library**.
5. Search for **Gmail API**.
6. Enable the Gmail API.

### 2. Configure the OAuth Consent Screen

1. Open [Google Auth Platform](https://console.cloud.google.com/auth).
2. Configure the application information.
3. Select the appropriate audience.
4. Configure the OAuth consent screen.
5. Add test users if the application is in testing mode.

### 3. Create OAuth Credentials

1. Navigate to the OAuth client configuration.
2. Create an OAuth client suitable for a local desktop application.
3. Download the OAuth client JSON file.
4. Save the file in the project's root directory as `credentials.json`.

The application requests the following OAuth scope:

```python
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly"
]
```

For an OAuth application in testing mode, the Gmail account used for authorization may need to be added as a test user.

**Security:** Never commit OAuth credentials or access tokens. Revoke and rotate exposed credentials if they are accidentally published.

## 🔐 Google OAuth Authentication

The project uses two local files for Google authentication.

| File | Purpose |
|---|---|
| `credentials.json` | OAuth client credentials downloaded from Google Cloud Console |
| `token.json` | Authentication token generated after successful authorization |

### Authentication Flow

1. The MCP server starts.
2. The authentication module checks for an existing token.
3. If a valid token exists, it is reused.
4. If the token is expired, the refresh flow is attempted where possible.
5. If authorization is required, the OAuth flow is initiated.
6. After successful authorization, the token is saved locally.
7. The authenticated credentials are used for Gmail API requests.

Each user should authorize access through their own Google account. For an OAuth application in testing mode, the account must be included in the configured test users.

## ▶️ Running the MCP Server

Run the server from the project root:

```powershell
uv run fastmcp run server.py --transport stdio
```

The server uses **STDIO transport**.

An MCP client launches the local server process and communicates with it through standard input and output.

The server is designed to be launched by an MCP client rather than used as a standalone email application.

## 🔌 Codex Integration

OpenAI Codex is an AI coding agent that supports MCP servers. It can discover and invoke the Gmail MCP tools when configured as a local MCP server.

### 1. Install Codex CLI

Follow the official installation instructions:

[Codex CLI Installation](https://developers.openai.com/codex/cli/)

Alternatively, install using npm when Node.js and npm are available:

```powershell
npm install -g @openai/codex
```

Verify the installation:

```powershell
codex --version
```

### 2. Register the Gmail MCP Server

Register the local Gmail MCP server using the Codex CLI:

```powershell
codex mcp add gmail_readonly_mcp -- "PATH_TO_UV_EXE" run --directory "PATH_TO_EMAIL_MCP" fastmcp run server.py --transport stdio
```

Replace:

- `PATH_TO_UV_EXE` with the absolute path to `uv.exe`.
- `PATH_TO_EMAIL_MCP` with the absolute path to your Gmail MCP project directory.

This configuration allows Codex to launch the FastMCP server locally using STDIO transport.

### 3. Verify the MCP Connection

```powershell
codex mcp list
```

The registered Gmail MCP server should appear in the list.

Navigate to the project directory and start Codex:

```powershell
cd PATH_TO_EMAIL_MCP
codex
```

Codex can now discover the registered Gmail MCP tools and invoke them when appropriate.

### 4. Example Instructions

```text
Find the five most recent emails from a particular sender.
```

```text
Search for emails containing a specified keyword.
```

```text
Find unread emails with attachments.
```

```text
Retrieve the complete details of a particular email.
```

```text
Show all messages belonging to a specific email conversation.
```

```text
Download an attachment from a selected email.
```

## 💻 ChatGPT for Windows

ChatGPT for Windows can be used alongside Codex during development.

Download the application:

[ChatGPT for Windows](https://chatgpt.com/download/)

ChatGPT can assist with:

- Understanding the project architecture.
- Explaining FastMCP and MCP concepts.
- Reviewing Python code.
- Debugging authentication and API errors.
- Understanding Gmail API operations.
- Improving documentation.
- Planning additional MCP tools.
- Reviewing test cases and CI failures.

You can provide relevant source files, code, or error logs when asking questions.

**Note:** Installing the ChatGPT Windows application does not automatically connect it to the local Gmail MCP server. The local MCP integration described in this README is configured through Codex. Direct ChatGPT MCP integration requires a separately supported connection and configuration.

## 🧪 Testing

The project uses pytest for automated testing.

Three categories of tests are intended to validate different parts of the application.

| Test category | Responsibility |
|---|---|
| Unit tests | Validate individual services, parsers, utilities, and Pydantic models |
| Integration tests | Validate MCP tool execution and interactions between server components |
| Contract tests | Validate the MCP tool interface, input schemas, names, descriptions, and expected response structures |

Install the development dependencies:

```powershell
uv sync --locked --group dev
```

### 1. Run Unit Tests

```powershell
uv run pytest tests/unit -m unit -v
```

Unit tests cover:

- OAuth authentication behavior using mocks
- Gmail service operations
- Search query construction
- Date and time filtering
- Email parsing
- Attachment handling
- Filename sanitization
- Pydantic input validation

### 2. Run Integration Tests

```powershell
uv run pytest tests/integration -m integration -v
```

Integration tests verify how the MCP tools and their supporting components work together.

External Gmail API calls should be mocked so tests do not depend on a real Gmail account or OAuth credentials.

### 3. Run Contract Tests

```powershell
uv run pytest tests/contracts -m contract -v
```

Contract tests verify the interface exposed to MCP clients.

They should cover:

- Expected tool registration
- Tool names
- Parameter names and types
- Required and optional parameters
- Default values
- Parameter descriptions
- Input constraints
- Validation behavior
- Response structure

### 4. Run the Complete Test Suite

```powershell
uv run pytest -v
```

### 5. Generate a Coverage Report

```powershell
uv run pytest --cov=server --cov=services --cov=validator --cov-report=term-missing --cov-report=xml
```

The command generates:

- Terminal coverage summary
- `coverage.xml` report

The coverage report helps identify untested code paths and areas that need additional tests.

## ⚙️ Continuous Integration

The repository uses GitHub Actions to automatically run tests.

Workflow file:

```text
.github/workflows/ci.yml
```

### CI Workflow

The workflow is configured to run on pushes and pull requests targeting the `main` and `trial` branches.

The pipeline performs the following operations:

1. Checks out the repository.
2. Installs `uv`.
3. Sets up Python 3.13.
4. Installs locked project and development dependencies.
5. Runs unit tests.
6. Runs integration tests.
7. Runs contract tests.
8. Runs the complete test suite with coverage.
9. Uploads the coverage report as a GitHub Actions artifact.

### CI Test Commands

```bash
uv run pytest tests/unit -m unit
uv run pytest tests/integration -m integration
uv run pytest tests/contracts -m contract
```

The contract test directory and corresponding tests must exist before this stage can pass.

The complete test suite is also executed to ensure that tests from different categories work together.

**CI does not require a real Gmail account or OAuth credentials when external Gmail operations are properly mocked in tests.**

## 🔐 Security

Security is an important part of this project.

- Uses Gmail's read-only OAuth scope.
- Does not expose tools for sending, deleting, or modifying emails.
- Keeps OAuth credentials outside version control.
- Validates tool inputs before performing operations.
- Sanitizes attachment filenames before saving files.
- Enforces attachment download size limits.
- Prevents overwriting existing files.
- Returns structured errors to MCP clients.

Ensure that `.gitignore` includes:

```gitignore
# Python environment
.venv/

# Python cache
__pycache__/
*.py[cod]

# Testing cache and reports
.pytest_cache/
.coverage
.coverage.*
coverage.xml
htmlcov/

# Google OAuth credentials
credentials.json
token.json

# Downloaded attachments
downloads/

# Environment variables
.env
.env.*
```

Email messages and attachments should be treated as untrusted input. An AI assistant should not follow instructions embedded in an email that conflict with its system instructions or the user's actual request.

> Read-only API access limits what this application can do through the authorized Gmail API scope. It does not mean that downloaded email content or local files are automatically safe.

## 🤝 Contributing

Contributions, suggestions, and bug reports are welcome.

1. Fork the repository.
2. Create a feature branch.
3. Make your changes.
4. Add or update tests where appropriate.
5. Run the test suite.
6. Submit a pull request describing your changes.

Please avoid committing OAuth credentials, access tokens, downloaded attachments, or other sensitive data.

## 📝 Project Note

This project was developed with the assistance of AI tools. The code and documentation are reviewed by the repository owner.

---

**Built with Python, Gmail API, Pydantic, and Model Context Protocol (MCP).**