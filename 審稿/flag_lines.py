#!/usr/bin/env python3
"""整部劇本挑句（作者 11-02）：多家族讀者各讀一次全劇，挑三種句子
  一、刻意說出的怪話：為了表現她失智、受影響、察覺自己忘了，硬塞的俏皮話或說明式台詞，真人不會這樣講
  二、唱歌、演出、排練的描寫不像真的：真的歌手、樂手、音控不會這樣講、這樣做
  三、其他所有硬得不像真人的台詞或旁白（作者 11-02：「全面查」）
  python3 審稿/flag_lines.py [劇本]  → 審稿/紀錄/flag_<時間>.md，兩位以上讀者挑到的句子排前面
提示詞由程式產生、不放例句；讀者走 llmshare（審稿/reader_ab.py 的 call）。"""
import json, re, sys, time, pathlib, concurrent.futures as cf
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from reader_ab import call, body, READERS, R
import os
READERS = os.environ['READERS'].split(',') if os.environ.get('READERS') else READERS
ASK = """你同時是兩種讀者：一般喜歡讀小說的人，以及在台灣當了二十年職業歌手、也做過樂手和音控的人。下面是一部視覺小說的完整劇本（〔圖〕是換圖標記，（唱）是歌詞，括號是台語的華語字幕）。
請挑出三種有問題的句子（歌詞不算）：
A：刻意說出的怪話。為了讓讀者知道她失智、受影響、察覺自己忘了，而讓角色說出的俏皮話、說明式的話，真人在那個當下不會這樣講。
B：唱歌、演出、排練、錄音、試音的描寫或台詞不像真的。真的歌手、鍵盤手、音控不會這樣講、這樣做，或術語用錯。
C：其他所有硬得不像真人的台詞或旁白：台灣人在那個當下、那個關係裡不會這樣講；太完整、太工整、像在說明、像設計好的台詞、語氣不對、接不上前一句。
只回 STRICT JSON（不要 markdown）：{"A": [{"scene": "場代號", "line": "原句逐字照抄（不含講者）", "why": "一句理由"}], "B": [同上], "C": [同上]}。A、B 每類最多 15 句，C 最多 40 句，寧缺勿濫。"""


def main():
    script = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else R / 'canon/劇本.md')
    text = body(script.read_text())
    # FLASH3=1：只用最便宜的 deepseek-v4.1-flash:1017，三種溫度各讀一次，取兩次以上挑到的（作者 11-02：成本）
    runs = [(f'flash@{t}', 'deepseek-v4.1-flash:1017', t) for t in (0.3, 0.7, 1.0)] if os.environ.get('FLASH3') else [(m, m, 0.3) for m in READERS]
    with cf.ThreadPoolExecutor(6) as ex:
        res = dict(zip([r[0] for r in runs], ex.map(lambda r: call(r[1], f'{ASK}\n\n{text}', r[2]), runs)))
    lines = [f'# 整部挑句 {time.strftime("%m%d_%H%M")}（{script.name}，讀者 {len(res)} 次）', '']
    for kind, name in (('A', '刻意說出的怪話'), ('B', '唱歌、演出的描寫不像真的'), ('C', '其他硬得不像真人的句子')):
        hits = {}
        for m, r in res.items():
            for h in (r or {}).get(kind, []) or []:
                key = re.sub(r'\s', '', h.get('line', ''))[:40]
                if key:
                    hits.setdefault(key, {'scene': h.get('scene'), 'line': h.get('line'), 'who': []})['who'].append(f'{m}：{h.get("why")}')
        lines.append(f'## {name}')
        for h in sorted(hits.values(), key=lambda h: -len(h['who'])):
            lines.append(f'- [{len(h["who"])}] {h["scene"]}｜「{h["line"]}」')
            lines += [f'  - {w}' for w in h['who']]
        lines.append('')
    out = R / f'審稿/紀錄/flag_{time.strftime("%m%d_%H%M")}.md'
    out.write_text('\n'.join(lines) + '\n'); print(out)
    print('\n'.join(l for l in lines if l.startswith(('##', '- ['))))


if __name__ == '__main__':
    main()
