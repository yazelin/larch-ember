"""行走圖（餘燼）。原為《雨幕》三人行走圖（二十一歲便服、十七歲高中制服）。照 ~/larch-sunset/art/make_walk_memory.py 的流程：
拿晚霞的沈淮行走圖當 3×4 格子與比例參考（art/ref_walk_grid.webp）＋各自的定錨立繪 → 洋紅幕生圖 → cutout key → 照格子切 12 格
→ 每格照參考圖的人物高度、腳底對齊 → 朝左那排用朝右鏡射。
python3 art/gen_walkers.py gen [名…] / build [名…]   → assets/art/walk/walk-<名>.webp（576×1024）
"""
import sys, pathlib, subprocess, concurrent.futures as cf
import numpy as np
from PIL import Image
from scipy import ndimage
sys.path.insert(0, str(pathlib.Path(__file__).parent))
R = pathlib.Path(__file__).resolve().parent.parent
RAW = R / 'art/raw/walk'
CUT = pathlib.Path.home() / '.claude/skills/cutout/cutout.py'
GRID = R / 'art/ref_walk_grid.webp'
ROW_H = [239, 229, 229, 224]
FOOT = 251
MAG = ('Solid flat pure magenta #FF00FF background, even lighting, crisp edges, no shadow, no ground, no gradient, nothing touches the image border. No text.')
OUTFIT = {   # 餘燼：參考圖用挑定的半身立繪（assets/art/p_*.webp）
    'yu_47': ('p_yu_47', 'YU JING, 47: shoulder-length wavy light-brown bob with a few silver strands, long drop earrings; an off-shoulder black lace evening gown to the floor.'),
    'cheng_45': ('p_cheng_45', 'CHENG XI, 45: short black hair with grey temples; dark navy shirt with sleeves rolled, black trousers, black wristwatch, black shoes.'),
    'zhou': ('p_zhou_62', 'TEACHER ZHOU, 62: neat white hair, thin gold-rimmed glasses; grey cardigan over a white shirt, dark trousers.'),
    'tao_73': ('p_tao_73', 'AH-TAO, 73: short grey permed curls; a floral blouse, a dark apron skirt, jade bracelet, carrying a small plastic bag.'),
    'azhe': ('p_azhe_30', 'A-ZHE, 30: side-swept black hair; black crew T-shirt, black cargo pants, a walkie-talkie on the belt and a headset around the neck.'),
}


def gen(name):
    import codex11
    p = ('Reference 1 is a walking sprite sheet: 3 columns x 4 rows (rows top to bottom: facing down, facing left, facing right, facing up; '
         'columns: left foot forward, standing, right foot forward). Draw a NEW sprite sheet with exactly the same 3x4 grid, the same chibi proportions, '
         'the same poses and the same soft anime style, but a different character. Reference 2 is the character\'s full portrait: copy the face, hair and outfit exactly. '
         f'Character: {OUTFIT[name][1]} Twelve separate full-body figures, evenly spaced, none touching. ' + MAG)
    return codex11.gen(p, str(RAW / f'{name}_raw.png'), refs=[str(GRID), str(R / f'assets/art/{OUTFIT[name][0]}.webp')], size='1024x1536')


def premul_resize(im, size):
    a = np.asarray(im, np.float32); al = a[..., 3:4] / 255.0
    pre = np.concatenate([a[..., :3] * al, a[..., 3:4]], -1)
    r = np.asarray(Image.fromarray(pre.round().astype(np.uint8), 'RGBA').resize(size, Image.LANCZOS), np.float32)
    al2 = np.clip(r[..., 3:4] / 255.0, 1e-4, 1.0)
    return Image.fromarray(np.concatenate([np.clip(r[..., :3] / al2, 0, 255), r[..., 3:4]], -1).round().astype(np.uint8), 'RGBA')


def build(name):
    subprocess.run([sys.executable, str(CUT), 'key', str(RAW / f'{name}_raw.png'), '-o', str(RAW / f'{name}_cut.png'), '--key', 'magenta'], check=True, capture_output=True)
    im = Image.open(RAW / f'{name}_cut.png').convert('RGBA')
    cw, ch = im.width / 3, im.height / 4
    sheet = Image.new('RGBA', (576, 1024), (0, 0, 0, 0))
    figs = {}
    for r in range(4):
        for c in range(3):
            fig = im.crop((round(c * cw), round(r * ch), round((c + 1) * cw), round((r + 1) * ch)))
            fa = np.asarray(fig).copy(); lab, n = ndimage.label(fa[..., 3] > 40)
            if n > 1:
                keep = 1 + int(np.argmax(ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))))
                fa[(lab != keep) & (lab > 0), 3] = 0
                fig = Image.fromarray(fa, 'RGBA')
            fig = fig.crop(fig.getbbox())
            h = ROW_H[r]; w = max(1, round(fig.width * h / fig.height))
            figs[(r, c)] = premul_resize(fig, (w, h))
    for c in range(3):   # 朝左＝朝右鏡射（記憶 reference_xu_sprite_pipeline_threeview）
        figs[(1, c)] = figs[(2, c)].transpose(Image.FLIP_LEFT_RIGHT)
    for (r, c), f in figs.items():
        sheet.alpha_composite(f, (c * 192 + (192 - f.width) // 2, r * 256 + FOOT - f.height))
    sheet.save(R / f'assets/art/walk/walk-{name.replace("_", "-")}.webp', 'WEBP', quality=92)
    print(name, 'ok')


if __name__ == '__main__':
    cmd, names = sys.argv[1], sys.argv[2:] or list(OUTFIT)
    if cmd == 'gen':
        with cf.ThreadPoolExecutor(3) as ex:
            for f in ex.map(gen, names): print(f)
    else:
        for n in names: build(n)
