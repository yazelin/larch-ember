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
    'backstage': 'the backstage of an old 1950s Tainan theater: warm tungsten bulbs, worn cream plaster, dark wood, old red brick, concrete floor, a wooden staircase',
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
    'd_door': (2, 3, 1, 'the same kind of wall section (cream plaster, dark wood wainscot) with a closed old dark-brown wooden door with a brass handle and a small blank brass plate, in a plain wooden door frame, centered; plain wall at the left and right edges', 'seg', 'green', True),
    'd_vanity': (4, 3, 1, 'an old theater dressing table seen from the front: a wide wooden table with drawers, above it a large rectangular mirror framed by evenly spaced round warm light bulbs; on the table an open notebook and a black wristwatch; a small photo tucked into the corner of the mirror frame; the whole piece is symmetrical', 'obj', 'green', True),
    'd_jewel': (1, 2, 1, 'a small round wooden side table with a carved wooden jewelry box on top', 'obj', 'green', False),
    'd_bench': (4, 2, 1, 'a long low wooden bench seen from the front with a faded red velvet cushion on the seat, straight and level', 'obj', 'green', True),
    'd_radio': (2, 2, 1, 'a small plain wooden side table with an old cream-colored plastic portable transistor radio on top, its corners worn white, the tuning shaft bare without a knob', 'obj', 'green', True),
    'd_chair': (1, 2, 1, 'an old wooden chair with a faded red velvet seat, seen from behind (the chair back toward the camera)', 'obj', 'green', False),
    'd_case': (2, 2, 1, 'an open black leather makeup case sitting on the floor, its trays showing neatly arranged brushes and lipsticks, a small glass box in the bottom tray', 'obj', 'green', True),
    'd_rack': (1, 4, 3, 'a narrow metal clothes rack with one navy jacket hanging on it, standing against a wall, drawn as a tall narrow object', 'obj', 'green', False),
    'd_sofa': (6, 2, 1, 'a long sofa seen from behind (its back toward the camera): a tall straight faded red velvet backrest with gold buttons, wooden feet, straight and level', 'obj', 'green', True),
    # 後台
    'b_wall': (11, 3, 1, 'a plain section of the back wall of an old theater backstage corridor: worn cream plaster with a few peeling patches, a dark brown wooden skirting, a faded painted stripe; completely plain, no doors, no windows, nothing hanging', 'strip', 'green', True),
    'b_door': (2, 3, 1, 'the same kind of wall section (worn cream plaster above, a dark brown wooden wainscot panelling band along the whole bottom third, dark skirting) with a closed old wooden dressing-room door and a small blank brass plate, in a plain frame, centered; the door goes all the way down to the bottom edge and the wainscot panelling continues on both sides down to the bottom edge; NO floor visible anywhere, plain wall at the left and right edges', 'seg', 'green', True),
    'b_piano': (3, 2, 1, 'an old black upright piano seen from the front, a small brass lamp on top', 'obj', 'green', True),
    'b_rail_e': (1, 4, 3, 'a short dark wooden banister rail with turned balusters standing along a balcony edge, drawn as a tall narrow object', 'obj', 'green', False),
    'b_balcony': (15, 3, 2, 'the front edge of an indoor second-floor balcony seen from the south: an ornate black cast-iron railing along the top, below it a full-storey-high old red brick wall face with four evenly spaced brass wall lamps glowing warm; runs straight across', 'strip', 'green', True),
    'b_cap': (2, 1, 1, 'a short flat-topped section of an old masonry wall, plaster and brick, seen from the south', 'seg', 'green', True),
    'b_divider': (1, 10, 8, 'one thin plaster-and-brick partition wall running straight north-south away from the viewer, so on screen it is one long narrow vertical strip: its long thin top edge runs from the top of the image downward, and at the bottom end you see the wall south-facing end face; about 1 cell wide and 10 cells tall', 'obj', 'green', True),
    'b_turn': (7, 3, 2, 'a wide masonry stairwell wall front seen from the south, plaster and old brick like the backstage back wall, COMPLETELY OPAQUE with no see-through gaps; near the left third a dark rounded archway whose interior is solid dark brown-black (opaque, nothing visible through it); a dark wooden lintel; a brass wall lamp; fills the full width', 'seg', 'green', True),
    'b_upper': (4, 5, 2, 'a thick masonry wall pier of the stairwell seen from the south, plaster and old brick, 4 cells wide and 5 cells tall, COMPLETELY OPAQUE and solid with no gaps; a heavy dark wooden beam across its bottom edge and a small hanging brass lamp near the top', 'seg', 'green', True),
    'b_cases': (2, 2, 1, 'two stacked black stage flight cases with metal corners', 'obj', 'green', True),
    'b_table': (3, 2, 1, 'a sturdy wooden workbench seen from the front with a desk lamp, a few sandbags and a roll of tape on top', 'obj', 'green', True),
    'b_sidedoor': (1, 3, 2, 'a tall narrow arched doorway with a dark wooden frame in a side wall, the opening glowing warm with a hint of deep red curtain beyond, drawn as a tall narrow object', 'obj', 'green', False),
    'b_backdoor': (1, 3, 2, 'a tall narrow dark steel back door in a side wall standing slightly open onto orange evening light, a small unlit exit lamp above (no text), drawn as a tall narrow object', 'obj', 'green', False),
    # 觀眾席
    'a_curtain': (6, 3, 1, 'a section of deep red velvet stage curtain with evenly spaced vertical folds and a gold fringe along the bottom hem', 'strip', 'green', True),
    'a_lip': (8, 2, 1, 'the front edge of an old wooden stage seen from the front: a wooden stage skirt with gold trim along the top edge and evenly spaced small footlights', 'strip', 'green', True),
    'a_piano': (3, 2, 1, 'a black grand piano with its lid closed, seen from the front', 'obj', 'green', True),
    'a_mic': (1, 2, 1, 'a straight black microphone stand with a microphone on top', 'obj', 'green', False),
    'a_seat6': (6, 2, 1, 'one row of exactly 6 old red velvet theater seats in a perfectly straight row seen from the front: tall seat backs, gold-trimmed armrests between the seats, six identical evenly spaced seats', 'obj', 'green', True),
    'a_seat8': (8, 2, 1, 'one row of exactly 8 old red velvet theater seats in a perfectly straight row seen from the front: tall seat backs, gold-trimmed armrests between the seats, eight identical evenly spaced seats', 'obj', 'green', True),
    'a_seat8rose': (8, 2, 1, 'exactly the same row of 8 red velvet theater seats as image 2, but the rightmost seat has a single deep red rose lying across its seat cushion', 'obj', 'green', True),
    'a_desk': (4, 2, 1, 'a sound mixing desk seen from the front with rows of faders and small glowing lights on a wooden stand', 'obj', 'green', True),
    'a_sidedoor': (1, 3, 2, 'a tall narrow stage-side doorway with a dark wooden frame in a side wall, a heavy red curtain half drawn, warm light beyond, drawn as a tall narrow object', 'obj', 'green', False),
    # 巷子
    'l_wall': (8, 3, 1, 'a plain section of weathered red brick wall of the back of an old theater: straight mortar lines, dark water stains, a low concrete base; completely plain, no doors, no windows, nothing hanging', 'strip', 'green', True),
    'l_door': (2, 3, 1, 'the same red brick wall section with a heavy dark-green iron stage door, closed, a warm yellow bulb in a wire cage above it, a worn concrete step; plain brick at the left and right edges', 'seg', 'green', True),
    'l_shop': (4, 3, 1, 'the same red brick wall as a market-side shopfront: a striped red-and-white canvas awning, a row of glowing orange paper lanterns hanging under it, a few wooden produce crates below, warm light', 'seg', 'green', True),
    'l_scooters': (4, 2, 1, 'two parked scooters side by side seen from the side, both facing left, one white and one red, parallel and upright', 'obj', 'green', True),
    'l_crates': (1, 2, 1, 'two stacked red plastic produce baskets', 'obj', 'green', False),
}
OPAQUE = {'b_turn', 'b_upper', 'b_cap', 'd_wall', 'b_wall', 'l_wall', 'a_curtain'}   # 整面要不透明（遮擋物與牆）
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
    if mode == 'strip':
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
        ys2, xs2 = np.where(mm); gx0, gx1, gy0, gy1 = xs2.min(), xs2.max() + 1, ys2.min(), ys2.max() + 1
        border = tuple(int(v) for v in np.asarray(im)[~mm].mean(0)) if (~mm).any() else (30, 30, 30)
        crop = im.crop((int(gx0), int(gy0), int(gx1), int(gy1))).resize(((wx1 - wx0) * S, (wy1 - wy0) * S), Image.LANCZOS)
        canvas = Image.new('RGB', (W * S, Hh * S), border); canvas.paste(crop, (int(wx0) * S, int(wy0) * S))
        got = floor_mask(canvas, textured).reshape(Hh, S, W, S).mean(axis=(1, 3)) > .5
        iou = float((got & want).sum() / max(1, (got | want).sum()))
        if best is None or iou > best[1]: best = (canvas, iou, '亮度＋紋理' if textured else '亮度顏色')
    return best


def stairs_ok(canvas, d, S):
    """樓梯地面閘門：每一段 kind=stairs 的區域，縱向每一格至少要有約一條橫向踏階邊緣（亮度的縱向梯度出現週期性峰值）。回傳 (全過, 各段峰值數)。"""
    L = np.asarray(canvas.convert('L')).astype(float); res = []; ok = True
    for g in d['ground']:
        if g['kind'] != 'stairs': continue
        for x, y, w, h in g['rects']:
            if h < 3: continue   # 舞台前兩小段階梯（1 格）不驗
            sub = L[y * S:(y + h) * S, x * S + S // 4:(x + w) * S - S // 4]
            prof = np.abs(np.diff(sub, axis=0)).mean(1)
            thr = prof.mean() + 1.0 * prof.std(); peaks = 0; last = -99
            for i in range(1, len(prof) - 1):
                if prof[i] > thr and prof[i] >= prof[i - 1] and prof[i] >= prof[i + 1] and i - last > S * .3: peaks += 1; last = i
            res.append((g['name'], h, peaks)); ok &= peaks >= max(3, int(h * .8))
    return ok, res


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
         f"{CAM}. Draw ONLY the floor surfaces and the dark wall areas: no furniture, no walls rising up, no windows, no doors, no people, no objects at all, no text.")
    out = os.path.join(RAW, f'ground-{a}.png'); S2 = 1536 // W; best = None
    for k in range(3):
        o = out if k == 0 else out.replace('.png', f'-try{k + 1}.png')
        try: codex11.gen(p + (' IMPORTANT: keep the floor rectangle exactly where image 1 puts it, with the same thick dark band at the top and thin band at the bottom. Both wooden staircases must show clearly separated steps: many distinct horizontal treads with a dark riser line between each, one step about every half cell.' if k else ''), o, [lay, anchor(a)], size='1536x1024')
        except Exception as e: print('地面第', k + 1, '次生成失敗', repr(e)[:120], flush=True); continue
        canvas, iou, how = align_ground(o, d, S2); sok, sres = stairs_ok(canvas, d, S2)
        print('地面第', k + 1, '次 IoU', round(iou, 3), '樓梯踏階', sres, '過' if sok else '不過', flush=True)
        good = iou >= .92 and sok
        log(dict(map=a, type='ground', ok=good, iou=round(iou, 3), stairs=sres, try_=k + 1))
        score = iou + (1 if sok else 0)
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


def cut(a):
    d = layout.load(a); od = os.path.join(G, f'assets/objects/{a}'); os.makedirs(od, exist_ok=True)
    for f in glob.glob(os.path.join(od, '*')): os.remove(f)
    cache, alt = {}, {}
    for o in layout.objects(d):
        t = type_of(o); fx, fy, fw, fh = o['vis']; pad = o['frame'][3] - fh; tw, th, _, _, mode, _, _ = TYPES[t]
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
        canvas, iou, how = align_ground(c, d, S2); sok, sres = stairs_ok(canvas, d, S2)
        print(os.path.basename(c), 'IoU', round(iou, 3), f'({how})', '樓梯', sres, '過' if sok else '不過')
        sc = iou + (1 if sok else 0)
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
