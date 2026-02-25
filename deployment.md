# Deployment Guide — AEM PDF Upload Client
## Corporate DMZ Windows Server

Two deployment options are available. Choose one based on your environment:

| | Option A — Standalone | Option B — Ignition Native |
|---|---|---|
| Files | Root folder scripts | `IgnitionVersion/` folder |
| Requires Python install | Yes | No |
| Trigger mechanism | Task Scheduler or `system.util.execute()` | Gateway Timer Event Script |
| Config location | `.env` file | Ignition Tags |

---

## 1. Prerequisites (Both Options)

### Firewall Ports (request from network team)
| Direction | Protocol | Port | Destination |
|---|---|---|---|
| Outbound | HTTPS | 443 | `ims-na1.adobelogin.com` (Adobe IMS) |
| Outbound | HTTPS | 443 | `author-pXXXXX-eYYYYY.adobeaemcloud.com` (AEM Cloud) |
| Outbound | TCP | 1433 | MS SQL Server host (Ignition DB) |

---

## Option A — Standalone Python Script

### A1. Additional Software Required
- **Python 3.12+** — download from [python.org](https://www.python.org/downloads/windows/)
  - During install: check **"Add Python to PATH"**
  - Verify: `python --version`
- **ODBC Driver 17 for SQL Server** — required by `db.py`
  - Download from Microsoft: search "ODBC Driver 17 for SQL Server download"

### A2. Installation
```
1. Copy root project folder to the VM, e.g.:
   C:\aem-client\

2. Open Command Prompt as Administrator in that folder

3. Install dependencies:
   pip install -r requirements.txt

4. Copy .env.example → .env and fill in real values:
   AEM_CLIENT_ID, AEM_CLIENT_SECRET, DB_PASSWORD, etc.
   Set AEM_MOCK_MODE=false

5. Generate sample PDF (first run only):
   python create_sample_pdf.py
```

### A3. Windows Task Scheduler Setup
```
1. Open Task Scheduler → Create Basic Task

2. Name:     AEM PDF Upload
   Trigger:  Daily / On event (match your Ignition workflow)
   Action:   Start a program

3. Program:  C:\Python312\python.exe
   Arguments: C:\aem-client\upload_asset.py
              --file "C:\pdfs\document.pdf"
              --title "My Document"

4. Under Settings → check "Run whether user is logged on or not"
   Store credentials for the service account that owns the task
```

> **Ignition alternative:** use `system.util.execute()` in a Gateway Event Script
> to call the same command — Task Scheduler is not needed in that case.

### A4. Verify
```cmd
cd C:\aem-client
python upload_asset.py --file sample\sample.pdf --title "Deploy Test"
```

Expected output:
```
21:07:34  INFO     [AUTH] Token acquired and cached
21:07:34  INFO     [AEM] CSRF token acquired
21:07:34  INFO     [AEM] Upload successful. Asset path: /content/dam/pdf-uploads/sample.pdf

Done. Asset available at: /content/dam/pdf-uploads/sample.pdf
```

---

## Option B — Ignition Native (Jython 2.7, Ignition 8.1.x)

No Python installation required. All code runs inside Ignition.

### B1. Named Database Connection
In the **Ignition Gateway** (browser → port 8088):
- Config → Databases → Connections → Add
- Name it exactly: `ignition_db`
- Connect to the same MS SQL Server instance
- The `aem_token_cache` table is created automatically on first run

### B2. Project Library Scripts
In **Ignition Designer** → Scripting → Project Library:
- Create a script named `aem_auth` — paste contents of [IgnitionVersion/aem_auth.py](IgnitionVersion/aem_auth.py)
- Create a script named `aem_client` — paste contents of [IgnitionVersion/aem_client.py](IgnitionVersion/aem_client.py)

### B3. Ignition Tags (Configuration)
Create the following String tags in the Tag Browser:
```
[default]AEM/Config/TokenURL          → https://ims-na1.adobelogin.com/ims/token/v3
[default]AEM/Config/ClientID          → your-client-id
[default]AEM/Config/ClientSecret      → your-client-secret
[default]AEM/Config/Scope             → openid,AdobeID,read_organizations
[default]AEM/Config/UploadBaseURL     → https://author-pXXXXX-eYYYYY.adobeaemcloud.com
[default]AEM/Config/AssetsDamPath     → /api/assets/pdf-uploads
[default]AEM/Upload/FilePath          → (set at runtime to trigger an upload)
[default]AEM/Upload/Title             → (set at runtime)
```

> Set **Tag Security** on `ClientSecret` so only the Gateway service account can read it.

### B4. Gateway Timer Script
- Designer → Gateway Event Scripts → Timer → Add Timer
- Set interval (e.g. 60 seconds)
- Paste contents of [IgnitionVersion/gateway_timer_script.py](IgnitionVersion/gateway_timer_script.py)

### B5. Triggering an Upload
From any Ignition script, write to the upload tags to queue a file:
```python
system.tag.writeBlocking(
    ["[default]AEM/Upload/FilePath", "[default]AEM/Upload/Title"],
    ["C:/pdfs/document.pdf",         "My Document"]
)
```
The Gateway Timer picks it up on the next tick, uploads, then clears the tag.

### B6. Verify
Check **Ignition Gateway → Status → Logs** and filter by:
- `AEMUpload` — top-level upload events
- `aem_auth` — token acquire/refresh events
- `aem_client` — CSRF and upload events

---

## 5. Security Notes (Both Options)

| Note | Standalone | Ignition Native |
|---|---|---|
| Credentials location | `.env` file — restrict file permissions to service account | Ignition Tags — apply Tag Security to `ClientSecret` |
| Never commit credentials | `.env` excluded via `.gitignore` | Tags are not in source control |
| Service account | Run Task Scheduler job as low-privilege service account | Gateway runs as its own service account |
| Secret rotation | Rotate `AEM_CLIENT_SECRET` in `.env` | Rotate value in the `ClientSecret` tag |

---

*Document version: 0.2 — 2026-02-25*
