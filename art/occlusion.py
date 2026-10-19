"""擋圖：照引擎的前後規則（圖片排序＝sort、人＝自己站的列，同值先畫圖片），把行走小人擺在指定格子，看誰被誰擋。
物件畫成半透明色塊、標名字；占地有碰撞的加斜線，只擋視覺的（占地全空隙）用虛線框。
python3 art/occlusion.py <地圖> x,y x,y …  → art/check/occlusion-<地圖>.png
"""
import sys, os, pathlib
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / 'src'))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import layout, blocks
R = pathlib.Path(__file__).resolve().parent.parent
S = 64
a, pts = sys.argv[1], [tuple(map(int, p.split(','))) for p in sys.argv[2:]]
d = layout.load(a); W, H = d['map']['w'], d['map']['h']
im = Image.new('RGBA', (W * S, H * S), blocks.GROUND['wood'] + (255,))
dr = ImageDraw.Draw(im)
for g in d['ground']:
    for x, y, w, h in g['rects']:
        dr.rectangle((x * S, y * S, (x + w) * S - 1, (y + h) * S - 1), fill=blocks.GROUND[g['kind']])
for i in range(W): dr.line((i * S, 0, i * S, H * S), fill=(0, 0, 0, 40))
for j in range(H): dr.line((0, j * S, W * S, j * S), fill=(0, 0, 0, 40))
font = ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc', 18)
walk = Image.open(R / 'assets/art/walk/walk-yu-47.webp').convert('RGBA').crop((192, 0, 384, 256))
walk = walk.crop(walk.getbbox()); sw = int(S * 1.1); sh = int(walk.height * sw / walk.width); walk = walk.resize((sw, sh))
items = [(o['sort'], 0, 'obj', o) for o in layout.objects(d)] + [(y, 1, 'man', (x, y)) for x, y in pts]
for _, _, kind, v in sorted(items, key=lambda t: (t[0], t[1])):
    layer = Image.new('RGBA', im.size, (0, 0, 0, 0)); ld = ImageDraw.Draw(layer)
    if kind == 'obj':
        fx, fy, fw, fh = v['frame']; c = blocks.KIND.get(v['kind'], (140, 140, 140))
        visual_only = not layout.foot_cells(v)
        ld.rectangle((fx * S, fy * S, (fx + fw) * S - 1, (fy + fh) * S - 1), fill=c + (150 if visual_only else 215,),
                     outline=(255, 255, 255, 255) if visual_only else None, width=3)
        for (cx, cy) in layout.foot_cells(v):
            for k in range(0, S, 10): ld.line((cx * S + k, cy * S, cx * S, cy * S + k), fill=(0, 0, 0, 90))
        ld.text((fx * S + 4, fy * S + 2), v['name'] + ('（只擋視覺）' if visual_only else ''), fill=(255, 255, 255, 255), font=font, stroke_width=2, stroke_fill=(0, 0, 0, 255))
        im.alpha_composite(layer)
    else:
        x, y = v
        im.alpha_composite(walk, (x * S + (S - sw) // 2, (y + 1) * S - sh))
        ImageDraw.Draw(im).text((x * S + 2, (y + 1) * S - 18), f'({x},{y})', fill=(255, 255, 0, 255), font=font, stroke_width=2, stroke_fill=(0, 0, 0, 255))
out = R / f'art/check/occlusion-{a}.png'
im.convert('RGB').save(out); print(out)
