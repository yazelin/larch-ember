# -*- coding: utf-8 -*-
"""公開站用的素材：從 assets/、art/ 縮成小檔放進 docs/media/。長邊 1600 以內、webp 品質 85，檔名一律 ASCII。
python3 site/media.py"""
import os
from PIL import Image
G = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = os.path.join(G, 'docs/media')
IMG = {   # 輸出名: (來源, 最長邊)
    'cover.webp': ('art/original/cover.png', 1600),
    'og.jpg': ('art/original/cover.png', 1200),
    'maps.webp': ('art/check/maps-all.jpg', 1600),
    # 人物立繪
    'p-yu-47.webp': ('assets/art/p_yu_47.webp', 900), 'p-yu-33.webp': ('assets/art/p_yu_33.webp', 900), 'p-yu-25.webp': ('assets/art/p_yu_25.webp', 900),
    'p-cheng-45.webp': ('assets/art/p_cheng_45.webp', 900), 'p-cheng-23.webp': ('assets/art/p_cheng_23.webp', 900),
    'p-zhou.webp': ('assets/art/p_zhou_62.webp', 900), 'p-azhe.webp': ('assets/art/p_azhe_30.webp', 900), 'p-tao.webp': ('assets/art/p_tao_73.webp', 900),
}
CG = ['prologue_1', 'prologue_3', 'soundcheck_2', 'dress_2', 'mem1_2', 'mem2_2', 'mem2_10', 'mem3_1', 'mem4_1',   # 沒有結局劇透
      'a_6', 'b_3', 'c_9']                                                                                       # 結局後的畫面（站上折疊）
for k in CG:
    IMG[f'cg-{k.replace("_", "-")}.webp'] = (f'assets/art/cg/s_{k}.webp', 1280)

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for name, (src, edge) in IMG.items():
        im = Image.open(os.path.join(G, src))
        im = im.convert('RGBA' if im.mode in ('RGBA', 'LA', 'P') and name.endswith('.webp') else 'RGB')
        im.thumbnail((edge, edge), Image.LANCZOS)
        p = os.path.join(OUT, name)
        im.save(p, quality=85, method=6) if name.endswith('.webp') else im.convert('RGB').save(p, quality=86)
    tot = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT))
    print(len(os.listdir(OUT)), '個檔', round(tot / 1e6, 1), 'MB', 'max', max(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT)) // 1000, 'KB')
