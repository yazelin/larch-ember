# -*- coding: utf-8 -*-
"""單色塊驗證（遵循《正式地圖開工前：先用色塊確認 RPG 的遮擋層次》與《十一分鐘》規範）。
讀 art/objects_<a>.yaml，產：
  assets/maps/<a>_blocks.webp       純色地面（每種地面一個顏色、淡格線）
  assets/blocks/<a>/<名>.webp       每個物件一張：佔地部分深色、往上長的部分淺色半透明、標名字
  art/check/blocks-<a>-plan.webp    整張設計圖：格線、佔地（實線）、視覺圖框（虛線）、排序列（紅線）、互動點（黃點）
用法：python3 art/blocks.py [bar|storage|bedroom]
"""
import os, sys
from PIL import Image, ImageDraw, ImageFont

H = os.path.dirname(os.path.abspath(__file__)); G = os.path.dirname(H)
sys.path.insert(0, os.path.join(G, 'src'))
import layout

PX = 48   # 1 細格 = 48 px（與遊戲引擎標準一致）
FONT = lambda s: ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', s)

GROUND = {
    'border': (40, 40, 40),
    'wood': (130, 95, 65),
    'carpet': (140, 45, 50),
    'tile': (140, 135, 125),
    'rug': (195, 160, 150),
    'asphalt': (55, 60, 70),
    'sidewalk': (120, 125, 130),
    'concrete': (150, 150, 145),
    'stairs': (185, 160, 110),
}

KIND = {
    '門': (120, 160, 120),
    '吧檯': (160, 90, 50),
    '櫃': (110, 100, 130),
    '桌': (140, 105, 75),
    '椅': (90, 60, 60),
    '床': (170, 110, 120),
    '雜物': (210, 160, 80),
    '隔間牆': (170, 170, 175),
}


def ground(d, a):
    W, Hh = d['map']['w'], d['map']['h']
    im = Image.new('RGB', (W * PX, Hh * PX), GROUND['wood'])
    dr = ImageDraw.Draw(im)
    for g in d['ground']:
        for x, y, w, h in g['rects']:
            dr.rectangle((x * PX, y * PX, (x + w) * PX - 1, (y + h) * PX - 1), fill=GROUND[g['kind']])
    for x in range(W):
        dr.line((x * PX, 0, x * PX, Hh * PX), fill=(100, 100, 100), width=1)   # 淡格線
    for y in range(Hh):
        dr.line((0, y * PX, W * PX, y * PX), fill=(100, 100, 100), width=1)
    os.makedirs(os.path.join(G, 'art/check/blocks'), exist_ok=True)
    out = os.path.join(G, f'art/check/blocks/{a}_ground.webp')
    im.save(out, 'WEBP')
    return out


def block(o):
    fx, fy, fw, fh = o['frame']; x, y, w, h = o['foot']
    c = KIND.get(o['kind'], (150, 150, 150))
    im = Image.new('RGBA', (fw * PX, fh * PX), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    # 往上長的部分（不佔空間）：淺色半透明，加白色斜線（表示人走入會被遮擋）
    light = tuple(min(255, int(v * 1.35 + 40)) for v in c) + (220,)
    if y > fy:
        dr.rectangle((0, 0, fw * PX - 1, (y - fy) * PX - 1), fill=light)
    if o.get('side'):
        dr.rectangle((0, 0, fw * PX - 1, fh * PX - 1), fill=light)
    for k in range(-fh * PX, fw * PX, 12):
        dr.line((k, 0, k + fh * PX, fh * PX), fill=(255, 255, 255, 60), width=2)
    # 佔地：深色不透明（門洞 gap 挖空）
    for (i, j) in layout.foot_cells(o):
        dr.rectangle(((i - fx) * PX, (j - fy) * PX, (i - fx + 1) * PX - 1, (j - fy + 1) * PX - 1),
                     fill=tuple(int(v * 0.6) for v in c) + (235,))
    dr.rectangle((0, 0, fw * PX - 1, fh * PX - 1), outline=(255, 255, 255, 255), width=2)
    f = FONT(max(10, min(18, int(PX * 0.35))))
    dr.text((4, 3), o['name'], fill=(255, 255, 255, 255), font=f, stroke_width=2, stroke_fill=(0, 0, 0, 255))
    return im


def plan(d, a):
    W, Hh = d['map']['w'], d['map']['h']; S = 48
    bg_file = os.path.join(G, f'art/check/blocks/{a}_ground.webp')
    im = Image.open(bg_file).convert('RGBA').resize((W * S, Hh * S), Image.NEAREST)
    lay = Image.new('RGBA', im.size, (0, 0, 0, 0)); dr = ImageDraw.Draw(lay); f = FONT(12)
    for o in layout.objects(d):
        fx, fy, fw, fh = o['frame']
        # 圖框虛線
        dr.rectangle((fx * S, fy * S, (fx + fw) * S - 1, (fy + fh) * S - 1), outline=(255, 255, 255, 200), width=1)
        # 佔地格
        for (i, j) in layout.foot_cells(o):
            c = KIND.get(o['kind'], (150, 150, 150))
            dr.rectangle((i * S + 1, j * S + 1, (i + 1) * S - 2, (j + 1) * S - 2), fill=c + (190,))
        # 排序列（紅色實線）
        dr.line((fx * S, (o['sort'] + 1) * S - 1, (fx + fw) * S, (o['sort'] + 1) * S - 1), fill=(255, 60, 60, 255), width=2)
        dr.text((fx * S + 2, fy * S + 2), o['name'], fill=(255, 255, 255, 255), font=f, stroke_width=2, stroke_fill=(0, 0, 0, 255))
    # 互動點與角色起點（黃色圓點）
    for k, (x, y) in d.get('points', {}).items():
        dr.ellipse((x * S + 10, y * S + 10, x * S + S - 10, y * S + S - 10), fill=(255, 220, 0, 255))
        dr.text((x * S + S - 4, y * S + 4), k, fill=(255, 240, 120, 255), font=f, stroke_width=2, stroke_fill=(0, 0, 0, 255))
    for x in range(0, W, 2):
        dr.text((x * S + 2, 2), str(x), fill=(255, 255, 255, 255), font=f, stroke_width=2, stroke_fill=(0, 0, 0, 255))
    for y in range(0, Hh, 2):
        dr.text((2, y * S + 2), str(y), fill=(255, 255, 255, 255), font=f, stroke_width=2, stroke_fill=(0, 0, 0, 255))
    im.alpha_composite(lay)
    os.makedirs(os.path.join(G, 'art/check'), exist_ok=True)
    out = os.path.join(G, f'art/check/blocks-{a}-plan.webp')
    im.convert('RGB').save(out, 'WEBP')
    return out


def main(a):
    d = layout.load(a); errs = layout.check(d)
    if errs: raise SystemExit(f'設計檔 {a} 有問題：\n' + '\n'.join(errs))
    ground(d, a)
    obs = layout.objects(d)   # 2026-10-20：色塊只放 art/check，不再寫進 assets（不要出貨）
    p = plan(d, a)
    print(f'Done {a}: plan saved to {p}, generated {len(obs)} objects')


if __name__ == '__main__':
    arg = sys.argv[1] if len(sys.argv) > 1 else 'bar'
    main(arg)
