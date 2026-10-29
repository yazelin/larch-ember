#!/bin/bash
cd ~/larch-ember/design/編輯意見
python3 - <<'PY' > gemini.md 2> gemini.err
import json, os, ssl, urllib.request
key = next(l.split('=',1)[1].strip().strip('"') for l in open(os.path.expanduser('~/.bashrc')) if 'GEMINI_IMAGE_KEY=' in l)
p = open('prompt_gemini.txt', encoding='utf-8').read()
req = urllib.request.Request('https://192.168.11.11/gemini-web/api/chat', json.dumps({'prompt': p}).encode(), {'Content-Type': 'application/json', 'x-goog-api-key': key})
r = json.loads(urllib.request.urlopen(req, timeout=900, context=ssl._create_unverified_context()).read().decode())
print(r.get('text') or r.get('response') or json.dumps(r, ensure_ascii=False)[:2000])
PY
wc -c gemini.md
