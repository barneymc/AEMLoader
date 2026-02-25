# AEM OAuth 2.0 Python Client — Requirements

## Overview

A Python-based client to authenticate with Adobe Experience Manager (AEM) as a Cloud Service
using OAuth 2.0 Client Credentials, and upload PDF files (with metadata) to AEM Assets.
The client runs as a **standalone synchronous Python 3.12 script on a server**.
Ignition (Inductive Automation) triggers it via a shell/system command call — this avoids
all constraints of Ignition's Jython 2.7 scripting engine (no asyncio, limited package support).

---

## 1. Context & Integration

| Item | Detail |
|---|---|
| Host Platform | Standalone Python 3.12 script on a server, triggered by Inductive Automation Ignition via `system.util.execute()` or equivalent shell call |
| Ignition Role | Ignition acts as the orchestrator/scheduler only — it does not run the Python code directly |
| Network Position | Corporate DMZ — accesses AEM Cloud Service externally over the internet |
| AEM Target | AEM as a Cloud Service (AEMaaCS) — Production environment only |

> **Note on Jython:** Ignition's built-in scripting engine uses Jython 2.7, which cannot
> run `asyncio`, and many modern pip packages are incompatible with it. The decision to
> run this client as an external CPython 3.12 process eliminates all of these constraints.

---

## 2. Authentication

### 2.1 Grant Type
- **OAuth 2.0 Client Credentials** (RFC 6749 §4.4)
- No browser/user interaction required — fully server-side
- PKCE is **not required** (not applicable to Client Credentials flow)

### 2.2 How It Works
```
Client Script  →  POST /ims/token/v3  →  Adobe IMS
                  (client_id, client_secret, grant_type, scope)
               ←  { access_token, expires_in }
Client Script  →  POST /api/assets/...  →  AEM Cloud (Bearer token in header)
```

### 2.3 Token Lifecycle
- On startup: check MS SQL token cache table for a valid, non-expired token
- If valid cached token exists: use it
- If missing or expired: request a new token from Adobe IMS, store it in the cache
- **Automatic token refresh** — re-acquire transparently when expired, no script restart needed
- Token revocation is **out of scope** for this version

### 2.4 Token Storage
- Tokens are persisted to an **on-premise MS SQL Server database** attached to the Ignition application
- Only the token value and its expiry timestamp are stored — never credentials
- Table: `aem_token_cache` (see Section 3.2)

### 2.5 OAuth Scopes
- The required scopes are defined by the AEM IMS service account configuration
- A placeholder value `openid,AdobeID,read_organizations` is used for mocking
- **Action required:** obtain the exact scope string from your AEM Cloud administrator
  when connecting to the real environment

---

## 3. Configuration

### 3.1 .env File
All configuration is loaded from a `.env` file at runtime. No hard-coded credentials in source code.

```dotenv
# ── OAuth 2.0 Client Credentials ──────────────────────────────────────────────
AEM_TOKEN_URL=https://ims-na1.adobelogin.com/ims/token/v3
AEM_CLIENT_ID=your-client-id-here
AEM_CLIENT_SECRET=your-client-secret-here
AEM_SCOPE=openid,AdobeID,read_organizations

# ── AEM Upload Target ──────────────────────────────────────────────────────────
AEM_UPLOAD_BASE_URL=https://author-pXXXXX-eYYYYY.adobeaemcloud.com
AEM_ASSETS_DAM_PATH=/api/assets/pdf-uploads

# ── MS SQL Server Token Cache ──────────────────────────────────────────────────
DB_SERVER=localhost
DB_NAME=ignition_db
DB_USER=sa
DB_PASSWORD=your-db-password
DB_TABLE_TOKEN_STORE=aem_token_cache

# ── Mock Mode ──────────────────────────────────────────────────────────────────
AEM_MOCK_MODE=true
```

### 3.2 SQL Token Cache Table Schema
```sql
CREATE TABLE aem_token_cache (
    id          INT           PRIMARY KEY DEFAULT 1,  -- single-row cache
    access_token NVARCHAR(MAX) NOT NULL,
    expires_at  DATETIME2     NOT NULL,
    created_at  DATETIME2     DEFAULT GETDATE()
);
```

---

## 4. AEM Operations

### 4.1 Asset Upload — PDF Files
- Upload PDF binary content to AEM Assets via the **AEM Assets HTTP API**
- Endpoint pattern: `POST {AEM_UPLOAD_BASE_URL}{AEM_ASSETS_DAM_PATH}/{filename}`
- Upload method: `multipart/form-data`
- Authorization header: `Bearer <access_token>`

### 4.2 Metadata
- **Metadata field in scope: `title`** (string)
- The `title` value is passed as a form field alongside the binary in the upload request
- Additional metadata fields can be added in future iterations

### 4.3 CSRF Token Handling
- AEM Cloud requires a CSRF token for all write operations (POST/PUT/PATCH/DELETE)
- Fetch prior to each upload: `GET {AEM_UPLOAD_BASE_URL}/libs/granite/csrf/token.json`
- Include in upload request header: `CSRF-Token: <token>`

### 4.4 DAM Folder
- Target DAM folder: `/content/dam/pdf-uploads/`
- A **sample folder structure and sample PDF** are included in the project for local development
  (see `sample/` directory)

---

## 5. Client Design

### 5.1 Runtime Model
- **Synchronous** Python — no asyncio
- Simple top-to-bottom script execution
- HTTP calls via the `requests` library

### 5.2 Python Version
- **Python 3.12+** (CPython — NOT Jython)

### 5.3 How Ignition Triggers the Script
```
Ignition Gateway Script / Timer
  └─▶ system.util.execute(["python", "C:/aem-client/upload_asset.py",
                            "--file", "C:/pdfs/document.pdf",
                            "--title", "My Document"])
```

### 5.4 Script Structure
```
aem-client/
├── upload_asset.py     ← entry point: parse args, orchestrate upload
├── auth.py             ← OAuth 2.0: acquire, cache, refresh token
├── aem_client.py       ← AEM HTTP ops: CSRF fetch, upload PDF, set metadata
├── db.py               ← MS SQL token persistence (pyodbc)
├── config.py           ← load & validate .env
├── mock.py             ← mock responses for IMS and AEM endpoints
├── sample/
│   └── sample.pdf      ← sample PDF for local development
├── .env                ← configuration (do not commit to source control)
├── .env.example        ← template with placeholder values
└── requirements.txt    ← pip dependencies
```

### 5.5 CLI Interface
```
python upload_asset.py --file <path-to-pdf> --title "<asset title>"
```

---

## 6. Mocking

A mock layer simulates AEM and Adobe IMS endpoints for development without real credentials.

### 6.1 Mocked Endpoints

| Endpoint | Mock Response |
|---|---|
| IMS token endpoint | `{ "access_token": "mock-token-abc123", "expires_in": 30 }` |
| AEM CSRF endpoint | `{ "token": "mock-csrf-token-xyz" }` |
| AEM Assets upload | HTTP 201, `{ "success": true, "path": "/content/dam/pdf-uploads/sample.pdf" }` |

### 6.2 Token Expiry Simulation
- `expires_in: 30` (30 seconds) in the mock token response forces rapid expiry
- Running the script twice within 30 seconds uses the cached token
- Running after 30 seconds triggers the refresh path — confirming that logic works

### 6.3 Toggle
- Set `AEM_MOCK_MODE=true` in `.env` to activate
- A banner is printed at startup: `[MOCK MODE] — no real AEM or IMS calls will be made`

---

## 7. Error Handling

- Simple, human-readable messages printed to stdout/stderr
- Script exits with code `0` on success, `1` on any error

| Error Scenario | Behaviour |
|---|---|
| Missing/invalid `.env` key | Print which key is missing, exit 1 |
| Token acquisition failure | Print HTTP status + body from IMS, exit 1 |
| Token refresh failure | Print error, exit 1 |
| CSRF token fetch failure | Print HTTP status, exit 1 |
| PDF file not found | Print file path, exit 1 |
| AEM upload failure (4xx/5xx) | Print HTTP status + AEM error body, exit 1 |
| SQL DB connection failure | Print connection error, exit 1 |

No retry logic or exponential backoff in this version.

---

## 8. Logging

Simple console output using Python's `logging` module at `INFO` level.

Example output:
```
[INFO]  [MOCK MODE] No real AEM or IMS calls will be made.
[INFO]  Loading config from .env
[INFO]  Token cache: found valid token (expires in 22s), reusing.
[INFO]  Fetching CSRF token...
[INFO]  CSRF token acquired.
[INFO]  Uploading sample.pdf → /api/assets/pdf-uploads/sample.pdf
[INFO]  Upload successful. AEM path: /content/dam/pdf-uploads/sample.pdf
```

---

## 9. Packaging & Distribution

- Delivered as a **collection of Python scripts** — not a pip package
- Dependencies managed via `requirements.txt`:

```
requests>=2.32
python-dotenv>=1.0
pyodbc>=5.1
```

---

## 10. Out of Scope (This Version)

- Token revocation
- Multiple AEM environments (dev/stage)
- PKCE
- Unit or integration tests *(to be added in a future iteration)*
- Retry / backoff logic
- Structured (JSON) logging
- PyPI packaging
- Async / aiohttp

---

## 11. Resolved Decisions

| # | Question | Resolution |
|---|---|---|
| 1 | SQL DB engine | **MS SQL Server** via `pyodbc` |
| 2 | AEM DAM folder path | **/content/dam/pdf-uploads/** — sample PDF included in `sample/` |
| 3 | OAuth scopes | Placeholder `openid,AdobeID,read_organizations` — confirm with AEM admin for production |
| 4 | Metadata fields | **title** only (string) |
| 5 | Jython constraint | **Resolved** — run as external CPython 3.12 process; Ignition calls via shell command |

---

*Document version: 0.2 — 2026-02-25*
