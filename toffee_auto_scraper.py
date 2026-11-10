import requests
import json
from datetime import datetime

# ----------------- অ্যাকাউন্ট কনফিগারেশন -----------------
BEARER_TOKEN = "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJodHRwczovL3RvZmZlZWxpdmUuY29tIiwiY291bnRyeSI6IkJEIiwiZF9pZCI6IjlhZDJjMzMwLTM4Y2QtNGNhMS1iYTkyLWI0YmMyODMzMDQxMSIsImV4cCI6MTc5ODE3ODYxNSwiaWF0IjoxNzk0MjkwNjE1LCJpc3MiOiJ0b2ZmZWVsaXZlLmNvbSIsImp0aSI6IjAxMDZlMjEwLTQ2MTAtNDdlOS1iMGQyLWE1YmRjNDRmOTBiNV8xNzk0MjkwNjE1IiwicHJvdmlkZXIiOiJ0b2ZmZWUiLCJyX2lkIjoiODNhMDVkNDItNjA2Ny00MjkxLTk0ZDAtYTUyNDM0OWQ0YmY1Iiwic19pZCI6IjBlYTExMTBiLTZhZGUtNGUwZC04NjBlLTZjNmUxNDEwOTA4MiIsInRva2VuIjoiYWNjZXNzIiwidHlwZSI6InN1YnNjcmliZXIifQ.StoEf-wLHfNTLPBupMIrkz42SbPQxZ1cMmaRnHzScBzcAWposuMGgRokmoJmbrDfE03Zv69OKFKfEW3DVxDUMg"

BASE_RAIL_URL = "https://content-prod.services.toffeelive.com/toffee/BD/DK/web/rail/generic/editorial-dynamic"
PLAYBACK_BASE = "https://entitlement-prod.services.toffeelive.com/toffee/BD/DK/web/playback"

# আপনার স্ক্রিনশট থেকে নেওয়া রেল আইডিগুলোর পূর্ণাঙ্গ তালিকা
RAIL_IDS = [
    "08d90cecf964eb9a5f6be2e1887066fd",
    "36eff4e5ed817e63c4a0859a0e11f1d5",
    "3adc241ef7c7788fb724d83a2c7cc3a5",
    "3d7f22f7c8c5e11127f7909a7426cb7e",
    "526bef1c147f0f61996cd39e337633e4",
    "55fdb2bedaca2de399b470fb0ce14117",
    "84a2451df95d2eb3d2b0d09c5fc34fb1",
    "911e8f640af3a8892b628714d4acc133",
    "9988b22058e87ba742a8d734e640e759",
    "be7d42854f019db42fbc22153674b888",
    "cb7ea308e7742680ea8df1aae153bc9b",
    "cceb01a3ecb01516539b0adad38c1400",
    "dbe3abe54a57d6ce187394341a603a7a",
    "ee4e3bee9cecd2a5da243a39d81236d8"
]

session = requests.Session()
session.headers.update({
    "User-Agent": "okhttp/5.1.0",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Authorization": f"Bearer {BEARER_TOKEN}",
    "client-api-header": "null",
    "Accept-Encoding": "gzip"
})

def fetch_all_channels():
    discovered_channels = {}
    print("[*] Scanning all Toffee rail APIs for channels...")
    
    for rail_id in RAIL_IDS:
        url = f"{BASE_RAIL_URL}/{rail_id}"
        try:
            res = session.get(url, timeout=10)
            if res.status_code != 200:
                continue
                
            data = res.json()
            items = data.get("list", [])
            
            for item in items:
                if item.get("v_type") == "channels" or item.get("subType") == "Live_TV":
                    ch_id = item.get("id")
                    ch_name = item.get("title")
                    
                    if ch_id and ch_id not in discovered_channels:
                        logo_url = ""
                        images = item.get("images", [])
                        if isinstance(images, list) and len(images) > 0 and isinstance(images[0], dict):
                            logo_path = images[0].get("path", "")
                            if logo_path:
                                logo_url = f"https://assets-prod.services.toffeelive.com/{logo_path}"
                        elif "ogImage" in item:
                            logo_url = item.get("ogImage", "")
                        
                        genres = item.get("genres", [])
                        category = genres[0] if isinstance(genres, list) and len(genres) > 0 else "Live TV"
                        
                        discovered_channels[ch_id] = {
                            "id": ch_id,
                            "name": ch_name,
                            "category": category,
                            "logo": logo_url
                        }
        except Exception as e:
            print(f"[!] Error scanning rail {rail_id}: {e}")
            
    channel_list = list(discovered_channels.values())
    print(f"[*] Total unique channels discovered: {len(channel_list)}")
    return channel_list

def get_channel_stream(channel_id):
    playback_url = f"{PLAYBACK_BASE}/{channel_id}"
    try:
        res = session.post(playback_url, json={}, timeout=10)
        if res.status_code != 200:
            return None
            
        data = res.json()
        stream_url = None
        
        if "playbackDetails" in data and "data" in data["playbackDetails"]:
            data_list = data["playbackDetails"]["data"]
            if isinstance(data_list, list) and len(data_list) > 0:
                raw_url = data_list[0].get("url")
                stream_url = raw_url.replace(" ", "") if raw_url else None
                
        if not stream_url:
            stream_url = data.get("stream_url") or data.get("url") or data.get("playback_url")
            
        return stream_url
    except Exception:
        pass
    return None

def main():
    raw_channels = fetch_all_channels()
    if not raw_channels:
        print("[!] No channels found.")
        return

    output_result = {
        "updated_at": datetime.now().isoformat() + "Z",
        "total_channels": 0,
        "channels": []
    }

    total = len(raw_channels)
    print(f"[*] Starting stream capture for {total} channels...")

    for idx, ch in enumerate(raw_channels, start=1):
        ch_id = ch["id"]
        ch_name = ch["name"]
        
        stream_link = get_channel_stream(ch_id)
        if stream_link:
            print(f"[{idx}/{total}] Captured: {ch_name}")
            host = stream_link.split("/")[2] if "://" in stream_link else "prod-linear-media.toffeelive.com"
            
            headers = {
                "Host": host,
                "cookie": "",
                "user-agent": "okhttp/5.1.0",
                "client-api-header": "null",
                "accept-encoding": "gzip"
            }

            output_result["channels"].append({
                "category_name": ch["category"],
                "name": ch_name,
                "link": stream_link,
                "headers": headers,
                "logo": ch["logo"]
            })
        else:
            print(f"[{idx}/{total}] Skipped: {ch_name}")

    output_result["total_channels"] = len(output_result["channels"])

    with open("toffee_channels.json", "w", encoding="utf-8") as f:
        json.dump(output_result, f, indent=4, ensure_ascii=False)
        
    with open("toffee_channels.m3u", "w", encoding="utf-8") as m3u_file:
        m3u_file.write("#EXTM3U\n")
        for ch in output_result["channels"]:
            name = ch["name"]
            cat = ch["category_name"]
            logo = ch["logo"]
            link = ch["link"]
            
            m3u_file.write(f'#EXTINF:-1 tvg-logo="{logo}" group-title="{cat}",{name}\n')
            m3u_file.write(f'#EXTVLCOPT:http-user-agent=okhttp/5.1.0\n')
            m3u_file.write(f'{link}\n')

    print(f"\n[*] Finished! Successfully saved {output_result['total_channels']} channels.")

if __name__ == "__main__":
    main()
