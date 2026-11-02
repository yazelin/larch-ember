#!/usr/bin/env python3
"""整部讀者盲測（作者 11-02：平鋪直敘之後還能不能讓人感動）。舊版、新版整部劇本從頭讀到尾，不說哪份是新的，A/B 對調各問一次。
  python3 審稿/reader_ab.py <舊版 git 版本> [新版檔，預設 canon/劇本.md]   → 審稿/紀錄/reader_ab_<時間>.json 與 .md
讀者走 llmshare（多家族），提示詞由程式產生、不放例句。"""
import json, os, re, subprocess, sys, time, pathlib, concurrent.futures as cf, urllib.request
R = pathlib.Path(__file__).resolve().parent.parent
READERS = ['deepseek-v4-pro', 'kimi-k3', 'glm-5.3', 'qwen3.5:397b', 'minimax-m3', 'mistral-large-4']
ASK = """你是一般讀者，喜歡讀小說，不是編輯。下面是同一部視覺小說的兩個版本，A 與 B，都從頭寫到尾。〔圖：…〕是換圖的標記，〔掉字〕表示那句之後會淡掉，（唱）是唱歌，括號是台語的華語字幕。
這部作品想讓讀者先感受到兩個人相識、相戀的浪漫，之後感受到失智、失憶、失語的悲傷。請你當讀者讀完兩份，誠實回答。
只回 STRICT JSON（不要 markdown），格式：
{"A": {"romance": [最多 3 句讓你覺得浪漫、喜歡上這兩個人的原句], "cry": [最多 3 句讓你最難過、想哭的原句], "contrived": [最多 3 句讓你覺得刻意、出戲、被打斷的原句], "flat": [最多 3 句你覺得情緒該到卻沒到的原句], "romance_score": 1到10, "sad_score": 1到10, "flow_score": 1到10（整部讀下來順不順、節奏有沒有被打斷）},
 "B": {同上},
 "prefer": "A" 或 "B"（整體哪一份比較讓你感動）, "why": "兩三句理由"}
原句要從劇本逐字抄（可以只抄一句台詞或旁白的內容，不含講者）。"""


def body(text):
    text = text.split('\n## 修改紀錄')[0]
    return text[text.index('\n## '):].strip()


def call(model, prompt, temperature=0.3):
    req = urllib.request.Request(os.environ.get('LLMSHARE_BASE_URL', 'https://llm-share.duotify.com/v1') + '/chat/completions',
                                 data=json.dumps({'model': model, 'temperature': temperature, 'messages': [{'role': 'user', 'content': prompt}]}).encode(),
                                 headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + os.environ['LLMSHARE_API_KEY']})
    for n in range(3):
        try:
            t = json.load(urllib.request.urlopen(req, timeout=900))['choices'][0]['message']['content']
            t = re.sub(r'<think>.*?</think>', '', t, flags=re.S).strip()
            return json.loads(t[t.index('{'):t.rindex('}') + 1])
        except Exception as e:  # noqa: BLE001
            print(model, '例外', repr(e)[:120], flush=True); time.sleep(15 * (n + 1))
    return None


def main():
    old = body(subprocess.run(['git', '-C', str(R), 'show', f'{sys.argv[1]}:canon/劇本.md'], capture_output=True, text=True, check=True).stdout)
    new = body((R / (sys.argv[2] if len(sys.argv) > 2 else 'canon/劇本.md')).read_text())
    jobs = []
    for m in READERS:
        for new_is in 'AB':
            a, b = (new, old) if new_is == 'A' else (old, new)
            jobs.append((m, new_is, f'{ASK}\n\n【版本 A】\n{a}\n\n【版本 B】\n{b}'))
    out = []
    with cf.ThreadPoolExecutor(6) as ex:
        for (m, new_is, _), r in zip(jobs, ex.map(lambda j: call(j[0], j[2]), jobs)):
            if not r:
                out.append({'model': m, 'new_is': new_is, 'error': True}); continue
            old_is = 'B' if new_is == 'A' else 'A'
            out.append({'model': m, 'new_is': new_is, 'prefer_new': r.get('prefer') == new_is, 'why': r.get('why'),
                        'new': r.get(new_is), 'old': r.get(old_is)})
            print(m, '新版在', new_is, '→ 選', '新版' if r.get('prefer') == new_is else '舊版', flush=True)
    stamp = time.strftime('%m%d_%H%M')
    (R / f'審稿/紀錄/reader_ab_{stamp}.json').write_text(json.dumps(out, ensure_ascii=False, indent=1))
    ok = [o for o in out if not o.get('error')]
    avg = lambda side, k: sum(float(o[side].get(k, 0) or 0) for o in ok if o.get(side)) / max(1, len(ok))
    lines = [f'# 整部讀者盲測 {stamp}（舊版 {sys.argv[1]}，讀者 {len(READERS)} 位 × A/B 對調）', '',
             f'- 選新版 {sum(o["prefer_new"] for o in ok)}、選舊版 {sum(not o["prefer_new"] for o in ok)}、沒答 {len(out) - len(ok)}',
             f'- 平均分（新／舊）：浪漫 {avg("new", "romance_score"):.1f}／{avg("old", "romance_score"):.1f}、悲傷 {avg("new", "sad_score"):.1f}／{avg("old", "sad_score"):.1f}、順暢 {avg("new", "flow_score"):.1f}／{avg("old", "flow_score"):.1f}', '']
    for k, name in (('romance', '新版讓人覺得浪漫的句子'), ('cry', '新版讓人想哭的句子'), ('contrived', '新版讓人出戲的句子'), ('flat', '新版情緒該到沒到的句子'),
                    ('contrived_old', '舊版讓人出戲的句子')):
        side, key = ('old', 'contrived') if k == 'contrived_old' else ('new', k)
        lines.append(f'## {name}')
        for o in ok:
            for q in (o.get(side) or {}).get(key, []) or []:
                lines.append(f'- 「{q}」（{o["model"]}）')
        lines.append('')
    lines.append('## 各讀者的理由')
    lines += [f'- {o["model"]}（新版在 {o["new_is"]}）選{"新版" if o["prefer_new"] else "舊版"}：{o["why"]}' for o in ok]
    (R / f'審稿/紀錄/reader_ab_{stamp}.md').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines[:4]))


if __name__ == '__main__':
    main()
