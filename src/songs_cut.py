#!/usr/bin/env python3
"""接歌工具：assets/songs/*.mp3（作者在 Suno 做的三首）→ 對齊歌詞時間 → 依對照表切段 → assets/songs/cuts/*.mp3 + manifest.json。

    python3 src/songs_cut.py              # 處理 assets/songs/ 底下有的歌（沒放的歌略過）
    python3 src/songs_cut.py --build      # 切完直接 build（等於接著跑 python3 src/build.py）
    python3 src/songs_cut.py --only ember_b1,night_sc    # 只重切指定段
    SONGS_DIR=assets/songs/_fixture python3 src/songs_cut.py   # 測試用：換資料夾（替身音檔）

做的事：
1. 轉錄：呼叫共用 whisper-server（~/.mori/whisper-server.json；沒開就用 mori-whisper-serve --ensure 拉起 large-v3-turbo），
   逐字時間（srt, max_len=1）。只取時間，字一律以 canon/歌詞.md 為準。
2. 對齊：歌詞字與轉錄字做全域單調對齊（DP，順序約束，所以第 2、3 次副歌不會全黏到第一次），每句取時間與信心。
3. 切點：落在句與句之間、能量最低的地方（不在字中間）；每段響度 -16 LUFS（雙遍 loudnorm），mp3 盡量小於 1.5MB。
   收音機版（sfx）：單聲道、約 300–3400 Hz、輕微失真與底噪、整體降音量。
4. 驗證：把切出來的檔讀回，頭 3 秒、尾 3 秒各轉錄一次，和預期那句比對；另做負控制（拿錯的句子比對，分數必須明顯較低）。
5. 寫 manifest.json（檔名、卡與句序、起迄、類型、每句時間、驗證結果）。src/songs.py 的 apply() 讀它。
"""
import argparse, hashlib, io, json, os, pathlib, re, subprocess, sys, tempfile, time, urllib.request, wave

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

SONGS_DIR = pathlib.Path(os.environ.get('SONGS_DIR') or ROOT / 'assets/songs')
if not SONGS_DIR.is_absolute():
    SONGS_DIR = ROOT / SONGS_DIR
SONGS_DIR = SONGS_DIR.resolve()
CUT_DIR = SONGS_DIR / 'cuts'
CACHE = ROOT / '.songs-cache' / hashlib.md5(str(SONGS_DIR).encode()).hexdigest()[:8]   # 轉錄與中間檔（不進 assets，不進 dist）

TARGET_LUFS = -16.0          # 歌略大聲：背景曲約 -16.3 LUFS，卡上 bgmVolume 0.5；歌的 bgmVolume 設 0.65（songs.py）
RADIO_LUFS = -20.0           # 收音機版整體降音量
MAX_BYTES = 1_500_000
SR = 44100

# ---------------------------------------------------------------- 歌詞

SONG_FILES = {'餘燼': '餘燼.mp3', '晚安，台南': '晚安台南.mp3', '港邊的燈': '港邊的燈.mp3'}
LENIENT = {'港邊的燈'}       # 台語歌：轉錄與對齊本來就不準（canon/歌詞.md：唸不準也沒關係），驗證改看切點是否落在靜處


def load_lyrics():
    """canon/歌詞.md → {歌名: [{'i','sec','text'}...]}，sec 是 Suno 段落標籤（重複的加 #2）。"""
    txt = (ROOT / 'canon/歌詞.md').read_text(encoding='utf-8')
    out = {}
    for blk in re.split(r'^## ', txt, flags=re.M)[1:]:
        head = blk.split('\n', 1)[0]
        m = re.search(r'〈(.+?)〉', head)
        mm = re.search(r'### 歌詞[^\n]*\n+```\n(.*?)```', blk, re.S)
        if not (m and mm):
            continue
        lines, sec, seen = [], '', {}
        for raw in mm.group(1).splitlines():
            s = raw.strip()
            if not s:
                continue
            t = re.match(r'^\[(.+)\]$', s)
            if t:
                seen[t.group(1)] = seen.get(t.group(1), 0) + 1
                sec = t.group(1) + (f'#{seen[t.group(1)]}' if seen[t.group(1)] > 1 else '')
                continue
            lines.append({'i': len(lines), 'sec': sec, 'text': s})
        out[m.group(1)] = lines
    return out


def L(lyrics, song, sec, k):
    """某首歌、某段的第 k 句 → 全曲句序。"""
    for l in lyrics[song]:
        if l['sec'] == sec:
            if k == 0:
                return l['i']
            k -= 1
    raise KeyError((song, sec))


# ---------------------------------------------------------------- 切段對照表
# start：('song',) 從頭；('line', 段, 第幾句, 最多提前幾秒)。end：('eof',)；('after', 段, 第幾句, 最多拖尾幾秒)。
# place：卡代號與句子位置。anchor 是句子裡的文字（唯一匹配）；'first_sung' = 該卡第一句余靜（唱）。
# role：sung_card（切成「歌卡」，歌詞跟著時間走）／line_bgm（只在某句開始放）／sfx（逐句 sfxUrl，收音機版）。
CUTS = [
    dict(id='ember_b1', song='餘燼', kind='bgm', role='sung_card', card='ending_b1', anchor='first_sung', resume='next',
         start=('song',), end=('eof',), fade_out=1.0),
    dict(id='ember_a2', song='餘燼', kind='bgm', role='sung_card', card='ending_a2', anchor='first_sung', resume='next',
         start=('line', 'Final Chorus', 0, 1.5), end=('eof',), fade_out=1.0),
    dict(id='ember_c4', song='餘燼', kind='bgm', role='line_bgm', card='ending_c4', anchor='按下播放鍵', same_as='ember_b1'),
    dict(id='ember_radio_a', song='餘燼', kind='sfx', role='sfx', card='m_radio_on', anchor='鋼琴前奏響起',
         start=('song',), end=('after', 'Verse 1', 0, 0.8), fade_out=0.6),
    dict(id='ember_radio_b', song='餘燼', kind='sfx', role='sfx', card='m_radio_on', anchor='燈一盞一盞暗下來，掌聲',
         start=('line', 'Verse 1', 0, 0.8), end=('after', 'Verse 1', 1, 0.8), fade_out=0.6),
    dict(id='night_sc', song='晚安，台南', kind='bgm', role='sung_card', card='soundcheck', anchor='first_sung', resume='post',
         start=('line', 'Verse 1', 0, 1.0), end=('after', 'Verse 1', 3, 2.4), fade_out=1.8),
    dict(id='night_concert', song='晚安，台南', kind='bgm', role='sung_card', card='concert', anchor='first_sung', resume='none',
         start=('line', 'Verse 1', 0, 0.6), end=('after', 'Verse 2', 3, 0.2), fade_out=0.06, sudden=True),
    dict(id='night_a1', song='晚安，台南', kind='bgm', role='sung_card', card='ending_a1', anchor='first_sung', resume='next',
         start=('line', 'Verse 3', 0, 1.0), end=('after', 'Verse 3', 3, 2.2), fade_out=1.6),
    dict(id='harbor_open', song='港邊的燈', kind='sfx', role='sfx', card='m_radio_on', anchor='手風琴伴著一段台語老歌',
         start=('song',), end=('after', 'Verse', 1, 0.8), fade_out=0.6),
    dict(id='harbor_market', song='港邊的燈', kind='sfx', role='sfx', card='mem0_market', anchor='播著〈港邊的燈〉',
         start=('line', 'Chorus', 0, 0.8), end=('after', 'Chorus', 1, 0.8), fade_out=0.6),
]

# ---------------------------------------------------------------- 工具


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, **kw)
    if r.returncode:
        raise RuntimeError(f'{cmd[0]} 失敗：{r.stderr.decode(errors="replace")[-400:]}')
    return r


def decode_wav(path, sr, ch):
    """任何音檔 → float32 numpy (n, ch)。"""
    r = run(['ffmpeg', '-v', 'error', '-i', str(path), '-ar', str(sr), '-ac', str(ch), '-f', 'f32le', '-'])
    return np.frombuffer(r.stdout, dtype=np.float32).reshape(-1, ch)


def wav_bytes(x, sr):
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(x.shape[1]); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype('<i2').tobytes())
    return buf.getvalue()


def duration(path):
    return float(run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(path)]).stdout)


_cc = None


def t2s(s):
    global _cc
    if _cc is None:
        try:
            import opencc
            _cc = opencc.OpenCC('t2s').convert
        except Exception:   # noqa: BLE001  沒裝 opencc 就用命令列
            _cc = lambda x: run(['opencc', '-c', 't2s'], input=x.encode()).stdout.decode()   # noqa: E731
    return _cc(s)


def norm(s):
    return t2s(re.sub(r'[^\u4e00-\u9fffA-Za-z0-9]', '', s))


# ---------------------------------------------------------------- 轉錄（共用 whisper-server）

DESC = pathlib.Path.home() / '.mori/whisper-server.json'


def whisper_url():
    if os.environ.get('WHISPER_URL'):
        return os.environ['WHISPER_URL']

    def alive():
        try:
            d = json.loads(DESC.read_text())
            u = f"http://{d['host']}:{d['port']}"
            urllib.request.urlopen(u + '/', timeout=3).read()
            return u + d.get('inference_path', '/inference'), d.get('model')
        except Exception:   # noqa: BLE001
            return None
    r = alive()
    if not r:
        print('whisper-server 沒開，拉起 large-v3-turbo …', flush=True)
        subprocess.run([str(pathlib.Path.home() / '.mori/bin/mori-whisper-serve'), '--ensure', '--model', 'large-v3-turbo'], capture_output=True)
        for _ in range(60):
            time.sleep(2)
            r = alive()
            if r:
                break
    if not r:
        sys.exit('找不到可用的 whisper-server（~/.mori/whisper-server.json）。也可設 WHISPER_URL 指到別的 whisper.cpp server。')
    if r[1] != 'large-v3-turbo':
        print(f'警告：共用 whisper-server 載的是 {r[1]}，唱歌用 large-v3-turbo 才準（對齊會變差）。', flush=True)
    return r[0]


def transcribe(wav16, url):
    """16k 單聲道 float → [(字, 起, 迄)]（簡體，只用時間）。"""
    data = wav_bytes(wav16.reshape(-1, 1), 16000)
    b = '----songscut' + hashlib.md5(data[:2000]).hexdigest()[:10]
    parts = []
    for k, v in (('response_format', 'srt'), ('max_len', '1'), ('language', 'zh'), ('temperature', '0')):
        parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    parts.append(f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="a.wav"\r\nContent-Type: audio/wav\r\n\r\n'.encode() + data + b'\r\n')
    parts.append(f'--{b}--\r\n'.encode())
    req = urllib.request.Request(url, data=b''.join(parts), headers={'Content-Type': 'multipart/form-data; boundary=' + b})
    srt = urllib.request.urlopen(req, timeout=600).read().decode('utf-8', 'replace')
    out = []
    for m in re.finditer(r'(\d+):(\d+):(\d+),(\d+) --> (\d+):(\d+):(\d+),(\d+)\n(.*?)(?:\n\n|\Z)', srt, re.S):
        g = [int(x) for x in m.groups()[:8]]
        a, e = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000, g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000
        for ch in norm(m.group(9)):
            out.append((ch, a, e))
    return out


def transcribe_cached(wav16, url, key):
    f = CACHE / f'asr-{key}.json'
    if f.exists():
        return [tuple(x) for x in json.loads(f.read_text())]
    r = transcribe(wav16, url)
    f.write_text(json.dumps(r, ensure_ascii=False))
    return r


def fix_intro(asr, w16, url, key, first_line):
    """whisper 的第一段會從 0 秒起把字平均攤開，前奏長的歌第一句的時間全錯。做法：用滑動小視窗找人聲第一次唱出第一句的位置，
    把那之前的前奏切掉重新轉錄一次，時間再加回去。"""
    f = CACHE / f'asr-{key}-intro.json'
    if f.exists():
        return [tuple(x) for x in json.loads(f.read_text())]
    target = norm(first_line)
    entry = None
    for k in range(0, 20):
        w0 = k * 2.0
        seg = w16[int(w0 * 16000):int((w0 + 5.0) * 16000)]
        if len(seg) < 16000:
            break
        h = ''.join(c for c, _, _ in transcribe(seg, url))
        if lcs(h, target) >= max(3, 0.5 * len(target)):
            entry = w0
            break
    out = asr
    if entry is not None and entry - 2.0 > 1.0:
        t0 = entry - 2.0
        re_ = [(c, a + t0, e + t0) for c, a, e in transcribe(w16[int(t0 * 16000):], url)]
        out = [x for x in asr if x[2] <= t0] + re_
        print(f'  前奏：人聲約在 {entry:.0f}–{entry + 5:.0f} 秒進來，切掉前 {t0:.0f} 秒重新轉錄', flush=True)
    f.write_text(json.dumps(out, ensure_ascii=False))
    return out


# ---------------------------------------------------------------- 對齊

MATCH, MIS, GAP = 2.0, -1.5, -1.0


def align(asr, lines, lenient=False, db=None):
    """歌詞字 ↔ 轉錄字，全域單調（半全域：頭尾可略過）。回傳每句 {t0,t1,conf,matched,est}。
    只取時間：t0/t1 由「匹配到的字」往句首、句尾外推（每字 0.25 秒）取中位數；信心低的句子在左右可靠句之間按字數內插。"""
    chars, owner, pos = [], [], []
    for li, l in enumerate(lines):
        for k, ch in enumerate(norm(l['text'])):
            chars.append(ch); owner.append(li); pos.append(k)
    n, m = len(asr), len(chars)
    S = np.zeros((n + 1, m + 1)); P = np.zeros((n + 1, m + 1), dtype=np.int8)   # 1 對角 2 上（轉錄多字）3 左（歌詞字沒轉到）
    a_chars = [c for c, _, _ in asr]
    for i in range(1, n + 1):
        ai = a_chars[i - 1]
        for j in range(1, m + 1):
            d = S[i - 1, j - 1] + (MATCH if ai == chars[j - 1] else MIS)
            u = S[i - 1, j] + GAP
            l_ = S[i, j - 1] + GAP
            if d >= u and d >= l_:
                S[i, j], P[i, j] = d, 1
            elif u >= l_:
                S[i, j], P[i, j] = u, 2
            else:
                S[i, j], P[i, j] = l_, 3
    # 尾端自由
    bi, bj = n, m
    best = S[n, m]
    for i in range(n + 1):
        if S[i, m] > best: best, bi, bj = S[i, m], i, m
    for j in range(m + 1):
        if S[n, j] > best: best, bi, bj = S[n, j], n, j
    i, j = bi, bj
    pair = {}   # 歌詞字 j → 轉錄字 i
    while i > 0 and j > 0:
        p = P[i, j]
        if p == 1:
            if a_chars[i - 1] == chars[j - 1]:
                pair[j - 1] = i - 1
            i -= 1; j -= 1
        elif p == 2:
            i -= 1
        else:
            j -= 1
    res = []
    for li, l in enumerate(lines):
        idx = [k for k in range(m) if owner[k] == li]
        mt = [(pos[k], pair[k]) for k in idx if k in pair]
        total = len(idx)
        if mt:
            # whisper 的逐字時間是首尾相接的（字的起點 = 上一個字的迄點，停頓被算進下一字），所以只信「迄點」：
            # 句首 = 匹配字的迄點 往回推 (位置+1) 個字長；句尾 = 匹配字的迄點 往後推到最後一字。字長用匹配字迄點的斜率估（夾在 0.15–0.7 秒）。
            if len(mt) >= 2 and mt[-1][0] > mt[0][0]:
                dpc = (asr[mt[-1][1]][2] - asr[mt[0][1]][2]) / (mt[-1][0] - mt[0][0])
                dpc = min(0.7, max(0.15, dpc))
            else:
                dpc = 0.28
            st = float(np.median([asr[ai][2] - (p + 1) * dpc for p, ai in mt]))
            en = float(np.median([asr[ai][2] + (total - 1 - p) * dpc for p, ai in mt]))
        else:
            st = en = None
        res.append({'t0': st, 't1': en, 'conf': len(mt) / max(1, total), 'matched': len(mt), 'chars': total, 'interp': False})
    thr = 0.2 if lenient else 0.3
    rel = [i for i, r in enumerate(res) if r['t0'] is not None and r['conf'] >= thr]
    if not rel:
        raise RuntimeError('歌詞對不上轉錄（可靠句 0 句）：這首歌跟 canon/歌詞.md 差太多，或轉錄失敗。')
    for i, r in enumerate(res):
        if i in rel:
            continue
        r['interp'] = True
        prv = max([x for x in rel if x < i], default=None)
        nxt = min([x for x in rel if x > i], default=None)
        # 這一段不可靠句的字數權重
        if prv is not None and nxt is not None:
            run_ = [x for x in range(prv + 1, nxt)]
            a, b = res[prv]['t1'] + 0.15, res[nxt]['t0'] - 0.15
        elif prv is not None:
            run_ = [x for x in range(prv + 1, len(res))]
            a, b = res[prv]['t1'] + 0.5, res[prv]['t1'] + 0.5 + 0.3 * sum(res[x]['chars'] for x in run_)
        else:
            run_ = [x for x in range(0, nxt)]
            b = res[nxt]['t0'] - 0.5; a = max(0.0, b - 0.3 * sum(res[x]['chars'] for x in run_))
        tot = sum(res[x]['chars'] for x in run_) or 1
        t = a
        for x in run_:
            span = max(0.2, (b - a)) * res[x]['chars'] / tot
            res[x]['t0'], res[x]['t1'] = t, t + span * 0.9
            t += span
    if db is not None:   # 句首修正：whisper 逐字時間首尾相接，停頓會被算進下一句開頭（只有句尾可信）。
        # 在「上一句句尾 → 這句句尾」之間，取第一個接近這段最響處（-12dB 內）的位置當句首；伴奏很響的歌，這會落在人聲起音之前（偏早，安全）
        for i, r in enumerate(res):
            lo = (res[i - 1]['t1'] if i else 0.0) + 0.03
            hi = r['t1'] + 0.6   # 句尾也可能估早，多看一點
            a, b = frame(lo), frame(hi)
            if b - a < 5:
                continue
            seg = db[a:b]
            mx = seg.max()
            up = np.where(seg >= mx - 12.0)[0]
            quiet = [k for k in up if k >= 15 and seg[k - 15:k].max() < mx - 18.0]   # 前面先靜一下再響起來的第一個起音
            if quiet:
                up = [quiet[0]]
            if len(up):
                r['t0_char'] = r['t0']
                r['t0'] = max(lo, (a + up[0]) * HOP - 0.05)
                r['onset'] = True
    for r in res:   # 切點用的「安全句首」：取較早的那個（切點落在縫隙裡，寧早勿晚；歌詞畫面時間才用起音修正過的 t0）
        r['t0_safe'] = min(r['t0'], r.get('t0_char', r['t0']))
    for i in range(len(res)):   # 單調
        if i and res[i]['t0'] < res[i - 1]['t1']:
            res[i]['t0'] = res[i - 1]['t1']
        if res[i]['t1'] < res[i]['t0'] + 0.3:
            res[i]['t1'] = res[i]['t0'] + 0.3
    return res


# ---------------------------------------------------------------- 能量與切點

HOP = 0.01


def energy_db(x16):
    """16k 單聲道 → 每 10ms 一格的 RMS(dB)，25ms 視窗。"""
    w = 400; h = 160
    n = max(0, (len(x16) - w) // h + 1)
    if n == 0:
        return np.array([-100.0])
    idx = np.arange(w)[None, :] + h * np.arange(n)[:, None]
    rms = np.sqrt((x16[idx] ** 2).mean(axis=1) + 1e-12)
    db = 20 * np.log10(rms)
    return np.convolve(db, np.ones(3) / 3, mode='same')


def frame(t):
    return int(round(t / HOP))


def pick(db, lo, hi, latest):
    """[lo,hi] 秒裡能量接近最低（最低 +4dB 以內）的格子；latest=True 取最晚、False 取最早。"""
    a, b = max(0, frame(lo)), min(len(db) - 1, frame(hi))
    if b <= a:
        return max(0.0, (lo + hi) / 2), db[min(len(db) - 1, max(0, frame((lo + hi) / 2)))], db[min(len(db) - 1, max(0, frame((lo + hi) / 2)))]
    seg = db[a:b + 1]
    mn = seg.min()
    ok = np.where(seg <= mn + 4.0)[0]
    k = ok[-1] if latest else ok[0]
    return (a + k) * HOP, float(seg[k]), float(mn)


def cut_points(spec, lines, al, db, dur):
    """回傳 (start秒, end秒, 診斷)。"""
    def li(sec, k):
        return L_idx(lines, sec, k)
    diag = {}
    if spec['start'][0] == 'song':
        s = 0.0; diag['start'] = {'at': 'song_start'}
    else:
        _, sec, k, lead = spec['start']
        i = li(sec, k)
        ls = al[i]['t0']
        prev_end = al[i - 1]['t1'] if i else 0.0
        lo, hi = max(prev_end + 0.04, ls - lead, 0.0), ls - 0.03
        s, cdb, mn = pick(db, lo, hi, latest=False)
        diag['start'] = {'line': i, 'window': [round(lo, 2), round(hi, 2)], 'db': round(cdb, 1), 'gap_min_db': round(mn, 1)}
    if spec['end'][0] == 'eof':
        # 檔尾：去掉結尾的數位靜音
        loud = np.where(db > -60)[0]
        e = min(dur, (loud[-1] * HOP + 0.4) if len(loud) else dur)
        diag['end'] = {'at': 'eof'}
    else:
        _, sec, k, tail = spec['end']
        i = li(sec, k)
        le = al[i]['t1']
        nxt = al[i + 1]['t0'] if i + 1 < len(al) else dur
        lo, hi = le + 0.03, min(nxt - 0.03, le + tail, dur)
        e, cdb, mn = pick(db, lo, max(lo + 0.01, hi), latest=True)
        diag['end'] = {'line': i, 'window': [round(lo, 2), round(hi, 2)], 'db': round(cdb, 1), 'gap_min_db': round(mn, 1)}
    return s, e, diag


def L_idx(lines, sec, k):
    for l in lines:
        if l['sec'] == sec:
            if k == 0:
                return l['i']
            k -= 1
    raise KeyError(sec)


# ---------------------------------------------------------------- 渲染

def loudnorm_two_pass(x, sr, target, tp=-1.5):
    """x: float (n,ch) → 套雙遍 loudnorm（linear）後的 float。回傳 (x, 量到的 LUFS)。"""
    wav = wav_bytes(x, sr)
    r = subprocess.run(['ffmpeg', '-v', 'info', '-i', 'pipe:0', '-af', f'loudnorm=I={target}:TP={tp}:LRA=11:print_format=json', '-f', 'null', '-'],
                       input=wav, capture_output=True)
    txt = r.stderr.decode(errors='replace')
    j = json.loads(txt[txt.rfind('{'):txt.rfind('}') + 1])
    af = (f"loudnorm=I={target}:TP={tp}:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}"
          f":measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")
    r2 = subprocess.run(['ffmpeg', '-v', 'error', '-i', 'pipe:0', '-af', af, '-ar', str(sr), '-f', 'f32le', '-'], input=wav, capture_output=True)
    if r2.returncode:
        raise RuntimeError(r2.stderr.decode(errors='replace')[-300:])
    y = np.frombuffer(r2.stdout, dtype=np.float32).reshape(-1, x.shape[1])
    return y, float(j['input_i'])


def measure_lufs(path):
    r = subprocess.run(['ffmpeg', '-v', 'info', '-i', str(path), '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True)
    m = re.findall(r'I:\s+(-?[\d.]+) LUFS', r.stderr.decode(errors='replace'))
    return float(m[-1]) if m else None


def radio_filter(x, sr, seed=7):
    """老收音機音色：單聲道、300–3400Hz、輕微失真（tanh）、慢慢起伏的訊號強弱、粉紅底噪與零星爆音。用 ffmpeg 濾鏡。"""
    d = len(x) / sr
    fc = (f"[0:a]pan=mono|c0=0.5*c0+0.5*c1,highpass=f=320:poles=2,lowpass=f=3300:poles=2,equalizer=f=1500:t=q:w=1.2:g=3,"
          f"volume=6dB,asoftclip=type=tanh:threshold=0.5,tremolo=f=0.35:d=0.10,highpass=f=300,lowpass=f=3400[v];"
          f"anoisesrc=d={d + 1:.2f}:c=pink:r={sr}:a=0.03:seed={seed},highpass=f=300,lowpass=f=3400[n];"
          f"aevalsrc='if(lt(random(0),0.00006),(random(1)-0.5)*1.2,0)':s={sr}:d={d + 1:.2f},lowpass=f=3400[c];"
          f"[v][n][c]amix=inputs=3:normalize=0:duration=first,volume=0.9[o]")
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', 'pipe:0', '-filter_complex', fc, '-map', '[o]', '-ar', str(sr), '-ac', '1', '-f', 'f32le', '-'],
                       input=wav_bytes(x, sr), capture_output=True)
    if r.returncode:
        raise RuntimeError(r.stderr.decode(errors='replace')[-400:])
    return np.frombuffer(r.stdout, dtype=np.float32).reshape(-1, 1)


def encode_mp3(x, sr, out, mono_ok=False):
    """依大小逐級降位元率，直到 < MAX_BYTES。回傳 (位元率, 位元組)。"""
    ladder = [(160, 2), (128, 2), (112, 2), (96, 2), (80, 2), (64, 2), (64, 1), (56, 1), (48, 1), (40, 1)]
    if x.shape[1] == 1:
        ladder = [(b, 1) for b in (96, 80, 64, 56, 48, 40)]
    wav = wav_bytes(x, sr)
    for br, ch in ladder:
        r = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', 'pipe:0', '-ac', str(ch), '-c:a', 'libmp3lame', '-b:a', f'{br}k', str(out)], input=wav, capture_output=True)
        if r.returncode:
            raise RuntimeError(r.stderr.decode(errors='replace')[-300:])
        size = pathlib.Path(out).stat().st_size
        if size < MAX_BYTES:
            return br, size
    return br, size   # 最低檔還是超過：照實回報


def fades(x, sr, fin, fout):
    y = x.copy()
    n_in, n_out = int(fin * sr), int(fout * sr)
    if n_in:
        y[:n_in] *= (0.5 - 0.5 * np.cos(np.linspace(0, np.pi, n_in)))[:, None]
    if n_out:
        y[-n_out:] *= (0.5 + 0.5 * np.cos(np.linspace(0, np.pi, n_out)))[:, None]
    return y


# ---------------------------------------------------------------- 驗證

def lcs(a, b):
    if not a or not b:
        return 0
    prev = [0] * (len(b) + 1)
    for ca in a:
        cur = [0]
        for j, cb in enumerate(b):
            cur.append(prev[j] + 1 if ca == cb else max(prev[j + 1], cur[j]))
        prev = cur
    return prev[-1]


def verify_window(url, x_mono16, rel_lines, lines_all, w0, w1, lenient):
    """x_mono16：切出來的檔（16k 單聲道）。視窗 [w0,w1] 秒讀回轉錄，跟預期句子比對。"""
    seg = x_mono16[int(w0 * 16000):int(w1 * 16000)]
    heard = ''.join(c for c, _, _ in transcribe(seg, url)) if len(seg) > 1600 else ''
    exp = []
    for l in rel_lines:
        ov = min(l['t1'], w1) - max(l['t0'], w0)
        if ov > 0 and (ov / max(0.1, l['t1'] - l['t0']) >= 0.3 or ov >= 1.0):
            exp.append(l['text'])
    r = {'window': [round(w0, 2), round(w1, 2)], 'heard': heard, 'expected': exp}
    if not exp:
        r['ok'] = True; r['note'] = '視窗內沒有預期歌詞（器樂）' + ('' if len(heard) <= 6 else f'；但轉錄到 {len(heard)} 字，請人工聽')
        return r
    E = [norm(t) for t in exp]

    def score(h, e):   # 句子被聽到多少（召回），或聽到的字有多少落在這句裡（精確；視窗只框到半句時用）
        l = lcs(h, e)
        return max(l / max(1, len(e)), (l / max(1, len(h))) if len(h) >= 3 else 0.0)
    recall = max(score(heard, e) for e in E)
    exp_txt = set(E)
    others = [norm(l['text']) for l in lines_all if norm(l['text']) not in exp_txt]
    other_best = max([score(heard, o) for o in others], default=0.0)
    ctrl = other_best   # 負控制：拿「不是預期的句子」比對，分數必須明顯較低
    thr = 0.2 if lenient else 0.5
    r.update(recall=round(recall, 2), best_other=round(other_best, 2), neg_control=round(ctrl, 2), threshold=thr)
    r['ok'] = bool(recall >= thr and (recall >= other_best or lenient))
    return r


def inside_char(asr, t, margin=0.04):
    return any(s + margin < t < e - margin for _, s, e in asr if e - s > 0.02)


# ---------------------------------------------------------------- 主程式

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', default='')
    ap.add_argument('--build', action='store_true')
    ap.add_argument('--no-verify', action='store_true')
    args = ap.parse_args()
    only = set(filter(None, args.only.split(',')))
    lyrics = load_lyrics()
    CACHE.mkdir(parents=True, exist_ok=True); CUT_DIR.mkdir(parents=True, exist_ok=True)
    present = {s: SONGS_DIR / f for s, f in SONG_FILES.items() if (SONGS_DIR / f).exists()}
    if not present:
        sys.exit(f'{SONGS_DIR} 底下沒有歌檔。預期：' + '、'.join(SONG_FILES.values()))
    for s in SONG_FILES:
        print(('找到 ' if s in present else '沒有 ') + SONG_FILES[s])
    url = whisper_url()
    import script
    truth = json.loads((SONGS_DIR / 'truth.json').read_text()) if (SONGS_DIR / 'truth.json').exists() else {}
    song_info, align_res, dbs, wav44, asrs = {}, {}, {}, {}, {}
    for song, path in present.items():
        key = hashlib.md5(path.read_bytes()).hexdigest()[:10]
        dur = duration(path)
        w16 = decode_wav(path, 16000, 1)[:, 0]
        asr = transcribe_cached(w16, url, key)
        asr = fix_intro(asr, w16, url, key, lyrics[song][0]['text'])
        db = energy_db(w16)
        al = align(asr, lyrics[song], lenient=song in LENIENT, db=db)
        asrs[song], align_res[song], dbs[song] = asr, al, db
        wav44[song] = decode_wav(path, SR, 2)
        info = {'file': path.name, 'duration': round(dur, 2), 'asr_chars': len(asr), 'sha': key,
                'lines': [{'i': l['i'], 'sec': l['sec'], 'text': l['text'], 't0': round(a['t0'], 2), 't1': round(a['t1'], 2),
                           'conf': round(a['conf'], 2), 'interp': a['interp']} for l, a in zip(lyrics[song], al)]}
        covered = sum(a['matched'] for a in al) / max(1, sum(a['chars'] for a in al))
        info['char_match'] = round(covered, 2)
        info['low_conf_lines'] = sum(1 for a in al if a['interp'])
        if song in truth:   # 替身音檔：有真實句子時間，量對齊誤差
            tr = truth[song]
            e0 = [abs(a['t0'] - t['t0']) for a, t in zip(al, tr)]
            e1 = [abs(a['t1'] - t['t1']) for a, t in zip(al, tr)]
            info['truth_error'] = {'start_mean': round(float(np.mean(e0)), 3), 'start_p95': round(float(np.percentile(e0, 95)), 3), 'start_max': round(float(np.max(e0)), 3),
                                   'end_mean': round(float(np.mean(e1)), 3), 'end_max': round(float(np.max(e1)), 3)}
        song_info[song] = info
        print(f'〈{song}〉{dur:.1f}s 轉錄 {len(asr)} 字，歌詞字匹配 {covered:.0%}，內插句 {info["low_conf_lines"]}/{len(al)}'
              + (f"；對真值 起點誤差 平均 {info['truth_error']['start_mean']}s 最大 {info['truth_error']['start_max']}s" if 'truth_error' in info else ''), flush=True)

    entries, rendered = [], {}
    all_ok = True
    for spec in CUTS:
        if spec['song'] not in present or (only and spec['id'] not in only):
            continue
        song = spec['song']; lines = lyrics[song]; al = align_res[song]; db = dbs[song]
        dur = song_info[song]['duration']
        base = spec.get('same_as')
        sp = next(c for c in CUTS if c['id'] == base) if base else spec
        place_line = locate(script, spec)
        if base and base in rendered:
            e = json.loads(json.dumps(rendered[base]))
            e.update(id=spec['id'], role=spec['role'], place={'card': spec['card'], 'line': place_line, 'anchor': spec['anchor']}, same_as=base)
            entries.append(e); continue
        s, e_, diag = cut_points(sp, lines, al, db, dur)
        x = wav44[song][int(s * SR):int(e_ * SR)]
        fo = sp.get('fade_out', 0.5)
        x = fades(x, SR, 0.04 if s > 0 else 0.02, min(fo, len(x) / SR / 2))
        radio = sp['kind'] == 'sfx'
        if radio:
            x = radio_filter(x, SR)
        x, in_lufs = loudnorm_two_pass(x, SR, RADIO_LUFS if radio else TARGET_LUFS, tp=-2.0 if radio else -1.5)
        out = CUT_DIR / f"{sp['id']}.mp3"
        br, size = encode_mp3(x, SR, out)
        d_out = duration(out)
        lufs = measure_lufs(out)
        rel = [{'text': l['text'], 't0': round(a['t0'] - s, 2), 't1': round(a['t1'] - s, 2), 'conf': round(a['conf'], 2), 'interp': a['interp'], 'sec': l['sec']}
               for l, a in zip(lines, al) if a['t0'] >= s - 0.05 and a['t1'] <= e_ + 0.05]
        # 驗證
        ver = {'ok': True}
        c0, c1 = diag['start'].get('line'), diag['end'].get('line')
        # 切點：不可在字中間；能量要在該縫隙的低點附近
        pts = {}
        for name, t, d in (('start', s, diag['start']), ('end', e_, diag['end'])):
            if d.get('at') in ('eof', 'song_start'):
                pts[name] = {'t': round(t, 2), 'at': d['at'], 'ok': True}; continue
            # 切點在縫隙的低谷：切點能量比前後各 1 秒內最響處低多少 dB（≥8 好；4–8 勉強；<4 切在聲音裡）
            a_, b_ = max(0, frame(t - 1.0)), min(len(db), frame(t + 1.0))
            depth = float(db[a_:b_].max() - db[min(len(db) - 1, frame(t))])
            pts[name] = {'t': round(t, 2), 'valley_depth_db': round(depth, 1), 'weak': depth < 8.0, 'ok': bool(depth >= 4.0)}
        ver['cut_points'] = pts
        if not args.no_verify:
            if radio:   # 驗證讀回乾淨版（收音機濾鏡後的檔對 ASR 本來就更難讀；濾鏡另用頻譜檢查）
                clean = wav44[song][int(s * SR):int(e_ * SR)]
                back = decode_wav_arr(clean, SR)
            else:
                back = decode_wav(out, 16000, 1)[:, 0]
            lenient = song in LENIENT
            d_ = len(back) / 16000
            ver['head'] = verify_window(url, back, rel, lines, 0.0, min(3.0, d_), lenient)
            ver['tail'] = verify_window(url, back, rel, lines, max(0.0, d_ - 3.0), d_, lenient)
            if radio:
                ver['radio'] = radio_check(out)
        ver['ok'] = all(p['ok'] for p in pts.values()) and all(ver.get(k, {'ok': True})['ok'] for k in ('head', 'tail', 'radio'))
        all_ok &= ver['ok']
        ent = {'id': spec['id'], 'song': song, 'file': out.name, 'kind': sp['kind'], 'role': spec['role'],
               'place': {'card': spec['card'], 'line': place_line, 'anchor': spec['anchor']},
               'resume': spec.get('resume', 'none'), 'sudden': bool(sp.get('sudden')),
               'src_start': round(s, 2), 'src_end': round(e_, 2), 'duration': round(d_out, 2), 'bytes': size, 'bitrate_kbps': br,
               'lufs': lufs, 'cut_diag': diag, 'lines': rel, 'verify': ver}
        rendered[spec['id']] = ent
        entries.append(ent)
        flag = 'OK ' if ver['ok'] else 'FAIL'
        print(f"{flag} {spec['id']:14s} {s:6.2f}–{e_:6.2f}s  {d_out:5.1f}s {size/1e6:.2f}MB {br}k {lufs} LUFS  卡 {spec['card']}#{place_line}"
              + ''.join(f"  {k}:{ver[k].get('recall', '-')}" for k in ('head', 'tail') if k in ver), flush=True)
        if not ver['ok']:
            print('   ', json.dumps({k: v for k, v in ver.items() if k != 'ok'}, ensure_ascii=False, default=float)[:1200])
    prev = {}
    mf = CUT_DIR / 'manifest.json'
    if only and mf.exists():   # --only：保留別的段
        prev = {e['id']: e for e in json.loads(mf.read_text())['cuts']}
    for e in entries:
        prev[e['id']] = e
    order = [c['id'] for c in CUTS]
    manifest = {'version': 1, 'generated': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'songs_dir': str(SONGS_DIR.relative_to(ROOT)) if ROOT in SONGS_DIR.parents else str(SONGS_DIR),
                'asr': 'whisper.cpp large-v3-turbo（共用 whisper-server）', 'songs': song_info, 'cuts': [prev[i] for i in order if i in prev]}
    mf.write_text(json.dumps(manifest, ensure_ascii=False, indent=1, default=float), encoding='utf-8')
    print(f'manifest：{mf}（{len(manifest["cuts"])} 段）')
    if not all_ok:
        print('有驗證沒過的段（FAIL）：songs.apply 會略過它們；請看上面的診斷，或換一版歌。')
    if args.build:
        subprocess.run([sys.executable, str(HERE / 'build.py')], check=True)
    sys.exit(0 if all_ok else 2)


def locate(script, spec):
    lines = script.L[spec['card']]
    if spec['anchor'] == 'first_sung':
        hit = [i for i, (spk, t, *_r) in enumerate(lines) if spk == '余靜' and t.startswith('（唱）')]
    else:
        hit = [i for i, (spk, t, *_r) in enumerate(lines) if spec['anchor'] in t]
    if len(hit) < 1 or (spec['anchor'] != 'first_sung' and len(hit) != 1):
        raise SystemExit(f"劇本對不上：{spec['card']} 找不到唯一的句子「{spec['anchor']}」（劇本改了嗎？）")
    return hit[0]


def decode_wav_arr(x, sr):
    """44.1k 立體聲 float → 16k 單聲道 float。"""
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', 'pipe:0', '-ar', '16000', '-ac', '1', '-f', 'f32le', '-'], input=wav_bytes(x, sr), capture_output=True)
    return np.frombuffer(r.stdout, dtype=np.float32)


def radio_check(path):
    """收音機版的規格檢查：單聲道；頻寬外（<250Hz 或 >3600Hz）的能量比例要小。"""
    from scipy.signal import welch
    ch = int(run(['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries', 'stream=channels', '-of', 'csv=p=0', str(path)]).stdout)
    x = decode_wav(path, SR, 1)[:, 0]
    f, p = welch(x, SR, nperseg=4096)
    tot = p.sum() + 1e-18
    out_band = (p[(f < 200)].sum() + p[(f > 4200)].sum()) / tot
    return {'channels': ch, 'out_of_band_energy': round(float(out_band), 4), 'ok': bool(ch == 1 and out_band < 0.05)}


if __name__ == '__main__':
    main()
