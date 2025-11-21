import os
import hmac
import hashlib
import base64
import uuid
import time
import urllib.parse
import requests
import json
import logging
import platform
import sys
from pathlib import Path
from datetime import datetime

# Constants
TOKEN_URL = "https://portalapi.lcegateway.com/Token"
REPORT_URL_BASE = "https://portalapi.lcegateway.com/GetReportBlobs"
TODAY = datetime.now().strftime("%Y-%m-%d")
BASE_DIR = Path.home() / "Downloads" / "LC Reports" / TODAY
BASE_DIR.mkdir(parents=True, exist_ok=True)

# Setup debug logging
DEBUG_LOG_DIR = Path.home() / "Downloads" / "LC Reports" / "_debug_logs"
DEBUG_LOG_DIR.mkdir(parents=True, exist_ok=True)
DEBUG_LOG_FILE = DEBUG_LOG_DIR / f"debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

def setup_debug_logger():
    """Setup a debug logger that writes to both file and console (if available)"""
    logger = logging.getLogger('LCReportDownloader')
    logger.setLevel(logging.DEBUG)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Check if running as EXE (PyInstaller sets this)
    is_exe = getattr(sys, 'frozen', False) or hasattr(sys, '_MEIPASS')
    
    # File handler - always create this
    try:
        # Ensure directory exists
        DEBUG_LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(DEBUG_LOG_FILE, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        # If we can't create log file, at least try console
        print(f"Warning: Could not create log file {DEBUG_LOG_FILE}: {e}")
    
    # Console handler - only add if not EXE or if console is available
    # In EXE mode with console=False, stdout might not be available
    if not is_exe:
        try:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            console_formatter = logging.Formatter('%(levelname)s - %(message)s')
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
        except Exception:
            # Silently fail if console isn't available
            pass
    
    # Log system information at startup
    logger.info("=" * 80)
    logger.info("LC REPORT DOWNLOADER - DEBUG SESSION STARTED")
    logger.info("=" * 80)
    logger.info(f"Running as EXE: {is_exe}")
    if is_exe:
        logger.info(f"EXE Path: {sys.executable if hasattr(sys, 'executable') else 'N/A'}")
    logger.info(f"System: {platform.system()} {platform.release()} {platform.version()}")
    logger.info(f"Python Version: {sys.version}")
    logger.info(f"Platform: {platform.platform()}")
    logger.info(f"Architecture: {platform.machine()}")
    logger.info(f"Log File: {DEBUG_LOG_FILE}")
    logger.info(f"Log Directory: {DEBUG_LOG_DIR}")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    logger.info("=" * 80)
    
    return logger

# Initialize logger
debug_logger = setup_debug_logger()

def generate_hmac_header(http_method, request_url):
    HMAC_USER = os.getenv("HMAC_USER")
    HMAC_KEY = os.getenv("HMAC_KEY")
    
    debug_logger.debug("=" * 80)
    debug_logger.debug("HMAC HEADER GENERATION")
    debug_logger.debug("=" * 80)
    debug_logger.debug(f"HTTP Method: {http_method}")
    debug_logger.debug(f"Original Request URL: {request_url}")
    debug_logger.debug(f"HMAC User: {HMAC_USER}")
    debug_logger.debug(f"HMAC Key Length: {len(HMAC_KEY) if HMAC_KEY else 0} characters")
    
    if not HMAC_USER or not HMAC_KEY:
        debug_logger.error("Missing HMAC credentials!")
        raise ValueError("HMAC_USER and HMAC_KEY environment variables must be set")
    
    nonce = uuid.uuid4().hex
    timestamp = str(int(time.time()))
    debug_logger.debug(f"Nonce: {nonce}")
    debug_logger.debug(f"Timestamp: {timestamp} (Unix time: {int(time.time())})")
    
    # Use the EXACT original approach that worked in v1.0.2
    # Encode the entire URL, then lowercase it (this is what v1.0.2 was doing)
    encoded_url = urllib.parse.quote(request_url, safe="").lower()
    debug_logger.debug(f"Encoded URL (original method - encode then lowercase): {encoded_url}")
    
    debug_logger.debug(f"Final Encoded URL (for HMAC): {encoded_url}")
    
    raw_string = HMAC_USER + http_method + encoded_url + timestamp + nonce
    debug_logger.debug(f"Raw String (before hashing): {HMAC_USER} + {http_method} + {encoded_url} + {timestamp} + {nonce}")
    debug_logger.debug(f"Raw String Length: {len(raw_string)} characters")
    
    raw_bytes = raw_string.encode("utf-8")
    key_bytes = base64.b64decode(HMAC_KEY)
    signature = base64.b64encode(hmac.new(key_bytes, raw_bytes, hashlib.sha256).digest()).decode()
    
    hmac_header = f"amx {HMAC_USER}:{signature}:{nonce}:{timestamp}"
    debug_logger.debug(f"Generated HMAC Header: {hmac_header}")
    debug_logger.debug("=" * 80)
    
    return hmac_header

def get_token():
    debug_logger.debug("=" * 80)
    debug_logger.debug("TOKEN REQUEST")
    debug_logger.debug("=" * 80)
    
    GATEWAY_USERNAME = os.getenv("GATEWAY_USERNAME")
    GATEWAY_PASSWORD = os.getenv("GATEWAY_PASSWORD")
    
    debug_logger.debug(f"Username: {GATEWAY_USERNAME}")
    debug_logger.debug(f"Password Length: {len(GATEWAY_PASSWORD) if GATEWAY_PASSWORD else 0} characters")
    debug_logger.debug(f"Token URL: {TOKEN_URL}")
    
    if not GATEWAY_USERNAME or not GATEWAY_PASSWORD:
        debug_logger.error("Missing gateway credentials!")
        raise ValueError("GATEWAY_USERNAME and GATEWAY_PASSWORD environment variables must be set")
    
    payload = {
        "grant_type": "password",
        "username": GATEWAY_USERNAME,
        "password": GATEWAY_PASSWORD
    }
    debug_logger.debug(f"Request Payload: grant_type=password, username={GATEWAY_USERNAME}")
    
    try:
        response = requests.post(TOKEN_URL, data=payload)
        debug_logger.debug(f"Response Status Code: {response.status_code}")
        debug_logger.debug(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 401:
            debug_logger.error(f"Token request failed with 401: {response.text[:200]}")
            raise ValueError(f"Authentication failed: Invalid username or password (Status: {response.status_code})")
        
        response.raise_for_status()
        token = response.json()["access_token"]
        debug_logger.debug(f"Token obtained successfully (length: {len(token)} characters)")
        debug_logger.debug(f"Token (first 50 chars): {token[:50]}...")
        debug_logger.debug("=" * 80)
        return token
    except requests.exceptions.RequestException as e:
        debug_logger.error(f"Token request exception: {str(e)}")
        raise

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
