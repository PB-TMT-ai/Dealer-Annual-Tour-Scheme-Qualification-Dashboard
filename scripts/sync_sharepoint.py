"""
SharePoint Excel Sync Script
-----------------------------
Downloads the latest Excel file from a SharePoint/OneDrive direct share link
and places it in the data/ folder so the dashboard picks it up automatically.

Usage:
    python scripts/sync_sharepoint.py --url "https://your-sharepoint-link"

    Or set the SHAREPOINT_EXCEL_URL environment variable:
    export SHAREPOINT_EXCEL_URL="https://your-sharepoint-link"
    python scripts/sync_sharepoint.py

Schedule this to run daily (cron, Task Scheduler, etc.) for automatic updates.
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# How long (in hours) before re-downloading even if a cached file exists
CACHE_MAX_AGE_HOURS = 24


def _cache_is_fresh(file_path: Path, max_age_hours: int = CACHE_MAX_AGE_HOURS) -> bool:
    """Return True if file exists and is younger than max_age_hours."""
    if not file_path.exists():
        return False
    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
    age_hours = (datetime.now() - mtime).total_seconds() / 3600
    return age_hours < max_age_hours


def sync(url: str, force: bool = False) -> Path:
    """Download Excel from SharePoint and save to data/ folder.

    Args:
        url: Direct download link for the SharePoint/OneDrive Excel file.
        force: If True, download even if a fresh cached copy exists.

    Returns:
        Path to the downloaded file.

    Raises:
        SystemExit: On download failure or invalid response.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Build filename with today's date for traceability
    today = datetime.now().strftime("%Y-%m-%d")
    output_file = DATA_DIR / f"sharepoint_sync_{today}.xlsx"

    # Skip download if fresh copy already exists
    if not force and output_file.exists() and _cache_is_fresh(output_file):
        print(f"[SKIP] Fresh file already exists: {output_file.name} (< {CACHE_MAX_AGE_HOURS}h old)")
        return output_file

    print(f"[SYNC] Downloading from SharePoint ...")
    try:
        resp = requests.get(url, timeout=120, allow_redirects=True)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"[ERROR] Download failed: {exc}", file=sys.stderr)
        sys.exit(1)

    # Validate we got a binary file, not an HTML login page
    content_type = resp.headers.get("Content-Type", "")
    if "html" in content_type.lower():
        print(
            "[ERROR] SharePoint returned an HTML page instead of a file.\n"
            "        The link likely requires authentication.\n"
            "        Make sure the sharing setting is 'Anyone with the link'.",
            file=sys.stderr,
        )
        sys.exit(1)

    if len(resp.content) < 1024:
        print(
            f"[WARN] Downloaded file is very small ({len(resp.content)} bytes). "
            "Double-check the link is correct.",
            file=sys.stderr,
        )

    output_file.write_bytes(resp.content)
    size_kb = len(resp.content) / 1024
    print(f"[OK] Saved {output_file.name} ({size_kb:,.0f} KB)")

    # Clean up older sync files to avoid clutter (keep last 3)
    sync_files = sorted(
        DATA_DIR.glob("sharepoint_sync_*.xlsx"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    for old_file in sync_files[3:]:
        old_file.unlink()
        print(f"[CLEANUP] Removed old file: {old_file.name}")

    return output_file


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download Excel from SharePoint into the data/ folder."
    )
    parser.add_argument(
        "--url",
        default=os.getenv("SHAREPOINT_EXCEL_URL", ""),
        help="Direct download link (or set SHAREPOINT_EXCEL_URL env var)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force download even if a fresh cached copy exists",
    )
    args = parser.parse_args()

    if not args.url.strip():
        print(
            "[ERROR] No URL provided.\n"
            "        Use --url or set the SHAREPOINT_EXCEL_URL environment variable.\n\n"
            "  How to get the SharePoint link:\n"
            "  1. Open the Excel file in SharePoint\n"
            "  2. Click Share -> 'Anyone with the link' -> Copy link\n"
            "  3. Pass that URL to this script",
            file=sys.stderr,
        )
        sys.exit(1)

    sync(args.url.strip(), force=args.force)


if __name__ == "__main__":
    main()
