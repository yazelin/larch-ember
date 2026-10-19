"""分層地圖設計檔（art/objects_<地圖>.yaml）→ 物件清單、碰撞、自由圖片事件。
遵循《正式地圖開工前：先用色塊確認 RPG 的遮擋層次》與《十一分鐘》規範。
引擎前後順序：自由圖片用 free.y+free.h-1、人用自己站的列，小的先畫；同值圖片先畫（人在上面）。
所以每個物件的圖框下緣放在佔地最下一列的下緣：人站在南邊一列畫在上面、站在圖框裡北邊的被蓋住。
碰撞照佔地格（gap 除外），不用 free.block。
"""
import pathlib, yaml
from mapkit import ev

ROOT = pathlib.Path(__file__).resolve().parent.parent


def load(a):
    return yaml.safe_load((ROOT / f'art/objects_{a}.yaml').read_text(encoding='utf-8'))


def objects(d):
    """展開 column（直的一格一段，各自排序）。每個 → foot、frame、sort、gapset"""
    out = []
    for o in d['objects']:
        if 'column' in o:
            x, y0, n = o['column']
            out += [dict(o, name=f"{o['name']}{i + 1}", foot=[x, y0 + i, 1, 1]) for i in range(n)]
        else:
            out.append(dict(o))
    for o in out:
        x, y, w, h = o['foot']
        if 'frame' in o:
            o['frame'] = tuple(o['frame'])
        else:
            up, side = o.get('up', 0), o.get('side', 0)
            o['frame'] = (x - side, y - up, w + 2 * side, h + up)
        o['sort'] = o.get('sort', y + h - 1)
        o['gapset'] = {tuple(c) for c in o.get('gap', [])}
    return out


def foot_cells(o):
    x, y, w, h = o['foot']
    return {(i, j) for j in range(y, y + h) for i in range(x, x + w)} - o['gapset']


def walls(d):
    out = set()
    for g in d['ground']:
        if g['kind'] == 'border':
            for x, y, w, h in g['rects']:
                out |= {(i, j) for j in range(y, y + h) for i in range(x, x + w)}
    for o in objects(d):
        out |= foot_cells(o)
    return out


def hold_cells(d):
    """放自由圖片事件的格子：地圖最外一圈（邊界，走不到）"""
    W, H = d['map']['w'], d['map']['h']
    return [(0, y) for y in range(H)] + [(W - 1, y) for y in range(H)] + [(x, 0) for x in range(1, W - 1)] + [(x, H - 1) for x in range(1, W - 1)]


def events(d, urls, conds=lambda name: []):
    """物件 → 自由圖片事件；urls：物件名 → 圖網址；conds：物件名 → 出現條件"""
    obs = objects(d); hold = hold_cells(d)
    assert len(hold) >= len(obs), f'物件 {len(obs)} 個，放事件的格子只有 {len(hold)} 個'
    return [ev(f'obj-{d["map"]["id"]}-{i}', *hold[i], name=o['name'],
               conditions=conds(o['name']),
               free={'url': urls[o['name']], 'x': o['frame'][0], 'y': o['frame'][1], 'w': o['frame'][2], 'h': o['frame'][3]})
            for i, o in enumerate(obs) if urls.get(o['name'])]


def reachable(d, start):
    """從 start 洪水填充能走到的格子"""
    W, H = d['map']['w'], d['map']['h']; wl = walls(d); seen = {tuple(start)}; st = [tuple(start)]
    while st:
        x, y = st.pop()
        for c in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= c[0] < W and 0 <= c[1] < H and c not in wl and c not in seen:
                seen.add(c); st.append(c)
    return seen


def check(d):
    """佔地不重疊、圖框在地圖內、物件不被整個蓋掉、事件點不在牆上而且從起點走得到"""
    W, H = d['map']['w'], d['map']['h']; obs = objects(d); errs = []; seen = {}
    for o in obs:
        fx, fy, fw, fh = o['frame']
        if fx < 0 or fy < 0 or fx + fw > W or fy + fh > H:
            errs.append(f"{o['name']} 圖框出界 {o['frame']}")
        for c in foot_cells(o):
            if c in seen:
                errs.append(f"{o['name']} 跟 {seen[c]} 佔地重疊 {c}")
            seen[c] = o['name']
    for o in obs:
        ox, oy, ow, oh = o['frame']
        for q in obs:
            if q is o or q['sort'] <= o['sort']: continue
            qx, qy, qw, qh = q['frame']
            if qx <= ox and qy <= oy and ox + ow <= qx + qw and oy + oh <= qy + qh:
                errs.append(f"{o['name']} 整個落在 {q['name']} 的圖框裡，會被完全蓋掉")
    wl = walls(d); pts = d['points']; ok = reachable(d, pts['hero_start'])
    for k, p in pts.items():
        if tuple(p) in wl:
            errs.append(f'事件點 {k} {p} 在牆上')
        elif tuple(p) not in ok:
            errs.append(f'事件點 {k} {p} 從起點走不到')
    return errs
