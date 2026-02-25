# AEM PDF Upload Client

A client that authenticates with **Adobe Experience Manager (AEM) as a Cloud Service**
using OAuth 2.0 and uploads PDF files with metadata to the AEM Digital Asset Manager (DAM).

Two implementations are provided — choose based on your environment:

| | Standalone (root folder) | Ignition Native ([IgnitionVersion/](IgnitionVersion/)) |
|---|---|---|
| Runtime | CPython 3.12 — external process | Jython 2.7 — inside Ignition 8.1 |
| Trigger | Windows Task Scheduler or `system.util.execute()` | Gateway Timer Event Script |
| Config | `.env` file | Ignition Tags |
| HTTP client | `requests` library | `system.net.*` + Java `HttpURLConnection` |
| Token cache | `pyodbc` | `system.db.*` — named DB connection |
| Python install needed | Yes | No |

---

## What This Does

```
Windows Server (DMZ)
│
├── Option A — Standalone
│   └── upload_asset.py --file document.pdf --title "My Doc"
│           ├─▶  Authenticates with Adobe IMS (OAuth 2.0 Client Credentials)
│           ├─▶  Caches the access token in MS SQL Server
│           ├─▶  Fetches a CSRF token from AEM
│           └─▶  Uploads the PDF + metadata to AEM Assets DAM
│
└── Option B — Ignition Native
    └── gateway_timer_script.py  (runs inside Ignition 8.1)
            ├─▶  Authenticates with Adobe IMS via system.net.httpPost()
            ├─▶  Caches the token via system.db.*
            ├─▶  Fetches a CSRF token from AEM
            └─▶  Uploads the PDF via Java HttpURLConnection
```

---

## How OAuth 2.0 Works Here

This client uses the **Client Credentials** grant — a fully automated, server-side OAuth flow
with no browser or user interaction required.

```
                    ┌─────────────────────┐
                    │   Adobe IMS          │
                    │  (Identity Server)   │
                    └─────────────────────┘
                              ▲
  1. POST /ims/token/v3       │   2. Returns access_token
     client_id                │      + expires_in
     client_secret            │
     grant_type=client_creds  │
                              │
                    ┌─────────────────────┐
                    │   This Script        │
                    │   (DMZ Server)       │
                    └─────────────────────┘
                              │
  3. POST /api/assets/...     │
     Authorization: Bearer    │
     CSRF-Token: <token>      ▼
                    ┌─────────────────────┐
                    │   AEM Cloud          │
                    │   (Assets DAM)       │
                    └─────────────────────┘
```

**Token caching:** The access token is stored in MS SQL Server and reused until it expires,
avoiding a round-trip to Adobe IMS on every upload. It is refreshed automatically when expired.

**The OAuth flow is identical in both implementations.** The endpoints, request format, and
token lifecycle logic are the same — only the underlying API calls differ:

| Step | Standalone | Ignition Native |
|---|---|---|
| Make the token POST | `requests.post()` | `system.net.httpPost()` |
| Store the token | `pyodbc` → SQL | `system.db.runPrepUpdate()` → SQL |
| Read cached token | `pyodbc` → SQL | `system.db.runQuery()` → SQL |
| Check expiry | Python `datetime` | `system.date.toMillis()` |
| Make the upload POST | `requests.post()` multipart | Java `HttpURLConnection` multipart |

> [auth.py](auth.py) and [IgnitionVersion/aem_auth.py](IgnitionVersion/aem_auth.py) are direct
> translations of each other — same logic, just different API calls. Any change to the OAuth
> flow must be made in both files.

---

## Call Chain

**Standalone:**
```
upload_asset.py              ← entry point (run this)
    │
    ├─▶ auth.get_valid_token()           ← auth.py handles all OAuth logic
    │       │
    │       ├─▶ aem_mock.mock_fetch_token()    (mock mode — no real calls)
    │       │         or
    │       ├─▶ db.load_token()               (check SQL cache for valid token)
    │       └─▶ POST /ims/token/v3            (real IMS call if missing/expired)
    │               └─▶ db.save_token()       (cache result in SQL)
    │
    └─▶ aem_client.upload_pdf()          ← aem_client.py handles AEM operations
            │
            ├─▶ GET  /libs/granite/csrf/token.json   (fetch CSRF token)
            └─▶ POST /api/assets/pdf-uploads/<file>  (upload PDF + title metadata)
```

**Ignition Native:**
```
gateway_timer_script.py      ← Gateway Timer Event Script
    │
    ├─▶ aem_auth.get_valid_token()       ← Project Library script
    │       │
    │       ├─▶ system.db.runQuery()          (check SQL cache)
    │       └─▶ system.net.httpPost()         (IMS call if missing/expired)
    │               └─▶ system.db.runPrepUpdate()  (cache result)
    │
    └─▶ aem_client.upload_pdf()          ← Project Library script
            │
            ├─▶ system.net.httpGet()          (fetch CSRF token)
            └─▶ Java HttpURLConnection        (multipart PDF upload)
```

---

## Project Files

### Standalone Version
| File | Purpose |
|---|---|
| [upload_asset.py](upload_asset.py) | Entry point — parse CLI args and orchestrate the upload |
| [auth.py](auth.py) | OAuth 2.0 — acquire, cache, and refresh the access token |
| [aem_client.py](aem_client.py) | AEM HTTP operations — CSRF fetch and PDF upload |
| [db.py](db.py) | MS SQL Server token cache — read/write `aem_token_cache` table |
| [config.py](config.py) | Load and validate `.env` configuration |
| [aem_mock.py](aem_mock.py) | Hardcoded mock responses for local development |
| [.env.example](.env.example) | Configuration template — copy to `.env` and fill in values |
| [requirements.txt](requirements.txt) | Python dependencies |
| [create_sample_pdf.py](create_sample_pdf.py) | Generates `sample/sample.pdf` for local testing |

### Ignition Native Version
| File | Purpose |
|---|---|
| [IgnitionVersion/aem_auth.py](IgnitionVersion/aem_auth.py) | Project Library script — OAuth token management |
| [IgnitionVersion/aem_client.py](IgnitionVersion/aem_client.py) | Project Library script — CSRF fetch and PDF upload |
| [IgnitionVersion/gateway_timer_script.py](IgnitionVersion/gateway_timer_script.py) | Gateway Timer Event Script — entry point |
| [IgnitionVersion/README.md](IgnitionVersion/README.md) | Ignition-specific setup instructions |

### Documentation
| File | Purpose |
|---|---|
| [deployment.md](deployment.md) | Step-by-step deployment guide for both options |
| [requirements.md](requirements.md) | Full project requirements document |
| [FutureWork.md](FutureWork.md) | Recommended enhancements for a corporate environment |

---

## Quick Start (Mock Mode — Standalone)

No AEM account or credentials needed — mock mode intercepts all HTTP calls.

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Generate sample PDF
python create_sample_pdf.py

# 3. Run in mock mode (AEM_MOCK_MODE=true is set in .env by default)
python upload_asset.py --file sample/sample.pdf --title "Test Document"
```

Expected output:
```
21:07:34  WARNING  ============================================================
21:07:34  WARNING  [MOCK MODE]  No real AEM or IMS calls will be made.
21:07:34  WARNING  ============================================================
21:07:34  INFO     [MOCK] IMS token endpoint → fake token issued (expires at 21:08:04 UTC)
21:07:34  INFO     [MOCK] AEM CSRF endpoint → returning fake CSRF token
21:07:34  INFO     [MOCK] AEM upload endpoint → 201 Created  asset_path=/content/dam/pdf-uploads/sample.pdf

Done. Asset available at: /content/dam/pdf-uploads/sample.pdf
```

---

## Configuration

### Standalone — copy [.env.example](.env.example) to `.env`:

```dotenv
AEM_TOKEN_URL=https://ims-na1.adobelogin.com/ims/token/v3
AEM_CLIENT_ID=your-client-id
AEM_CLIENT_SECRET=your-client-secret
AEM_SCOPE=openid,AdobeID,read_organizations

AEM_UPLOAD_BASE_URL=https://author-pXXXXX-eYYYYY.adobeaemcloud.com
AEM_ASSETS_DAM_PATH=/api/assets/pdf-uploads

DB_SERVER=localhost\SQLEXPRESS
DB_NAME=ignition_db
DB_USER=sa
DB_PASSWORD=your-db-password

AEM_MOCK_MODE=false   # set true for local development
```

> `.env` is excluded from source control via [.gitignore](.gitignore) — never commit it.

### Ignition Native — create these String tags in the Tag Browser:

```
[default]AEM/Config/TokenURL       → https://ims-na1.adobelogin.com/ims/token/v3
[default]AEM/Config/ClientID       → your-client-id
[default]AEM/Config/ClientSecret   → your-client-secret  ← apply Tag Security
[default]AEM/Config/Scope          → openid,AdobeID,read_organizations
[default]AEM/Config/UploadBaseURL  → https://author-pXXXXX-eYYYYY.adobeaemcloud.com
[default]AEM/Config/AssetsDamPath  → /api/assets/pdf-uploads
[default]AEM/Upload/FilePath       → (set at runtime to trigger an upload)
[default]AEM/Upload/Title          → (set at runtime)
```

---

## Dependencies (Standalone only)

| Package | Version | Purpose |
|---|---|---|
| `requests` | >=2.32 | HTTP client for IMS and AEM calls |
| `python-dotenv` | >=1.0 | Load `.env` configuration |
| `pyodbc` | >=5.1 | MS SQL Server token cache |

Also required: **ODBC Driver 17 for SQL Server** (Microsoft download).
The Ignition Native version has no pip dependencies — it uses Ignition's built-in APIs.

---

## Deployment

See [deployment.md](deployment.md) for full instructions covering both options,
including firewall rules, software prerequisites, and verification steps.
