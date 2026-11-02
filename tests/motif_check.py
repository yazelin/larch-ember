#!/usr/bin/env python3
"""物件檢查（作者 2026-11-02：平鋪直敘把故事講好，拿掉第二屆比賽版的收集物件與後來加的小儀式，見 審稿/準則.md 第 16 條）。
python3 tests/motif_check.py [劇本.md]   拿掉的物件又出現、或留下的物件出現在規定以外的場，就 exit 1。（唱）的歌詞不算。"""
import re, sys, pathlib
p = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parent.parent / 'canon/劇本.md'
BANNED = {'票根': r'票根|票角', '敲兩下': r'敲兩下|敲了兩下|敲兩聲', '玫瑰放門內': r'門內右邊|壓到線',
          '四折歌譜': r'四折|摺四|折四|摺成四|折成四', '定位手錶': r'手錶|GPS|錶帶', '耳墜': r'耳墜|耳環',
          '信': r'信紙|這封信|底座|底蓋', '修收音機': r'旋鈕'}
ONLY = {'玫瑰／花': (r'玫瑰|花梗|一朵', {'door2004', 'roses', 'monitor', 'confess'}),
        '半分鐘／保溫杯': (r'半分鐘|保溫杯|放涼', {'open', 'song2023'})}
text = p.read_text(encoding='utf-8').split('\n## 修改紀錄')[0]
scenes = [(m.group(1), m.group(2)) for m in re.finditer(r'^## ([A-Za-z0-9_]+)[^\n]*\n(.*?)(?=^## |\Z)', text, re.S | re.M)]
bad = 0
for name, body in scenes:
    for ln in body.split('\n'):
        if '（唱）' in ln: continue
        for k, pat in BANNED.items():
            if re.search(pat, ln): bad += 1; print(f'✗ {name}｜拿掉的「{k}」：{ln}')
        for k, (pat, ok) in ONLY.items():
            if re.search(pat, ln) and name not in ok: bad += 1; print(f'✗ {name}｜「{k}」只能在 {"、".join(sorted(ok))}：{ln}')
print(f'物件問題 {bad} 處'); sys.exit(1 if bad else 0)
