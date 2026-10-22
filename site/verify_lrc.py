# -*- coding: utf-8 -*-
"""抽查動態歌詞：每首每個版本取至少 6 行（含開頭、副歌、結尾），把 LRC 該行時間前後各 2 秒的音檔做辨識，
比對聽到的字和那一句（以及它前後句、全曲最像的句子）。python3 site/verify_lrc.py"""
import json, os, random, re, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.argv = sys.argv[:1]
import make_lrc as M
S = M.S

def parse(p):
    out = []
    for raw in open(p, encoding='utf-8'):
        m = re.match(r'^\[(\d+):(\d+\.\d+)\](.*)$', raw.strip())
        if m: out.append((int(m.group(1)) * 60 + float(m.group(2)), m.group(3)))
    return out

if __name__ == '__main__':
    url = S.whisper_url(); L = M.all_lyrics(); rnd = random.Random(7)
    st = json.load(open(M.MUSIC / 'lyrics.json'))
    res = {}
    for sid, song in M.SONGS.items():
        if st[sid]['mode'] != 'dynamic': continue
        rows = parse(M.MUSIC / f'{sid}.lrc'); lines = L[song]
        w16 = S.decode_wav(M.MUSIC / f'{sid}.mp3', 16000, 1)[:, 0]; dur = len(w16) / 16000
        idx = {0, len(rows) - 1}
        secs = [l['sec'] for l in lines]
        for want in ('Chorus', 'Verse 2', 'Bridge', 'Final Chorus', 'Verse 3'):
            c = [i for i, x in enumerate(secs) if x.startswith(want)]
            if c: idx.add(c[len(c) // 2])
        while len(idx) < 8 and len(rows) > 8: idx.add(rnd.randrange(len(rows)))
        out = []
        for i in sorted(idx):
            t = rows[i][0]; a, b = max(0, t - 2), min(dur, t + 2)
            seg = w16[int(a * 16000):int(b * 16000)]
            h1 = ''.join(c for c, _, _ in S.transcribe(seg, url))        # whisper.cpp（跟對齊用的 DTW 不同引擎）
            h2 = ''.join(c for c, _, _ in M.dtw_chars(seg))              # openai-whisper
            heard = h1 if len(h1) >= len(h2) else h2
            heard = h1 + '／' + h2
            h1, h2 = [''.join(c for c, _, _ in M.strip_hallu([(c, 0, 0) for c in h])) for h in (h1, h2)]; heard = h1 + '／' + h2
            sc = [max(S.lcs(h1, S.norm(l['text'])), S.lcs(h2, S.norm(l['text']))) / max(1, len(S.norm(l['text']))) for l in lines]
            own = sc[i]; near = max(sc[max(0, i - 1):i + 2]); best = max(range(len(lines)), key=lambda k: sc[k])
            ok = near >= 0.4
            out.append(dict(i=i, t=round(t, 1), text=rows[i][1], heard=heard, own=round(own, 2), near=round(near, 2), best=best, ok=ok))
        res[sid] = out
        print('==', sid, f'{sum(o["ok"] for o in out)}/{len(out)}')
        for o in out: print(f'  #{o["i"]:>2} {o["t"]:>6}s {"OK " if o["ok"] else "?? "} 自身{o["own"]:.2f} 鄰近{o["near"]:.2f} 最像#{o["best"]}　{o["text"]}　聽到：{o["heard"]}')
    json.dump(res, open('/tmp/lrc-verify.json', 'w'), ensure_ascii=False, indent=1)
