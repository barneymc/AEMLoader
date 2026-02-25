"""
upload_asset.py — AEM PDF upload entry point.

Usage:
    python upload_asset.py --file <path-to-pdf> --title "<asset title>"

Ignition example:
    system.util.execute([
        "python", "C:/aem-client/upload_asset.py",
        "--file", "C:/pdfs/document.pdf",
        "--title", "My Document"
    ])
"""
import argparse
import logging
import sys

import auth
import aem_client
from config import load_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Upload a PDF to AEM Assets")
    parser.add_argument("--file",  required=True, help="Path to the PDF file to upload")
    parser.add_argument("--title", required=True, help="Asset title (metadata)")
    args = parser.parse_args()

    cfg = load_config()

    if cfg.mock_mode:
        log.warning("=" * 60)
        log.warning("[MOCK MODE]  No real AEM or IMS calls will be made.")
        log.warning("=" * 60)

    token = auth.get_valid_token(cfg)
    result = aem_client.upload_pdf(cfg, args.file, args.title, token)

    print(f"\nDone. Asset available at: {result['asset_path']}")
    sys.exit(0)


if __name__ == "__main__":
    main()
