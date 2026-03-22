import sys
from pathlib import Path

if len(sys.argv) < 2:
    print("Usage: python update_token.py YOUR_TOKEN_HERE")
    sys.exit(1)

new_token = sys.argv[1].strip()
env_path = Path('D:/gold_tier/.env')
content = env_path.read_text(encoding='utf-8')

# Replace token line
lines = []
for line in content.splitlines():
    if line.strip().startswith('FACEBOOK_ACCESS_TOKEN='):
        lines.append(f'FACEBOOK_ACCESS_TOKEN={new_token}')
        print("Token updated!")
    else:
        lines.append(line)

env_path.write_text('\n'.join(lines), encoding='utf-8')
print("Saved to .env")
