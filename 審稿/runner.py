#!/usr/bin/env python3
"""審稿自動化：問題單、待辦、結案、閘門、出貨。從《續》移植（2026-10-23，作者同意），加上七項評分。步驟見 README.md。
  日常五步（照順序，從 ~/larch-ember 跑）：
  python3 審稿/runner.py next canon/劇本.md                  各場狀態，最後一行印「下一步」
  python3 審稿/runner.py read canon/劇本.md <場代號>          讀稿人讀這一場＋設定查證 → 問題單 → 原句已消失的自動結案 → 印待辦
  python3 審稿/runner.py packet canon/劇本.md <場代號>        修稿包：準則、這一場、問題、別處引用的句子、走逐條改還是重寫比賽
  python3 審稿/runner.py gate canon/劇本.md <場代號> [--base REF] [--by claude]   改完比舊稿：共識問題數＋非同家族評審兩兩比較
  python3 審稿/runner.py ship "提交訊息" <檔…> [--ripple-ok "理由"]   連帶掃描→重建→檢查→只 add 列出的檔→提交（不 push）
  其他：
  python3 審稿/runner.py gate --files <舊.txt> <新.txt> [--by codex]   兩份稿直接比（比賽稿用）
  python3 審稿/runner.py restore canon/劇本.md <場代號> [--base REF]    閘門三輪不過：只把這一場換回 base 版
  python3 審稿/runner.py editors                                     把 design/編輯意見/ 三位主編的意見併進問題單（標來源「主編」）
  python3 審稿/runner.py ingest <sweep 目錄> ／ todo [場代號] ／ resolve <id> 改了|不改|升級 "理由" ／ facts ／ good ／ report ／ export <路徑> ／ selftest
規則見 流程.md；資料存 問題單.json、事實.json、好句.json；閘門紀錄在 紀錄/gate_*.md。"""
import json, re, sys, pathlib, datetime, subprocess
D = pathlib.Path(__file__).resolve().parent
ISS, FAC, GOOD = D / '問題單.json', D / '事實.json', D / '好句.json'
load = lambda p: json.loads(p.read_text()) if p.exists() else {}
save = lambda p, o: p.write_text(json.dumps(o, ensure_ascii=False, indent=1))
ESCALATE_TYPES = ('設定矛盾',)
SCENE_LEVEL = {'沒有打動人的句子': '這一場沒有打動人的句子（評分一）', '對白沒有真人的痕跡': '對白沒有打斷、說一半、答非所問這些真人的痕跡（評分二）'}

def parse_read(txt):
    out = []
    for l in txt.splitlines():
        f = [x.strip() for x in l.split('｜')]
        if len(f) >= 5 and re.match(r'^[\d、,\-–~ ]+$', f[0]): out.append(dict(lines=f[0], quote=f[1].strip('「」'), type=f[2], why=f[3], fix=f[4]))
    return out

def parse_good(txt):   # 「好句｜行號｜原句｜好在哪」；「好句｜無｜…」→ []
    rows, none = [], False
    for l in txt.splitlines():
        f = [x.strip() for x in l.strip().lstrip('-*0123456789. ').split('｜')]
        if f and f[0] == '好句':
            if len(f) > 1 and f[1].startswith('無'): none = True
            elif len(f) >= 4 and re.match(r'^\d', f[1]): rows.append(dict(lines=f[1], quote=f[2].strip('「」'), why=f[3]))
    return rows, (none or not rows)

def parse_trace(txt):   # 「痕跡｜有或沒有｜說明」→ '有'／'沒有'／'不適用'／None
    for l in txt.splitlines():
        f = [x.strip() for x in l.strip().lstrip('-*0123456789. ').split('｜')]
        if f and f[0] == '痕跡' and len(f) > 1:
            return '沒有' if f[1].startswith('沒') else '不適用' if '不適用' in f[1] else '有' if f[1].startswith('有') else None
    return None

def parse_fact(txt):
    out = []
    for l in txt.splitlines():
        m = re.match(r'^\s*\d+\.\s*(.+)', l); f = [x.strip() for x in (m.group(1) if m else l).split('｜')]
        if len(f) >= 4 and f[1].split('（')[0] in ('符合設定', '與設定矛盾', '違反研究D節', '不確定'): out.append(dict(quote=f[0].strip('「」'), kind=f[1], basis=f[2], risk=f[3]))
    return out

def sections(md):
    return {m.group(1): m.group(2) for m in re.finditer(r'^## (\S+)\n(.*?)(?=^## |\Z)', md, re.S | re.M)}

def same(a, b):
    qa, qb = re.sub(r'\W', '', a['quote']), re.sub(r'\W', '', b['quote'])
    return bool(qa and qb and (qa[:8] in qb or qb[:8] in qa)) or (bool(a['lines']) and a['lines'] == b['lines'] and a['type'] == b['type'])

def norm(t): return re.sub(r'[\W\d]', '', t)

def frags(quote):   # 原句常把幾句用／或……串起來：拆開，每段取前 8 字；先拿掉「講者：」
    quote = re.sub(r'(^|[／/])\s*[^：:／/]{1,8}?(（[^）]*）)?[：:]', r'\1', quote)
    return [q[:8] for q in (norm(x) for x in re.split(r'[／/「」…]+|\.{3}', quote)) if len(q) >= 2]

def _new_id(iss): return f"{len(iss) + 1:04d}"

def scene_level(iss, scene, kind, who_hit, responded):   # 兩位以上讀稿人判定 → 開一條必修；之後讀稿沒人再判定 → 自動結案
    hit = next((i for i in iss.values() if i['scene'] == scene and i['type'] == kind and i['status'] == 'open'), None)
    if len(who_hit) >= 2:
        if hit:
            for w in who_hit:
                if w not in hit['who']: hit['who'].append(w)
        else:
            iid = _new_id(iss); iss[iid] = dict(id=iid, scene=scene, lines='', quote='', type=kind, why=SCENE_LEVEL[kind], who=sorted(who_hit), notes={},
                                                status='open', found=today(), anchored=False, level='scene')
    elif hit and responded >= 2 and len(who_hit) <= 1:
        hit.update(status='fixed', resolution='這次讀稿只剩 0 到 1 位讀稿人判定（自動結案）', closed=today())

def ingest(d):
    iss, fac, good = load(ISS), load(FAC), load(GOOD); n_new = 0
    for f in sorted(pathlib.Path(d).glob('*.md')):
        md = f.read_text(); scene = md.splitlines()[0].lstrip('# ').strip(); sec = sections(md)
        src = norm(sec.get('原文', ''))
        readers = [k[2:] for k in sec if k.startswith('讀_')]
        no_good, no_trace, responded = [], [], 0
        for who in readers:
            raw = sec[f'讀_{who}']
            if raw.strip() and raw.strip() != '（沒有回應）': responded += 1
            else: continue
            g, none = parse_good(raw)
            if none: no_good.append(who)
            good.setdefault(scene, {})[who] = g
            if parse_trace(raw) == '沒有': no_trace.append(who)
            for it in parse_read(raw):
                hit = next((i for i in iss.values() if i['scene'] == scene and i.get('level') != 'scene' and same(i, it)), None)
                if hit:
                    if who not in hit['who']: hit['who'].append(who); hit['notes'][who] = it['fix']
                else:
                    iid = _new_id(iss); n_new += 1
                    iss[iid] = dict(id=iid, scene=scene, lines=it['lines'], quote=it['quote'], type=it['type'], why=it['why'], who=[who], notes={who: it['fix']},
                                    status='escalate' if it['type'] in ESCALATE_TYPES else 'open', found=today())
                    if src: iss[iid]['anchored'] = any(q in src for q in frags(it['quote']))
        scene_level(iss, scene, '沒有打動人的句子', no_good, responded)
        scene_level(iss, scene, '對白沒有真人的痕跡', no_trace, responded)
        if any(k.startswith('查證_') for k in sec): fac[scene] = {who: parse_fact(sec.get(f'查證_{who}', '')) for who in ('deepseek', 'codex')}
    save(ISS, iss); save(FAC, fac); save(GOOD, good); print(f'新增 {n_new} 條，問題單共 {len(iss)} 條')

def todo(key=None):
    iss = [i for i in load(ISS).values() if i['status'] in ('open', 'escalate') and (not key or key == i['scene'])]
    iss.sort(key=lambda i: (-len(i['who']), i['scene'], i['id']))
    for i in iss:
        print(f"[{i['id']}] {'必修' if len(i['who']) > 1 else '參考'}{'·升級' if i['status'] == 'escalate' else ''} {i['scene'][:14]} 行{i['lines'] or '整場'} {i['type']}（{'、'.join(i['who'])}）\n    原句：{i['quote'] or '（整場）'}\n    為什麼：{i['why']}" + ('\n    建議：' + ' / '.join(f'{w}:{t}' for w, t in i['notes'].items()) if i['notes'] else ''))
    print(f'共 {len(iss)} 條')

def resolve(iid, how, why):
    iss = load(ISS); i = iss[iid]; i['status'] = {'改了': 'fixed', '不改': 'wontfix', '升級': 'escalate'}[how]; i['resolution'] = why; i['closed'] = today(); save(ISS, iss); print('ok', iid, i['status'])

def facts():
    for sc, d in load(FAC).items():
        rows = {(f['quote'], f['kind'], f['risk']) for ws in d.values() for f in ws if f['kind'].split('（')[0] in ('與設定矛盾', '違反研究D節', '不確定')}
        if rows: print('##', sc); [print(f'- {k}｜{q}｜{r}') for q, k, r in sorted(rows)]

def good_lines(key=None):   # 評分一的摘句本：讀稿人挑出的好句
    for sc, d in load(GOOD).items():
        if key and sc != key: continue
        rows = [(w, g) for w, gs in d.items() for g in gs]
        print(f'## {sc}（{len(rows)} 句）')
        for w, g in rows: print(f"- 行{g['lines']}「{g['quote']}」｜{g['why']}（{w}）")

def report():
    from collections import Counter
    c = Counter((i['scene'][:14], i['status'], '必修' if len(i['who']) > 1 else '參考') for i in load(ISS).values())
    for k, v in sorted(c.items()): print(k, v)

def export(path):
    from collections import Counter, defaultdict
    iss = load(ISS); fac = load(FAC); by = defaultdict(list)
    for i in iss.values(): by[i['scene']].append(i)
    L = ['# 審稿清單（自動產生，改問題單請用 runner.py，不要手改）', '']
    cnt = Counter(w for i in iss.values() for w in i['who']); multi = Counter(w for i in iss.values() if len(i['who']) > 1 for w in i['who'])
    L += ['## 各讀稿人', '', '| 讀稿人 | 提出條數 | 其中有人同意（≥2 位提到） |', '|---|---|---|'] + [f'| {w} | {c} | {multi[w]} |' for w, c in cnt.most_common()] + ['']
    for sc, items in by.items():
        items.sort(key=lambda i: (-len(i['who']), int(re.match(r'\d+', i['lines']).group()) if re.match(r'\d+', i['lines'] or '') else 0))
        L += [f'## {sc}', '']
        for i in items:
            tag = ('必修' if len(i['who']) > 1 else '參考') + ('·升級' if i['status'] == 'escalate' else '') + f"（{'、'.join(i['who'])}）"
            L += [f"- [{i['id']}] {tag} 行{i['lines'] or '整場'}｜{i['type']}｜{i['status']}", f"  - 原句：{i['quote'] or '（整場）'}", f"  - 為什麼：{i['why']}"] + (['  - 建議：' + ' / '.join(f'{w}：{t}' for w, t in i['notes'].items())] if i['notes'] else [])
        rows = {(f['quote'], f['kind'], f['basis'][:60]) for ws in fac.get(sc, {}).values() for f in ws if f['kind'].split('（')[0] in ('與設定矛盾', '違反研究D節', '不確定')}
        if rows: L += ['', '**設定查證（矛盾／違反研究／不確定）**'] + [f'- {k}｜{q}｜依據：{b}' for q, k, b in sorted(rows)]
        L += ['']
    pathlib.Path(path).write_text('\n'.join(L)); print('寫到', path, f'共 {len(iss)} 條')

# ── 評分七：主編意見併進問題單 ──
EDITORS = {'ed_codex': 'codex.md', 'ed_gemini': 'gemini.md', 'ed_deepseek': 'deepseek.md'}

def _bigrams(t): t = norm(t); return {t[i:i + 2] for i in range(len(t) - 1)}

def editors(script='canon/劇本.md'):
    """design/編輯意見/ 底下三位主編的意見 → 問題單。只收指到具體場代號的條目；同一場兩位以上主編講到相近的事（字的二元組重疊 ≥ 0.12）就合併成一條，算必修。"""
    ed = REPO / 'design/編輯意見'; codes = [c for c, _ in sr.scenes(REPO / script)[1]]
    iss = load(ISS); n_new = n_merge = 0
    for who, fn in EDITORS.items():
        p = ed / fn
        if not p.exists() or not p.read_text().strip(): print(f'{who}：沒有檔或是空的，略過'); continue
        txt = p.read_text()
        if txt.lstrip().startswith('{'):   # gemini-web 的原始 JSON：取 text；它長回應常截斷，太短就不收
            try: txt = json.loads(txt).get('text') or ''
            except Exception: txt = ''
        if len(re.sub(r'\s', '', txt)) < 800 or '【作品概要】' in txt:
            print(f'{who}：回應太短或只是回顯提示詞（可能被截斷，{len(txt)} 字），略過；要重跑這一位主編'); continue
        items = [x.strip() for x in re.split(r'\n(?=(?:\d+[.、)]\s|#{2,4}\s))', txt) if x.strip()]   # 只按主要條目切，子項目留在條目裡
        for it in items:
            hit_codes = [c for c in codes if re.search(r'(?<![A-Za-z0-9_])' + re.escape(c) + r'(?![A-Za-z0-9_])', it)]
            if len(hit_codes) > 4: hit_codes = ['全劇']   # 談結構的條目點到很多場：記成一條全劇問題，不要每場複製
            for c in hit_codes:
                why = re.sub(r'\s+', ' ', it)[:400]
                if any(i['scene'] == c and i.get('source') == '主編' and who in i['who'] and i['why'] == why for i in iss.values()): continue
                bg = _bigrams(why)
                hit = next((i for i in iss.values() if i['scene'] == c and i.get('source') == '主編' and who not in i['who']
                            and len(bg & _bigrams(i['why'])) / max(1, len(bg | _bigrams(i['why']))) >= 0.12), None)
                if hit: hit['who'].append(who); hit['notes'][who] = why; n_merge += 1
                else:
                    iid = _new_id(iss); n_new += 1
                    iss[iid] = dict(id=iid, scene=c, lines='', quote='', type='主編意見', why=why, who=[who], notes={}, status='open', found=today(), anchored=False, level='scene', source='主編',
                                    scenes=[x for x in codes if re.search(r'(?<![A-Za-z0-9_])' + re.escape(x) + r'(?![A-Za-z0-9_])', it)])
    save(ISS, iss); print(f'主編意見：新增 {n_new} 條、合併 {n_merge} 次（兩位以上主編講到＝必修）')

# ── 讀、修稿包、閘門、還原、出貨。寫的人（包括 Claude 自己）不判自己的稿：判由程式與非同家族評審。──
sys.path.insert(0, str(D)); import scene_review as sr
from concurrent.futures import ThreadPoolExecutor
REPO = D.parent
CARRY = ['canon/劇本.md', 'canon/歌詞.md', 'src/*.py', 'tests/*.mjs', 'tests/*.py']   # 會跟著劇本走的檔；design 與舊稿是歷史，不查
PAIR = """下面是互動小說裡同一場戲的兩個版本。請用台灣讀者的耳朵選出整體比較好的一版：自然好讀、像真人在說話、意思一次讀懂、讓人想看下去、讓人喜歡這兩個人，而且這一場該交代的事都還在（靠刪掉內容換來的乾淨不算好）。
【背景】{ctx}
【版本A】
{a}
【版本B】
{b}
第一行只寫「選：A」或「選：B」，第二行用一句話說最主要的理由。不要客套。"""
today = lambda: datetime.date.today().isoformat()
CONTEST_MUST, CONTEST_RATIO = 6, 0.3   # 沿用《續》的初值，跑完幾場看成本與 gate 結果再調
SPK = re.compile(r'^([^\s：:〔#選\-|]{1,12}?)(（[^）]*）)?：(.*)$')

def cell(row):   # 「講者：台詞」→ 台詞（拿掉（唱）（念）這類前綴）；不是台詞行回 None
    m = SPK.match(row.strip())
    if not m: return None
    return re.sub(r'^（[^）]{1,4}）', '', m.group(3)).strip() or None

def long_enough(t): return len(re.sub(r'\W', '', t)) >= 4

@__import__('functools').lru_cache(None)
def _carry(): return [(f.relative_to(REPO), f.read_text(errors='ignore').splitlines()) for pat in CARRY for f in sorted(REPO.glob(pat))]
def refs(t): return [f'{f}:{n}' for f, ls in _carry() for n, l in enumerate(ls, 1) if t in l]

def git_show(script, base):
    rel = pathlib.Path(script).resolve().relative_to(REPO)
    return subprocess.run(['git', '-C', str(REPO), 'show', f'{base}:{rel}'], capture_output=True, text=True, check=True).stdout

def scene_of(script, key, text=None):   # → (檔頭背景, 場代號, 帶行號的這一場)；先比對完整代號，沒有才比對子字串
    ctx, sc = sr.scenes_text(text if text is not None else pathlib.Path(script).read_text())
    hit = [(t, b) for t, b in sc if t == key] or [(t, b) for t, b in sc if key in t]
    if len(hit) != 1: sys.exit(f'場代號「{key}」對到 {len(hit)} 場，請給完整代號（例如 m_letter）')
    return ctx, *hit[0]

def callbacks(body):
    cb = []
    for l in body.splitlines():
        t = cell(l.split('｜', 1)[-1])
        if t and long_enough(t) and len(h := refs(t)) > 1: cb.append((t, h))
    return cb

def autoclose(script):   # 原句已經不在這一場的 open 問題自動結案；整場層級的問題由下一次讀稿判定
    _, sc = sr.scenes(pathlib.Path(script)); text = {t: norm(b) for t, b in sc}
    iss = load(ISS); n = 0
    for i in iss.values():
        qs = frags(i['quote'])
        if i['status'] == 'open' and i.get('level') != 'scene' and i.get('anchored') is not False and i['scene'] in text and qs and not any(q in text[i['scene']] for q in qs):
            i.update(status='fixed', resolution='原句已不在這一場（自動結案）', closed=today()); n += 1
    save(ISS, iss); print(f'自動結案 {n} 條')

def read(script, key):
    _, title, _ = scene_of(script, key)
    ingest(sr.sweep(pathlib.Path(script), [title])); autoclose(script); todo(title)

def packet(script, key):
    _, title, body = scene_of(script, key)
    iss = [i for i in load(ISS).values() if i['scene'] == title and i['status'] in ('open', 'escalate')]
    must = [i for i in iss if len(i['who']) > 1]
    n = sum(1 for l in body.splitlines() if cell(l.split('｜', 1)[-1]))
    print(f'# 修稿包：{title}\n\n' + (D / '準則.md').read_text() + '\n## 這一場（行號｜內容）\n' + body + '\n')
    print(f'## 問題：必修 {len(must)} 條（≥2 位讀稿人或主編提到），參考 {len(iss) - len(must)} 條'); todo(title)
    print('\n## 讀稿人挑出的好句（盡量保留）'); good_lines(title)
    print('\n## 這些句子別處也有（改了要一起改，不然就保留原句）')
    for t, h in callbacks(body) or [('（沒有）', [])]: print(f'- {t}' + ('\n  ' + '、'.join(h) if h else ''))
    big = len(must) >= CONTEST_MUST or (n and len(must) / n >= CONTEST_RATIO)
    print('\n## 走哪條路\n' + (f'問題多（必修 ≥{CONTEST_MUST} 條或佔台詞 {CONTEST_RATIO:.0%} 以上）：走重寫比賽（同一場只比一次；比過還不過閘門就逐條改）。\n  python3 審稿/contest.py write {title} {script}\n  自己的版本寫進 審稿/比賽/{title}/draft_claude.txt（寫完之前不要打開別人的稿），再 python3 審稿/contest.py judge {title}，把勝出稿換進劇本' if big
          else '逐條改：只改有問題的句子，沒被點到的句子不動。作者要求句子由 codex 寫：把這份修稿包交給 codex，你負責套用與驗證。不改的用 runner.py resolve <id> 不改 "理由" 結案。'))
    print(f'\n改完：python3 審稿/runner.py gate {script} {title}')

def numbered(t): return '\n'.join(f'{k + 1}｜{l}' for k, l in enumerate(x for x in t.splitlines() if x.strip()))

def read_all(ctx, body):
    with ThreadPoolExecutor(len(sr.READERS)) as ex:
        return dict(zip(sr.READERS, ex.map(lambda f: sr.call(f, sr.READ.format(ctx=ctx, body=body[:14000])), sr.READERS.values())))

def clusters(outs):
    cl = []
    for who, txt in outs.items():
        for it in parse_read(txt):
            c = next((c for c in cl if same(c[0], it)), None)
            c[1].add(who) if c else cl.append((it, {who}))
    return cl

def pairwise(ctx, old, new, by):   # 評審排除 anthropic（原稿與多數改稿出自 Claude）與新稿作者的家族；A/B 順序對調各問一次
    judges = {w: f for w, f in sr.READERS.items() if sr.FAMILY[w] not in ('anthropic', sr.FAMILY.get(by))}
    def one(j):
        w, f, nf = j; r = sr.call(f, PAIR.format(ctx=ctx, a=new if nf else old, b=old if nf else new)); m = re.search(r'選[：:]\s*([AB])', r)
        return w, (None if not m else (m.group(1) == 'A') == nf), (r.strip().splitlines() or [''])[-1][:90]
    jobs = [(w, f, nf) for w, f in judges.items() for nf in (True, False)]
    with ThreadPoolExecutor(max(1, len(jobs))) as ex: res = list(ex.map(one, jobs))
    return sum(v is True for _, v, _ in res), sum(v is False for _, v, _ in res), res

def verdict(fresh, fixed, win, lose):
    return (fresh < fixed and win >= lose) or (fresh <= fixed and win >= lose + 2)

def absent(c, text): return not any(q in text for q in frags(c[0]['quote']))

def gate(a):
    by = a[a.index('--by') + 1] if '--by' in a else 'claude'
    if a[0] == '--files':
        old, new = (numbered(pathlib.Path(x).read_text()) for x in a[1:3]); ctx, title, script = '', pathlib.Path(a[2]).stem, None
    else:
        script, key = a[0], a[1]; base = a[a.index('--base') + 1] if '--base' in a else 'HEAD'
        ctx, title, new = scene_of(script, key); old = scene_of(script, title, git_show(script, base))[2]
    if old == new: sys.exit('這一場跟 base 一樣，沒有可以比的（已提交的改動要複審請用 read）')
    with ThreadPoolExecutor(3) as ex:
        fo, fn, fp = ex.submit(read_all, ctx, old), ex.submit(read_all, ctx, new), ex.submit(pairwise, ctx, old, new, by)
        rn = fn.result(); mo, mn, (win, lose, votes) = [c for c in clusters(fo.result()) if len(c[1]) > 1], [c for c in clusters(rn) if len(c[1]) > 1], fp.result()
    po, pn = norm(old), norm(new)
    fresh, fixed = [c for c in mn if absent(c, po)], [c for c in mo if absent(c, pn)]
    ok = verdict(len(fresh), len(fixed), win, lose)
    L = [f'# 閘門：{title}（{datetime.datetime.now():%m-%d %H:%M}，新稿作者 {by}，讀稿人 {"、".join(sr.READERS)}）', '', f'結果：{"通過" if ok else "不通過"}',
         f'- 改動造成的共識問題（≥2 位讀稿人提到）：修掉 {len(fixed)} 條、新出現 {len(fresh)} 條（全部：舊 {len(mo)} 條、新 {len(mn)} 條）',
         f'- 兩兩比較（非同家族評審、A/B 對調）：新稿贏 {win}、舊稿贏 {lose}、沒答 {len(votes) - win - lose}',
         '- 通過條件：新出現的比修掉的少且新稿不輸；或沒有多且新稿多贏兩票以上', '', '## 新稿還有的共識問題（下一輪要改）']
    L += [f"- 行{c[0]['lines']}「{c[0]['quote']}」{c[0]['type']}：{c[0]['why']}（{'、'.join(sorted(c[1]))}）" + ('［新出現］' if c in fresh else '') for c in mn] or ['（沒有）']
    L += ['', '## 修掉的'] + ([f"- 「{c[0]['quote']}」{c[0]['type']}" for c in fixed] or ['（沒有）'])
    L += ['', '## 評審'] + [f"- {w}：{'新稿' if v else '舊稿' if v is False else '沒答'}｜{why}" for w, v, why in votes]
    out = sr.OUT / ('gate_' + re.sub(r'\W', '_', title)[:24] + f'_{datetime.datetime.now():%m%d_%H%M%S}.md'); out.write_text('\n'.join(L) + '\n')
    print('\n'.join(L)); print('存到', out)
    if script:
        d = sr.OUT / f'sweep_{pathlib.Path(script).stem}_gate_{datetime.datetime.now():%m%d_%H%M%S}'; d.mkdir()
        (d / 'scene.md').write_text(f'# {title}\n\n' + ''.join(f'## 讀_{w}\n{t}\n\n' for w, t in rn.items()) + f'## 原文\n{new}\n')
        ingest(d)
        if ok: sr.mark(pathlib.Path(script), title, new)
        autoclose(script)
    sys.exit(0 if ok else 1)

def restore(script, key, base='HEAD'):
    def span(text):
        ls = text.splitlines(keepends=True)
        idx = [i for i, l in enumerate(ls) if l.startswith('## ')] + [len(ls)]
        hit = [(x, y) for x, y in zip(idx, idx[1:]) if ls[x][3:].split('（')[0].strip() == key]
        if len(hit) != 1: sys.exit(f'「{key}」對到 {len(hit)} 場')
        return ls, *hit[0]
    p = pathlib.Path(script); nl, x, y = span(p.read_text()); ol, u, v = span(git_show(script, base))
    p.write_text(''.join(nl[:x] + ol[u:v] + nl[y:])); print('這一場已換回', base)

def tests_running():   # 只算工作目錄在 larch-ember 的試玩
    for pid in subprocess.run(['pgrep', '-f', '^node tests/'], capture_output=True, text=True).stdout.split():
        try:
            if pathlib.Path(f'/proc/{pid}/cwd').resolve() == REPO: return True
        except OSError: pass
    return False

TRAILER = 'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>'

def ship(a):
    ok_ripple = a[a.index('--ripple-ok') + 1] if '--ripple-ok' in a else None
    msg, files = a[0], [str(pathlib.Path(x).resolve()) for x in a[1:] if x not in ('--ripple-ok', ok_ripple)]
    if tests_running(): sys.exit('有餘燼的試玩在跑：等它結束再 ship（同時重建會讓試玩失敗）')
    diff = subprocess.run(['git', '-C', str(REPO), 'diff', '-U0', 'HEAD', '--', *files], capture_output=True, text=True).stdout.splitlines()
    gone = ({cell(l[1:]) for l in diff if l.startswith('-') and not l.startswith('---')} - {cell(l[1:]) for l in diff if l.startswith('+') and not l.startswith('+++')}) - {None}
    left = [(t, h) for t in sorted(gone) if long_enough(t) and (h := refs(t))]
    for t, h in left: print(f'舊句子別處還在：{t}\n  ' + '、'.join(h))
    if left and not ok_ripple: sys.exit('要一起改；確定不用改就加 --ripple-ok "理由"')
    for cmd in (['python3', 'src/build.py'], ['python3', 'tests/check_voice.py'], [str(pathlib.Path.home() / 'speak-tw/bin/speak-tw'), '--public', 'canon/劇本.md'], ['python3', 'tests/map_check.py'], ['python3', 'tests/motif_check.py']):
        r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True); out = r.stdout + r.stderr
        bad = r.returncode != 0 or ('speak-tw' in cmd[0] and not re.search(r'(?<!\d)0 處要改', out))
        print('FAIL' if bad else 'ok  ', ' '.join(pathlib.Path(cmd[0]).name if i == 0 else c for i, c in enumerate(cmd)))
        if bad: print(out[-3000:]); sys.exit(1)
    body = msg if TRAILER in msg else msg + '\n\n' + TRAILER
    for cmd in (['git', 'add', '--', *files], ['git', 'commit', '-q', '-m', body]):   # 不 push（作者：推送與發佈要點頭）
        r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
        if r.returncode: sys.exit(r.stdout + r.stderr + f'\ngit 失敗：{" ".join(cmd[:3])}')
    print(subprocess.run(['git', 'log', '--oneline', '-1'], cwd=REPO, capture_output=True, text=True).stdout.strip())
    print('下一步（run_in_background，一次一個，跑的時候不要 build）：' + '；'.join(f'END={e} SPEED=16 AUDIO=1 node tests/play_full.mjs' for e in 'abc'))

def nxt(script):
    p = pathlib.Path(script); st = sr._load().get(p.name, {}); _, sc = sr.scenes(p); iss = list(load(ISS).values()); plan = []
    try: head = {t: b for t, b in sr.scenes_text(git_show(script, 'HEAD'))[1]}
    except subprocess.CalledProcessError: head = {}
    for k, (title, body) in enumerate(sc):
        e = st.get(title); must = sum(1 for i in iss if i['scene'] == title and i['status'] == 'open' and len(i['who']) > 1)
        tag = '從沒審過' if not e else ('已審' if e['hash'] == sr._h(body) else '審過後改了')
        print(f"{tag:<5} 第{e['輪'] if e else 0}輪 必修{must:>2}  {title}")
        if must: plan.append((0, k, f'python3 審稿/runner.py packet {script} {title}'))
        elif tag == '審過後改了': plan.append((1, k, f'python3 審稿/runner.py {"gate" if head.get(title) != body else "read"} {script} {title}'))
        elif tag == '從沒審過': plan.append((2, k, f'python3 審稿/runner.py read {script} {title}'))
    print('下一步：' + (min(plan)[2] if plan else '這份劇本每場都審過、沒有未修的必修'))

def selftest():   # 不打外部模型
    assert cell('余靜：我寫這麼多規矩給自己喔。') == '我寫這麼多規矩給自己喔。' and cell('余靜（心）：杯子在右邊。') == '杯子在右邊。'
    assert cell('余靜：（唱）燈一盞一盞暗下來') == '燈一盞一盞暗下來' and cell('〔圖：s_a_1〕') is None and cell('選項：') is None and cell('- 有人會坐在三排十四號。 → ending_a') is None
    outs = {'codex': '3｜你今天很愛寫字耶。｜真人不會這樣說｜太順｜改', 'deepseek': '3｜你今天很愛寫字耶｜真人不會這樣說｜像台詞｜改\n7｜嗯。｜單字連答｜太短｜改', 'geminiweb': '無'}
    cl = clusters(outs); assert sorted(len(c[1]) for c in cl) == [1, 2], cl
    assert verdict(1, 3, 3, 3) and not verdict(1, 3, 2, 4) and not verdict(2, 2, 4, 3) and verdict(2, 2, 5, 1) and not verdict(3, 0, 4, 2)
    g, none = parse_good('好句｜12｜河岸留言那晚，你唱〈天烏烏〉，我沒走。｜一句話裝了十八年\n痕跡｜有｜她打斷他'); assert len(g) == 1 and not none
    g, none = parse_good('好句｜無｜｜這一場沒有打動人的句子'); assert g == [] and none
    assert parse_trace('痕跡｜沒有｜一問一答') == '沒有' and parse_trace('痕跡｜有｜打斷') == '有' and parse_trace('痕跡｜不適用｜') == '不適用'
    iss = {}
    scene_level(iss, 'm_x', '沒有打動人的句子', ['codex', 'deepseek'], 3); assert len(iss) == 1 and len(next(iter(iss.values()))['who']) == 2
    scene_level(iss, 'm_x', '沒有打動人的句子', ['codex'], 3); assert next(iter(iss.values()))['status'] == 'fixed'
    body = norm('1｜余靜：拿得動。\n2｜程希：你拿不動。')
    assert any(q in body for q in frags('余靜：拿得動。／程希：拿不動。')) and absent(({'quote': '我也聽你的啊。'}, set()), '那你輸了呢')
    print('selftest ok')

if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'ingest': ingest(a[1])
    elif a[0] == 'todo': todo(a[1] if len(a) > 1 else None)
    elif a[0] == 'resolve': resolve(a[1], a[2], a[3])
    elif a[0] == 'facts': facts()
    elif a[0] == 'good': good_lines(a[1] if len(a) > 1 else None)
    elif a[0] == 'report': report()
    elif a[0] == 'export': export(a[1])
    elif a[0] == 'editors': editors(*(a[1:2]))
    elif a[0] == 'next': nxt(a[1])
    elif a[0] == 'read': read(a[1], a[2])
    elif a[0] == 'packet': packet(a[1], a[2])
    elif a[0] == 'gate': gate(a[1:])
    elif a[0] == 'restore': restore(a[1], a[2], a[a.index('--base') + 1] if '--base' in a else 'HEAD')
    elif a[0] == 'ship': ship(a[1:])
    elif a[0] == 'selftest': selftest()
