"""
Ignition Project Library Script: aem_client

Place in: Designer -> Scripting -> Project Library -> New Script
Name it:  aem_client

Handles AEM HTTP operations:
  - CSRF token fetch  via system.net.httpGet()
  - PDF upload        via Java HttpURLConnection (multipart/form-data)

The multipart upload uses Java classes directly because Ignition's
system.net.httpPost() does not support multipart/form-data.

Note: This is Jython 2.7 — no f-strings, no type hints, no asyncio.
"""
import json

from java.io import DataOutputStream, File, FileInputStream
from java.net import URL


def fetch_csrf_token(upload_base_url, access_token):
    """Fetch a CSRF token from the AEM Granite endpoint."""
    logger = system.util.getLogger("aem_client")
    url = upload_base_url + "/libs/granite/csrf/token.json"
    logger.info("Fetching CSRF token from AEM...")

    try:
        response_text = system.net.httpGet(
            url,
            connectTimeout=10000,
            readTimeout=30000,
            username=None,
            password=None,
            headerValues={"Authorization": "Bearer " + access_token}
        )
    except Exception as e:
        logger.error("CSRF token fetch failed: " + str(e))
        raise

    data = json.loads(response_text)
    logger.info("CSRF token acquired.")
    return data["token"]


def upload_pdf(config, file_path, title, access_token):
    """
    Upload a PDF to AEM Assets using Java HttpURLConnection (multipart/form-data).

    config: dict with keys: upload_base_url, assets_dam_path
    Returns: asset_path string on success. Raises Exception on failure.
    """
    logger = system.util.getLogger("aem_client")

    if not File(file_path).exists():
        raise Exception("File not found: " + file_path)

    csrf_token = fetch_csrf_token(config["upload_base_url"], access_token)

    # Build upload URL
    filename = file_path.replace("\\", "/").split("/")[-1]
    upload_url = config["upload_base_url"] + config["assets_dam_path"] + "/" + filename
    boundary = "----AEMBoundary" + str(system.date.toMillis(system.date.now()))

    logger.info("Uploading {} -> {}".format(filename, upload_url))

    # Open Java HTTP connection
    url_obj = URL(upload_url)
    conn = url_obj.openConnection()
    conn.setDoOutput(True)
    conn.setRequestMethod("POST")
    conn.setRequestProperty("Authorization", "Bearer " + access_token)
    conn.setRequestProperty("CSRF-Token", csrf_token)
    conn.setRequestProperty("Content-Type", "multipart/form-data; boundary=" + boundary)
    conn.setConnectTimeout(10000)
    conn.setReadTimeout(120000)

    out = DataOutputStream(conn.getOutputStream())

    # -- title metadata field --
    out.writeBytes("--" + boundary + "\r\n")
    out.writeBytes("Content-Disposition: form-data; name=\"title\"\r\n\r\n")
    out.writeBytes(title + "\r\n")

    # -- PDF binary field --
    out.writeBytes("--" + boundary + "\r\n")
    out.writeBytes(
        "Content-Disposition: form-data; name=\"file\"; filename=\"{}\"\r\n".format(filename)
    )
    out.writeBytes("Content-Type: application/pdf\r\n\r\n")

    fis = FileInputStream(File(file_path))
    buf = [0] * 8192
    n = fis.read(buf)
    while n != -1:
        out.write(buf, 0, n)
        n = fis.read(buf)
    fis.close()

    out.writeBytes("\r\n--" + boundary + "--\r\n")
    out.flush()
    out.close()

    status = conn.getResponseCode()
    conn.disconnect()

    if status == 201:
        asset_path = config["assets_dam_path"] + "/" + filename
        logger.info("Upload successful. Asset path: " + asset_path)
        return asset_path

    raise Exception("Upload failed: HTTP {}".format(status))
