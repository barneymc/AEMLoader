"""
aem_client.py — AEM HTTP operations: CSRF token fetch and PDF asset upload.
"""
import logging
import os

import requests

import aem_mock
from config import Config

log = logging.getLogger(__name__)


def _fetch_csrf_token(cfg: Config, access_token: str) -> str:
    """Fetch a CSRF token from the AEM Granite endpoint."""
    if cfg.mock_mode:
        return aem_mock.mock_fetch_csrf_token()

    url = f"{cfg.upload_base_url}/libs/granite/csrf/token.json"
    log.info(f"[AEM] Fetching CSRF token from {url}")
    resp = requests.get(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    if not resp.ok:
        log.error(f"[AEM] CSRF token fetch failed: HTTP {resp.status_code} — {resp.text}")
        raise SystemExit(1)

    log.info("[AEM] CSRF token acquired.")
    return resp.json()["token"]


def upload_pdf(cfg: Config, file_path: str, title: str, access_token: str) -> dict:
    """
    Upload a PDF file to AEM Assets with a title metadata field.

    Returns a dict with keys: status_code, asset_path.
    Exits with code 1 on any error.
    """
    if not os.path.isfile(file_path):
        log.error(f"[AEM] File not found: {file_path}")
        raise SystemExit(1)

    csrf_token = _fetch_csrf_token(cfg, access_token)

    if cfg.mock_mode:
        return aem_mock.mock_upload_asset(file_path, title)

    filename = os.path.basename(file_path)
    url = f"{cfg.upload_base_url}{cfg.assets_dam_path}/{filename}"
    log.info(f"[AEM] Uploading {filename} → {url}")

    with open(file_path, "rb") as f:
        resp = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "CSRF-Token": csrf_token,
            },
            files={"file": (filename, f, "application/pdf")},
            data={"title": title},
            timeout=120,
        )

    if resp.status_code == 201:
        asset_path = resp.headers.get("Location", url)
        log.info(f"[AEM] Upload successful. Asset path: {asset_path}")
        return {"status_code": 201, "asset_path": asset_path}

    log.error(f"[AEM] Upload failed: HTTP {resp.status_code} — {resp.text}")
    raise SystemExit(1)
