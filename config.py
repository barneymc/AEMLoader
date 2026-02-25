"""
config.py — Load and validate .env configuration.
"""
import os
import logging
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)

_REQUIRED_KEYS = [
    "AEM_TOKEN_URL",
    "AEM_CLIENT_ID",
    "AEM_CLIENT_SECRET",
    "AEM_SCOPE",
    "AEM_UPLOAD_BASE_URL",
    "AEM_ASSETS_DAM_PATH",
    "DB_SERVER",
    "DB_NAME",
    "DB_USER",
    "DB_PASSWORD",
]


@dataclass
class Config:
    token_url: str
    client_id: str
    client_secret: str
    scope: str
    upload_base_url: str
    assets_dam_path: str
    db_server: str
    db_name: str
    db_user: str
    db_password: str
    db_table: str
    mock_mode: bool


def load_config() -> Config:
    missing = [k for k in _REQUIRED_KEYS if not os.getenv(k)]
    if missing:
        log.error(f"[CONFIG] Missing required .env keys: {', '.join(missing)}")
        raise SystemExit(1)

    return Config(
        token_url=os.getenv("AEM_TOKEN_URL"),
        client_id=os.getenv("AEM_CLIENT_ID"),
        client_secret=os.getenv("AEM_CLIENT_SECRET"),
        scope=os.getenv("AEM_SCOPE"),
        upload_base_url=os.getenv("AEM_UPLOAD_BASE_URL"),
        assets_dam_path=os.getenv("AEM_ASSETS_DAM_PATH"),
        db_server=os.getenv("DB_SERVER"),
        db_name=os.getenv("DB_NAME"),
        db_user=os.getenv("DB_USER"),
        db_password=os.getenv("DB_PASSWORD"),
        db_table=os.getenv("DB_TABLE_TOKEN_STORE", "aem_token_cache"),
        mock_mode=os.getenv("AEM_MOCK_MODE", "false").lower() == "true",
    )
