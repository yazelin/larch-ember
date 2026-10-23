#!/usr/bin/env python3
"""伏筆帳（評分六，作者 2026-10-23）：扣回物件在 A／B／C 三條路線上，每個「回收」之前都要有出處。
python3 tests/motif_check.py [劇本.md]   預設 canon/劇本.md；有回收沒有出處就 exit 1。
路線＝劇本順序的共同場景（結局與程希視角以外）＋該結局的 ending_<x>* 場景。地圖調查點的實際觸發順序由玩家決定，這裡用劇本順序近似；
所以「出處」只認共同場景與回憶，回收認結局場景。"""
import re, sys, pathlib
p = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parent.parent / 'canon/劇本.md'
MOTIFS = {   # 名稱：比對樣式
    '票根背面的字': r'河岸留言那晚',
    '三排十四號': r'三排十四號|第三排左邊第十四',
    '半分鐘的水': r'半分鐘',
    '敲兩下': r'敲兩下|敲了兩下|敲兩聲',
    '玫瑰放門內右邊': r'門內右邊',
    '四折歌譜': r'四折|摺四|折四|四道折痕|摺成四|對摺兩次',
    '手錶型 GPS': r'手錶|定位手錶|GPS',
    '「唱完再戴回去」': r'唱完再戴|唱完戴回',
    '天烏烏': r'天烏烏|天黑黑',
    '走音／那我唱你跳': r'走音|我唱，你跳',
    '紙條「今天有人坐在三排十四號」': r'今天有人坐在三排十四號',
}
text = p.read_text(encoding='utf-8').split('\n## 修改紀錄')[0]
scenes = [(m.group(1), m.group(2)) for m in re.finditer(r'^## ([A-Za-z0-9_]+)[^\n]*\n(.*?)(?=^## |\Z)', text, re.S | re.M)]
common = [c for c, _ in scenes if not c.startswith(('ending_', 'cheng_pov'))]
routes = {x: common + [c for c, _ in scenes if c.startswith(f'ending_{x}')] for x in 'abc'}
body = dict(scenes)
bad = 0
for name, pat in MOTIFS.items():
    where = [c for c, b in scenes if re.search(pat, b)]
    first = where[0] if where else '（沒有出現）'
    print(f'■ {name}：第一次 {first}；出現在 {len(where)} 場')
    for x, order in routes.items():
        pay = [c for c in order if c.startswith('ending_') and re.search(pat, body[c])]
        setup = [c for c in order if not c.startswith('ending_') and re.search(pat, body[c])]
        if pay and not setup:
            bad += 1; print(f'    ✗ 結局 {x.upper()} 回收在 {"、".join(pay)}，之前沒有出處')
        elif pay:
            print(f'    結局 {x.upper()}：出處 {setup[0]}（共 {len(setup)} 場）→ 回收 {"、".join(pay)}')
        elif setup:
            print(f'    結局 {x.upper()}：只有鋪陳、這條路線沒有回收')
    if where and all(not c.startswith('ending_') for c in where) and len(where) == 1:
        print('    提醒：只出現一次，沒有回收')
print(f'回收沒有出處 {bad} 處'); sys.exit(1 if bad else 0)
