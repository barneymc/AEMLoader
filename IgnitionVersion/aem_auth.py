"""
Ignition Project Library Script: aem_auth

Place in: Designer -> Scripting -> Project Library -> New Script
Name it:  aem_auth

Handles OAuth 2.0 Client Credentials token management using:
  - system.net.httpPost() for Adobe IMS token requests
  - system.db.*()         for token caching in MS SQL Server

Note: This is Jython 2.7 — no f-strings, no type hints, no asyncio.
"""
import json

EXPIRY_BUFFER_SECONDS = 60  # Refresh token this many seconds before actual expiry


def _is_expired(expires_at):
    """Check whether a cached token (java.util.Date) is expired."""
    now = system.date.now()
    buffer_ms = EXPIRY_BUFFER_SECONDS * 1000
    return system.date.toMillis(now) >= (system.date.toMillis(expires_at) - buffer_ms)


def _ensure_table(db_connection, table_name):
    """Create the token cache table if it does not already exist."""
    sql = """
        IF NOT EXISTS (
            SELECT * FROM sysobjects WHERE name = '{table}' AND xtype = 'U'
        )
        CREATE TABLE {table} (
            id           INT           PRIMARY KEY DEFAULT 1,
            access_token NVARCHAR(MAX) NOT NULL,
            expires_at   DATETIME2     NOT NULL,
            created_at   DATETIME2     DEFAULT GETDATE()
        )
    """.format(table=table_name)
    system.db.runUpdateQuery(sql, database=db_connection)


def _load_token(db_connection, table_name):
    """Return (access_token, expires_at) or (None, None) if cache is empty."""
    sql = "SELECT access_token, expires_at FROM {table} WHERE id = 1".format(
        table=table_name
    )
    results = system.db.runQuery(sql, database=db_connection)
    if len(results) > 0:
        row = results[0]
        return row["access_token"], row["expires_at"]
    return None, None


def _save_token(db_connection, table_name, access_token, expires_at):
    """Upsert the token record (single-row cache, id = 1)."""
    sql = """
        MERGE {table} AS target
        USING (SELECT 1 AS id) AS src ON target.id = src.id
        WHEN MATCHED THEN
            UPDATE SET access_token = ?, expires_at = ?, created_at = GETDATE()
        WHEN NOT MATCHED THEN
            INSERT (id, access_token, expires_at) VALUES (1, ?, ?);
    """.format(table=table_name)
    system.db.runPrepUpdate(
        sql,
        [access_token, expires_at, access_token, expires_at],
        database=db_connection
    )


def _request_new_token(token_url, client_id, client_secret, scope):
    """POST to Adobe IMS and return (access_token, expires_in_seconds)."""
    logger = system.util.getLogger("aem_auth")
    post_data = "grant_type=client_credentials&client_id={}&client_secret={}&scope={}".format(
        client_id, client_secret, scope
    )
    try:
        response_text = system.net.httpPost(
            token_url,
            "application/x-www-form-urlencoded",
            post_data
        )
    except Exception as e:
        logger.error("Token request failed: " + str(e))
        raise

    data = json.loads(response_text)
    return data["access_token"], int(data.get("expires_in", 3600))


def get_valid_token(config):
    """
    Return a valid Bearer access token.
    Checks the DB cache first; requests a new one from IMS if missing or expired.

    config: dict with keys:
        token_url, client_id, client_secret, scope,
        db_connection, db_table
    """
    logger = system.util.getLogger("aem_auth")

    _ensure_table(config["db_connection"], config["db_table"])
    access_token, expires_at = _load_token(config["db_connection"], config["db_table"])

    if access_token and expires_at and not _is_expired(expires_at):
        logger.info("Token cache: valid token found — reusing.")
        return access_token

    if access_token:
        logger.info("Token cache: expired — refreshing...")
    else:
        logger.info("Token cache: empty — requesting new token from IMS...")

    access_token, expires_in = _request_new_token(
        config["token_url"],
        config["client_id"],
        config["client_secret"],
        config["scope"]
    )

    expires_at = system.date.addSeconds(system.date.now(), expires_in)
    _save_token(config["db_connection"], config["db_table"], access_token, expires_at)
    logger.info("Token acquired and cached.")
    return access_token
