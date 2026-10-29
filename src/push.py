"""推到 Larch（照 larch-tangshi 的 src/push.py）：快照 → 重建 → 素材網址換成 jsDelivr（每個檔釘自己最後改動的 commit）
→ 整包 PUT（If-Match）→ 讀回比對 → 預熱 jsDelivr。素材不存 Larch（作者 10-29：用公開 repo 走 jsDelivr）。
素材要先 commit 並推上 GitHub（yazelin/larch-ember），jsDelivr 才抓得到。

    python3 src/push.py "這次改了什麼"
"""
import json, os, re, sys, time, pathlib, subprocess, urllib.request, urllib.error, urllib.parse
sys.path.insert(0, os.path.dirname(__file__))
import build

ROOT = build.R
REPO = 'yazelin/larch-ember'
KEY = open(os.path.expanduser('~/.config/larch/key')).read().strip()
BASE = f'https://larch.ink/api/agent/projects/{build.PROJECT_ID}'


class HttpFail(SystemExit):
    def __init__(self, msg, status=None):
        super().__init__(msg); self.status = status


def req(method, body=None, etag=None, tries=6):
    """429、5xx、網路錯誤退避重試；其他 HTTP 錯誤直接結束。"""
    h = {'Authorization': 'Bearer ' + KEY, 'Content-Type': 'application/json'}
    if etag: h['If-Match'] = etag
    last = None
    for t in range(tries):
        try:
            r = urllib.request.Request(BASE, method=method, headers=h, data=json.dumps(body).encode() if body is not None else None)
            with urllib.request.urlopen(r, timeout=300) as resp:
                return resp.headers.get('ETag'), json.loads(resp.read() or b'{}')
        except urllib.error.HTTPError as e:
            last = f'{e.code} {e.read()[:300]}'
            if e.code != 429 and e.code < 500 or tries == 1: raise HttpFail(f'{method} → {last}', e.code)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last = repr(e)
            if tries == 1: raise HttpFail(f'{method} → {last}')
        print(f'{method} 失敗（{last}），{10 * (t + 1)} 秒後重試', flush=True)
        time.sleep(10 * (t + 1))
    raise HttpFail(f'{method} 重試 {tries} 次仍失敗：{last}')


def _git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def to_cdn(text):
    """/files/assets/… → jsDelivr，每個檔釘在它自己最後一次改動的 commit（沒改的檔網址不變，快取一直熱）。"""
    sha = _git('rev-parse', 'HEAD').strip()
    dirty = [l for l in _git('status', '--porcelain', '--', 'assets').splitlines() if l.strip()]
    if dirty: raise SystemExit(f'素材有沒 commit 的變更，jsDelivr 抓不到：{dirty[:5]}')
    if not _git('branch', '-r', '--contains', sha).strip():
        raise SystemExit(f'{sha[:7]} 還沒推上 GitHub，jsDelivr 抓不到；先 git push')
    last = {}
    def pin(m):
        rel = m.group(1)
        if rel not in last: last[rel] = _git('log', '-1', '--format=%H', '--', f'assets/{rel}').strip()
        if not last[rel]: raise SystemExit(f'assets/{rel} 沒有 commit 紀錄')
        return f'https://cdn.jsdelivr.net/gh/{REPO}@{last[rel]}/assets/{rel}'
    return re.sub(r'/files/assets/([\w./-]+\.(?:png|webp|jpg|mp3))', pin, text)


def prewarm(text):
    """每個 jsDelivr 網址先抓一次（冷 2 秒以上、熱 0.1～0.2 秒）；冷抓逾時被快取成 404 的，清掉再抓。"""
    from concurrent.futures import ThreadPoolExecutor
    urls = sorted(set(re.findall(r'https://cdn\.jsdelivr\.net/gh/[^"\\]+', text)))
    def fetch(u):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'}), timeout=120) as r: return r.status
        except urllib.error.HTTPError as e: return e.code
        except Exception: return 0
    def get(u):
        q, code = urllib.parse.quote(u, safe=':/@'), 0
        for _ in range(3):
            code = fetch(q)
            if code == 200: return 200
            if code == 404: fetch(q.replace('https://cdn.jsdelivr.net/', 'https://purge.jsdelivr.net/', 1))
        return code
    with ThreadPoolExecutor(3) as ex: codes = list(ex.map(get, urls))
    bad = [u for u, c in zip(urls, codes) if c != 200]
    print(f'預熱 jsDelivr：{len(urls) - len(bad)}/{len(urls)} 個檔回 200', flush=True)
    if bad: raise SystemExit(f'專案已經推上去了，但這些檔 jsDelivr 抓不到（玩家會看不到）：{bad[:5]}')


def content_key(board):
    """比對用的內容指紋：卡片 id、類型、背景、台詞、插件內容、連線。"""
    def node(n):
        d = n['data']
        return (n['id'], d.get('type'), d.get('background'), [l.get('text') for l in d.get('dialogueLines') or []],
                (d.get('pluginValues') or {}).get('content'))
    return json.dumps([[node(n) for n in board['nodes']], sorted((e['source'], e['target']) for e in board['edges'])],
                      ensure_ascii=False, sort_keys=True)


def main(summary):
    etag, cur = req('GET')
    snap = ROOT / 'snapshots' / time.strftime('%Y%m%d-%H%M%S.json')
    snap.parent.mkdir(exist_ok=True)
    snap.write_text(json.dumps(cur, ensure_ascii=False))
    print('快照', snap)

    built = json.loads(to_cdn(json.dumps(build.build(), ensure_ascii=False)))
    text = json.dumps(built, ensure_ascii=False)
    left = re.findall(r'/files/assets/[^"\\]+', text)
    if left: raise SystemExit(f'還有沒換掉的本機路徑：{left[:5]}')

    etag, cur = req('GET')
    online = cur.get('project', cur)
    project = dict(online)
    # ponytail: 整個專案換成重製版（作者 10-29 點頭）；設定以本機為準，作者在網頁改的其他設定（本機沒有的鍵）保留
    for k in ('boards', 'nodes', 'edges', 'variables', 'activeBoardId', 'name', 'description', 'projectThumbnail'):
        if k in built: project[k] = built[k]
    project['settings'] = {**(online.get('settings') or {}), **built['settings']}
    try:
        req('PUT', {'project': project, 'summary': summary}, etag, tries=1)
    except HttpFail as e:
        if e.status in (409, 412): raise SystemExit(f'PUT 被擋下（{e.status}）：網頁上有人改過專案（編輯器分頁開著？）。先確認再重推。')
        raise

    _, back = req('GET')
    back = back.get('project', back)
    b0, w0 = back['boards'][0], built['boards'][0]
    def check(ok, msg):
        if not ok: raise SystemExit('讀回比對失敗：' + msg)
    check(back.get('name') == built['name'], f"名稱是 {back.get('name')}")
    check(back.get('description') == built['description'], '簡介沒更新')
    check(content_key(b0) == content_key(w0), '卡片內容（台詞、插件、背景、連線）跟本機不一樣')
    check(back['settings'].get('plugins', {}).get('credits-roll', {}).get('enabled'), '片尾字卷插件沒開')
    ui = bool(back['settings'].get('customInterfaces', {}).get('title'))
    prewarm(text)
    print('推送完成，讀回比對通過：', len(b0['nodes']), '張卡、', len(b0['edges']), '條線；自訂標題介面', '有寫進去' if ui else '沒寫進去（要在編輯器匯入 ui/信紙與餘燼.html）')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '更新')
