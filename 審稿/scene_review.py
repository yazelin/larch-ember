#!/usr/bin/env python3
"""讀稿人、提示詞、一幕幕讀稿（sweep）。從《續》的 xu/審稿/scene_review.py 移植（2026-10-23，作者同意）；日常用 runner.py 的 read／packet／gate／ship，不必直接叫這支。
  sweep <劇本.md> [場代號…]   每場讀稿人各找問題（含七項評分），另做設定查證；不給場代號就全部
  status <劇本.md>            每場審到第幾輪、審過後有沒有改
輸出存到 審稿/紀錄/。llmshare 只用 deepseek-v4.1-flash:1017（作者 2026-10-20）。"""
import os, subprocess, sys, pathlib, datetime, time, re, json, hashlib
ROOT = pathlib.Path(__file__).resolve().parent.parent          # ~/larch-ember
OUT = pathlib.Path(__file__).resolve().parent / '紀錄'; OUT.mkdir(exist_ok=True)
RPM_FILE = pathlib.Path.home() / '.cache' / 'llmshare-rpm'      # 本機所有 llmshare 呼叫共用的請求時間戳（跟《續》同一個檔）
AVAIL = pathlib.Path.home() / '.cache' / 'ember-review-readers.json'


def rpm_slot(limit=15):
    """llmshare 這把金鑰每分鐘只准 15 次（2026-10-22 量到）；本機所有呼叫加起來最近 60 秒滿 limit 次就等。"""
    import fcntl
    RPM_FILE.parent.mkdir(exist_ok=True)
    while True:
        with open(RPM_FILE, 'a+') as f:
            fcntl.flock(f, fcntl.LOCK_EX); f.seek(0); now = time.time()
            ts = [float(x) for x in f.read().split() if now - float(x) < 60]
            if len(ts) < limit:
                f.seek(0); f.truncate(); f.write(' '.join(map(str, ts + [now]))); return
            wait = 60.5 - (now - min(ts))
        time.sleep(wait)


def _bashrc(name):   # .bashrc 尾端的 export 對非互動腳本無效，直接讀檔
    for l in open(os.path.expanduser('~/.bashrc'), encoding='utf-8', errors='ignore'):
        if l.strip().startswith(('export ' + name + '=', name + '=')): return l.split('=', 1)[1].strip().strip('"').strip("'")
    return os.environ.get(name, '')


def ds(p):
    rpm_slot(); return subprocess.run(['llmshare', 'raw', 'deepseek-v4.1-flash:1017', p], capture_output=True, text=True, timeout=600).stdout.strip()
def gm(p):   # 作者自架 gemini-web（.11 瀏覽器驅動）；長回應可能截斷，所以不做查證
    import urllib.request
    q = urllib.request.Request('http://192.168.11.11:8070/api/chat', data=json.dumps({'prompt': p, 'timeout': 300}).encode(),
                               headers={'Content-Type': 'application/json', 'x-goog-api-key': _bashrc('GEMINI_IMAGE_KEY')})
    try: j = json.loads(urllib.request.urlopen(q, timeout=360).read().decode()); return (j.get('text') or j.get('response') or '').strip()
    except Exception: return ''
def ag(model):   # 本機 agy（Antigravity CLI）；plan 模式、在 /tmp 跑，不讀檔不改檔
    def f(p):
        try:
            r = subprocess.run(['agy', '-p', p + '\n只回答，不要讀檔或使用任何工具。', '--model', model, '--mode', 'plan'], capture_output=True, text=True, timeout=900, cwd='/tmp')
            return '' if 'AGY_ERROR' in r.stdout or 'quota' in r.stdout.lower()[:300] else r.stdout.strip()
        except Exception: return ''
    return f
def cx(p):
    r = subprocess.run(['codex', 'exec', '-m', os.environ.get('CODEX_MODEL', 'gpt-6.1-sol'), '--skip-git-repo-check', '-s', 'read-only', '-C', '/tmp', '-'], input=p, capture_output=True, text=True, timeout=900).stdout
    return r.split('tokens used', 1)[-1].split('\n', 1)[-1].strip() if 'tokens used' in r else r.strip()
_ds_lock = __import__('threading').Lock()
def qw(p):   # llmshare 上的 qwen3.5:397b；2026-10-29 argon 額度用完（七天）時補第三位讀稿人
    try: return subprocess.run(['llmshare', 'raw', 'qwen3.5:397b', p], capture_output=True, text=True, timeout=900, env={**os.environ, 'LLMSHARE_ALLOW_ANY': '1'}).stdout.strip()
    except Exception: return ''


def dsl(p):   # 同一時間只送一個、間隔 3 秒
    with _ds_lock: time.sleep(3); return ds(p)

# 讀稿人＝四個家族各一位（跟《續》同一組）。2026-10-23 移植時 agy 的 opus 與 argon 額度用完，所以 available() 會把它們拿掉；
# google 家族缺席時用作者自架的 gemini-web 補位（《續》因為長回應截斷不用它，這裡只在 argon 不在時才上場）。
# 要強制指定：環境變數 READERS=codex,deepseek,geminiweb
PREFERRED = {'opus': ag('claude-opus-5-5-high'), 'codex': cx, 'argon': ag('gemini-4-argon-high'), 'deepseek': dsl}
FALLBACK = {'google': ('geminiweb', gm)}
FAMILY = {'qwen': 'alibaba', 'claude': 'anthropic', 'opus': 'anthropic', 'codex': 'openai', 'argon': 'google', 'geminiweb': 'google', 'deepseek': 'deepseek'}
ALL = {**PREFERRED, 'geminiweb': gm, 'qwen': qw}


def available():
    """探一次各讀稿人（快取 30 分鐘），額度用完或沒回應的拿掉；google 家族全缺時補 gemini-web。"""
    if os.environ.get('READERS'): return {k: ALL[k] for k in os.environ['READERS'].split(',') if k in ALL}
    cache = json.loads(AVAIL.read_text()) if AVAIL.exists() else {}
    if time.time() - cache.get('t', 0) > 1800:
        ok = {}
        for k, f in PREFERRED.items():
            try: ok[k] = bool(f('回一個字：好。').strip()) if k in ('opus', 'argon') else True   # codex、deepseek 失敗由 call() 重試，不先探
            except Exception: ok[k] = False
        cache = {'t': time.time(), 'ok': ok}; AVAIL.write_text(json.dumps(cache))
    r = {k: f for k, f in PREFERRED.items() if cache['ok'].get(k)}
    if not any(FAMILY[k] == 'google' for k in r): k, f = FALLBACK['google']; r[k] = f
    return r


READERS = available()

READ = """你是互動小說（視覺小說）的挑剔審稿人，用台灣讀者的耳朵一幕一幕讀，也要出聲念念看。下面是一場戲（第 N 行是這場內的行號）。
格式說明：「講者：台詞」；「余靜（心）」是她的心聲；「旁白」只該寫畫面上看得到的事；（唱）是歌詞，照歌詞檔不能改，不要挑歌詞；（念）是念信或念紙條；〔圖〕〔掉字〕是演出標記；台語台詞後面括號是華語字幕。
這部作品的病是早發性阿茲海默症（以找詞困難為主）。余靜在作者定的方向裡：用笑遮羞、笑完安靜；為別人的感受道歉；病識感時有時無；對她以為是「工作人員」的丈夫客氣、有距離；忘記要有代價。程希一次只問一個問題、自稱工作人員，但他不是沒有情緒的聖人。

一、找問題。類型只用這些：
真人不會這樣說（出聲念出來沒有人會這樣講）、念不出口的書面語、搭配不當、口氣不合角色或身分、角色走樣、單字連答、口頭禪重複、旁白替讀者下結論或解釋心情、含蓄到看不懂、對話接不上、金句腔、病的描寫不真實（突然全好、一夕全忘、忘了也不在乎、只有忘沒有在補、把病演成恐怖或懲罰）、設定矛盾（只限這一場真的出現的設定）。
每個問題一行：「行號｜原句｜類型｜為什麼｜建議怎麼改（一句）」。最多 12 個，最嚴重的排前面；沒問題的句子不用提。

二、找好句。這一場最打動人的句子，最多三句，每句一行：「好句｜行號｜原句｜好在哪（一句）」。這一場一句都沒有，就只寫一行「好句｜無｜｜這一場沒有打動人的句子」。

三、真人的痕跡。看這一場的對白有沒有真人說話的痕跡（打斷、說一半、答非所問、重複、顧左右而言他）。只寫一行：「痕跡｜有或沒有｜一句說明」。這一場沒有對白就寫「痕跡｜不適用｜」。

不要客套，不要寫戲。
【這一幕的背景】{ctx}
【場景】
{body}"""

FACT = """你是設定查證員。下面是一場戲，以及這部作品的設定來源（可信的依據）與失智症研究整理裡「要避免的錯誤寫法」。
把這場戲裡每一個有設定性的內容（人名、稱呼、年紀、年代與日期、地點、物件與它的來由、病的表現、誰知道什麼）逐一分類：
符合設定｜與設定矛盾｜違反研究D節｜不確定。
每個一行：「原句｜類別｜依據（引設定來源或研究的原句；沒有就寫「無依據」）｜風險（一句）」。
重要：你自己的記憶不可靠，沒有依據就一律標「不確定」。設計稿與劇本衝突時，以「設定補正」與「以劇本為準」的段落為準。只列有設定性的內容，最多 15 個。
【設定來源】
{canon}
【研究：要避免的錯誤寫法】
{hist}
【這一幕的背景】{ctx}
【場景】
{body}"""

# 設計稿寫完之後劇本又改過的設定（以劇本為準；新的拍板寫在這裡，查證員才不會拿舊設計稿誤報）
CANON_FIX = """【設定補正（2026-10-23，以這裡為準）】
- 票根背面的句子是「河岸留言那晚，你唱〈天烏烏〉，我沒走。」（設計稿裡的舊句子已作廢）。
- 天黑分歧的選項文字：「有人會坐在三排十四號。」「周老師在等我開口。」「阿爸一個人收不完。」提示是「她心裡聽見誰？」。
- 〈晚安，台南〉的歌詞是 canon/歌詞.md 的現行版本（B 版）。
- 結局 C：石階上程希握住她的手，手是冰的，把手錶型 GPS 戴回她左手腕；之後加隔天的電台播報與報紙，再接紀念演出（設計見 design/結局C修改.md）。
- 余靜的戲依 design/余靜改寫方向.md（作者決定：用笑遮羞、笑完安靜；病識感時有時無；程希離開九十秒時她獨處，三個聲音依序出現）。"""


def canon_text():
    d = (ROOT / 'design/重寫.md').read_text(encoding='utf-8')
    keep = [s for s in re.split(r'\n(?=## )', d) if s.startswith(('## 一', '## 三', '## 四', '## 五', '## 六', '## 八', '## 十、', '## 劇本第二稿'))]
    extra = [(ROOT / p).read_text(encoding='utf-8') for p in ('design/余靜改寫方向.md', 'design/結局C修改.md') if (ROOT / p).exists()]
    return CANON_FIX + '\n\n' + '\n\n'.join(keep) + '\n\n' + '\n\n'.join(extra)


def research_d():
    t = (ROOT / 'design/失智症反應研究.md').read_text(encoding='utf-8')
    m = re.search(r'## D\..*?(?=\n## E\.)', t, re.S); return m.group(0) if m else ''


STATE = pathlib.Path(__file__).resolve().parent / '狀態.json'
def _h(t): return hashlib.md5(t.encode()).hexdigest()[:8]
def _load(): return json.loads(STATE.read_text()) if STATE.exists() else {}
def mark(p, title, body):
    st = _load(); e = st.setdefault(p.name, {}).setdefault(title, {'輪': 0}); e.update(hash=_h(body), 時間=datetime.datetime.now().strftime('%m-%d %H:%M'), 輪=e['輪'] + 1); STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1))
def status(p):
    st = _load().get(p.name, {}); _, sc = scenes(p)
    for title, body in sc:
        e = st.get(title); tag = '從沒審過' if not e else ('已審（內容沒變）' if e['hash'] == _h(body) else '審過後改了，要複審')
        print(f"{tag:<14} 第{e['輪'] if e else 0}輪 {e['時間'] if e else '':<12} {title}")

def scenes(p): return scenes_text(p.read_text(encoding='utf-8'))
def scenes_text(text):
    """→ (檔頭背景, [(場代號, 帶行號的這一場)])。場代號＝ ## 後面括號前的代號（例如 m_letter）；修改紀錄不算一場。"""
    text = text.split('\n## 修改紀錄')[0]
    lines = text.splitlines()
    idx = [i for i, l in enumerate(lines) if l.startswith('## ')] + [len(lines)]
    ctx = '\n'.join(lines[:8])[:900]
    out = []
    for a, b in zip(idx, idx[1:]):
        code = lines[a][3:].strip().split('（')[0].strip()
        out.append((code, '\n'.join(f'{k+1}｜{t}' for k, t in enumerate(lines[a:b]) if t.strip())))
    return ctx, out

def call(f, prompt, tries=3):
    r = ''
    for k in range(tries):
        r = f(prompt)
        if r and 'rate' not in r.lower()[:200]: return r
        time.sleep(25)
    return r or '（沒有回應）'

def sweep(p, keys):
    from concurrent.futures import ThreadPoolExecutor
    ctx, sc = scenes(p); sc = [s for s in sc if not keys or s[0] in keys]
    canon, hist = canon_text(), research_d()
    stamp = datetime.datetime.now().strftime('%m%d_%H%M%S'); d = OUT / f'sweep_{p.stem}_{stamp}'; d.mkdir()
    def one(item):
        title, body = item; body = body[:14000]
        jobs = {**{f'讀_{w}': (f, READ.format(ctx=ctx, body=body)) for w, f in READERS.items()},
                '查證_deepseek': (dsl, FACT.format(canon=canon, hist=hist, ctx=ctx, body=body)), '查證_codex': (cx, FACT.format(canon=canon, hist=hist, ctx=ctx, body=body))}
        with ThreadPoolExecutor(len(jobs)) as ex2: res = dict(zip(jobs, ex2.map(lambda fp: call(*fp), jobs.values())))
        out = f'# {title}\n\n' + ''.join(f'## {k}\n{v}\n\n' for k, v in res.items()) + f'## 原文\n{body}\n'
        (d / (re.sub(r'\W', '_', title)[:40] + '.md')).write_text(out); mark(p, title, body); return title
    with ThreadPoolExecutor(1) as ex:   # ponytail: 一次一場、場內並行；機器負載低再加
        for t in ex.map(one, sc): print('完成', t, flush=True)
    print('存到', d); return d

if __name__ == '__main__':
    mode, a = sys.argv[1], pathlib.Path(sys.argv[2])
    if mode == 'sweep': sweep(a, sys.argv[3:]); sys.exit()
    if mode == 'status': status(a); sys.exit()
