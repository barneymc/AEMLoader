"""
aem_mock.py — Hardcoded mock responses for IMS and AEM endpoints.

Activated when AEM_MOCK_MODE=true in .env.

Token expires_in is intentionally short (30 seconds) so that running
the script twice more than 30 seconds apart exercises the refresh path.
"""
import logging
import os
from datetime import datetime, timedelta, timezone

log = logging.getLogger(__name__)

MOCK_ACCESS_TOKEN = "mock-access-token-abc123xyz"
MOCK_TOKEN_EXPIRES_IN = 30          # seconds — short to test refresh logic
MOCK_CSRF_TOKEN = "mock-csrf-token-xyz987"


def mock_fetch_token() -> dict:
    """Simulate an Adobe IMS token endpoint response."""
    expires_at = datetime.now(tz=timezone.utc) + timedelta(seconds=MOCK_TOKEN_EXPIRES_IN)
    log.info(
        f"[MOCK] IMS token endpoint → fake token issued "
        f"(expires at {expires_at.strftime('%H:%M:%S')} UTC)"
    )
    return {
        "access_token": MOCK_ACCESS_TOKEN,
        "expires_in": MOCK_TOKEN_EXPIRES_IN,
    }


def mock_fetch_csrf_token() -> str:
    """Simulate the AEM Granite CSRF token endpoint."""
    log.info("[MOCK] AEM CSRF endpoint → returning fake CSRF token")
    return MOCK_CSRF_TOKEN


def mock_upload_asset(file_path: str, title: str) -> dict:
    """Simulate a successful AEM Assets upload (HTTP 201)."""
    filename = os.path.basename(file_path)
    asset_path = f"/content/dam/pdf-uploads/{filename}"
    log.info(f"[MOCK] AEM upload endpoint → 201 Created  asset_path={asset_path}")
    return {
        "status_code": 201,
        "asset_path": asset_path,
    }
