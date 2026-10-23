#!/usr/bin/env python3
"""全劇台詞的「AI 味」機械掃描。從《續》移植（2026-10-23）；規則與《續》相同。
只抓固定句型與用詞，判斷是不是真的有問題、怎麼改，交給讀稿人（codex）逐句看；這份是給他們與作者的第一張地圖。
用法：python3 審稿/ai_scan.py [--json 輸出.json] [--examples N]（從 ~/larch-ember 跑）"""
import json, re, sys, pathlib
from collections import Counter, defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
FILES = [ROOT / 'canon/劇本.md']

# (代號, 說明, 判斷函式) ── 抓到不等於一定要改，例如真的在比較兩件事的「不是……是……」
def rx(p): return lambda spk, t: re.search(p, t)
RULES = [
    ('否定再肯定', '「不是……而是」「不是 X，是 Y」（準則 4 禁用）', rx(r'不是[^。！？]{1,20}(而是|，是|，就是|；是)')),
    ('沒有只是', '「我沒有 X。我只是 Y」（準則 10 禁用）', rx(r'沒有[^。！？]{0,15}[。，]我?只是')),
    ('比喻詞', '彷彿、宛如、如同、好像……一樣', rx(r'彷彿|仿佛|宛如|如同|好像[^。]{1,12}一樣|像是[^。]{1,12}一樣')),
    ('抽象大詞', '那一刻、一瞬間、時光、歲月、命運、宿命、溫柔、孤獨、寂靜、靈魂、永遠', rx(r'那一刻|這一刻|一瞬間|剎那|時光|歲月|命運|宿命|溫柔|孤獨|寂靜|靈魂|永遠')),
    ('慢鏡頭副詞', '緩緩、輕輕地、靜靜地、默默地、深深地、淡淡的、微微', rx(r'緩緩|輕輕地|靜靜地|默默地|深深地|淡淡的|微微')),
    ('臉部特寫', '嘴角、眼底、眸、心頭、指尖', rx(r'嘴角|眼底|眸|心頭|指尖')),
    ('沒說話', '什麼都沒說、一句話也沒說、沒有說話（全劇最常見的收尾）', rx(r'什麼都沒說|什麼也沒說|一句話也沒說|一句話都沒說|沒有說話|沒說話')),
    ('碎句疊', '一句台詞裡三個以上的短句（四個字以內）接連用句號斷開', lambda spk, t: len(re.findall(r'(?:^|[。！？])[^。！？，、]{1,4}[。！？]', t)) >= 3),
    ('三連排比', '同一個開頭連用三次（「一……，一……，一……」之類）', lambda spk, t: any(len(set(g)) == 1 for g in re.findall(r'(?:^|[，。；])(\w)[^，。；]{1,10}[，；](\1)[^，。；]{1,10}[，；](\1)', t))),
    ('旁白說心情', '旁白直接寫心裡、覺得、感到（準則 6：旁白不解釋內心）', lambda spk, t: spk == '旁白' and re.search(r'(?<!手)心裡|覺得|感到|感覺|心想|明白了|懂了', t)),
    ('原來', '「原來……」「才知道……」的頓悟收尾', rx(r'(^|[，。])原來|才明白|這才知道')),
]

SPK = re.compile(r'^([^\s：:〔#選\-|]{1,12}?)(（[^）]*）)?：(.*)$')

def rows(path):   # 餘燼的劇本是「講者：台詞」一行一句；（唱）歌詞不掃（照歌詞檔），修改紀錄不掃
    scene = ''
    for n, l in enumerate(path.read_text(encoding='utf-8').split('\n## 修改紀錄')[0].splitlines(), 1):
        if l.startswith('## '): scene = l[3:].split('（')[0].strip(); continue
        m = SPK.match(l.strip())
        if not m or '（唱）' in m.group(3)[:4]: continue
        yield n, scene, m.group(1), m.group(3)

def main():
    want_json = sys.argv[sys.argv.index('--json') + 1] if '--json' in sys.argv else None
    n_ex = int(sys.argv[sys.argv.index('--examples') + 1]) if '--examples' in sys.argv else 3
    hits, per_file, total = [], defaultdict(Counter), Counter()
    lines = Counter()
    for f in FILES:
        for n, scene, spk, t in rows(f):
            lines[f.name] += 1
            for key, desc, fn in RULES:
                if fn(spk, t):
                    hits.append(dict(file=f.name, line=n, scene=scene, speaker=spk, rule=key, text=t))
                    per_file[f.name][key] += 1; total[key] += 1
    print(f'掃了 {len(FILES)} 份劇本、{sum(lines.values())} 句台詞，抓到 {len(hits)} 處（同一句可能中好幾條）\n')
    for key, desc, _ in RULES:
        print(f'【{key}】{total[key]} 處　{desc}')
        for h in [h for h in hits if h['rule'] == key][:n_ex]:
            print(f"    {h['file']}:{h['line']}｜{h['speaker']}｜{h['text'][:70]}")
    print('\n每份劇本（每百句幾處）：')
    for f in FILES:
        c = per_file[f.name]; k = sum(c.values())
        print(f"  {f.name:<12} {lines[f.name]:>5} 句　{k:>4} 處　{k * 100 / max(lines[f.name], 1):5.1f}／百句　" + '、'.join(f'{a}{b}' for a, b in c.most_common(4)))
    if want_json: pathlib.Path(want_json).write_text(json.dumps(hits, ensure_ascii=False, indent=1))

if __name__ == '__main__':
    main()
