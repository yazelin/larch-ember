# -*- coding: utf-8 -*-
"""原聲帶的動態歌詞：只取時間，文字一律用官方歌詞。
python3 site/make_lrc.py [曲 id …]     → docs/music/<id>.lrc + docs/music/lyrics.json（逐曲狀態）＋ /tmp 報告
做法（沿用 src/songs_cut.py 的轉錄與對齊函式，只讀不改）：
 1. 找人聲第一次進來的位置（5 秒小視窗滑動辨識，避開前奏的幻覺）。
 2. 從那裡起切成 24 秒小窗（每 20 秒一窗）分別辨識，只取每窗中間 20 秒；整首一次跑會掉進重複迴圈。
 3. 濾掉已知的幻覺字串（「作曲李宗盛」「優優獨播劇場」「ZitherHarp」…）。
 4. 歌詞字與辨識字做全域單調對齊（副歌重複也不會黏到前面），句首取起音，再提前一點點。
 5. 字數對到不到 45% 的曲子退回靜態歌詞。
〈港邊的燈〉台語，辨識聽不出字：時間用作者手標的前 8 句（src/songs_cut.py 的 MANUAL_LINES）。"""
import json, os, pathlib, re, sys, tempfile

HERE = pathlib.Path(__file__).resolve().parent
G = HERE.parent
os.environ.setdefault('SONGS_DIR', os.path.join(tempfile.gettempdir(), 'ember-lrc-songs'))
os.makedirs(os.environ['SONGS_DIR'], exist_ok=True)
sys.path.insert(0, str(G / 'src'))
import songs_cut as S   # noqa: E402

MUSIC = G / 'docs/music'
SONGS = {  # id: (歌名鍵, 檔)
    'ember-studio': '餘燼', 'ember-audience': '餘燼', 'ember-harmony': '餘燼', 'ember-chorus': '餘燼',
    'goodnight-tainan': '晚安，台南', 'harbor-lights': '港邊的燈',
}
HALLU = ['作曲李宗盛', '中文字幕志愿者李宗盛', '中文字幕志愿者', 'ZitherHarp', '优优独播剧场', 'YoYoTelevisionSeriesExclusive', '李宗盛', '字幕志愿者']
LEAD = 0.2          # 句首在起音之上再提前（align 已取起音再提前 0.05 秒）
GATE = 0.45         # 對到的字數佔歌詞總字數的比例，低於這個退靜態
WIN, HOP = 24.0, 20.0


def lyrics_night():
    t = (G / 'design/歌詞重寫/codex.md').read_text(encoding='utf-8')
    blk = t.split('## 〈晚安，台南〉版本 B', 1)[1]
    body = re.search(r'```text\n(.*?)```', blk, re.S).group(1)
    out, sec, seen = [], '', {}
    for raw in body.splitlines():
        s = raw.strip()
        if not s: continue
        m = re.match(r'^\[(.+)\]$', s)
        if m:
            seen[m.group(1)] = seen.get(m.group(1), 0) + 1
            sec = m.group(1) + (f'#{seen[m.group(1)]}' if seen[m.group(1)] > 1 else '')
            continue
        out.append({'i': len(out), 'sec': sec, 'text': s})
    return out


def all_lyrics():
    L = S.load_lyrics()
    L['晚安，台南'] = lyrics_night()
    return L


_model = None


def dtw_chars(seg16, offset=0.0):
    """openai-whisper large-v3-turbo 的字詞時間（交叉注意力 DTW，比 whisper.cpp 的逐字時間穩，長音不會把字攤平）。
    回傳 [(字, 起, 迄)]（簡體，只用時間），詞內多字平均切開。"""
    global _model
    import numpy as np, whisper
    if _model is None:
        _model = whisper.load_model('large-v3-turbo', device='cuda')
    r = _model.transcribe(seg16.astype(np.float32), language='zh', temperature=0, condition_on_previous_text=False,
                          word_timestamps=True, fp16=True)
    out = []
    for sg in r['segments']:
        for w in sg['words']:
            cs = S.norm(w['word'])
            if not cs: continue
            a, e = w['start'], w['end']
            for k, c in enumerate(cs):
                out.append((c, a + offset + (e - a) * k / len(cs), a + offset + (e - a) * (k + 1) / len(cs)))
    return out


def find_entry(w16, lines):
    """人聲第一次進來的位置（秒）。視窗從靜默或前奏起頭會先吐幻覺字，所以掃描視窗起點：
    找第一個「有 8 字以上歌詞字、而且第一個歌詞字就貼在視窗起點」的位置。"""
    lyr = set(''.join(S.norm(l['text']) for l in lines))
    w0 = 4.0
    while w0 < 60:
        seg = w16[int(w0 * 16000):int((w0 + 24.0) * 16000)]
        if len(seg) < 16000 * 6: break
        r = [x for x in strip_hallu(dtw_chars(seg, w0)) if x[0] in lyr]
        if len(r) >= 8:
            if r[0][1] - w0 <= 1.5: return w0
            w0 = max(w0 + 1.0, r[0][1] - 1.0)
            continue
        w0 += 2.0
    return 0.0


def windowed(w16, key, start):
    f = S.CACHE / f'dtwwin-{key}-{start:.1f}.json'
    if f.exists(): return json.loads(f.read_text())
    n = len(w16) / 16000
    out, t, first = [], start, True
    while t < n - 1:
        seg = w16[int(t * 16000):int(min(n, t + WIN) * 16000)]
        if len(seg) > 16000:
            lo = t if first else t + 2.0
            hi = n + 1 if t + HOP >= n else t + WIN - 2.0
            out += [list(x) for x in dtw_chars(seg, t) if lo <= (x[1] + x[2]) / 2 < hi]
        first = False
        t += HOP
    f.write_text(json.dumps(out, ensure_ascii=False)); return out


def strip_hallu(asr):
    s = ''.join(c for c, _, _ in asr)
    keep = [True] * len(asr)
    for h in sorted(HALLU, key=len, reverse=True):
        hn = S.norm(h)
        for m in re.finditer(re.escape(hn), s):
            for k in range(m.start(), m.end()): keep[k] = False
    return [x for x, k in zip(asr, keep) if k]


def fix_unsure(al, asr):
    """字對不上的句子（辨識聽成同音字，例如「魚攤收了」聽成「雨潭受了」）原本是在左右可靠句之間內插，會落在前一句尾巴上。
    改成：把辨識結果依停頓（>1.2 秒）切成樂句，夾在左右可靠句之間、數量剛好等於這段不可靠句數的樂句，依序當它們的句首。
    數量對不上就維持內插。"""
    phrases = []
    for c, a_, e in asr:
        if phrases and a_ - phrases[-1][1] <= 1.2: phrases[-1][1] = e
        else: phrases.append([a_, e])
    rel = [i for i, x in enumerate(al) if not x['interp']]
    i = 0
    while i < len(al):
        if not al[i]['interp']: i += 1; continue
        j = i
        while j + 1 < len(al) and al[j + 1]['interp']: j += 1
        p = max([r for r in rel if r < i], default=None); n = min([r for r in rel if r > j], default=None)
        if p is not None and n is not None:
            lo, hi = al[p]['t0'] + 1.5, al[n]['t0'] - 0.3
            cand = [ph for ph in phrases if lo < ph[0] < hi and ph[0] > al[p]['t0'] + (al[p]['t1'] - al[p]['t0']) * 0.8]
            first = [x for x in asr if al[p]['t1'] - 0.1 <= x[1] < hi]   # 前一句唱完之後辨識到的第一個字
            if j == i and first:
                al[i]['t0'] = first[0][1]; al[i]['t0_fixed'] = True
            elif len(cand) == j - i + 1:
                for k, ph in zip(range(i, j + 1), cand):
                    al[k]['t0'] = ph[0]; al[k]['t0_fixed'] = True
        i = j + 1


def fmt_ts(t): return f'[{int(t // 60):02d}:{t % 60:05.2f}]'


def process(sid, url, lyrics):
    song = SONGS[sid]
    lines = lyrics[song]
    mp3 = MUSIC / f'{sid}.mp3'
    dur = S.duration(mp3)
    w16 = S.decode_wav(mp3, 16000, 1)[:, 0]
    db = S.energy_db(w16)
    info = {'id': sid, 'song': song, 'duration': round(dur, 1), 'lines': len(lines)}
    if song in S.MANUAL_LINES:   # 台語老歌：作者手標
        man = S.MANUAL_LINES[song]
        assert len(man) == len(lines)
        times = [a for a, _ in man]
        info.update(mode='dynamic-manual', matched=1.0, unsure=[], note='前 8 句為作者手標；95 秒之後的副歌重複沒有標')
        return info, [(t, l['text'], l['sec']) for t, l in zip(times, lines)]
    key = S.hashlib.md5(mp3.read_bytes()).hexdigest()[:10]
    entry = find_entry(w16, lines)
    start = entry
    A = strip_hallu([tuple(x) for x in windowed(w16, key, start)])
    B = strip_hallu([tuple(x) for x in windowed(w16, key, start + 10.0)])   # 第二組視窗（錯開 10 秒）補第一組被幻覺吃掉的地方
    asr = sorted(A + [b for b in B if not any(abs(b[1] - a_[1]) < 0.4 for a_ in A)], key=lambda x: x[1])
    al = S.align(asr, lines)   # DTW 字詞時間本身就貼著起音，不再用能量起音修正
    cov = sum(a['matched'] for a in al) / max(1, sum(a['chars'] for a in al))
    info.update(entry=round(entry, 1), asr_chars=len(asr), matched=round(cov, 2),
                unsure=[i for i, a in enumerate(al) if a['interp']])
    if cov < GATE:
        info.update(mode='static', note=f'字數只對到 {cov:.0%}，低於 {GATE:.0%}，退回靜態歌詞')
        return info, None
    fix_unsure(al, asr)
    t0 = []
    for i, a in enumerate(al):
        t = max(0.0, a['t0'] - LEAD)
        if t0 and t < t0[-1] + 0.3: t = t0[-1] + 0.3
        t0.append(min(t, dur - 0.5))
    info['mode'] = 'dynamic'
    info['conf'] = [round(a['conf'], 2) for a in al]
    return info, [(t, l['text'], l['sec']) for t, l in zip(t0, lines)]


def main():
    ids = sys.argv[1:] or list(SONGS)
    url = None; S.CACHE.mkdir(parents=True, exist_ok=True)
    lyrics = all_lyrics()
    status = {}
    for sid in ids:
        info, rows = process(sid, url, lyrics)
        status[sid] = info
        if rows:
            body = ['[ti:%s]' % info['song'], '[ar:余靜]', '[by:歌詞文字為官方歌詞，時間由辨識對齊後校正]', '']
            body += [f'{fmt_ts(t)}{text}' for t, text, _ in rows]
            (MUSIC / f'{sid}.lrc').write_text('\n'.join(body) + '\n', encoding='utf-8')
            info['secs'] = [sec for _, _, sec in rows]
            info['times'] = [round(t, 2) for t, _, _ in rows]
        elif (MUSIC / f'{sid}.lrc').exists():
            (MUSIC / f'{sid}.lrc').unlink()
        print(sid, info['mode'], 'match', info.get('matched'), 'unsure', info.get('unsure'), flush=True)
    p = MUSIC / 'lyrics.json'
    old = json.loads(p.read_text()) if p.exists() else {}
    old.update({k: {kk: vv for kk, vv in v.items() if kk != 'conf'} for k, v in status.items()})
    # 靜態曲也要有歌詞文字：頁面從這裡讀
    for sid, song in SONGS.items():
        if sid in old: old[sid]['text'] = [{'text': l['text'], 'sec': l['sec']} for l in lyrics[song]]
    p.write_text(json.dumps(old, ensure_ascii=False, indent=1), encoding='utf-8')
    json.dump(status, open('/tmp/lrc-status.json', 'w'), ensure_ascii=False)


if __name__ == '__main__':
    main()
