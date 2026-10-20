"""五張地圖（design/地圖.md、作者 2026-10-19：用 RPG 做天黑之前的探索；2026-10-21 後台拆成各自平的二樓與一樓，用樓梯口傳送）。
化妝間（主地圖）→ 後台二樓（鋼琴）→ 樓梯 → 後台一樓 → 觀眾席（從側台門進）／後門巷子（從後門出）。
地圖事件調查物件 → 播劇本卡（回憶是連續 CG 的劇情卡）→ 回到地圖。四條線都走過、回到化妝間 → 天黑分歧。
"""
from mapkit import *
import layout

ROOT = layout.ROOT
W = lambda n: walker(f'/files/assets/art/walk/walk-{n}.webp')


def _urls(a):
    d = layout.load(a)
    ground = f'/files/assets/maps/{a}_ground.webp'
    urls = {o['name']: f"/files/assets/objects/{a}/{o['name']}.webp" for o in layout.objects(d)
            if (ROOT / f"assets/objects/{a}/{o['name']}.webp").exists()}
    return d, ground, urls


def _map(mid, title, a, events, guidance, env):
    d, ground, urls = _urls(a)
    evs = events + [dict(e, id=e['id'].replace(f"obj-{d['map']['id']}", f'obj-{mid}')) for e in layout.events(d, urls, taken=[(e['x'], e['y']) for e in events])]
    return map_node(mid, title, map_dict(title, d['map']['w'], d['map']['h'], ground, layout.walls(d), evs, guidance, env))


def _env(tint, strength, lights, dark=0.15):
    return {'weather': 'clear', 'intensity': 0, 'darkness': dark, 'shake': 0,
            'lights': [dict(zip(('id', 'x', 'y', 'radius', 'color'), l[:5]), flicker=bool(l[5])) for l in lights],   # flicker 是布林，給數字整張地圖讀不了
            'ambience': {'tint': tint, 'tintStrength': strength, 'vignette': 0.4, 'particles': 'motes', 'density': 0.08}}


def P(a):
    return {k: tuple(v) for k, v in layout.load(a)['points'].items()}


def hero(x, y, d='up'):
    return ev('hero', x, y, actor='player', direction=d, sprite=W('yu-47'), actorId='yu')


def look(eid, x, y, label, actions, conds=None):
    return ev(eid, x, y, name=label, marker={'label': label, 'kind': 'quest'}, conditions=conds or [], actions=actions)


def door(eid, cells, target, arrive, name='門'):
    """一扇 2 格寬的門（或樓梯口）：前面兩格都是觸發點（id 與 id-b）；arrive 要落在門前、不能踩到觸發格"""
    return [ev(eid if i == 0 else f'{eid}-b', x, y, name=name, trigger='touch', actions=[jump(target, arrive=arrive)]) for i, (x, y) in enumerate(cells)]


def G(text, eid, conds):
    return {'text': text, 'eventId': eid, 'conditions': conds}


ALL_DONE = [cond('letter', True), cond('zhou', True), cond('seat', True), cond('tao', True)]


def dressing():
    p = P('dressing')
    events = [
        hero(*p['hero_start']),
        npc('cheng', *p['cheng'], W('cheng-45'), direction='left', name='先生', actions=[card('m_dressing_intro')]),
        ev('intro', 2, 10, trigger='auto', once=True, actions=[card('m_dressing_intro')]),
        look('window', *p['window'], '窗', [card('m_window')]),
        look('mirror', *p['mirror'], '鏡子角落的照片', [card('m_mirror'), card('mem2_monitor'), card('mem2_rose'), card('mem2_europe'), card('mem2_stage')]),
        look('notebook', *p['notebook'], '筆記本', [card('m_notebook'), card('mem3_forget')]),
        look('rose', *p['case'], '化妝箱', [card('m_rose_dry'), card('mem1_door')]),
        look('jewel', *p['jewel'], '首飾盒', [card('m_jewelry'), setv('knob', True)], [cond('knob', False)]),
        look('radio', *p['radio'], '阿爸的收音機',
             [branch([cond('knob', True)],
                     [card('m_radio_on'), card('m_letter'), card('mem4_clinic'), card('mem4_letter'), card('mem4_name'), card('m_note'), setv('letter', True)],
                     [card('m_radio')])], [cond('letter', False)]),
        *door('door', [p['door'], p['door_b']], 'm-backstage-2f', {'x': 4, 'y': 4, 'direction': 'down'}),
        # 四條線都走過、回到化妝間：天黑
        ev('dark', 3, 10, trigger='auto', once=True, conditions=ALL_DONE, actions=[jump('branch_dark')]),
    ]
    guide = [G('收音機旁邊的東西', 'radio', [cond('letter', False)]), G('走廊盡頭的鋼琴聲', 'door', [cond('zhou', False)]),
             G('天黑之前，回到化妝間', 'dark', ALL_DONE)]
    return _map('m-dressing', '化妝間', 'dressing', events, guide,
                _env('#ff9a4d', 0.22, [('lamp-mirror', 3, 4, 4, '#ffd59a', 0.05), ('sunset', 8, 3, 7, '#ff8a3d', 0)]))


def backstage2f():
    p = P('backstage2f')
    events = [
        hero(*p['hero_start'], 'down'),   # 每張地圖都要剛好一位主角；實際位置由跳轉的 arrive 決定
        npc('zhou', *p['piano'], W('zhou'), direction='up', name='彈琴的人', conditions=[cond('zhou', False)],
            actions=[card('m_corridor'), setv('zhou', True)]),
        *door('to-dressing', [p['to_dressing'], p['to_dressing_b']], 'm-dressing', {'x': 15, 'y': 4, 'direction': 'down'}),
        *door('stairs-down', [p['stairs_down'], p['stairs_down_b']], 'm-backstage', {'x': 15, 'y': 8, 'direction': 'down'}, name='階梯：下樓'),
    ]
    guide = [G('彈琴的人', 'zhou', [cond('zhou', False)]),
             G('下樓：階梯走到底', 'stairs-down', [cond('zhou', True), cond('seat', False)]),   # 分兩條：導引條件只能 AND，兩條互斥
             G('下樓：階梯走到底', 'stairs-down', [cond('zhou', True), cond('seat', True), cond('tao', False)]),
             G('回化妝間', 'to-dressing', ALL_DONE)]
    return _map('m-backstage-2f', '後台二樓', 'backstage2f', events, guide,
                _env('#ffb070', 0.18, [('lamp-door', 4, 5, 4, '#ffcf8a', 0.06), ('lamp-piano', 9, 5, 4, '#ffcf8a', 0.06), ('lamp-stair', 15, 5, 3, '#ffd59a', 0.04)]))


def backstage():
    p = P('backstage')
    events = [
        hero(*p['hero_start'], 'down'),
        *door('to-stage', [p['stage_door'], p['stage_door_b']], 'm-auditorium', {'x': 4, 'y': 4, 'direction': 'down'}),
        *door('to-alley', [p['back_door'], p['back_door_b']], 'm-alley', {'x': 4, 'y': 4, 'direction': 'down'}),
        *door('stairs-up', [p['stairs_up'], p['stairs_up_b']], 'm-backstage-2f', {'x': 15, 'y': 8, 'direction': 'down'}, name='階梯：上樓'),
    ]
    guide = [G('側台門：通觀眾席', 'to-stage', [cond('seat', False)]), G('後門：通巷子', 'to-alley', [cond('tao', False)]),
             G('上樓：階梯走到底', 'stairs-up', ALL_DONE)]
    return _map('m-backstage', '後台一樓', 'backstage', events, guide,
                _env('#ffb070', 0.18, [('lamp-stage', 4, 5, 4, '#ffcf8a', 0.06), ('lamp-back', 11, 5, 4, '#ffcf8a', 0.06), ('lamp-stair', 15, 5, 3, '#ffd59a', 0.04)]))


def auditorium():
    p = P('auditorium')
    events = [
        hero(*p['hero_start'], 'down'),
        npc('azhe', *p['azhe'], W('azhe'), direction='up', name='阿哲', actions=[say('阿哲：余老師，聲音我會顧好。')]),
        look('seat314', *p['seat314'], '三排十四號', [card('m_auditorium'), setv('seat', True)], [cond('seat', False)]),
        *door('to-backstage', [p['side_door'], p['side_door_b']], 'm-backstage', {'x': 4, 'y': 4, 'direction': 'down'}),
    ]
    guide = [G('三排十四號', 'seat314', [cond('seat', False)]), G('回後台', 'to-backstage', [cond('seat', True)])]
    return _map('m-auditorium', '觀眾席', 'auditorium', events, guide,
                _env('#ff9a5a', 0.15, [('stage', 12, 4, 9, '#ffd59a', 0.03)], dark=0.25))


def alley():
    p = P('alley')
    events = [
        hero(*p['hero_start'], 'down'),
        npc('tao', *p['tao'], W('tao-73'), direction='left', name='阿桃姨', conditions=[cond('tao', False)],
            actions=[card('m_alley'), card('mem0_market'), setv('tao', True)]),
        *door('to-backstage', [p['door'], p['door_b']], 'm-backstage', {'x': 11, 'y': 4, 'direction': 'down'}),
    ]
    guide = [G('有人在叫你', 'tao', [cond('tao', False)]), G('回後台', 'to-backstage', [cond('tao', True)])]
    return _map('m-alley', '後門巷子', 'alley', events, guide,
                _env('#ff8a3d', 0.25, [('market', 16, 6, 6, '#ffb060', 0.08)], dark=0.3))


def all_maps():
    return [dressing(), backstage2f(), backstage(), auditorium(), alley()]
