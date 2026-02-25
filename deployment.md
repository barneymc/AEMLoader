# Deployment Guide — AEM PDF Upload Client
## Corporate DMZ Windows Server

---

## 1. Prerequisites

### Firewall Ports (request from network team)
| Direction | Protocol | Port | Destination |
|---|---|---|---|
| Outbound | HTTPS | 443 | `ims-na1.adobelogin.com` (Adobe IMS) |
| Outbound | HTTPS | 443 | `author-pXXXXX-eYYYYY.adobeaemcloud.com` (AEM Cloud) |
| Outbound | TCP | 1433 | MS SQL Server host (Ignition DB) |

### Software
- **Python 3.12+** — download from [python.org](https://www.python.org/downloads/windows/)
  - During install: check **"Add Python to PATH"**
  - Verify: `python --version`
- **ODBC Driver 17 for SQL Server** — required by `db.py`
  - Download from Microsoft: search "ODBC Driver 17 for SQL Server download"

---

## 2. Installation

```
1. Copy project folder to VM, e.g.:
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

---

## 3. Windows Task Scheduler Setup

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

---

## 4. Verify Deployment

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

## 5. Security Notes

- `.env` contains credentials — restrict file permissions to the service account only
- Do not store `.env` in source control (`.gitignore` already excludes it)
- Run the Task Scheduler job under a **dedicated low-privilege service account**, not a personal or admin account
- Rotate `AEM_CLIENT_SECRET` per your organisation's credential policy

---

*Document version: 0.1 — 2026-02-25*
