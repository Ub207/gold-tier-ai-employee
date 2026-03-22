import os, json, requests
from pathlib import Path

for line in Path('D:/gold_tier/.env').read_text(encoding='utf-8').splitlines():
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        os.environ[k.strip()] = v.strip()

token = os.environ.get('FACEBOOK_ACCESS_TOKEN', '')
page_id = os.environ.get('FACEBOOK_PAGE_ID', '')

print("Checking Facebook Page:", page_id)

# Get Instagram account linked to this Facebook Page
r = requests.get(
    f'https://graph.facebook.com/v19.0/{page_id}',
    params={
        'access_token': token,
        'fields': 'id,name,instagram_business_account'
    },
    timeout=15
)
data = r.json()
if 'error' in data:
    print("Error:", data['error']['message'])
else:
    print("Page Name:", data.get('name'))
    ig = data.get('instagram_business_account')
    if ig:
        print("Instagram Business Account ID:", ig['id'])
        print("\nAdd this to .env:")
        print(f"INSTAGRAM_USER_ID={ig['id']}")
    else:
        print("Instagram Business Account linked nahi hai is Page se")
        print("Facebook Page ko Instagram Business account se link karo")
