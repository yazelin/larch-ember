"""【尚未執行；執行＝寫入 Larch】介面 Skill 的網址只收 R2／larch.ink／相對路徑（jsDelivr 會被擋），介面用到的音效要先上傳到 Larch 拿 R2 網址。
這支把 ui/sfx/*.mp3 用 larch_upload_media 傳上去，結果記在 ui/hosted.json；ember.py 讀它，之後重跑 ember.py／pack.py 就會帶 R2 網址。
需要金鑰檔（~/.config/larch/key）。作者點頭之後才跑：python3 ui/host_audio.py（已上傳過的跳過）。標題 BGM 由別人做、不經過這裡。"""
import base64, json, os, pathlib, urllib.request
ROOT = pathlib.Path(__file__).resolve().parent.parent
PROJECT_ID = 'project-904c48a1-2797-4a7e-916a-75b1117e6211'
OUT = ROOT / 'ui/hosted.json'


def call(name, args, i=[0]):
    key = open(os.path.expanduser(os.environ.get('LARCH_KEY_FILE', '~/.config/larch/key'))).read().strip()
    H = {'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream'}
    i[0] += 1
    body = json.dumps({'jsonrpc': '2.0', 'id': i[0], 'method': 'tools/call', 'params': {'name': name, 'arguments': args}}).encode()
    with urllib.request.urlopen(urllib.request.Request('https://larch.ink/mcp', body, H), timeout=180) as r:
        raw = r.read().decode()
    if raw.startswith('event:') or '\ndata:' in raw:
        raw = [l[5:] for l in raw.splitlines() if l.startswith('data:')][-1]
    res = json.loads(raw)
    if 'error' in res or res['result'].get('isError'):
        raise SystemExit(f'{name} 失敗：{json.dumps(res, ensure_ascii=False)[:500]}')
    return json.loads(res['result']['content'][0]['text'])


if __name__ == '__main__':
    hosted = json.loads(OUT.read_text()) if OUT.exists() else {}
    for f in sorted((ROOT / 'ui/sfx').glob('*.mp3')):
        k = f.stem
        if k in hosted:
            continue
        r = call('larch_upload_media', {'projectId': PROJECT_ID, 'name': f'ui-{k}.mp3', 'mimeType': 'audio/mpeg', 'category': 'sfx',
                                         'base64': base64.b64encode(f.read_bytes()).decode()})
        url = next((v for v in json.dumps(r).split('"') if v.startswith('https://') and v.endswith('.mp3')), None)
        assert url, ('上傳結果找不到網址', json.dumps(r, ensure_ascii=False)[:400])
        hosted[k] = url
        OUT.write_text(json.dumps(hosted, ensure_ascii=False, indent=1))
        print(k, url)
