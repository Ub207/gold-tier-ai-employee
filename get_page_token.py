import os, json, requests
from pathlib import Path

for line in Path('D:/gold_tier/.env').read_text(encoding='utf-8').splitlines():
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        os.environ[k.strip()] = v.strip()

user_token = os.environ.get('FACEBOOK_ACCESS_TOKEN', '')

print("Getting your Facebook Pages...")
r = requests.get(
    'https://graph.facebook.com/v19.0/me/accounts',
    params={'access_token': user_token},
    timeout=15
)
data = r.json()

if 'error' in data:
    print("Error:", data['error']['message'])
elif not data.get('data'):
    print("Koi page nahi mila — token mein pages_show_list permission add karo")
else:
    print("\nTumhare Pages:")
    for page in data['data']:
        print(f"\nPage: {page['name']}")
        print(f"Page ID: {page['id']}")
        print(f"Page Access Token: {page['access_token']}")
        print("\n.env mein ye update karo:")
        print(f"FACEBOOK_ACCESS_TOKEN={page['access_token']}")
        print(f"FACEBOOK_PAGE_ID={page['id']}")
