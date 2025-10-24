import os
import hmac
import hashlib
import base64
import uuid
import time
import urllib.parse
import requests
import json
from pathlib import Path
from datetime import datetime

# Constants
TOKEN_URL = "https://portalapi.lcegateway.com/Token"
REPORT_URL_BASE = "https://portalapi.lcegateway.com/GetReportBlobs"
TODAY = datetime.now().strftime("%Y-%m-%d")
BASE_DIR = Path.home() / "Downloads" / "LC Reports" / TODAY
BASE_DIR.mkdir(parents=True, exist_ok=True)

def generate_hmac_header(http_method, request_url):
    HMAC_USER = os.getenv("HMAC_USER")
    HMAC_KEY = os.getenv("HMAC_KEY")
    nonce = uuid.uuid4().hex
    timestamp = str(int(time.time()))
    encoded_url = urllib.parse.quote(request_url, safe="").lower()
    raw_string = HMAC_USER + http_method + encoded_url + timestamp + nonce
    raw_bytes = raw_string.encode("utf-8")
    key_bytes = base64.b64decode(HMAC_KEY)
    signature = base64.b64encode(hmac.new(key_bytes, raw_bytes, hashlib.sha256).digest()).decode()
    return f"amx {HMAC_USER}:{signature}:{nonce}:{timestamp}"

def get_token():
    GATEWAY_USERNAME = os.getenv("GATEWAY_USERNAME")
    GATEWAY_PASSWORD = os.getenv("GATEWAY_PASSWORD")
    payload = {
        "grant_type": "password",
        "username": GATEWAY_USERNAME,
        "password": GATEWAY_PASSWORD
    }
    response = requests.post(TOKEN_URL, data=payload)
    response.raise_for_status()
    return response.json()["access_token"]

def get_previously_downloaded_files(base_dir, today_folder):
    all_files = set()
    for subfolder in base_dir.iterdir():
        if subfolder.is_dir() and subfolder != today_folder:
            for file in subfolder.glob("*"):
                all_files.add(file.name)
    return all_files

def download_reports(token, username):
    file_name = "all"
    full_url = f"{REPORT_URL_BASE}?userName={username}&fileName={file_name}"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "HMacAuthorizationHeader": generate_hmac_header("GET", full_url)
    }

    print(f"Requesting report list from: {full_url}")
    response = requests.get(full_url, headers=headers)
    response.raise_for_status()

    try:
        raw_json_string = response.json()
        report_list = json.loads(raw_json_string)
    except Exception as e:
        print("Failed to double-parse JSON:", e)
        print("Raw response text:", response.text[:500])
        return

    if not isinstance(report_list, list):
        print("Expected a list but got:", type(report_list))
        return

    previously_downloaded = get_previously_downloaded_files(BASE_DIR.parent, BASE_DIR)

    print(f"Found {len(report_list)} reports.")
    downloaded = 0
    skipped = 0

    for report in report_list:
        name = report.get("ReportName")
        url = report.get("ReportBlobUri")
        if not name or not url:
            continue

        if name in previously_downloaded:
            print(f"Skipping (already downloaded in past): {name}")
            skipped += 1
            continue

        filepath = BASE_DIR / name
        try:
            print(f"Downloading: {name}")
            r = requests.get(url)
            r.raise_for_status()
            with open(filepath, "wb") as f:
                f.write(r.content)
            print(f"Saved to: {filepath}")
            downloaded += 1
        except Exception as e:
            print(f"Failed to download {name}: {e}")

    print(f"\n✅ Done: {downloaded} downloaded, {skipped} skipped")
    print(f"📁 Files saved to: {BASE_DIR}")

def main():
    token = get_token()
    download_reports(token, GATEWAY_USERNAME)  # pyright: ignore[reportUndefinedVariable]

if __name__ == "__main__":
    main()
