"""餘燼的分層地圖美術管線（2026-10-20 照《十一分鐘》art/objects_gen.py 重做；舊的 art/objects_gen.old.py 留作歷史）。
流程：色塊構圖（art/compose.py）→ 畫風定錨（整間房一張，art/style/<map>_style_v1.png）→ 地面（從地面色塊生成）→ 每種物件用定錨上那個物件附近的裁切當參考圖逐一生成（綠幕）
      → 機械品質閘門（傾斜、被切掉、比例、不透明、綠邊）→ 去背、縮進圖框、下緣貼齊 → 合成預覽。
相機規格全部統一：固定 3/4 俯視（約 50 度，從南邊看，看得到頂面與朝南的正面），光從左上，物件邊緣與畫面邊緣平行、不旋轉。
用法：python3 art/mapgen.py style dressing
      python3 art/mapgen.py ground dressing
      python3 art/mapgen.py gen dressing [種類…] [--redo]
      python3 art/mapgen.py cut dressing          → assets/objects/<map>/<物件名>.webp
      python3 art/mapgen.py review dressing       → art/check/maps-review/<map>-composed.jpg ＋ 物件總覽
      python3 art/mapgen.py all dressing
"""
import glob, json, math, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from PIL import Image, ImageDraw

H = os.path.dirname(os.path.abspath(__file__)); G = os.path.dirname(H)
sys.path[:0] = [os.path.join(G, 'src'), H]
import layout, blocks, codex11   # 產圖走 .11 codex-image

OBJ_PX = 96                       # 物件每格 96 px
RAW = os.path.join(H, 'raw/mapgen')
STYLE = os.path.join(H, 'style')
REPORT = os.path.join(H, 'check/mapgen-report.json')
CUTOUT = os.path.expanduser('~/.claude/skills/cutout/cutout.py')

BASE = ('warm hand-painted 2D game map art, storybook illustration style with clean crisp outlines and visible soft brush texture, '
        'warm golden-hour palette of orange, amber, deep red and dark brown; NOT pixel art, NOT blurry, NOT photographic')
LOOK = {
    'dressing': 'the second-floor dressing room of an old 1950s Tainan theater at sunset, cream lime-plaster walls, dark wood, faded red velvet',
    'backstage': 'the ground-floor backstage of an old 1950s Tainan theater: warm tungsten bulbs, old red brick walls, dark wood, grey concrete floor with faded stage tape marks, a wooden staircase going up along the east side',
    'backstage2f': 'the second-floor backstage landing of an old 1950s Tainan theater: warm tungsten bulbs, worn cream plaster walls, dark wood, an old wooden plank floor with a faded dark-red rug, a wooden staircase going down along the east side',
    'auditorium': 'the auditorium of an old 1950s Tainan theater: red velvet seats, a wooden stage with deep red curtains, warm stage lights',
    'alley': 'a narrow back alley behind an old Tainan theater at dusk: weathered red brick wall, wet asphalt reflecting the orange lights of an evening market at the far right end',
}
CAM = ('the same fixed 3/4 top-down camera looking from the south (about 50 degrees; you see the top surface and the south-facing front), '
       'light from the upper left. Everything is drawn perfectly axis-aligned: horizontal edges exactly horizontal, vertical edges exactly vertical, '
       'absolutely no rotation, no tilt, no perspective skew')
SEG = ('This is one section cut out of a long continuous wall: both the left and right ends are cut straight off (neighbouring sections will be joined side by side), '
       'no corners, no end caps, the same height and the same top outline at both ends; the section fills the full width of the image (only a very thin margin left and right).')

# 種類 → (圖框寬, 圖框高, 佔地深, 描述, 模式, 幕色, 方正)；模式：strip 一長條（多段共用、切段）、seg 牆上的一段（含窗或門，填滿寬）、obj 獨立物件（縮進圖框）。
TYPES = {
    # 化妝間
    'd_wall': (6, 3, 1, 'a plain section of the interior back wall of an old Tainan theater dressing room: warm cream lime-plaster with soft age stains, the lower third is dark brown wood wainscot panelling with evenly spaced raised panels, a thin wooden picture rail along the top; completely plain, no window, no door, no furniture, nothing hanging', 'strip', 'green', True),
    'd_window': (4, 3, 1, 'the same kind of wall section (cream plaster above, dark wood wainscot panelling below) with one tall rectangular wooden-framed window in the middle showing a glowing orange sunset sky over old Tainan tiled rooftops, a stone sill, and deep red velvet curtains tied back neatly on both sides; plain wall continues at the left and right edges', 'seg', 'green', True),
    'd_vanity': (4, 3, 1, 'an old theater dressing table seen from the front: a wide wooden table with drawers, above it a large rectangular mirror framed by evenly spaced round warm light bulbs; on the table an open notebook and a black wristwatch; a small photo tucked into the corner of the mirror frame; the whole piece is symmetrical', 'obj', 'green', True),
    'd_jewel': (1, 2, 1, 'a small round wooden side table with a carved wooden jewelry box on top', 'obj', 'green', False),
    'd_bench': (4, 2, 1, 'a long low wooden bench seen from the front with a faded red velvet cushion on the seat, straight and level', 'obj', 'green', True),
    'd_radio': (2, 2, 1, 'a small plain wooden side table with an old cream-colored plastic portable transistor radio on top, its corners worn white, the tuning shaft bare without a knob', 'obj', 'green', True),
    'd_chair': (1, 2, 1, 'an old wooden chair with a faded red velvet seat, seen from behind (the chair back toward the camera)', 'obj', 'green', False),
    'd_case': (2, 2, 1, 'an open black leather makeup case sitting on the floor, its trays showing neatly arranged brushes and lipsticks, a small glass box in the bottom tray', 'obj', 'green', True),
    'd_rack': (1, 4, 3, 'a narrow metal clothes rack with one navy jacket hanging on it, standing against a wall, drawn as a tall narrow object', 'obj', 'green', False),
    'd_sofa': (6, 2, 1, 'a long sofa seen from behind (its back toward the camera): a tall straight faded red velvet backrest with gold buttons, wooden feet, straight and level', 'obj', 'green', True),
    # 門：每扇門單獨生成成「含門框的門」，統一縮成 1.7×2.9 格再貼到那面牆的連續牆面上（作者：門製作得非常奇怪；規則：門約 3 格高、2 格寬，嵌在朝南的牆面裡）
    'door_wood': (2, 3, 1, 'one single closed old dark-brown wooden door with a brass handle and a small blank brass name plate, set in a plain dark wooden door frame (architrave) with a thin wooden threshold at the bottom, seen from the front; the whole door including its frame is 1.7 cells wide and 2.9 cells tall (width:height = 0.59:1)', 'door', 'green', True),
    'door_iron': (2, 3, 1, 'one single closed heavy dark-green painted iron stage door with a handle, set in a plain stone door frame (architrave) with a worn concrete step at the bottom and a small warm yellow bulb in a wire cage above the frame, seen from the front; the whole door including its frame, step and lamp is 1.7 cells wide and 2.9 cells tall (width:height = 0.59:1)', 'door', 'green', True),
    'door_stage': (2, 3, 1, 'one single closed heavy dark-brown wooden door with iron straps and a ring handle, set in a plain light stone door frame (architrave) with a worn stone threshold step at the bottom, seen from the front; the whole door including its frame and step is 1.7 cells wide and 2.9 cells tall (width:height = 0.59:1)', 'door', 'green', True),
    'door_steel': (2, 3, 1, 'one single closed dark grey steel back door with a horizontal push bar and a small blank sign plate above, set in a plain light stone door frame (architrave) with a black rubber door mat at the bottom, seen from the front; the whole door including its frame and mat is 1.7 cells wide and 2.9 cells tall (width:height = 0.59:1)', 'door', 'green', True),
    'door_stage2': (2, 3, 1, 'one single closed heavy dark-brown wooden stage door with a brass handle in a plain dark wooden door frame (architrave) with a small pelmet above it and a worn wooden step at the bottom, seen from the front; the whole door including its frame and step is 1.7 cells wide and 2.9 cells tall (width:height = 0.59:1)', 'door', 'green', True),
    # 後台
    'b_wall': (11, 3, 1, 'a plain section of the back wall of an old theater backstage corridor: worn cream plaster with a few peeling patches, a dark brown wooden skirting, a faded painted stripe; completely plain, no doors, no windows, nothing hanging', 'strip', 'green', True),
    'b_piano': (3, 2, 1, 'an old black upright piano seen from the front, a small brass lamp on top', 'obj', 'green', True),
    'b_rail_e': (1, 4, 3, 'a short dark wooden banister rail with turned balusters standing along a balcony edge, drawn as a tall narrow object', 'obj', 'green', False),
    'b_balcony': (15, 5, 4, 'the front edge of an indoor second-floor balcony seen from the south: along the top a one-cell-tall ornate black cast-iron railing, below it a full-storey old red brick wall face four cells tall with evenly spaced brass wall lamps glowing warm; plain brick wall with no doors; runs straight across', 'strip', 'green', True),
    'b_cap': (2, 1, 1, 'a short flat-topped section of an old masonry wall, plaster and brick, seen from the south', 'seg', 'green', True),
    'b_divider': (1, 12, 10, 'one thin plaster-and-brick partition wall running straight north-south away from the viewer, so on screen it is one long narrow vertical strip: its long thin top edge runs from the top of the image downward, and at the bottom end you see the wall south-facing end face; about 1 cell wide and 12 cells tall', 'obj', 'green', True),
    'b_turn': (7, 3, 2, 'a wide masonry stairwell wall front seen from the south, plaster and old brick like the backstage back wall, COMPLETELY OPAQUE with no see-through gaps; near the left third a dark rounded archway whose interior is solid dark brown-black (opaque, nothing visible through it); a dark wooden lintel; a brass wall lamp; fills the full width', 'seg', 'green', True),
    'b_upper': (4, 5, 2, 'a thick masonry wall pier of the stairwell seen from the south, plaster and old brick, 4 cells wide and 5 cells tall, COMPLETELY OPAQUE and solid with no gaps; a heavy dark wooden beam across its bottom edge and a small hanging brass lamp near the top', 'seg', 'green', True),
    'b_cases': (2, 2, 1, 'two stacked black stage flight cases with metal corners', 'obj', 'green', True),
    'b_table': (3, 2, 1, 'a sturdy wooden workbench seen from the front with a desk lamp, a few sandbags and a roll of tape on top', 'obj', 'green', True),
    'b_brick': (11, 3, 1, 'a plain section of old red brick wall of a theater backstage: straight cement mortar lines, a few darker bricks, a low dark concrete base; completely plain, no doors, no windows, nothing hanging', 'strip', 'green', True),
    'b_arch': (2, 3, 1, 'a wall section with one dark rounded archway in the middle leading to a stairwell: plaster and old brick around it, a dark wooden lintel, a small brass wall lamp above; the inside of the arch is solid dark brown-black (opaque, nothing visible through it); plain wall continues left and right of the arch', 'seg', 'green', True),
    'b_bench': (4, 2, 1, 'a long low plain wooden bench seen from the front, worn dark wood, four legs, straight and level', 'obj', 'green', True),
    'b_rack': (2, 2, 1, 'a wheeled metal costume rack seen from the front with three stage costumes hanging on it (a dark red dress, a navy jacket, a cream shirt), small caster wheels at the bottom', 'obj', 'green', True),
    'b_trunk': (2, 2, 1, 'one large old wooden steamer trunk with brass corners and a leather handle, closed lid, seen from the front', 'obj', 'green', True),
    'b_mirror': (1, 2, 1, 'a standing full-length cheval mirror in a dark wooden frame on two small feet, seen from the front, the glass reflecting warm light', 'obj', 'green', False),
    'b_plant': (1, 2, 1, 'a large leafy green potted plant in a plain terracotta pot, seen from the front', 'obj', 'green', False),
    'b_ladder': (1, 2, 1, 'a plain wooden step ladder standing upright, seen from the front', 'obj', 'green', False),
    'b_reel': (2, 2, 1, 'a big wooden cable drum standing on its side with black electric cable wound around it, seen from the front', 'obj', 'green', True),
    'b_propbox': (2, 2, 1, 'an open wooden prop crate with a few small stage props sticking out of it (a paper fan, a lantern, a rolled scroll), seen from the front', 'obj', 'green', True),
    # 觀眾席
    'a_curtain': (6, 3, 1, 'a section of deep red velvet stage curtain with evenly spaced vertical folds and a gold fringe along the bottom hem', 'strip', 'green', True),
    'a_lip': (8, 3, 1, 'the front of an old wooden stage seen from the front, 3 cells tall: along the top a gold-trimmed lip with small evenly spaced round footlights in the top cell, below it a dark wood panelled stage skirt two cells tall with evenly spaced raised panels', 'strip', 'green', True),
    'a_piano': (3, 2, 1, 'a black grand piano with its lid closed, seen from the front', 'obj', 'green', True),
    'a_mic': (1, 2, 1, 'a straight black microphone stand with a microphone on top', 'obj', 'green', False),
    'a_seat6': (6, 2, 1, 'one row of exactly 6 old red velvet theater seats in a perfectly straight row seen from the front: tall seat backs, gold-trimmed armrests between the seats, six identical evenly spaced seats', 'obj', 'green', True),
    'a_seat8': (8, 2, 1, 'one row of exactly 8 old red velvet theater seats in a perfectly straight row seen from the front: tall seat backs, gold-trimmed armrests between the seats, eight identical evenly spaced seats', 'obj', 'green', True),
    'a_seat8rose': (8, 2, 1, 'exactly the same row of 8 red velvet theater seats as image 2, but the rightmost seat has a single deep red rose lying across its seat cushion', 'obj', 'green', True),
    'a_desk': (4, 2, 1, 'a sound mixing desk seen from the front with rows of faders and small glowing lights on a wooden stand', 'obj', 'green', True),
    # 巷子
    'l_wall': (8, 3, 1, 'a plain section of weathered red brick wall of the back of an old theater: straight mortar lines, dark water stains, a low concrete base; completely plain, no doors, no windows, nothing hanging', 'strip', 'green', True),
    'l_shop': (4, 3, 1, 'the same red brick wall as a market-side shopfront: a striped red-and-white canvas awning, a row of glowing orange paper lanterns hanging under it, a few wooden produce crates below, warm light', 'seg', 'green', True),
    'l_scooters': (4, 2, 1, 'two parked scooters side by side seen from the side, both facing left, one white and one red, parallel and upright', 'obj', 'green', True),
    'l_crates': (1, 2, 1, 'two stacked red plastic produce baskets', 'obj', 'green', False),
}
OPAQUE = {'b_turn', 'b_upper', 'b_cap', 'd_wall', 'b_wall', 'b_brick', 'b_arch', 'l_wall', 'a_curtain'}
DOOR_WALL = {('dressing', 'door_wood'): 'd_wall', ('backstage2f', 'door_wood'): 'b_wall', ('backstage', 'door_stage'): 'b_brick', ('backstage', 'door_steel'): 'b_brick', ('alley', 'door_iron'): 'l_wall', ('auditorium', 'door_stage2'): 'a_curtain'}   # 門貼在哪種牆面上
DOOR_W, DOOR_H = 1.7, 2.9   # 所有門（含門框）統一大小，單位：格   # 整面要不透明（遮擋物與牆）
FLOORS = {a: '' for a in LOOK}


def anchor(a): return os.path.join(STYLE, f'{a}_style_v1.webp')
def raw_path(a, t): return os.path.join(RAW, f'obj-{a}-{t}.png')


def size_for(w, h):
    r = w / h
    return '1536x1024' if r > 1.25 else ('1024x1536' if r < 0.8 else '1024x1024')


def type_of(o): return o['type']


def crop_ref(a, d, o):
    im = Image.open(anchor(a)).convert('RGB'); W, Hh = d['map']['w'], d['map']['h']; sx, sy = im.width / W, im.height / Hh
    fx, fy, fw, fh = o['frame']; m = 2
    box = (max(0, (fx - m) * sx), max(0, (fy - m) * sy), min(im.width, (fx + fw + m) * sx), min(im.height, (fy + fh + m) * sy))
    os.makedirs(RAW, exist_ok=True); out = os.path.join(RAW, f"ref-{a}-{o['name']}.png")
    im.crop(tuple(map(int, box))).save(out); return out


def prompt(t, a, hint=''):
    w, h, dd, desc, mode, key, rect = TYPES[t]
    bg = '#00FF00 pure green'
    p = (f"Game map object sprite, one single object only. Match the art style of image 1 exactly: image 1 is a crop of the same painted game map ({BASE}; {LOOK[a]}); use image 1 ONLY for style, colours and camera and ignore whatever else appears in it, "
         f"{CAM}. Redraw the object cleanly and completely as a standalone sprite with crisp clean outlines.\n"
         f"Draw: {desc}.\n"
         f"Proportions: its bounding box is {w} cells wide and {h} cells tall (width:height = {w}:{h}); the bottom {dd} cell(s) are its footprint on the floor, "
         f"the top {h - dd} cell(s) the part rising up. It fills that box: it touches (within 2%) the left, right and bottom edges of its box and nothing is cropped.\n")
    if mode == 'door': p = p.replace(f"Proportions: its bounding box is {w} cells wide and {h} cells tall (width:height = {w}:{h}); the bottom {dd} cell(s) are its footprint on the floor, the top {h - dd} cell(s) the part rising up. It fills that box", "Proportions: it fills its bounding box")
    if mode == 'strip':
        p += (SEG + f" Draw it as one long straight horizontal strip about {max(w, h * 4)} cells wide and {h} cells tall; place it in the lower part of the image.\n")
    elif mode == 'seg':
        p += SEG + "\n"
    if hint: p += hint + '\n'
    p += (f"Draw only this object: no floor, no cast shadow on the floor, no people, no other objects, no glow halo spilling outside it. "
          f"Background: a completely flat opaque {bg} fill, no gradient, no shadow. No text, no letters, no watermark.")
    return p


# ── 去背與閘門 ──
def key_full(src):
    out = src.replace('.png', '-key.png')
    subprocess.run([sys.executable, CUTOUT, 'key', src, '-o', out, '--key', 'green', '--fuzz', '18', '--erode', '1', '--band', '0'], check=True, capture_output=True)
    im = Image.open(out).convert('RGBA'); os.remove(out)
    a = np.asarray(im).copy()
    r, g, b = a[..., 0].astype(int), a[..., 1].astype(int), a[..., 2].astype(int)
    spill = (a[..., 3] > 0) & (g > np.maximum(r, b) + 12)      # 殘留綠邊：把綠色壓回
    a[..., 1][spill] = np.minimum(g, np.maximum(r, b) + 8)[spill].astype(np.uint8)
    return Image.fromarray(a, 'RGBA')


def edge_slope(mask, x0, x1, top=False):
    xs = np.arange(int(x0 + (x1 - x0) * .1), int(x0 + (x1 - x0) * .9))
    ys = []
    for x in xs:
        col = np.where(mask[:, x])[0]
        if len(col): ys.append(col.min() if top else col.max())
        else: ys.append(np.nan)
    ys = np.array(ys, float); ok = ~np.isnan(ys)
    if ok.sum() < 20: return 0.0
    k = np.polyfit(xs[ok], ys[ok], 1)[0]
    return math.degrees(math.atan(k))


def check_raw(path, t):
    w, h, dd, desc, mode, key, rect = TYPES[t]
    full = key_full(path); A = np.asarray(full)[..., 3] > 128; Hh, Ww = A.shape
    bb = full.getbbox(); probs = []; m = {}
    if not bb: return dict(ok=False, problems=['去背後全空'], m={})
    x0, y0, x1, y1 = bb; bw, bh = x1 - x0, y1 - y0
    margins = dict(left=x0, top=y0, right=Ww - x1, bottom=Hh - y1); m['margins'] = margins
    need = ['top', 'bottom'] if mode in ('strip', 'seg') else ['left', 'right', 'top', 'bottom']
    cut = [k for k in need if margins[k] < 4]
    if cut: probs.append('貼到圖邊（可能被切掉）：' + ','.join(cut))
    asp = bw / bh; want = w / h; m['aspect'] = round(asp, 2); m['want'] = round(want, 2)
    if mode == 'door':
        if not (.45 <= asp <= .78): probs.append(f'門的比例不對（{asp:.2f}，要約 {DOOR_W / DOOR_H:.2f}）')
    elif mode == 'strip':
        if asp < want * .45: probs.append(f'長條太短（比例 {asp:.2f} < {want * .45:.2f}），鏡射接長也不夠')   # 不夠寬的長條會在 cut 時鏡射接長
    elif not ((.62 if rect else .4) <= asp / want <= 1.65):   # 寬扁的家具比框胖沒關係（縮放以寬為準），只擋極端
        probs.append(f'比例不對（{asp:.2f}，要 {want:.2f}）')
    if rect:
        sb = edge_slope(A, x0, x1); m['bottom_deg'] = round(sb, 2)
        if abs(sb) > 2.5: probs.append(f'下緣傾斜 {sb:.1f} 度')
        if mode in ('strip', 'seg'):
            st = edge_slope(A, x0, x1, top=True); m['top_deg'] = round(st, 2)
            if abs(st) > 2.5: probs.append(f'上緣傾斜 {st:.1f} 度')
    if t in OPAQUE:
        cov = A[y0:y1, x0:x1].mean(); m['opaque'] = round(float(cov), 3)
        if cov < .97: probs.append(f'有透空 {cov:.2%}')
    return dict(ok=not probs, problems=probs, m=m)


def log(entry):
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    data = json.load(open(REPORT, encoding='utf-8')) if os.path.exists(REPORT) else []
    data.append(dict(entry, t=time.strftime('%F %T'))); json.dump(data, open(REPORT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


HINTS = ['', 'IMPORTANT: draw it perfectly straight and level, edges exactly parallel to the image edges, and keep the WHOLE object fully inside the image with a margin all around.',
         'IMPORTANT: the previous attempts were tilted or cropped. Draw it perfectly frontal and level (a flat orthographic-like front view with only a slight top-down tilt), centered, whole object visible with clear margin.']


def gen_one(a, t, ref, extra_refs=(), tries=3):
    w, h = TYPES[t][:2]; best = None
    for k in range(tries):
        out = raw_path(a, t) if k == 0 else raw_path(a, t).replace('.png', f'-try{k + 1}.png')
        try: codex11.gen(prompt(t, a, HINTS[min(k, 2)]), out, [ref, *extra_refs], size=size_for(w, h))
        except Exception as e: print(t, '第', k + 1, '次生成失敗', repr(e)[:120], flush=True); continue
        r = check_raw(out, t); r['try'] = k + 1; r['file'] = out
        log(dict(map=a, type=t, **{x: r[x] for x in ('ok', 'problems', 'm', 'try')}))
        print(t, '第', k + 1, '次', '過' if r['ok'] else '不過 ' + '；'.join(r['problems']), flush=True)
        if best is None or len(r['problems']) < len(best['problems']): best = r
        if r['ok']: break
    if best and best['file'] != raw_path(a, t):
        Image.open(best['file']).save(raw_path(a, t))
    return best


def gen(a, only=(), redo=False):
    d = layout.load(a); jobs = {}
    for o in layout.objects(d):
        t = type_of(o)
        if (only and t not in only) or t in jobs or (not redo and os.path.exists(raw_path(a, t))): continue
        jobs[t] = o
    results = {}
    def run(t):
        o = jobs[t]; extra = []
        if t == 'a_seat8rose': extra = [raw_path(a, 'a_seat8')]
        results[t] = gen_one(a, t, crop_ref(a, d, o), extra)
    first = [t for t in jobs if t != 'a_seat8rose']
    print(len(jobs), '種', flush=True)
    with ThreadPoolExecutor(4) as ex: list(ex.map(run, first))
    if 'a_seat8rose' in jobs: run('a_seat8rose')
    bad = {t: r['problems'] for t, r in results.items() if r and not r['ok']}
    print('閘門沒過的：', bad or '無', flush=True)
    return results


# ── 定錨與地面 ──
def style(a):
    subprocess.run([sys.executable, os.path.join(H, 'compose.py'), a], check=True, capture_output=True)
    d = layout.load(a)
    objs = '; '.join(f"{o['name']}: {o.get('desc', '')}" for o in d['objects'])
    floors = '; '.join(f"{g['name']}: {g.get('desc', '')}" for g in d['ground'] if g['kind'] != 'border' and g.get('desc'))
    refs = [os.path.join(G, f'art/check/compose-{a}.webp')]
    if a == 'dressing': refs.append(os.path.join(STYLE, 'old_dressing_ground.webp'))   # 舊化妝間地面的木頭與地毯質感（作者沒有抱怨畫風）
    else: refs.append(anchor('dressing'))
    p = (f"A complete top-down painted game map ({BASE}). Follow EXACTLY the layout of image 1: each flat colour block is one thing, the darker block is its footprint on the floor and "
         f"the lighter block above it is the part rising up (seen from the south at about 50 degrees, so tall things and walls show their south-facing front). "
         f"Match the painting style, colour palette, brush texture and lighting of image 2 (ignore image 2's furniture layout). This map: {LOOK[a]}. "
         f"Floors: {floors}. Things on the map: {objs}. {CAM}. Everything tidy, evenly spaced and aligned to a grid. No people, no text, no letters, no UI.")
    os.makedirs(STYLE, exist_ok=True)
    codex11.gen(p, anchor(a), refs, size='1536x1024'); print('style ok', anchor(a))



def want_mask(d):
    W, Hh = d['map']['w'], d['map']['h']; want = np.zeros((Hh, W), bool)
    for g in d['ground']:
        if g['kind'] == 'border': continue
        for x, y, w, h in g['rects']: want[y:y + h, x:x + w] = True
    for g in d['ground']:
        if g['kind'] == 'border':
            for x, y, w, h in g['rects']: want[y:y + h, x:x + w] = False
    return want


def floor_mask(im, textured=True):
    """地板＝夠亮，或偏紅褐（陰影下的木頭與地毯），或有紋理（深色濕柏油：外框牆是完全平的，紋理為 0）；深灰色的外框牆不算"""
    from scipy import ndimage
    a = np.asarray(im.convert('RGB')).astype(int); L = (a[..., 0] * 3 + a[..., 1] * 6 + a[..., 2]) / 10
    gy, gx = np.gradient(L); tex = ndimage.uniform_filter(np.abs(gx) + np.abs(gy), size=7)
    m = (L > 58) | (((a[..., 0] - a[..., 2]) > 18) & (L > 25))
    return m | (tex > 2.0) if textured else m


def align_ground(raw_png, d, S):
    """模型會把地板置中、邊框厚度各畫各的，位置跟設計差一兩格：量出生成圖裡地板的實際範圍，縮放貼回設計的格子上。
    判斷「哪裡是地板」有兩種方法各有盲點（只看亮度與顏色：深色濕柏油會被當成外框；加上紋理：有紋理的深色外框會被當成地板），
    兩種都試，採用格子層級重疊度（IoU）高的。回傳 (對位後的圖, IoU, 用哪種)。IoU < 0.92 就是形狀對不上，要重產。"""
    from scipy import ndimage
    from PIL import ImageFilter
    im = Image.open(raw_png).convert('RGB'); W, Hh = d['map']['w'], d['map']['h']; want = want_mask(d)
    ys, xs = np.where(want); wx0, wx1, wy0, wy1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    best = None
    for textured in (False, True):
        m = floor_mask(im.filter(ImageFilter.GaussianBlur(3)), textured)
        lab, n = ndimage.label(m); k = 1 + int(np.argmax(ndimage.sum(m, lab, range(1, n + 1)))); mm = lab == k
        rs, cs = mm.sum(1), mm.sum(0)   # 模型有時會多畫一條窄窄的凸出（門口）：只取寬度過半的列與行當地板範圍
        ys2 = np.where(rs > .5 * rs.max())[0]; xs2 = np.where(cs > .5 * cs.max())[0]
        gx0, gx1, gy0, gy1 = xs2.min(), xs2.max() + 1, ys2.min(), ys2.max() + 1
        border = tuple(int(v) for v in np.asarray(im)[~mm].mean(0)) if (~mm).any() else (30, 30, 30)
        crop = im.crop((int(gx0), int(gy0), int(gx1), int(gy1))).resize(((wx1 - wx0) * S, (wy1 - wy0) * S), Image.LANCZOS)
        canvas = Image.new('RGB', (W * S, Hh * S), border); canvas.paste(crop, (int(wx0) * S, int(wy0) * S))
        got = floor_mask(canvas, textured).reshape(Hh, S, W, S).mean(axis=(1, 3)) > .5
        iou = float((got & want).sum() / max(1, (got | want).sum()))
        if best is None or iou > best[1]: best = (canvas, iou, '亮度＋紋理' if textured else '亮度顏色')
    return best


def stair_rows(d):
    """每一段樓梯真正露出來的列（後面的地面矩形蓋過去的列不算，例如 B 段尾端被一樓地面蓋住）"""
    W, Hh = d['map']['w'], d['map']['h']; grid = [[None] * W for _ in range(Hh)]
    for g in d['ground']:
        for x, y, w, h in g['rects']:
            for j in range(y, y + h):
                for i in range(x, x + w): grid[j][i] = g['kind']
    out = []
    for g in d['ground']:
        if g['kind'] != 'stairs' or g.get('nogate'): continue
        for x, y, w, h in g['rects']:
            rows = [j for j in range(y, y + h) if all(grid[j][i] == 'stairs' for i in range(x, x + w))]
            if len(rows) >= 3: out.append((g['name'], x, w, rows))   # 舞台前的 1 格小階梯不驗
    return out


def riser_count(canvas, x, w, rows, S, thr=.55, min_w=9):
    """沿樓梯縱向取亮度剖面：立面（階與階之間的暗帶）要夠深（低於踏面亮度的 55%）又夠寬（≥ 9 px，約 0.14 格）才算一階。
    木板的板縫只有 1 到 5 px 寬，不算。回傳 (立面數, 所有暗帶寬)。"""
    L = np.asarray(canvas.convert('L')).astype(float)
    p = np.convolve(L[rows[0] * S:(rows[-1] + 1) * S, x * S + S // 4:(x + w) * S - S // 4].mean(1), np.ones(3) / 3, 'same')[8:-8]
    dark = p < thr * np.percentile(p, 70); runs = []; n = 0
    for v in dark:
        if v: n += 1
        elif n: runs.append(n); n = 0
    if n: runs.append(n)
    return sum(r >= min_w for r in runs), sorted(runs)


def stairs_ok(canvas, d, S):
    """樓梯地面閘門：每一段露出來的樓梯，立面（暗帶）數要 ≥ 每格 0.9 條（至少 3 條）。回傳 (全過, [(名稱, 露出幾格, 立面數)])。"""
    res = []; ok = True
    for name, x, w, rows in stair_rows(d):
        n, _ = riser_count(canvas, x, w, rows, S); res.append((name, len(rows), n)); ok &= n >= max(3, int(len(rows) * .9))
    return ok, res


def fix_stairs(canvas, d, S):
    """生成圖裡有一段樓梯畫成平木板、另一段是真的階梯時：把合格那段的階梯貼到不合格那段上（從上緣對齊），兩段樣式一致。
    只在寬度相同、合格那段夠長時才補。回傳 (圖, 被補的段名)。"""
    segs = stair_rows(d); good = []; bad = []
    for name, x, w, rows in segs:
        n, _ = riser_count(canvas, x, w, rows, S)
        (good if n >= max(3, int(len(rows) * .9)) else bad).append((name, x, w, rows))
    out = canvas.copy(); fixed = []
    for name, x, w, rows in bad:
        donors = [g for g in good if g[2] == w and len(g[3]) >= len(rows)]
        if not donors: continue
        dn, dx, dw, drows = donors[0]
        patch = canvas.crop((dx * S, drows[0] * S, (dx + dw) * S, (drows[0] + len(rows)) * S))
        out.paste(patch, (x * S, rows[0] * S)); fixed.append(name)
    return out, fixed


def no_stairs_ok(canvas, d, S):
    """d['no_stairs'] 範圍（格）內不能有階梯立面（暗帶 ≥ 9 px 且夠深）；回傳是否乾淨"""
    ok = True
    for x, y, w, h in d.get('no_stairs', []):
        n, runs = riser_count(canvas, x, w, list(range(y, y + h)), S); print('  無階梯範圍', (x, y, w, h), '立面', n, '乾淨' if n <= 1 else '有階梯殘留'); ok &= n <= 1
    return ok


def ground(a):
    d = layout.load(a); W, Hh = d['map']['w'], d['map']['h']; S = 32
    im = Image.new('RGB', (W * S, Hh * S)); dr = ImageDraw.Draw(im)
    for g in d['ground']:
        for x, y, w, h in g['rects']: dr.rectangle((x * S, y * S, (x + w) * S - 1, (y + h) * S - 1), fill=blocks.GROUND[g['kind']])
    os.makedirs(RAW, exist_ok=True); lay = os.path.join(RAW, f'ground-layout-{a}.png'); im.save(lay)
    desc = '; '.join(f"{g['name']}: {g.get('desc', '')}" for g in d['ground'] if g['kind'] != 'border')
    p = (f"Top-down painted game map floor texture only ({BASE}), following exactly the colour-region layout of image 1 (each flat colour is one floor material). "
         f"Match the painting style, palette and lighting of image 2, but IGNORE image 2's layout completely (its furniture, rug position and doorways are irrelevant). {LOOK[a]}. Floor materials: {desc}. "
         "The dark regions are solid walls seen from above: draw them as a dark plaster wall top / dark masonry, plain and flat. "
         f"The floor is completely flat everywhere: NO staircase, NO steps, NO stair treads, NO railings anywhere on the floor (image 2 may show a doorway in a wall, ignore it). {CAM}. Draw ONLY the floor surfaces and the dark wall areas: no furniture, no walls rising up, no windows, no doors, no people, no objects at all, no text.")
    out = os.path.join(RAW, f'ground-{a}.png'); S2 = 1536 // W; best = None
    for k in range(3):
        o = out if k == 0 else out.replace('.png', f'-try{k + 1}.png')
        try: codex11.gen(p + (' IMPORTANT: keep the floor rectangle exactly where image 1 puts it, with the same thick dark band at the top and thin band at the bottom. ' if k else ''), o, [lay, anchor(a)], size='1536x1024')
        except Exception as e: print('地面第', k + 1, '次生成失敗', repr(e)[:120], flush=True); continue
        canvas, iou, how = align_ground(o, d, S2); sok, sres = stairs_ok(canvas, d, S2); fixed = []
        if not sok:
            c2, fixed = fix_stairs(canvas, d, S2); sok2, sres2 = stairs_ok(c2, d, S2)
            if sok2: canvas, sok, sres = c2, True, sres2
        print('地面第', k + 1, '次 IoU', round(iou, 3), '樓梯立面', sres, '過' if sok else '不過', ('；補貼：' + '、'.join(fixed)) if fixed else '', flush=True)
        nost = no_stairs_ok(canvas, d, S2)
        good = iou >= .92 and sok and nost
        log(dict(map=a, type='ground', ok=good, iou=round(iou, 3), stairs=sres, cloned=fixed, try_=k + 1))
        score = iou + (1 if sok else 0) + (1 if nost else 0)
        if best is None or score > best[1]: best = (canvas, score, o)
        if good: break
    os.makedirs(os.path.join(G, 'assets/maps'), exist_ok=True)
    best[0].save(os.path.join(G, f'assets/maps/{a}_ground.webp'), quality=92); print('ground 分數', round(best[1], 3), best[2])
    print('ground ok')


# ── 切段 ──
def extend_strip(fig, want):
    """長條牆生成圖不夠寬：左右交替鏡射接長到 height×want（接縫處左右對稱，牆面連得起來）"""
    need = round(fig.height * want)
    if fig.width >= need: return fig
    out = fig; flip = True
    while out.width < need:
        add = fig.transpose(Image.FLIP_LEFT_RIGHT) if flip else fig
        c = Image.new('RGBA', (out.width + add.width, fig.height)); c.alpha_composite(out, (0, 0)); c.alpha_composite(add, (out.width, 0)); out = c; flip = not flip
    return out


def seg_slice(fig, fw, fh, idx):
    sw = round(fig.height * fw / fh)
    if sw >= fig.width: return fig
    span = fig.width - sw; x0 = (idx * sw) % (span + 1)
    return fig.crop((x0, 0, x0 + sw, fig.height))


def match_aspect(fig, fw, fh):
    """牆上的一段（窗、門）：生成圖比框寬就左右對稱裁掉多餘的牆；比框窄就把兩端的牆鏡射補寬。這樣高度會跟旁邊的牆段完全對齊，上緣不會露縫。"""
    want = fw / fh; asp = fig.width / fig.height
    if asp > want:
        nw = round(fig.height * want); x0 = (fig.width - nw) // 2
        return fig.crop((x0, 0, x0 + nw, fig.height))
    if asp < want:
        nw = round(fig.height * want); extra = nw - fig.width; l = extra // 2; r = extra - l
        c = Image.new('RGBA', (nw, fig.height))
        c.alpha_composite(fig, (l, 0))
        strip_l = fig.crop((0, 0, min(l, fig.width), fig.height)).transpose(Image.FLIP_LEFT_RIGHT)
        strip_r = fig.crop((max(0, fig.width - r), 0, fig.width, fig.height)).transpose(Image.FLIP_LEFT_RIGHT)
        if l: c.alpha_composite(strip_l, (l - strip_l.width, 0))
        if r: c.alpha_composite(strip_r, (l + fig.width, 0))
        return c
    return fig


def fit(fig, fw, fh, mode):
    W, Hh = fw * OBJ_PX, fh * OBJ_PX
    if mode == 'seg': fig = match_aspect(fig, fw, fh)
    s = W / fig.width if mode in ('strip', 'seg') else min(W / fig.width, Hh / fig.height)
    nw, nh = max(1, round(fig.width * s)), max(1, round(fig.height * s))
    f = fig.resize((nw, nh), Image.LANCZOS)
    if nh > Hh: f = f.crop((0, nh - Hh, nw, nh)); nh = Hh
    c = Image.new('RGBA', (W, Hh)); c.alpha_composite(f, ((W - nw) // 2, Hh - nh)); return c


FACADE = {'b_balcony', 'door_stage', 'door_steel'}


def door_insert(a, t):
    """含門框的門 → 統一縮成 DOOR_W×DOOR_H 格（生成圖比例已過閘門，形變小）"""
    f = key_full(raw_path(a, t)); g = f.crop(f.getbbox())
    return g.resize((round(DOOR_W * OBJ_PX), round(DOOR_H * OBJ_PX)), Image.LANCZOS)


def facade_line(a, d):
    """陽台前緣整排：長條（欄杆＋磚牆）合成一張連續的長圖，兩扇門的門（統一大小、含石框）貼在上面、下緣貼齊地面；
    之後每一段（左、門、中、門、右）都是這一張長圖的切片，不會有接縫（十一分鐘 lines 的做法）。回傳 (長圖, 最左邊的格)。"""
    objs = [o for o in layout.objects(d) if type_of(o) in FACADE]
    if not any(type_of(o) == 'b_balcony' for o in objs): return None   # 舊的 U 型樓梯後台才有陽台前緣；拆成兩張平地圖後沒有
    xmin = min(o['vis'][0] for o in objs); xmax = max(o['vis'][0] + o['vis'][2] for o in objs); Wc = xmax - xmin; Hc = objs[0]['vis'][3]
    f = key_full(raw_path(a, 'b_balcony')); f = f.crop(f.getbbox()); f = f.crop((4, 0, f.width - 4, f.height))
    comp = fit(seg_slice(extend_strip(f, Wc / Hc * 1.15), Wc, Hc, 0), Wc, Hc, 'strip')
    for o in objs:
        t = type_of(o)
        if t == 'b_balcony': continue
        fx, fy, fw, fh = o['vis']; ins = door_insert(a, t)
        comp.alpha_composite(ins, ((fx - xmin) * OBJ_PX + (fw * OBJ_PX - ins.width) // 2, fh * OBJ_PX - ins.height))
    return comp, xmin


def cut(a):
    d = layout.load(a); od = os.path.join(G, f'assets/objects/{a}'); os.makedirs(od, exist_ok=True)
    for f in glob.glob(os.path.join(od, '*')): os.remove(f)
    cache, alt = {}, {}
    line = facade_line(a, d)   # 後台陽台前緣：整排合成再切段
    for o in layout.objects(d):
        t = type_of(o); fx, fy, fw, fh = o['vis']; pad = o['frame'][3] - fh; tw, th, _, _, mode, _, _ = TYPES[t]
        if line is not None and t in FACADE:
            comp, xmin = line; ox = (fx - xmin) * OBJ_PX
            comp.crop((ox, 0, ox + fw * OBJ_PX, fh * OBJ_PX)).save(os.path.join(od, f"{o['name']}.webp"), quality=93); continue
        if mode == 'door':   # 一般牆上的門：同一面牆的連續牆面切片當底，門（統一大小）貼在中間、下緣貼齊
            wt = DOOR_WALL[(a, t)]
            if wt not in cache:
                f = key_full(raw_path(a, wt)); cache[wt] = f.crop(f.getbbox())
            alt[wt] = alt.get(wt, 0) + 1; wf = cache[wt]
            base = fit(seg_slice(extend_strip(wf.crop((4, 0, wf.width - 4, wf.height)), fw / fh * 1.15), fw, fh, alt[wt] - 1), fw, fh, 'strip')
            ins = door_insert(a, t); base.alpha_composite(ins, ((fw * OBJ_PX - ins.width) // 2, fh * OBJ_PX - ins.height))
            base.save(os.path.join(od, f"{o['name']}.webp"), quality=93); continue
        if mode == 'obj' and (fw, fh) != (tw, th): raise SystemExit(f"{o['name']} 圖框 {fw}×{fh} 跟種類 {t} 的 {tw}×{th} 不一致")
        if t not in cache:
            if not os.path.exists(raw_path(a, t)): raise SystemExit(f'缺 {t} 的產圖')
            f = key_full(raw_path(a, t)); cache[t] = f.crop(f.getbbox())
        fig = cache[t]; alt[t] = alt.get(t, 0) + 1
        if mode == 'strip': fig = seg_slice(extend_strip(fig.crop((4, 0, fig.width - 4, fig.height)), fw / fh * 1.15), fw, fh, alt[t] - 1)   # 去掉左右各 4px 的去背邊，鏡射接縫才不會有線
        img = fit(fig, fw, fh, mode)
        if pad:   # 排序比圖框下緣大的遮擋牆：下面補透明列，引擎才會照 sort 排
            c = Image.new('RGBA', (fw * OBJ_PX, (fh + pad) * OBJ_PX)); c.alpha_composite(img, (0, 0)); img = c
        img.save(os.path.join(od, f"{o['name']}.webp"), quality=93)
    print(od, len(layout.objects(d)), '個物件')


# ── 合成預覽與總覽 ──
def review(a):
    d = layout.load(a); W, Hh = d['map']['w'], d['map']['h']; gp = os.path.join(G, f'assets/maps/{a}_ground.webp')
    g = Image.open(gp).convert('RGBA'); S = g.width / W
    canvas = g.copy()
    for o in sorted(layout.objects(d), key=lambda o: (o['sort'], 0)):
        f = os.path.join(G, f"assets/objects/{a}/{o['name']}.webp")
        if not os.path.exists(f): continue
        fx, fy, fw, fh = o['frame']; im = Image.open(f).convert('RGBA').resize((round(fw * S), round(fh * S)), Image.LANCZOS)
        canvas.alpha_composite(im, (round(fx * S), round(fy * S)))
    os.makedirs(os.path.join(H, 'check/maps-review'), exist_ok=True)
    canvas.convert('RGB').save(os.path.join(H, f'check/maps-review/{a}-composed.jpg'), quality=88)
    fs = sorted(glob.glob(os.path.join(RAW, f'obj-{a}-*.png'))); fs = [f for f in fs if '-try' not in f]; tiles = []
    for f in fs:
        im = Image.open(f).convert('RGB'); im.thumbnail((300, 300)); tiles.append(im)
    cols = 5; out = Image.new('RGB', (cols * 300, max(1, (len(tiles) + cols - 1) // cols) * 300), 'white')
    for i, t in enumerate(tiles): out.paste(t, ((i % cols) * 300, (i // cols) * 300))
    out.save(os.path.join(H, f'check/maps-review/{a}-objects.jpg'), quality=82)
    print('review ok', a)


def audit(a):
    """驗收表：每種物件的原圖閘門（傾斜、貼邊、比例、不透明）＋ 切完後每個物件實際佔圖框的比例。"""
    d = layout.load(a); rows = []; seen = set(); bad = 0
    print(f'{"種類":12}{"結果":4} 下緣傾斜 上緣傾斜 比例/要   不透明  備註')
    for o in layout.objects(d):
        t = type_of(o)
        if t in seen: continue
        seen.add(t); r = check_raw(raw_path(a, t), t); m = r['m']
        print(f'{t:12}{"過" if r["ok"] else "不過":4} {m.get("bottom_deg", "-"):>7} {m.get("top_deg", "-"):>7} {m.get("aspect", "-")}/{m.get("want", "-")} {m.get("opaque", "-"):>7}  {"；".join(r["problems"])}')
        bad += not r['ok']
    print('— 切完後每個物件佔圖框 —')
    for o in layout.objects(d):
        f = os.path.join(G, f"assets/objects/{a}/{o['name']}.webp")
        if not os.path.exists(f): print(f"  ✗ 缺 {o['name']}"); bad += 1; continue
        im = Image.open(f).convert('RGBA'); bb = im.getbbox(); W, Hh = im.size
        if not bb: print(f"  ✗ {o['name']} 全透明"); bad += 1; continue
        fw, fh = o['frame'][2], o['frame'][3]; vis = o['vis'][3]
        wr, hr = (bb[2] - bb[0]) / W, (bb[3] - bb[1]) / (Hh * vis / fh)
        flag = '' if wr > .5 and hr > .45 else '  ← 偏小'
        flag += '' if bb[3] >= Hh * .97 or (o['frame'][3] - vis) else '  ← 下緣沒貼齊'
        print(f"  {o['name']:8} 框 {fw}×{fh}  寬佔 {wr:.0%} 高佔 {hr:.0%}{flag}")
        if flag: bad += 1
    print('不合格', bad)


def realign(a, raw=None):
    """用已經生成的原圖重新對位並存檔（改了對位判斷、不想重產時用）；raw 預設用 ground 紀錄裡分數最高的那張"""
    d = layout.load(a); W = d['map']['w']; S2 = 1536 // W
    cands = [raw] if raw else sorted(glob.glob(os.path.join(RAW, f'ground-{a}*.png')))
    cands = [c for c in cands if 'layout' not in c]; best = None
    for c in cands:
        canvas, iou, how = align_ground(c, d, S2); sok, sres = stairs_ok(canvas, d, S2); fixed = []
        if not sok:
            c2, fixed = fix_stairs(canvas, d, S2); sok2, sres2 = stairs_ok(c2, d, S2)
            if sok2: canvas, sok, sres = c2, True, sres2
        print(os.path.basename(c), 'IoU', round(iou, 3), f'({how})', '樓梯立面', sres, '過' if sok else '不過', ('；補貼：' + '、'.join(fixed)) if fixed else '')
        sc = iou + (1 if sok else 0) + (1 if no_stairs_ok(canvas, d, S2) else 0)
        if best is None or sc > best[1]: best = (canvas, sc, c, iou, sok)
    best[0].save(os.path.join(G, f'assets/maps/{a}_ground.webp'), quality=92)
    print('採用', os.path.basename(best[2]), 'IoU', round(best[3], 3), '樓梯', '過' if best[4] else '不過')


if __name__ == '__main__':
    cmd, a, *rest = sys.argv[1:]
    if cmd == 'gen': gen(a, [r for r in rest if not r.startswith('--')], '--redo' in rest)
    elif cmd == 'all':
        if not os.path.exists(anchor(a)): style(a)
        with ThreadPoolExecutor(2) as ex: list(ex.map(lambda f: f(), [lambda: ground(a), lambda: gen(a)]))
        cut(a); review(a)
    else: globals()[cmd](a)
