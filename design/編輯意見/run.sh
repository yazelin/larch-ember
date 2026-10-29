#!/bin/bash
cd ~/larch-ember/design/編輯意見
( llmshare raw deepseek-v4.1-flash:1017 "$(cat prompt.txt)" > deepseek.md 2> deepseek.err ) &
( python3 - <<'PY' > gemini.md 2> gemini.err
import json, os, re, ssl, urllib.request
key = next(l.split('=',1)[1].strip().strip('"') for l in open(os.path.expanduser('~/.bashrc')) if 'GEMINI_IMAGE_KEY=' in l)
p = open('prompt.txt', encoding='utf-8').read()
req = urllib.request.Request('https://192.168.11.11/gemini-web/api/chat', json.dumps({'prompt': p}).encode(), {'Content-Type': 'application/json', 'x-goog-api-key': key})
r = urllib.request.urlopen(req, timeout=900, context=ssl._create_unverified_context()).read().decode()
try: r = json.loads(r).get('response') or r
except Exception: pass
print(r)
PY
) &
( cd ~/larch-ember && codex exec --skip-git-repo-check -s read-only -o design/編輯意見/codex.md - < design/編輯意見/prompt.txt > design/編輯意見/codex.out 2> design/編輯意見/codex.err ) &
wait
echo done > done.flag
