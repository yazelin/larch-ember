"""洋紅背景去背（自己算，不經 cutout 工具：那支會改尺寸，跟原圖對不上）。
透明度直接看原圖每個像素的洋紅程度 m = min(R,B) − G：純背景 m≈255 全透；頭髮縫隙裡混了橘的洋紅 m≈80 半透；頭髮、皮膚、紅禮服 m≤0 不透。
再把殘留的淡洋紅去色。python3 art/despill.py 原圖.png 輸出.webp"""
import sys, numpy as np
from PIL import Image


def key(raw, dst):
    a = np.asarray(Image.open(raw).convert('RGBA')).astype(np.int16)
    m = np.minimum(a[..., 0], a[..., 2]) - a[..., 1]
    a[..., 3] = (255 * np.clip(1 - (m - 20) / 50, 0, 1)).astype(np.int16)
    mask = m > 4
    a[..., 0][mask] -= m[mask]; a[..., 2][mask] -= m[mask]
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')
    im.crop(im.getbbox()).save(dst, quality=92)


if __name__ == '__main__':
    key(sys.argv[1], sys.argv[2])
