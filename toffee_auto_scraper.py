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
    """
    ওয়েবসাইট থেকে কোনো ম্যানুয়াল আইডি ছাড়া স্বয়ংক্রিয়ভাবে
    সব লাইভ ও স্পোর্টস চ্যানেলের ডেটা পার্স করে বের করে।
    """
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

            # পদ্ধতি ১: রেগুলার এক্সপ্রেশন দিয়ে ওয়াচ রুটের সব ইউনিক চ্যানেল স্লাগ/আইডি ফিল্টার
            # Toffee-এর চ্যানেল লিঙ্ক সাধারণত /watch/ বা /live/ এর পরে আইডি থাকে
            slug_matches = re.findall(r'/(?:watch|live)/([A-Za-z0-9_-]{15,30})', res.text)
            for slug in slug_matches:
                if slug not in discovered_channels:
                    discovered_channels[slug] = {
                        "id": slug,
                        "name": f"Channel {slug[:6]}",
                        "category": "Sports" if "sports" in url else "Live TV"
                    }

            # পদ্ধতি ২: Next.js হাইড্রেটেড ডেটা অবজেক্ট পার্স করা (নাম ও লোগো সহ পাওয়ার জন্য)
            match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', res.text)
            if match:
                data = json.loads(match.group(1))
                page_props = data.get("props", {}).get("pageProps", {})
                
                # রিকার্সিভলি অবজেক্ট স্ক্যান করে চ্যানেল লিস্ট খুঁজে বের করা
                def extract_channel_objects(obj):
                    if isinstance(obj, dict):
                        # কোনো অবজেক্টে id এবং title/name থাকলে সেটি চ্যানেল হিসেবে ধরা
                        if "id" in obj and ("title" in obj or "name" in obj) and "category" in obj:
                            cid = str(obj["id"])
                            discovered_channels[cid] = {
                                "id": cid,
                                "name": obj.get("title") or obj.get("name"),
                                "category": obj.get("category", "Live TV"),
                                "logo": obj.get("logo") or obj.get("poster") or ""
                            }
                        for k, v in obj.items():
                            extract_channel_objects(v)
                    elif isinstance(obj, list):
                        for item in obj:
                            extract_channel_objects(item)

                extract_channel_objects(page_props)

        except Exception as e:
            print(f"[!] Error scanning {url}: {e}")

    return list(discovered_channels.values())

def get_channel_stream(channel_id):
    """রেজিস্টার্ড ইউজার আইডি পাস করে ফ্রেশ প্লেব্যাক লিঙ্ক ও সিডিএন কুকি নেওয়া"""
    playback_url = f"{PLAYBACK_BASE}/{channel_id}"
    payload = {
        "device_id": DEVICE_ID,
        "subscriber_id": SUBSCRIBER_ID,
        "subscriber_type": "REGISTERED",
        "msisdn": MSISDN
    }

    try:
        res = session.post(playback_url, json=payload, timeout=10)
        if res.status_code == 200:
            data = res.json()
            stream_url = data.get("stream_url") or data.get("url") or data.get("playback_url")
            
            # এজ সিডিএন কুকি কালেকশন
            cookies_dict = session.cookies.get_dict()
            cookie_header = "; ".join([f"{k}={v}" for k, v in cookies_dict.items()])
            
            return stream_url, cookie_header
    except Exception:
        pass
    return None, None

def main():
    channels = discover_all_channels()
    total = len(channels)
    print(f"[*] Total channels discovered automatically: {total}")

    output_result = {
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "total_channels": 0,
        "channels": []
    }

    for idx, ch in enumerate(channels, start=1):
        ch_id = ch["id"]
        ch_name = ch.get("name", "Unknown")
        
        stream_link, cookies = get_channel_stream(ch_id)
        if stream_link:
            print(f"[{idx}/{total}] Captured: {ch_name}")
            
            # সিডিএন হোস্ট পার্স করা
            host = stream_link.split("/")[2] if "://" in stream_link else "prod-linear-media.toffeelive.com"
            
            headers = {
                "User-Agent": session.headers["User-Agent"],
                "Referer": "https://toffeelive.com/",
                "Origin": "https://toffeelive.com",
                "Host": host
            }
            if cookies:
                headers["Cookie"] = cookies

            output_result["channels"].append({
                "id": ch_id,
                "name": ch_name,
                "category": ch.get("category", "Live TV"),
                "logo": ch.get("logo", ""),
                "link": stream_link,
                "headers": headers
            })

    output_result["total_channels"] = len(output_result["channels"])

    # ফাইল এক্সপোর্ট (JSON)
    with open("toffee_channels.json", "w", encoding="utf-8") as f:
        json.dump(output_result, f, indent=2, ensure_ascii=False)

    print(f"\n[*] Finished! Successfully saved {output_result['total_channels']} working channels to toffee_channels.json")

if __name__ == "__main__":
    main()
