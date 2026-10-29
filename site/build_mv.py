# -*- coding: utf-8 -*-
"""產生 docs/mv.html（〈餘燼〉MV 頁，給遊戲結局用小遊戲卡全螢幕嵌入）與 docs/media/mv/*.webp。
python3 site/build_mv.py
分鏡表在 site/mv_storyboard.json：start 對齊 LRC 的第幾句（或秒數），這支程式把它換成秒，檢查順序與音檔長度。
mv.html 含結局劇透：不放進首頁導覽，原聲帶頁也不連過去，頁面加 noindex。
embed=1 時頁面上沒有任何連結（不掛推廣 footer），播完或按「繼續」送 {type:'larch:mv:done'} 給父層。"""
import html as H, json, os, re, subprocess, sys
from PIL import Image

G = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get('MEDIA_BASE', '')


def lrc_times(audio):
    out = []
    for raw in open(os.path.join(G, f'docs/music/{audio}.lrc'), encoding='utf-8'):
        m = re.match(r'^\[(\d+):(\d+\.\d+)\](.*)$', raw.strip())
        if m: out.append((int(m.group(1)) * 60 + float(m.group(2)), m.group(3)))
    return out


def duration(p):
    return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p]))


def resolve(key, sb):
    lines = lrc_times(sb['audio'])
    dur = duration(os.path.join(G, f"docs/music/{sb['audio']}.mp3"))
    shots = []
    for s in sb['shots']:
        st = s['start']
        t0 = float(st['t']) if 't' in st else lines[st['line'] - 1][0]
        shots.append(dict(t0=round(t0, 2), cg=s['cg'], move=s['move'], blank=bool(s.get('blank')), sec=s.get('sec', '')))
    for a, b in zip(shots, shots[1:]):
        assert b['t0'] > a['t0'], f'{key} 分鏡時間沒有往前：{a} {b}'
        a['t1'] = b['t0']
    shots[-1]['t1'] = round(dur, 2)
    assert shots[-1]['t0'] < dur, f'{key} 最後一鏡超過音檔長度'
    return dict(title=sb['title'], ending=sb['ending'], status=sb['status'], dur=round(dur, 2),
                audio=BASE + f"music/{sb['audio']}.mp3", lrc=BASE + f"music/{sb['audio']}.lrc", shots=shots), lines


def export(cg):
    out = os.path.join(G, f'docs/media/mv/{cg}.webp')
    if not os.path.exists(out):
        im = Image.open(os.path.join(G, f'assets/art/cg/s_{cg}.webp')).convert('RGB')
        im.thumbnail((1600, 1600), Image.LANCZOS)
        im.save(out, quality=80, method=6)
    return out


if __name__ == '__main__':
    SB = json.load(open(os.path.join(HERE, 'mv_storyboard.json'), encoding='utf-8'))
    data = {}
    for k, v in SB.items():
        if k.startswith('_'): continue
        r, lines = resolve(k, v)
        for s in r['shots']:
            export(s['cg']); s['img'] = BASE + f"media/mv/{s['cg']}.webp"
        data[k] = r
        print(k, v['status'], len(r['shots']), '鏡', '長', r['dur'])
    css = open(os.path.join(HERE, 'mv.css'), encoding='utf-8').read()
    js = open(os.path.join(HERE, 'mv.js'), encoding='utf-8').read()
    page = f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="color-scheme" content="dark">
<meta name="robots" content="noindex">
<title>餘燼 · 最終遺忘的橘色餘燼</title>
<meta name="theme-color" content="#0d0705">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@500;700&display=swap">
<style>{css}</style>
</head>
<body>
<div class="film" aria-hidden="true"><i id="fA"></i><i id="fB"></i></div>
<div class="shade" aria-hidden="true"></div>
<canvas id="fx" aria-hidden="true"></canvas>
<div class="lyric" aria-live="off"><p id="lA"></p><p id="lB"></p></div>
<div class="black" id="black" aria-hidden="true"></div>
<div class="start" id="start">
  <p class="t" id="stitle">餘燼</p>
  <button type="button" id="go" class="go" aria-label="播放"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5v14l11-7z"/></svg><span>播放</span></button>
  <p class="s" id="sub"></p>
</div>
<button type="button" id="next" class="next" hidden>繼續</button>
<button type="button" id="again" class="again" hidden>再看一次</button>
<p class="sign" id="sign">最終遺忘的橘色餘燼 · 林亞澤</p>
<script>
const MV = {json.dumps(data, ensure_ascii=False)};
{js}
</script>
</body>
</html>
"""
    open(os.path.join(G, 'docs/mv.html'), 'w', encoding='utf-8').write(page)
    print('docs/mv.html')
