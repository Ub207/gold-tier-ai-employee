import os, json, requests
from pathlib import Path

for line in Path('D:/gold_tier/.env').read_text(encoding='utf-8').splitlines():
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        os.environ[k.strip()] = v.strip()

token = os.environ.get('FACEBOOK_ACCESS_TOKEN', '')
if not token:
    print("ERROR: FACEBOOK_ACCESS_TOKEN .env mein nahi mila")
    exit(1)

print("Testing Facebook connection...")
try:
    r = requests.get(
        'https://graph.facebook.com/v19.0/me',
        params={'access_token': token, 'fields': 'id,name'},
        timeout=15
    )
    data = r.json()
    if 'error' in data:
        print("Facebook Error:", data['error']['message'])
    else:
        print("Facebook Connected!")
        print("Name:", data.get('name'))
        print("ID:", data.get('id'))
except Exception as e:
    print("Error:", e)
