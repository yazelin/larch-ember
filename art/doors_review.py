"""六扇門的前後對照：左舊右新，各一格「門＋門前一格」。舊圖從 git 歷史取（OLD 目錄），新圖從 art/check/maps-review/*-composed.jpg。
python3 art/doors_review.py <舊合成圖目錄>   → art/check/maps-review/doors-before-after.jpg"""
import sys
from PIL import Image, ImageDraw, ImageFont
G = '/home/ct/larch-ember/art/check/maps-review/'
OLD = sys.argv[1]
FONT = ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 18)
# (地圖, 地圖寬格, 名稱, 舊框(格), 新框(格))；框 = (x0, y0, x1, y1)
DOORS = [
    ('dressing', 18, '化妝間門', (13.5, 0, 17.5, 4.5), (13.5, 0, 17.5, 4.5)),
    ('backstage', 24, '後台通化妝間的門', (2, 0, 6, 4.5), (2, 0, 6, 4.5)),
    ('backstage', 24, '側台門（通觀眾席）', (-0.5, 10, 2.5, 14), (1.5, 6.6, 6.5, 12.7)),
    ('backstage', 24, '後門（通巷子）', (21.5, 11, 24, 14.5), (9, 6.6, 14, 12.7)),
    ('auditorium', 26, '舞台的門（通後台）', (-0.5, 3, 3.5, 7), (1.5, 0, 6.5, 4.5)),
    ('alley', 18, '巷子後門', (2, 0, 6, 4.5), (2, 0, 6, 4.5)),
]
T = 300
rows = []
for m, W, name, ob, nb in DOORS:
    po, pn = Image.open(f'{OLD}/{m}-composed.jpg').convert('RGB'), Image.open(f'{G}{m}-composed.jpg').convert('RGB')
    so, sn = po.width / W, pn.width / W
    a = po.crop(tuple(int(v * so) for v in ob)); b = pn.crop(tuple(int(v * sn) for v in nb))
    a.thumbnail((T, T)); b.thumbnail((T, T))
    row = Image.new('RGB', (2 * T + 30, T + 28), (30, 30, 30)); row.paste(a, (0, 28)); row.paste(b, (T + 30, 28))
    d = ImageDraw.Draw(row); d.text((6, 4), f'{name}　左：舊　右：新', fill=(255, 235, 150), font=FONT); rows.append(row)
cols = 2; out = Image.new('RGB', (cols * (2 * T + 30), ((len(rows) + 1) // 2) * (T + 28)), (30, 30, 30))
for i, r in enumerate(rows): out.paste(r, ((i % cols) * (2 * T + 30), (i // cols) * (T + 28)))
out.save(G + 'doors-before-after.jpg', quality=88); print(out.size)
