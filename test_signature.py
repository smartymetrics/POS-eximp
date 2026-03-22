import requests
import base64
from urllib.parse import urlparse, parse_qs

def _get_google_drive_direct_link(url):
    if not url: return url
    if "drive.google.com" not in url:
        # If it's a long string without drive.google.com, it might be a naked ID
        if len(url) > 20 and " " not in url:
            return f"https://drive.google.com/uc?export=download&id={url}"
        return url
    try:
        file_id = None
        if "/file/d/" in url:
            file_id = url.split("/file/d/")[1].split("/")[0]
        elif "id=" in url:
            parsed = urlparse(url)
            file_id = parse_qs(parsed.query).get("id", [None])[0]
        elif "/open?" in url:
            parsed = urlparse(url)
            file_id = parse_qs(parsed.query).get("id", [None])[0]
        
        if file_id:
            return f"https://drive.google.com/uc?export=download&id={file_id}"
    except Exception:
        pass
    return url

def test_fetch(url):
    print(f"Testing URL: {url}")
    direct = _get_google_drive_direct_link(url)
    print(f"Direct Link: {direct}")
    try:
        res = requests.get(direct, timeout=10)
        print(f"Status: {res.status_code}")
        print(f"Content-Type: {res.headers.get('Content-Type')}")
        if res.ok:
            print(f"Success! Fetched {len(res.content)} bytes.")
            return True
        else:
            print(f"Failed: {res.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")
    return False

# Test with a known public image or common formats
test_fetch("https://drive.google.com/file/d/1Xy_z.../view") # Example format
