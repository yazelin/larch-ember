# -*- coding: utf-8 -*-
"""《餘燼》配樂第二版（作者 11-02）：只做 5 首，每首用 gemini-web 產的完整曲子（約 3 分鐘），不切循環，只做頭尾淡入淡出；
播放器播完自動重播。舊的 60 秒循環版留在 art/music.py。
  python3 art/bgm_full.py [名字…]   → 產生 → -16 LUFS、淡入 2 秒、淡出 5 秒 → assets/bgm/<名字>.mp3；有人聲就重產，最多 3 次"""
import os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import music as M

TAIL = 'instrumental only, no vocals, no singing, no choir, no humming, a complete piece of about three minutes with a gentle intro and a soft natural ending'
T = {   # 名字：(提示詞, 給代聽的場景)
 'home': ('Warm nostalgic Taiwanese old-song feeling, soft accordion and gentle piano, light plucked bass, a fishmonger father and his daughter at a dusk fish market by a canal in Tainan, tender and a little wistful, 84 BPM, major key',
          '台南黃昏市場的魚攤與運河：父親與女兒，溫暖懷舊帶一點思念'),
 'love': ('Tender romantic piano with light strings and a soft nylon guitar, a shy young singer and a quiet sound engineer slowly falling in love over years of concerts, warm, hopeful, intimate, 90 BPM',
          '2001 到 2013 年：女歌手與不太說話的音控師慢慢相戀，溫暖、青澀、甜'),
 'ill': ('Restrained minimal solo piano with long pauses and a faint cold pad, a woman learning she has early-onset Alzheimer\'s, quiet, tender, holding back tears, 58 BPM, minor',
         '2021 到 2024 年：忘詞、確診、叫不出丈夫的名字，克制、安靜、想哭沒哭'),
 'backstage': ('Slow breathing piano and soft sustained strings in an old theatre dressing room on a late afternoon, orange window light, tender and sad, a husband quietly looking after his wife who no longer recognises him, 60 BPM',
               '2026 年下午，老戲院化妝間：她認不出丈夫，他靜靜陪著，溫柔而悲傷'),
 'dusk': ('Sparse piano over a low soft drone, faint distant street sounds, nightfall, a woman with dementia wandering out to find her late father, then found by her husband on dark canal steps, uneasy at first then gently relieved, 54 BPM',
          '天黑：她走失去找過世的父親，丈夫在運河石階找到她，先是不安，最後輕輕放下'),
}


def finish(name):
    src = os.path.join(M.RAW, f'{name}.mp3'); out = os.path.join(M.OUT, f'{name}.mp3')
    dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', src], capture_output=True, text=True).stdout)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-af',
                    f'loudnorm=I=-16:TP=-1.5:LRA=11,afade=t=in:d=2,afade=t=out:st={dur - 5:.2f}:d=5', '-b:a', '160k', out], check=True)
    return dur


def main(names):
    bk, ak = M.bashrc_key(), M.audit_key()
    for n in names:
        M.PROMPT[n] = f'{T[n][0]}, {TAIL}'
        for k in range(3):
            if not M.gen(n, bk):
                continue
            a = M.listen(os.path.join(M.RAW, f'{n}.mp3'), T[n][1], ak) or {}
            if a.get('has_vocals'):
                print(f'{n} 第{k + 1}次有人聲，重產', flush=True); continue
            d = finish(n)
            print(f"{n} 完成 {d:.0f} 秒 適配 {a.get('fits_scene')} {a.get('mood')}", flush=True); break


if __name__ == '__main__':
    main(sys.argv[1:] or list(T))
