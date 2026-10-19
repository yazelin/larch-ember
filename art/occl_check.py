"""遮擋驗證（四張地圖通用）：照引擎規則（排序大於人所在列的圖片才蓋住人；等於的話人在上面）算每一格人物被蓋住的比例。
人高 3.4 格、寬 1.1 格，站在 (x,y) 畫面佔 x-0.05..x+1.05、y-2.4..y+1。出圖前先過這關，不靠肉眼。
檢查：
  1. 地圖上每個走得到的格子，人物不准「整個被藏起來」，除非設計檔 checks.hidden 明列（後台樓梯的轉折）。
  2. 設計檔 checks.path 列的路線：hidden 的格子必須 100% 被藏、visible 的格子必須看得見（被蓋住不到 10%）。
  3. 負控制：拿掉 checks.occluders 列的遮擋牆，原本被藏的格子必須都現身。沒有這項，檢查不算數。
  4. 全地圖「被蓋住超過 45% 但沒到全藏」的格子列出來（座椅靠背蓋腳是設計的，其餘要人工看）。
python3 art/occl_check.py backstage
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / 'src'))
import layout

HW, HH, N = 1.1, 3.4, 30


def coverage(x, y, pieces):
    x0, y0 = x + 0.5 - HW / 2, y + 1 - HH
    total = cov = 0
    for i in range(N):
        for j in range(N):
            px, py = x0 + (i + .5) * HW / N, y0 + (j + .5) * HH / N
            if py < 0: continue   # 在地圖北緣之外，畫面看不到
            total += 1
            if any(fx <= px < fx + fw and fy <= py < fy + fh for (fx, fy, fw, fh) in pieces):
                cov += 1
    return cov / total if total else 0


def cell_cov(cell, obs):
    x, y = cell
    return coverage(x, y, [o['vis'] for o in obs if o['sort'] > y])


def label(c): return '全藏' if c > .98 else ('全見' if c < .10 else '蓋一部分')


def main(a):
    d = layout.load(a); chk = d.get('checks', {}); bad = 0
    obs = layout.objects(d)
    wl = layout.walls(d); ok = layout.reachable(d, d['points']['hero_start'])
    hidden_ok = {tuple(c) for c in chk.get('hidden', [])}
    print(f'— {a}：走得到的 {len(ok)} 格 —')
    hid = [c for c in sorted(ok) if cell_cov(c, obs) > .98]
    extra = [c for c in hid if c not in hidden_ok]
    print('整個人被藏起來的格子：', hid)
    if extra: print('  ✗ 設計沒有要藏、卻被藏的格子：', extra); bad += 1
    miss = [c for c in hidden_ok if cell_cov(c, obs) <= .98]
    if miss: print('  ✗ 設計要藏、卻沒藏住的格子：', [(c, round(cell_cov(c, obs), 2)) for c in miss]); bad += 1
    part = [(c, round(cell_cov(c, obs), 2)) for c in sorted(ok) if .45 < cell_cov(c, obs) <= .98]
    print('被蓋住超過 45% 但沒全藏的格子：', part or '無')
    if chk.get('path'):
        print('— 路線 —')
        for c in chk['path']:
            c = tuple(c); v = cell_cov(c, obs); s = label(v)
            want = '全藏' if c in hidden_ok else '全見'
            flag = '' if s == want else f'  ✗ 預期 {want}'; bad += bool(flag)
            print(c, f'{v:4.0%}', s, flag)
    drop = set(chk.get('occluders', []))
    if drop:
        keep = [o for o in obs if o['name'] not in drop]
        neg = [c for c in sorted(ok) if cell_cov(c, keep) > .98]
        print('— 負控制：拿掉', sorted(drop), '—'); print('仍然全藏的格：', neg, '（應為空）'); bad += bool(neg)
    print('不合格', bad); return bad


if __name__ == '__main__':
    sys.exit(1 if main(sys.argv[1]) else 0)
