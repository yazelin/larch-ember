# -*- coding: utf-8 -*-
"""原聲帶頁用的素材：六首歌重新編成 128kbps MP3、六張專輯封面縮 600px、背景 CG 轉 webp。
來源音檔在 ~/下載/有封面/（已內嵌封面，原檔不動），輸出 docs/music/、docs/media/。python3 site/music_assets.py"""
import os, subprocess
from PIL import Image
G = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.expanduser('~/下載/有封面')
AUDIO = {  # 輸出名: 原檔名
    'ember-studio.mp3': '餘燼-錄音室版.mp3',
    'ember-audience.mp3': '餘燼-台下跟唱版(收音較差).mp3',
    'ember-harmony.mp3': '餘燼-合聲版.mp3',
    'ember-chorus.mp3': '餘燼-演唱會大合唱(余靜有完全停下來台下收音很好).mp3',
    'goodnight-tainan.mp3': '晚安，台南.mp3',
    'harbor-lights.mp3': '港邊的燈.mp3',
}
COVERS = ['studio', 'audience', 'harmony', 'chorus', 'night', 'harbor']
BG = {  # 輸出名: 來源（沒有結局與關係揭曉的畫面）
    'bg-soundcheck-1.webp': 'assets/art/cg/s_soundcheck_1.webp', 'bg-soundcheck-2.webp': 'assets/art/cg/s_soundcheck_2.webp',
    'bg-prologue-1.webp': 'assets/art/cg/s_prologue_1.webp', 'bg-prologue-3.webp': 'assets/art/cg/s_prologue_3.webp',
    'bg-soundcheck-4.webp': 'assets/art/cg/s_soundcheck_4.webp',
    'bg-concert-2.webp': 'assets/art/cg/s_concert_2.webp', 'bg-concert-3.webp': 'assets/art/cg/s_concert_3.webp',
    'bg-dress-1.webp': 'assets/art/cg/s_dress_1.webp', 'bg-canal-1.webp': 'art/raw/cg/cg_1988_canal_1.png', 'bg-canal-2.webp': 'art/raw/cg/cg_1988_canal_2.png',
}
if __name__ == '__main__':
    os.makedirs(os.path.join(G, 'docs/music'), exist_ok=True); os.makedirs(os.path.join(G, 'docs/media'), exist_ok=True)
    for out, f in AUDIO.items():
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', os.path.join(SRC, f), '-vn', '-map_metadata', '-1', '-c:a', 'libmp3lame', '-b:a', '128k', os.path.join(G, 'docs/music', out)], check=True)
    for k in COVERS:
        im = Image.open(os.path.join(G, f'art/raw/songcovers/{k}.jpg')).convert('RGB'); im.thumbnail((600, 600), Image.LANCZOS)
        im.save(os.path.join(G, f'docs/media/cover-{k}.webp'), quality=85, method=6)
    for out, src in BG.items():
        im = Image.open(os.path.join(G, src)).convert('RGB'); im.thumbnail((1920, 1920), Image.LANCZOS)
        q = 82
        while True:
            im.save(os.path.join(G, 'docs/media', out), quality=q, method=6)
            if os.path.getsize(os.path.join(G, 'docs/media', out)) < 350_000 or q <= 60: break
            q -= 6
    a = sum(os.path.getsize(os.path.join(G, 'docs/music', f)) for f in os.listdir(os.path.join(G, 'docs/music')))
    print('音檔', round(a / 1e6, 1), 'MB')
    for out in BG: print(out, os.path.getsize(os.path.join(G, 'docs/media', out)) // 1000, 'KB')
