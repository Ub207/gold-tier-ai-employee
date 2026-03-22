import os, json, requests
from pathlib import Path

for line in Path('D:/gold_tier/.env').read_text(encoding='utf-8').splitlines():
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        os.environ[k.strip()] = v.strip()

token = os.environ.get('FACEBOOK_ACCESS_TOKEN', '')
page_id = os.environ.get('FACEBOOK_PAGE_ID', '')

print("Posting test message to Facebook Page...")
r = requests.post(
    f'https://graph.facebook.com/v19.0/{page_id}/feed',
    data={
        'message': 'AI Employee Gold Tier test post - automation working! #AI #Automation',
        'access_token': token
    },
    timeout=15
)
data = r.json()
if 'error' in data:
    print("Error:", data['error']['message'])
else:
    print("Post successful!")
    print("Post ID:", data.get('id'))
    print("Live on Facebook page!")
