#!/bin/bash
cd ~/larch-ember/design/讀者反應
P=$(cat prompt.txt)
( llmshare raw deepseek-v4.1-flash:1017 "$P" > deepseek.md 2> deepseek.err ) &
( python3 - <<'PY' > gemini.md 2> gemini.err
import json, urllib.request
p = open('prompt.txt', encoding='utf-8').read()
r = urllib.request.urlopen(urllib.request.Request('http://192.168.11.11:8070/api/chat', json.dumps({'prompt': p}).encode(), {'Content-Type': 'application/json'}), timeout=600).read().decode()
try: r = json.loads(r).get('response') or r
except Exception: pass
print(r)
PY
) &
( cd ~/larch-ember && codex exec --skip-git-repo-check -s read-only - < design/讀者反應/prompt.txt > design/讀者反應/codex.md 2> design/讀者反應/codex.err ) &
wait
echo done > done.flag
