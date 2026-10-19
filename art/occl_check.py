"""遮擋驗證：沿路線每一格，照引擎規則（排序大於人所在列的圖片才蓋住人；等於的話人在上面）算人物被蓋住的比例。
人高 3.4 格、寬 1.1 格，站在 (x,y) 畫面佔 x-0.05..x+1.05、y-2.4..y+1。出圖前先過這關，不靠肉眼。
python3 art/occl_check.py backstage          → 印出每格狀態
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / 'src'))
import layout

HW, HH, N = 1.1, 3.4, 40


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
    return cov / total


def status(path, d, drop=()):
    obs = [o for o in layout.objects(d) if o['name'] not in drop]
    out = []
    for (x, y) in path:
        pieces = [o['frame'] for o in obs if o['sort'] > y]
        c = coverage(x, y, pieces)
        out.append(((x, y), c, '全藏' if c > .98 else ('全見' if c < .10 else '蓋一部分')))
    return out


PATHS = {'backstage': [(11, 6), (12, 6)] + [(12, y) for y in range(5, 0, -1)] + [(13, 1), (14, 1)] + [(15, y) for y in range(1, 12)]}
# 預期：A 段下半全見；第 2 列（含）以北全藏（轉折）；B 段第 2–4 列全藏；第 5 列起全見
EXPECT = {'backstage': {(12, 2): '全藏', (12, 1): '全藏', (13, 1): '全藏', (14, 1): '全藏', (15, 1): '全藏', (15, 2): '全藏', (15, 3): '全藏', (15, 4): '全藏',
                        (12, 6): '全見', (12, 5): '全見', (15, 5): '全見', (15, 6): '全見', (15, 8): '全見', (15, 11): '全見'}}

if __name__ == '__main__':
    a = sys.argv[1]; d = layout.load(a); bad = 0
    print('— 設計 —')
    for p, c, s in status(PATHS[a], d):
        want = EXPECT[a].get(p); ok = want is None or want == s; bad += not ok
        print(f'{p} {c:4.0%} {s}', '' if ok else f'  ✗ 預期 {want}')
    print('— 負控制：拿掉兩面遮擋牆，轉折與 B 上段不該被藏 —')
    neg = status(PATHS[a], d, drop=('轉折牆', 'B 上段牆'))
    hid = [p for p, c, s in neg if s == '全藏']
    print('仍然全藏的格：', hid, '（應為空）'); bad += bool(hid)
    print('不合格', bad)
