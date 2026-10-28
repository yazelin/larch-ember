#!/usr/bin/env python3
"""docs/music/*.lrc（公開站原聲帶頁的逐句時間，site/make_lrc.py 用 DTW 字詞時間做的）→ assets/songs/times.json。
songs_cut.py 對「音檔指紋（md5 前 10 碼）對得上」的歌直接用這些句首時間，不再用 whisper.cpp 逐字時間（同一首換窗起點句首會差到約 4 秒）。
換了歌檔就要重跑：python3 src/songs_times.py ；歌檔變了而 LRC 沒重做時，指紋對不上，songs_cut.py 會退回辨識，不會用錯時間。
"""
import hashlib, json, pathlib, re, subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
SONGS = ROOT / 'assets/songs'
# 虛擬歌名 → (LRC 檔, 歌檔名)
MAP = {'餘燼@錄音室': ('ember-studio', '餘燼-錄音室.mp3'), '餘燼@台下': ('ember-audience', '餘燼-台下.mp3'),
       '餘燼@大合唱': ('ember-chorus', '餘燼-大合唱.mp3'), '晚安，台南': ('goodnight-tainan', '晚安台南.mp3'),
       '餘燼@合聲': ('ember-harmony', '餘燼-合聲.mp3')}


def parse(path):
    out = []
    for l in path.read_text(encoding='utf-8').splitlines():
        m = re.match(r'^\[(\d+):(\d+\.\d+)\](.*)$', l)
        if m:
            out.append((int(m.group(1)) * 60 + float(m.group(2)), m.group(3).strip()))
    return out


def main():
    out = {}
    for name, (lrc, f) in MAP.items():
        mp3 = SONGS / f
        if not mp3.exists():
            print('沒有', f); continue
        rows = parse(ROOT / 'docs/music' / f'{lrc}.lrc')
        dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(mp3)], capture_output=True, text=True).stdout)
        out[name] = {'file': f, 'sha': hashlib.md5(mp3.read_bytes()).hexdigest()[:10], 'duration': round(dur, 2),
                     't0': [round(t, 2) for t, _ in rows], 'text': [x for _, x in rows]}
        print(f'{name}: {len(rows)} 句，{dur:.1f} 秒')
    (SONGS / 'times.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
