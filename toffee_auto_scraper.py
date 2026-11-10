import requests
import json
import re
from datetime import datetime

# ----------------- অ্যাকাউন্ট কনফিগারেশন -----------------
DEVICE_ID = "0c973f38-7b01-4ac2-8f0c-74635b1f6602"
SUBSCRIBER_ID = "0ea1110b-6ade-4e0d-860e-6c6e14109082"
MSISDN = "8801701982218"
APP_VERSION = "6.0.0"

BASE_URL = "https://toffeelive.com"
PLAYBACK_BASE = "https://entitlement-prod.services.toffeelive.com/toffee/BD/DK/web/playback"

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Origin": BASE_URL,
    "Referer": f"{BASE_URL}/",
    "Accept": "application/json, text/plain, */*",
    "x-device-id": DEVICE_ID,
    "x-subscriber-id": SUBSCRIBER_ID,
    "x-app-version": APP_VERSION,
    "x-platform": "web"
})

def discover_all_channels():
    discovered_channels = {}
    endpoints_to_scan = [
        f"{BASE_URL}/bn/live",
        f"{BASE_URL}/bn/sports"
    ]

    print("[*] Scanning Toffee pages for live/sports channels...")

    for url in endpoints_to_scan:
        try:
            res = session.get(url, timeout=15)
            if res.status_code != 200:
                continue

            slug_matches = re.findall(r'/(?:watch|live)/([A-Za-z0-9_-]{15,30})', res.text)
            for slug in slug_matches:
                if slug not in discovered_channels:
                    discovered_channels[slug] = {
                        "id": slug,
                        "name": f"Channel {slug[:6]}",
                        "category": "Sports" if "sports" in url else "Live TV",
                        "logo": ""
                    }

            match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', res.text)
            if match:
                data = json.loads(match.group(1))
                page_props = data.get("props", {}).get("pageProps", {})
                
                def extract_channel_objects(obj):
                    if isinstance(obj, dict):
                        if "id" in obj and ("title" in obj or "name" in obj):
                            cid = str(obj["id"])
                            discovered_channels[cid] = {
                                "id": cid,
                                "name": obj.get("title") or obj.get("name"),
                                "category": obj.get("category", "Live TV"),
                                "logo": obj.get("logo") or obj.get("poster") or ""
                            }
                        for k, v in obj.items():
                            extract_channel_objects(v)
