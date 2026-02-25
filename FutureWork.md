# Future Work & Enhancements

Recommendations for future phases of the AEM PDF Upload Client in a corporate environment.
Items are grouped by theme and ordered by priority within each section.

---

## 1. Security

**Priority: High**

| Item | Detail |
|---|---|
| Secret management | Move `AEM_CLIENT_SECRET` and `DB_PASSWORD` out of `.env` into a vault — Azure Key Vault, HashiCorp Vault, or Windows DPAPI. The `.env` approach is acceptable for early stages but is not suitable at enterprise scale. |
| Encrypt token cache | The access token stored in the `aem_token_cache` SQL table is currently plain text. Encrypting that column (SQL Server Always Encrypted or application-level AES) reduces exposure if the DB is ever compromised. |
| SQL least privilege | The DB account should only have `SELECT`, `INSERT`, and `UPDATE` on `aem_token_cache` — not broad `sa` rights as used in the current dev config. |
| Audit log | Record every upload attempt (filename, timestamp, AEM asset path, success/fail, error message) to a separate SQL table for compliance and traceability. |

---

## 2. Reliability

**Priority: High**

| Item | Detail |
|---|---|
| Retry with backoff | Transient network failures in a DMZ are common. Simple retry logic — 3 attempts at 5s / 15s / 30s intervals — would make the script significantly more resilient without adding much complexity. |
| Failed upload queue | If an upload fails after all retries, write the file path, title, and error to a SQL table so failed jobs can be retried later rather than silently dropped. |
| Alerting on failure | Send a Microsoft Teams webhook message or email notification on unrecoverable failure, so someone is notified without having to manually check logs. |

---

## 3. Observability

**Priority: Medium**

| Item | Detail |
|---|---|
| Structured logging | Write JSON-formatted log entries to a file or log aggregator (Splunk, Azure Monitor, ELK). Makes log searching, dashboards, and alerting far easier in a corporate environment compared to plain console output. |
| Windows Event Log | Write critical errors to the Windows Event Log. Corporate IT monitoring tools (SCOM, Datadog, etc.) typically watch the Event Log automatically, meaning failures surface without any extra configuration. |
| Upload metrics | Track upload count, failure rate, and token refresh frequency over time — useful for capacity planning and detecting AEM-side issues. |

---

## 4. Scalability

**Priority: Medium**

| Item | Detail |
|---|---|
| Batch uploads | Currently the script handles one PDF per invocation. A `--folder` argument to process a directory of PDFs in a single run would be a natural and low-effort next step. |
| Multiple environments | Support dev / stage / prod via named env files (`.env.prod`, `.env.stage`) selected with a `--env` flag, rather than manually swapping `.env` content. |
| Queue-based processing | If upload volume grows significantly, feeding from a message queue (Azure Service Bus, MSMQ) decouples Ignition from the upload process entirely and provides built-in retry, ordering, and dead-lettering. |

---

## 5. Code Quality

**Priority: Medium**

| Item | Detail |
|---|---|
| Unit tests | `auth.py` and `aem_client.py` are both highly testable given the mock layer already in place. Adding a `pytest` test suite would be a low-effort, high-value improvement. |
| CI/CD pipeline | A GitHub Actions workflow to run tests and a linter (`ruff`) on every push would catch regressions before they reach the server. |
| Type hints | Adding Python type hints throughout improves IDE support and makes the codebase easier to hand over to a colleague. |

---

## 6. Infrastructure

**Priority: Low — plan early, implement later**

| Item | Detail |
|---|---|
| Corporate proxy support | If the DMZ routes outbound traffic through a proxy, the `requests` library needs `HTTP_PROXY` / `HTTPS_PROXY` environment variables configured. Worth confirming with the network team now even if not immediately needed. |
| Private AEM endpoint | Adobe supports private networking for AEM as a Cloud Service, removing the public internet hop entirely. Worth exploring with your network team as a longer-term security improvement. |
| Windows service wrapper | Wrapping the script as a Windows Service (using `pywin32` or NSSM) instead of Task Scheduler gives better process management, automatic restart on failure, and cleaner integration with Windows monitoring. |

---

## Recommended Implementation Order

For a corporate environment, tackle these first:

1. **Audit log** — low effort, immediately useful for compliance
2. **SQL least privilege** — quick win, reduces attack surface
3. **Retry with backoff** — small code change, large reliability gain
4. **Alerting on failure** — Teams webhook is a few lines; avoids silent failures
5. **Secret vault** — more involved but critical before production sign-off

---

*Document version: 0.1 — 2026-02-25*
