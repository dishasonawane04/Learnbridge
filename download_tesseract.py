import urllib.request
import json
import ssl
import sys

print("Fetching latest Tesseract release URL from API...")
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

req = urllib.request.Request("https://api.github.com/repos/UB-Mannheim/tesseract/releases/latest", headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req, context=ctx) as response:
        data = json.loads(response.read().decode('utf-8'))
        
    exe_url = None
    for asset in data.get('assets', []):
        if str(asset.get('name', '')).endswith('.exe') and 'w64' in str(asset.get('name', '')):
            exe_url = asset['browser_download_url']
            break
            
    if exe_url:
        print(f"Found URL: {exe_url}")
        print("Downloading...")
        exe_req = urllib.request.Request(exe_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(exe_req, context=ctx) as exe_response, open("tesseract_installer.exe", 'wb') as f:
            f.write(exe_response.read())
        print("Download complete.")
    else:
        print("Could not find EXE link in the release assets.")
        
except Exception as e:
    print(f"Error: {e}")
