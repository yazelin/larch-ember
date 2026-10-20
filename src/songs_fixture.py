#!/usr/bin/env python3
"""替身歌檔（只用來測接歌流程，不是正式資產）：把 canon/歌詞.md 的歌詞用 larch-tts 橋接「念」出來，
墊一層輕輕的和弦當伴奏（句與句之間不是死寂），輸出到 assets/songs/_fixture/，並寫 truth.json（每句真實起迄，量對齊誤差用）。

    python3 src/songs_fixture.py
    SONGS_DIR=assets/songs/_fixture python3 src/songs_cut.py
    SONGS_DIR=assets/songs/_fixture python3 src/build.py     # 之後用 AUDIO=1 END=a node tests/play_full.mjs 試玩

金鑰讀 ~/.config/larch-tts/key，不寫進任何檔案。_fixture 與 .songs-cache 在 .gitignore 裡，測完不 commit。
"""
import hashlib, json, os, pathlib, random, subprocess, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import songs_cut as sc

OUT = ROOT / 'assets/songs/_fixture'
TTS = OUT / 'tts'
URL = 'http://192.168.11.11:8072/tts'
SR = 44100
VOICE = {'餘燼': 'Chinese (Mandarin)_Warm_Bestie', '晚安，台南': 'Chinese (Mandarin)_Warm_Bestie', '港邊的燈': 'Larch_Mandarin_Uncle'}
# 每首的節奏：前奏秒數、句間停頓、段間停頓、尾奏
SHAPE = {'餘燼': (9.0, 1.1, 3.0, 4.0), '晚安，台南': (2.6, 1.0, 2.6, 3.5), '港邊的燈': (5.0, 0.9, 2.2, 3.0)}


def tts(job):
    text, voice = job
    f = TTS / (hashlib.md5(f'{voice}|{text}'.encode()).hexdigest()[:12] + '.mp3')
    if f.exists():
        return f
    key = open(os.path.expanduser('~/.config/larch-tts/key')).read().strip()
    body = json.dumps({'text': text, 'voice': voice, 'format': 'mp3', 'emotion': 'calm'}).encode()
    for k in range(4):
        try:
            data = urllib.request.urlopen(urllib.request.Request(URL, data=body, headers={'Content-Type': 'application/json', 'X-API-Key': key}), timeout=300).read()
            f.write_bytes(data)
            return f
        except Exception as e:   # noqa: BLE001
            print('retry', text, k + 1, repr(e)[:80], flush=True)
            import time; time.sleep(5 * (k + 1))
    raise SystemExit('TTS 失敗：' + text)


def pad(seconds, seed):
    """輕輕的和弦＋每 1.6 秒一下的衰減音（像鋼琴伴奏），約 -28 dBFS。"""
    n = int(seconds * SR); t = np.arange(n) / SR
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    notes = [220.0, 261.63, 329.63, 392.0]
    for k in range(int(seconds / 1.6) + 1):
        t0 = k * 1.6; f = notes[(k * 3) % 4] * (0.5 if k % 4 == 0 else 1)
        m = t >= t0
        env = np.exp(-(t[m] - t0) * 1.8)
        x[m] += env * (np.sin(2 * np.pi * f * t[m]) + 0.4 * np.sin(2 * np.pi * 2 * f * t[m]))
    x += 0.15 * np.sin(2 * np.pi * 110 * t)
    x /= np.abs(x).max()
    return (x * 0.06 + rng.normal(0, 0.0008, n)).astype(np.float32)


def main():
    OUT.mkdir(parents=True, exist_ok=True); TTS.mkdir(exist_ok=True)
    lyrics = sc.load_lyrics()
    jobs = sorted({(l['text'], VOICE[s]) for s in SHAPE for l in lyrics[s]})
    print(len(jobs), '句要念（已有的跳過）', flush=True)
    with ThreadPoolExecutor(3) as ex:
        files = dict(zip(jobs, ex.map(tts, jobs)))
    truth = {}
    for song, (intro, gap, sec_gap, outro) in SHAPE.items():
        rnd = random.Random(song)
        t = intro; segs = []; tr = []; prev_sec = lyrics[song][0]['sec']
        for l in lyrics[song]:
            if l['sec'] != prev_sec:
                t += sec_gap; prev_sec = l['sec']
            v = sc.decode_wav(files[(l['text'], VOICE[song])], SR, 1)[:, 0]
            v = v * (0.5 / max(0.05, np.abs(v).max()))
            segs.append((t, v))
            tr.append({'t0': round(t, 3), 't1': round(t + len(v) / SR, 3)})
            t += len(v) / SR + gap * rnd.uniform(0.7, 1.3)
        total = t + outro
        mix = pad(total, sum(map(ord, song)))
        for st, v in segs:
            a = int(st * SR); mix[a:a + len(v)] += v
        mix[-int(1.5 * SR):] *= np.linspace(1, 0, int(1.5 * SR))
        st = np.stack([mix, mix * 0.97], axis=1)
        out = OUT / sc.SONG_FILES[song]
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'wav', '-i', 'pipe:0', '-c:a', 'libmp3lame', '-b:a', '128k', str(out)], input=sc.wav_bytes(st, SR), check=True)
        truth[song] = tr
        print(f'{out.name}  {total:.1f}s  {len(tr)} 句', flush=True)
    (OUT / 'truth.json').write_text(json.dumps(truth, ensure_ascii=False), encoding='utf-8')


if __name__ == '__main__':
    main()
