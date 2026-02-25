"""
auth.py — OAuth 2.0 Client Credentials token management.

Flow:
  1. In mock mode → return hardcoded mock token immediately (no DB or HTTP).
  2. In real mode → check SQL cache; reuse if valid, otherwise call IMS and cache result.
"""
import logging
from datetime import datetime, timedelta, timezone

import requests

import aem_mock
import db
from config import Config

log = logging.getLogger(__name__)

# Refresh the token this many seconds before it actually expires,
# to avoid using a token that expires mid-request.
_EXPIRY_BUFFER_SECONDS = 60


def _is_expired(expires_at: datetime) -> bool:
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    cutoff = datetime.now(tz=timezone.utc) + timedelta(seconds=_EXPIRY_BUFFER_SECONDS)
    return cutoff >= expires_at


def _request_new_token(cfg: Config) -> tuple[str, datetime]:
    """Call the IMS token endpoint and return (access_token, expires_at)."""
    resp = requests.post(
        cfg.token_url,
        data={
            "grant_type": "client_credentials",
            "client_id": cfg.client_id,
            "client_secret": cfg.client_secret,
            "scope": cfg.scope,
        },
        timeout=30,
    )
    if not resp.ok:
        log.error(f"[AUTH] Token request failed: HTTP {resp.status_code} — {resp.text}")
        raise SystemExit(1)

    data = resp.json()
    access_token = data["access_token"]
    expires_in = int(data.get("expires_in", 3600))
    expires_at = datetime.now(tz=timezone.utc) + timedelta(seconds=expires_in)
    return access_token, expires_at


def get_valid_token(cfg: Config) -> str:
    """Return a valid Bearer token, refreshing or acquiring one as needed."""

    # ── Mock mode: skip DB and HTTP entirely ──────────────────────────────────
    if cfg.mock_mode:
        data = aem_mock.mock_fetch_token()
        return data["access_token"]

    # ── Real mode ─────────────────────────────────────────────────────────────
    db.ensure_table(cfg)

    access_token, expires_at = db.load_token(cfg)

    if access_token and expires_at and not _is_expired(expires_at):
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        remaining = int(
            (expires_at - datetime.now(tz=timezone.utc)).total_seconds()
        )
        log.info(f"[AUTH] Using cached token (expires in {remaining}s)")
        return access_token

    if access_token:
        log.info("[AUTH] Cached token expired — refreshing...")
    else:
        log.info("[AUTH] No cached token found — requesting new token...")

    access_token, expires_at = _request_new_token(cfg)
    db.save_token(cfg, access_token, expires_at)
    log.info(f"[AUTH] Token acquired and cached (expires at {expires_at.isoformat()})")
    return access_token
