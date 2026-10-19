"""分層地圖與獨立物件正式美術生成（遵循《正式地圖開工前：先用色塊確認 RPG 的遮擋層次》與《十一分鐘》規範）。
- 純地面底圖：無烘焙家具、無牆面、無人。
- 獨立透明物件：純色幕（綠幕/洋紅幕）生成，使用 cutout skill（~/.claude/skills/cutout/cutout.py）去背。
- 嚴格遵守：所有圖檔一律以 .webp 格式儲存！
用法：
  python3 art/objects_gen.py ground [bar|storage|bedroom]
  python3 art/objects_gen.py gen [bar|storage|bedroom]
  python3 art/objects_gen.py cut [bar|storage|bedroom]
  python3 art/objects_gen.py props
  python3 art/objects_gen.py all
"""
import glob, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageDraw

H = os.path.dirname(os.path.abspath(__file__))
G = os.path.dirname(H)
sys.path.insert(0, os.path.join(G, 'src'))
sys.path.insert(0, H)
import layout, blocks, codex11

PX = 48
OUT_PX = 128   # 輸出解析度：每格 128 像素。遊戲照格數決定圖畫多大，圖本身解析度高只會更清楚（2026-10-18 作者：物件解析度很差）
CUTOUT = os.path.expanduser('~/.claude/skills/cutout/cutout.py')
RAW = os.path.join(H, 'raw')

LOOK = {
    'dressing': 'the second-floor dressing room of an old 1950s Tainan theater at sunset, warm golden-orange light, dark wood, faded red velvet, soft painted anime RPG map style matching a cinematic warm palette',
    'backstage': 'the backstage corridor of an old 1950s Tainan theater, warm tungsten bulbs, old wooden floor, worn plaster walls, soft painted anime RPG map style, warm palette',
    'auditorium': 'the auditorium of an old 1950s Tainan theater after soundcheck, rows of red velvet seats, a wooden stage with warm stage lights, soft painted anime RPG map style, warm palette',
    'alley': 'a narrow old Tainan back alley at dusk behind a theater, wet asphalt reflecting the orange lights of an evening market at the far end, soft painted anime RPG map style, warm palette',
}

FLOOR = {
    'dressing': 'old warm-brown wooden floorboards with a faded burgundy rug in the middle; dark plaster walls along the top edge and sides; a doorway gap in the bottom wall. Top-down RPG map floor only.',
    'backstage': 'a long old wooden corridor floor with scuffs and tape marks; plaster walls along the top and bottom; a stair opening on the left edge and a back door on the right. Top-down RPG map floor only.',
    'auditorium': 'a wooden stage across the top, below it a deep red carpeted auditorium floor with aisles on both sides; dark side walls. Top-down RPG map floor only.',
    'alley': 'a narrow wet asphalt alley with puddles and a thin film of water reflecting orange market lights from the right edge; old brick building walls along the top and bottom. Top-down RPG map floor only.',
}

# (fw, fh, foot_depth, prompt_desc, fill_width, plate_color)
TYPES = {
    'd_window': (5, 2, 1, 'a large old wooden-framed west window seen from inside, showing an orange sunset over old Tainan tiled rooftops, red velvet curtains tied at the sides', True, 'magenta'),
    'd_vanity': (4, 3, 1, 'an old theater dressing table with a mirror framed by round light bulbs, a small photo tucked in the mirror corner, an open notebook and a black wristwatch on the table', True, 'green'),
    'd_jewel': (1, 2, 1, 'a small round side table with a carved wooden jewelry box on it', True, 'green'),
    'd_radio': (2, 2, 1, 'a small side table with an old cream plastic portable transistor radio, its corners worn white', True, 'green'),
    'd_case': (2, 2, 1, 'an open black makeup case on the floor, trays of brushes and lipsticks, a small glass box in the bottom tray', True, 'green'),
    'd_rack': (1, 4, 3, 'an empty metal clothes rack seen from the side, one navy jacket hanging on it', True, 'green'),
    'd_chair': (1, 2, 1, 'an old wooden chair with a faded velvet seat', True, 'green'),
    'b_door': (2, 2, 1, 'an old wooden dressing room door with a small brass name plate (no readable text)', True, 'magenta'),
    'b_piano': (3, 2, 1, 'an old black upright piano against a wall, a lamp on top', True, 'magenta'),
    'b_cases': (2, 2, 1, 'two stacked black flight cases for stage equipment', True, 'magenta'),
    'a_block6': (6, 10, 10, 'a block of old ornate red velvet theater seats seen from above, 5 rows of 6 seats with empty walking rows between them, gold-trimmed armrests', True, 'green'),
    'a_block8': (8, 10, 10, 'a block of old ornate red velvet theater seats seen from above, 5 rows of 8 seats with empty walking rows between them, gold-trimmed armrests', True, 'green'),
    'a_piano': (3, 2, 1, 'a black grand piano on a wooden stage, lid closed', True, 'magenta'),
    'a_desk': (4, 2, 1, 'a sound mixing desk with many faders and small glowing lights on a wooden platform', True, 'magenta'),
    'l_door': (2, 2, 1, 'an old theater back door in a brick wall, a rolled-up metal shutter, warm light from inside', True, 'magenta'),
    'l_scooter': (2, 2, 1, 'two parked Taiwanese scooters side by side', True, 'magenta'),
    'l_basket': (1, 2, 1, 'a red plastic vegetable basket on an upturned crate', True, 'green'),
}

OBJ_TYPE_MAP = {
    '朝西的窗': 'd_window', '化妝台': 'd_vanity', '首飾盒小桌': 'd_jewel', '收音機桌': 'd_radio', '化妝箱': 'd_case', '衣架': 'd_rack', '椅子': 'd_chair',
    '化妝間門': 'b_door', '直立鋼琴': 'b_piano', '器材箱': 'b_cases',
    '左區': 'a_block6', '中區': 'a_block8', '右區': 'a_block6', '鋼琴': 'a_piano', '音控台': 'a_desk',
    '後門': 'l_door', '機車': 'l_scooter', '菜籃': 'l_basket',
}

FALLBACK_RAW = {}

# 作者 2026-10-19：地圖要跟 CG 是同一個地方、大小也要對得起來 → 地面與物件都拿選定的 CG 當參考
SCENE_REF = {
    'dressing': ['assets/art/cg/s_dress_1.webp', 'assets/art/cg/s_branch_1.webp'],
    'backstage': ['assets/art/cg/s_prologue_4.webp', 'assets/art/cg/s_c_1.webp'],
    'auditorium': ['assets/art/cg/s_soundcheck_1.webp', 'assets/art/cg/s_concert_1.webp'],
    'alley': ['assets/art/cg/s_c_1.webp', 'assets/art/cg/s_c_4.webp'],
}
SCENE_NOTE = ' The extra reference images are cinematic stills of this SAME place: match its architecture, materials, colors, furniture design and warm lighting exactly, only seen from the top-down RPG map angle.'


def get_type(o, a):
    n = o['name']
    t = OBJ_TYPE_MAP.get(n)
    if callable(t):
        return t(a)
    return t


def raw_path(t):
    base = os.path.join(RAW, f'{t}_raw.png')
    if not os.path.exists(base) and t in FALLBACK_RAW:
        fallback = os.path.join(RAW, f'{FALLBACK_RAW[t]}_raw.png')
        if os.path.exists(fallback):
            return fallback
    return base


def prompt_for(t, a):
    fw, fh, dd, desc, fill_w, plate = TYPES[t]
    bg_desc = '#00FF00 pure green' if plate == 'green' else '#FF00FF pure magenta'
    p = (
        f"Game map object sprite, one single object only, {LOOK[a]}. "
        f"3/4 top-down camera view from the south (about 50 degrees elevation, showing top and south-facing front), soft even lighting. "
        f"Redraw the object cleanly and completely as a standalone sprite.\n"
        f"Draw: {desc}.\n"
        f"Proportions: bounding box is {fw} grid cells wide and {fh} grid cells tall (aspect ratio {fw}:{fh}). "
        f"The bottom {dd} cells are its floor footprint; the top {fh - dd} cells rise up.\n"
        f"Draw only this object: no floor, no shadows on floor, no people, no background scenery. Clean edges.\n"
        f"Background: a completely flat opaque solid {bg_desc} fill, uniform color, absolutely no gradient, no drop shadow. No text, no letters."
    )
    return p


def gen_ground(a):
    d = layout.load(a)
    W, Hh = d['map']['w'], d['map']['h']
    os.makedirs(os.path.join(G, 'assets/maps'), exist_ok=True)
    os.makedirs(RAW, exist_ok=True)
    
    # 產構圖
    # 地面只照地面區塊畫：物件的色塊不能進構圖，不然地面會把物件位置畫成亮塊（雨幕 2026-10-18）
    compose_path = os.path.join(G, f'art/check/compose-{a}-ground.webp')
    if not os.path.exists(compose_path):
        subprocess.run([sys.executable, os.path.join(H, 'compose.py'), a], check=True, env=dict(os.environ, NOOBJ='1'))
        os.replace(os.path.join(G, f'art/check/compose-{a}.webp'), compose_path)
    
    out_raw = os.path.join(RAW, f'ground_{a}_raw.png')
    prompt = (
        f"Top-down painted anime RPG game map floor, {LOOK[a]}. Follow the floor region layout of image 1 exactly. "
        f"{FLOOR[a]} "
        f"Dimensions: {W} cells wide by {Hh} cells tall. Rich textures, atmospheric lighting. "
        f"Draw ONLY the floor surface materials: absolutely NO furniture, NO counters, NO walls rising up, NO doors, NO people, NO text."
    )
    if not os.path.exists(out_raw):
        print(f'Generating ground for {a}...')
        codex11.gen(prompt + SCENE_NOTE, out_raw, refs=[compose_path] + [os.path.join(G, r) for r in SCENE_REF[a]], size='1536x1024')
    
    # 縮放成 W * 48 x H * 48 並存為 .webp
    im = Image.open(out_raw).convert('RGB')
    target_size = (W * OUT_PX, Hh * OUT_PX) if im.width >= W * OUT_PX else im.size   # 不縮小：原圖不夠大就保留原圖（原本縮成每格 48 像素，遊戲再放大就糊了）
    im_resized = im.resize(target_size, Image.LANCZOS)
    out_webp = os.path.join(G, f'assets/maps/{a}_ground.webp')
    im_resized.save(out_webp, 'WEBP', quality=95)
    print(f'Saved clean ground: {out_webp} ({target_size[0]}x{target_size[1]})')


def gen_objects(a, redo=False):
    d = layout.load(a)
    obs = layout.objects(d)
    jobs = {}
    for o in obs:
        t = get_type(o, a)
        if not t:
            print(f'Warning: no type for object {o["name"]}')
            continue
        if t in FALLBACK_RAW:
            continue
        rp = raw_path(t)
        if redo or not os.path.exists(rp):
            jobs[t] = prompt_for(t, a)
    
    if not jobs:
        print(f'All raw objects for {a} already exist.')
        return

    print(f'Generating {len(jobs)} raw object sprites for {a}...')
    def run_one(item):
        t, p = item
        rp = raw_path(t)
        size = '1024x1536' if TYPES[t][1] > TYPES[t][0] else '1536x1024'
        try:
            codex11.gen(p + SCENE_NOTE, rp, refs=[os.path.join(G, r) for r in SCENE_REF[a]], size=size)
            print(f'Generated {t} -> {rp}')
        except Exception as e:
            print(f'Failed {t}: {e}')

    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(run_one, jobs.items()))


def key_out(src, plate):
    """嚴格使用 cutout skill（~/.claude/skills/cutout/cutout.py），絕不用模型。"""
    out_png = src.replace('.png', '-keyed.png')
    cmd = [
        sys.executable, CUTOUT, 'key', src,
        '-o', out_png,
        '--key', plate,
        '--fuzz', '18',
        '--erode', '1',
        '--band', '2'
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    im = Image.open(out_png).convert('RGBA')
    if os.path.exists(out_png):
        os.remove(out_png)
    bbox = im.getbbox()
    if bbox:
        return im.crop(bbox)
    return im


def resize_premul(im, w, h):
    """Premultiplied alpha LANCZOS 縮放（防止縮圖把底色混回邊緣）"""
    import numpy as np
    a = np.asarray(im.convert("RGBA"), np.float32)
    al = a[..., 3:4] / 255.0
    pre = np.concatenate([a[..., :3] * al, a[..., 3:4]], -1)
    r = np.asarray(Image.fromarray(pre.round().astype(np.uint8), "RGBA").resize((w, h), Image.LANCZOS), np.float32)
    al2 = np.clip(r[..., 3:4] / 255.0, 1e-4, 1.0)
    rgb = np.clip(r[..., :3] / al2, 0, 255)
    out_arr = np.concatenate([rgb, r[..., 3:4]], -1).round().astype(np.uint8)
    return Image.fromarray(out_arr, "RGBA")


def fit_sprite(fig, fw, fh, fill_w=False, plate='green'):
    """縮進圖框 (fw*48, fh*48)：等比縮放、下緣貼齊、水平置中。使用 premultiplied alpha。"""
    W, Hh = fw * OUT_PX, fh * OUT_PX
    if fill_w:
        s = W / fig.width
    else:
        s = min(W / fig.width, Hh / fig.height)
    nw, nh = max(1, round(fig.width * s)), max(1, round(fig.height * s))
    f = resize_premul(fig, nw, nh)
    if nh > Hh:
        f = f.crop((0, nh - Hh, nw, nh))
        nh = Hh
    canvas = Image.new('RGBA', (W, Hh), (0, 0, 0, 0))
    canvas.alpha_composite(f, ((W - nw) // 2, Hh - nh))
    return canvas


def cut_objects(a):
    d = layout.load(a)
    od = os.path.join(G, f'assets/objects/{a}')
    os.makedirs(od, exist_ok=True)
    obs = layout.objects(d)
    
    for o in obs:
        t = get_type(o, a)
        fw, fh = o['frame'][2], o['frame'][3]
        rp = raw_path(t)
        if not os.path.exists(rp):
            print(f'Error: missing raw image for {t} ({rp})')
            continue
        plate = TYPES[t][5]
        fill_w = TYPES[t][4]
        fig = key_out(rp, plate)
        canvas = fit_sprite(fig, fw, fh, fill_w=fill_w)
        out_webp = os.path.join(od, f"{o['name']}.webp")
        canvas.save(out_webp, 'WEBP')
        print(f'Saved object: {out_webp} ({fw*OUT_PX}x{fh*OUT_PX})')


def process_props():
    """處理 assets/props/ 與 assets/objects/obj_wood_box.webp"""
    props = {
        'prop_spoon': ('art/raw/prop_spoon_raw.webp', 'magenta', 'assets/props/prop_spoon.webp'),
        'prop_saffron': ('art/raw/prop_saffron_raw.webp', 'magenta', 'assets/props/prop_saffron.webp'),
        'prop_key': ('art/raw/prop_key_raw.webp', 'magenta', 'assets/props/prop_key.webp'),
        'prop_pepper': ('art/raw/prop_pepper_raw.webp', 'magenta', 'assets/props/prop_pepper.webp'),
        'obj_wood_box': ('art/raw/obj_wood_box_green.webp', 'green', 'assets/objects/obj_wood_box.webp'),
    }
    for k, (src, plate, dst) in props.items():
        src_path = os.path.join(G, src)
        dst_path = os.path.join(G, dst)
        if not os.path.exists(src_path):
            print(f'Skip prop {k}: {src_path} not found')
            continue
        print(f'Keying prop {k} via cutout skill...')
        fig = key_out(src_path, plate)
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        fig.save(dst_path, 'WEBP')
        print(f'Saved prop {k} -> {dst_path} {fig.size}')


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'all'
    maps = ['dressing', 'backstage', 'auditorium', 'alley']
    
    if cmd == 'props':
        process_props()
    elif cmd == 'ground':
        target = sys.argv[2] if len(sys.argv) > 2 else 'bar'
        gen_ground(target)
    elif cmd == 'gen':
        target = sys.argv[2] if len(sys.argv) > 2 else 'bar'
        gen_objects(target)
    elif cmd == 'cut':
        target = sys.argv[2] if len(sys.argv) > 2 else 'bar'
        cut_objects(target)
    elif cmd == 'all':
        process_props()
        for m in maps:
            print(f'=== Processing {m} ===')
            gen_ground(m)
            gen_objects(m)
            cut_objects(m)


if __name__ == '__main__':
    main()
