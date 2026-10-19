#!/usr/bin/env python3
"""地圖靜態檢查（從 build 出來的 project.json 讀，不靠設計檔）：
  1. 每張地圖剛好一位主角、事件都在地圖內、每格最多一個事件、事件 id 合法。
  2. 每個會動作的事件（NPC、調查點、門）所在格不是牆，而且從主角起點走得到。
  3. 導引（guidance）指向的事件，目標格走得到（作者回報「走不過去」的根因：門開在牆格上）。
  4. 跳轉（jump arrive）落點：不是牆、走得到、而且不是剛好落在另一個會立刻觸發的 touch 事件上（會彈回去）。
  5. 自由圖片：每張圖的檔案都存在。
python3 tests/map_check.py [dist/project.json]
"""
import json, os, re, sys

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(R, 'dist/project.json')
P = json.load(open(path, encoding='utf-8')); P = P.get('project', P)
nodes = {n['id']: n for n in P['boards'][0]['nodes']}
maps = {}
for nid, n in nodes.items():
    d = n['data']
    if d.get('pluginCardId') == 'map':
        maps[nid] = json.loads(d['pluginValues']['map'])
bad = []


def walls_of(m):
    W = m['width']; t = m['layers'][0]['tiles']
    return {(i % W, i // W) for i, v in enumerate(t) if v}


def reach(m, start, walls):
    W, H = m['width'], m['height']; seen = {start}; st = [start]
    while st:
        x, y = st.pop()
        for c in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= c[0] < W and 0 <= c[1] < H and c not in walls and c not in seen:
                seen.add(c); st.append(c)
    return seen


def jumps(actions):
    for a in actions or []:
        if a.get('kind') == 'jump': yield a
        for k in ('if',):
            if k in a:
                yield from jumps(a[k].get('then')); yield from jumps(a[k].get('else'))


for mid, m in maps.items():
    W, H = m['width'], m['height']; wl = walls_of(m); evs = m['events']
    heroes = [e for e in evs if e.get('actor') == 'player']
    if len(heroes) != 1: bad.append(f'{mid}: 主角 {len(heroes)} 位')
    cells = {}
    for e in evs:
        if not (0 <= e['x'] < W and 0 <= e['y'] < H): bad.append(f"{mid}: 事件 {e['id']} 在地圖外")
        if (e['x'], e['y']) in cells: bad.append(f"{mid}: {e['id']} 跟 {cells[(e['x'], e['y'])]} 同一格")
        cells[(e['x'], e['y'])] = e['id']
        if not re.fullmatch(r'[A-Za-z0-9_-]+', e['id']): bad.append(f"{mid}: 事件 id 不合法 {e['id']}")
        f = e.get('free')
        if f:
            u = f['url'].replace('/files/', '')
            if not os.path.exists(os.path.join(R, 'dist', u)) and not os.path.exists(os.path.join(R, u)): bad.append(f"{mid}: 圖不存在 {f['url']}")
    hero = (heroes[0]['x'], heroes[0]['y']); ok = reach(m, hero, wl)
    byid = {e['id']: e for e in evs}
    for e in evs:
        if e.get('actor') == 'player' or e.get('free') or not e.get('actions'): continue
        c = (e['x'], e['y'])
        if e.get('actor') == 'npc':
            near = any((c[0] + dx, c[1] + dy) in ok for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            if not near: bad.append(f"{mid}: NPC {e['id']} {c} 旁邊沒有走得到的格子")
        elif c in wl or c not in ok:
            bad.append(f"{mid}: 事件 {e['id']} {c} {'在牆上' if c in wl else '從主角起點走不到'}")
    for g in m.get('guidance', []):
        e = byid.get(g['eventId'])
        if not e: bad.append(f"{mid}: 導引指向不存在的事件 {g['eventId']}"); continue
        c = (e['x'], e['y'])
        okc = c in ok if e.get('actor') != 'npc' else any((c[0] + dx, c[1] + dy) in ok for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        if not okc: bad.append(f"{mid}: 導引『{g['text']}』的目標 {g['eventId']} {c} 走不到")
    for e in evs:
        for j in jumps(e.get('actions')):
            tgt = j.get('cardId'); arr = j.get('arrive')
            if tgt in maps and arr:
                tm = maps[tgt]; twl = walls_of(tm); th = [x for x in tm['events'] if x.get('actor') == 'player'][0]
                c = (arr['x'], arr['y'])
                if c in twl: bad.append(f"{mid}→{tgt}: arrive {c} 在牆上")
                elif c not in reach(tm, (th['x'], th['y']), twl): bad.append(f"{mid}→{tgt}: arrive {c} 走不到")
                hit = [x['id'] for x in tm['events'] if (x['x'], x['y']) == c and x.get('trigger') == 'touch']
                if hit: bad.append(f"{mid}→{tgt}: arrive {c} 剛好落在 touch 事件 {hit}，會彈回去")
    print(f'{mid}: {W}x{H}，事件 {len(evs)}，走得到 {len(ok)} 格，導引 {len(m.get("guidance", []))}')
print('不合格', len(bad))
for b in bad: print(' ✗', b)
sys.exit(1 if bad else 0)
