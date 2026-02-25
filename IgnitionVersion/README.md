# AEM Upload Client — Ignition Native Version

This folder contains a rewrite of the AEM PDF upload client designed to run
**natively inside Ignition 8.1.x** as Gateway Event Scripts, with no external
Python installation required.

---

## How It Differs From the Standalone Version

| | Standalone (root folder) | Ignition Native (this folder) |
|---|---|---|
| Runtime | CPython 3.12 — external process | Jython 2.7 — inside Ignition |
| HTTP client | `requests` library | `system.net.*` + Java `HttpURLConnection` |
| Config | `.env` file | Ignition Tags |
| Token cache | `pyodbc` + connection string | `system.db.*` — named DB connection |
| Scheduling | Windows Task Scheduler | Gateway Timer Event Script |
| Python install needed | Yes | No |
| Multipart upload | Simple (`requests`) | Java interop (`HttpURLConnection`) |

---

## Files

| File | Where it goes in Ignition |
|---|---|
| [aem_auth.py](aem_auth.py) | Designer → Scripting → Project Library → script named `aem_auth` |
| [aem_client.py](aem_client.py) | Designer → Scripting → Project Library → script named `aem_client` |
| [gateway_timer_script.py](gateway_timer_script.py) | Designer → Gateway Event Scripts → Timer → New Timer |

---

## Setup Steps

### 1. Named Database Connection
In the **Ignition Gateway** (browser, port 8088):
- Config → Databases → Connections → Add
- Name it exactly: `ignition_db`
- Connect to the same MS SQL Server used by the standalone version
- The `aem_token_cache` table will be created automatically on first run

### 2. Project Library Scripts
In **Ignition Designer**:
- Scripting → Project Library → right-click → New Script
- Create two scripts named `aem_auth` and `aem_client`
- Paste the contents of [aem_auth.py](aem_auth.py) and [aem_client.py](aem_client.py) respectively

### 3. Ignition Tags (Configuration)
Create the following String tags in your tag browser:

```
[default]AEM/
    Config/
        TokenURL          → https://ims-na1.adobelogin.com/ims/token/v3
        ClientID          → your-client-id
        ClientSecret      → your-client-secret (consider Tag Security)
        Scope             → openid,AdobeID,read_organizations
        UploadBaseURL     → https://author-pXXXXX-eYYYYY.adobeaemcloud.com
        AssetsDamPath     → /api/assets/pdf-uploads
    Upload/
        FilePath          → (set this at runtime to trigger an upload)
        Title             → (set this at runtime)
```

> **Security note:** Set Tag Security on `ClientSecret` so only the Gateway
> service account can read it.

### 4. Gateway Timer Script
- Designer → Gateway Event Scripts → Timer → Add Timer
- Set your desired interval (e.g. every 60 seconds)
- Paste the contents of [gateway_timer_script.py](gateway_timer_script.py)

### 5. Triggering an Upload
To queue a PDF for upload, write to the tags from any Ignition script:

```python
system.tag.writeBlocking(
    ["[default]AEM/Upload/FilePath", "[default]AEM/Upload/Title"],
    ["C:/pdfs/document.pdf",         "My Document"]
)
```

The Gateway Timer will pick it up on the next tick, upload it, and clear the tag.

---

## Logs
All log output appears in:
- Ignition Gateway → Status → Logs → filter by logger `AEMUpload`, `aem_auth`, or `aem_client`
