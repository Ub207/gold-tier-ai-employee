import os, json, requests
from pathlib import Path

for line in Path('D:/gold_tier/.env').read_text(encoding='utf-8').splitlines():
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        os.environ[k.strip()] = v.strip()

token = os.environ.get('FACEBOOK_ACCESS_TOKEN', '')
page_id = os.environ.get('FACEBOOK_PAGE_ID', '')

# Step 1: Check what this token is
print("Checking token info...")
r = requests.get(
    'https://graph.facebook.com/v19.0/me',
    params={'access_token': token, 'fields': 'id,name,category'},
    timeout=15
)
me = r.json()
print("Token belongs to:", me.get('name'), "| ID:", me.get('id'))
print("Category:", me.get('category', 'User (not a page)'))

# Step 2: Try posting directly
print("\nTrying to post...")
r2 = requests.post(
    f'https://graph.facebook.com/v19.0/{page_id}/feed',
    json={
        'message': 'AI Employee Gold Tier - System Test. Automation working! #AIEmployee #GoldTier',
        'access_token': token
    },
    timeout=15
)
data = r2.json()
if 'error' in data:
    print("Post Error:", data['error']['message'])
    print("Error Code:", data['error'].get('code'))
else:
    print("POST SUCCESSFUL!")
    print("Post ID:", data.get('id'))
