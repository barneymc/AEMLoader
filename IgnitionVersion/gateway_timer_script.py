"""
Ignition Gateway Timer Event Script

Place in: Designer -> Gateway Event Scripts -> Timer -> Add Timer
Set interval to match your upload frequency (e.g. every 60 seconds).

Requires Project Library scripts: aem_auth, aem_client
Requires Ignition Tags at paths defined in the config block below.
Requires a named DB connection called 'ignition_db' in the Gateway.

How it works:
  1. Reads the file path and title from Tags on each timer tick.
  2. If no file is queued (FilePath tag is empty), it does nothing.
  3. If a file is queued, it authenticates, uploads, and clears the tag.
"""
logger = system.util.getLogger("AEMUpload")

# ── Configuration (read from Ignition Tags) ───────────────────────────────────
# Adjust tag paths to match your project structure.
config = {
    "token_url":       system.tag.readBlocking(["[default]AEM/Config/TokenURL"])[0].value,
    "client_id":       system.tag.readBlocking(["[default]AEM/Config/ClientID"])[0].value,
    "client_secret":   system.tag.readBlocking(["[default]AEM/Config/ClientSecret"])[0].value,
    "scope":           system.tag.readBlocking(["[default]AEM/Config/Scope"])[0].value,
    "upload_base_url": system.tag.readBlocking(["[default]AEM/Config/UploadBaseURL"])[0].value,
    "assets_dam_path": system.tag.readBlocking(["[default]AEM/Config/AssetsDamPath"])[0].value,
    "db_connection":   "ignition_db",     # Named DB connection in Ignition Gateway
    "db_table":        "aem_token_cache",
}

# ── Check for a queued upload ─────────────────────────────────────────────────
file_path = system.tag.readBlocking(["[default]AEM/Upload/FilePath"])[0].value
title     = system.tag.readBlocking(["[default]AEM/Upload/Title"])[0].value

if not file_path:
    logger.info("No file queued for upload — skipping.")
else:
    try:
        logger.info("Upload triggered: {} ({})".format(file_path, title))

        token      = aem_auth.get_valid_token(config)
        asset_path = aem_client.upload_pdf(config, file_path, title, token)

        logger.info("Done. Asset available at: " + asset_path)

        # Clear the upload tags so the same file is not uploaded again
        system.tag.writeBlocking(
            ["[default]AEM/Upload/FilePath", "[default]AEM/Upload/Title"],
            ["", ""]
        )

    except Exception as e:
        logger.error("AEM upload failed: " + str(e))
        # Tag is NOT cleared on failure — allows manual retry or investigation
