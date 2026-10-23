#!/usr/bin/env python3
"""重寫比賽（問題多的場才用，要不要走這條由 runner.py packet 判斷，對應評分四「比較練習」）：同一份修稿包，各家寫手各寫一版；自己的版本放 draft_claude.txt 一起比。
  python3 審稿/contest.py write <場代號> canon/劇本.md   寫手產出 比賽/<場代號>/draft_<人>.txt（自己的版本要在看別人的稿之前寫好）
  python3 審稿/contest.py judge <場代號>                 評審匿名排名（順序打亂兩次，同家族的票不算）＋每份稿的共識問題數 → 結果.md 與勝出稿
勝出規則由程式算，寫稿的人不挑：去掉同家族票的平均名次取前三，其中共識問題最少的勝，同數比平均名次。從《續》移植（2026-10-23）。"""
import sys, pathlib, random, re, concurrent.futures as cf
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import scene_review as sr, runner as R
D = pathlib.Path(__file__).resolve().parent / '比賽'
WRITERS = {k: sr.READERS[k] for k in ('opus', 'codex', 'deepseek') if k in sr.READERS}   # 《續》兩輪 argon、gemini-web 都在後段，不當寫手
W = """你是互動小說（視覺小說）的編劇。請把下面這一場戲改寫成更自然、讓台灣讀者喜歡讀的版本。
改的依據是審稿人列出的問題（見下），也可以自己發現並改掉其他問題。保留這一場必須完成的事；台詞要像真人說話。
【寫稿準則】
{rules}
【背景】{ctx}
【審稿人列出的問題】
{issues}
【這些句子別處也引用，盡量保留原句】
{calls}
【原稿】
{body}
輸出格式：第一行照抄原稿的 ## 標題行；之後每行「講者：台詞」，講者照原稿用的名字（旁白、余靜（心）也照原稿）；〔圖：…〕〔掉字〕標記照原稿保留在原本的相對位置；（唱）的歌詞逐字照原稿；選項區塊照原稿。只輸出改寫後的整場，不要行號、不要說明、不要列修改處。"""
J = """你是互動小說的資深編劇，下面是同一場戲的 {n} 個匿名版本。請用台灣讀者的耳朵，依「自然好讀、像真人在說話、意思清楚、讓人想看下去、讓人喜歡這兩個人，而且這場該交代的事都在」排名。
{drafts}
先用一行寫「排名：」後面用 > 連接，例如「排名：C>A>B>D」（最好在前）。再各用一句話說最好的那版好在哪、最差的那版差在哪。不要客套。"""

def issues_for(title):
    return '\n'.join(f"- 第{i['lines'] or '整場'}行「{i['quote'][:50]}」：{i['type']}，{i['why'][:200]}" for i in R.load(R.ISS).values() if i['scene'] == title and i['status'] in ('open', 'escalate')) or '（沒有）'

def pick(names, res, dfx):
    pos = {n: [] for n in names}
    for jn, order, _ in res:
        for i, n in enumerate([n for n in order or [] if sr.FAMILY.get(n) != sr.FAMILY[jn]]): pos[n].append(i + 1)
    mean = {n: sum(v) / len(v) for n, v in pos.items() if v}
    top = sorted(mean, key=mean.get)[:3]
    return pos, mean, min(top, key=lambda n: (len(dfx[n]), mean[n]))

def judge(out):
    drafts = {f.stem[6:]: f.read_text().strip() for f in sorted(out.glob('draft_*.txt')) if f.read_text().strip()}
    names = list(drafts)
    def run(job):
        jn, f, seed = job; order = names[:]; random.Random(seed).shuffle(order); lab = {chr(65 + i): n for i, n in enumerate(order)}
        txt = sr.call(f, J.format(n=len(order), drafts='\n\n'.join(f'【版本{l}】\n{drafts[n]}' for l, n in lab.items())))
        m = re.search(r'排名[：:]\s*([A-Z](?:\s*>\s*[A-Z])+)', txt)
        return jn, ([lab[l] for l in re.findall(r'[A-Z]', m.group(1)) if l in lab] if m else None), txt
    with cf.ThreadPoolExecutor(4) as ex: res = list(ex.map(run, [(jn, f, s) for jn, f in sr.READERS.items() for s in (1, 2)]))
    with cf.ThreadPoolExecutor(2) as ex: dfx = dict(zip(names, ex.map(lambda n: [c for c in R.clusters(R.read_all('', R.numbered(drafts[n]))) if len(c[1]) > 1], names)))
    pos, mean, win = pick(names, res, dfx)
    notes = [f'## 評審 {jn}\n排名（真名）：' + (' > '.join(order) if order else '解析失敗') + '\n' + txt + '\n' for jn, order, txt in res]
    L = ['# 比賽結果', '', f'勝出：{win}（規則：去掉同家族票的平均名次前三名裡，共識問題最少；同數比名次）', '',
         '| 寫手 | 平均名次（去掉同家族票） | 票數 | 共識問題 |', '|---|---|---|---|']
    L += [f'| {n} | {mean[n]:.2f} | {len(pos[n])} | {len(dfx[n])} |' for n in sorted(mean, key=mean.get)]
    L += ['', '## 勝出稿還有的共識問題（換進劇本後要改）'] + ([f"- 行{c[0]['lines']}「{c[0]['quote']}」{c[0]['type']}：{c[0]['why']}（{'、'.join(sorted(c[1]))}）" for c in dfx[win]] or ['（沒有）'])
    (out / '結果.md').write_text('\n'.join(L + [''] + notes)); print('\n'.join(L))

if __name__ == '__main__':
    if sys.argv[1] == 'selftest':
        res = [('codex', ['codex', 'deepseek', 'claude', 'geminiweb'], ''), ('deepseek', ['deepseek', 'claude', 'geminiweb', 'codex'], ''), ('geminiweb', ['geminiweb', 'claude', 'codex', 'deepseek'], '')]
        pos, mean, win = pick(['geminiweb', 'claude', 'codex', 'deepseek'], res, {'geminiweb': [1, 2], 'claude': [1, 2, 3], 'codex': [], 'deepseek': [1]})
        assert pos['claude'] == [2, 1, 1] and win == 'deepseek', (pos, mean, win)   # 前三 claude、deepseek、geminiweb（同分照名單順序），共識問題最少的是 deepseek
        sys.exit(print('selftest ok'))
    mode, key = sys.argv[1], sys.argv[2]; out = D / key; out.mkdir(parents=True, exist_ok=True)
    if mode == 'write':
        ctx, title, body = R.scene_of(sys.argv[3], key)
        calls = '\n'.join(f'- {t}' for t, _ in R.callbacks(body)) or '（沒有）'
        p = W.format(rules=(D.parent / '準則.md').read_text(), ctx=ctx, issues=issues_for(title), calls=calls, body=body)
        with cf.ThreadPoolExecutor(3) as ex:
            for k, t in zip(WRITERS, ex.map(lambda f: sr.call(f, p), WRITERS.values())): (out / f'draft_{k}.txt').write_text(t); print('寫完', k, len(t))
    else: judge(out)
