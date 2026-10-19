"""四張地圖（design/地圖.md、作者 2026-10-19：用 RPG 做天黑之前的探索，後台一張圖看得到二樓與一樓）。
化妝間（主地圖）→ 後台（二樓陽台＋樓梯＋一樓）→ 觀眾席（一樓，從側台門進）／後門巷子（一樓，從後門出）。
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
        ev('door', *p['door'], name='門', trigger='touch', actions=[jump('m-backstage', arrive={'x': 4, 'y': 4, 'direction': 'down'})]),
        # 四條線都走過、回到化妝間：天黑
        ev('dark', 3, 10, trigger='auto', once=True, conditions=ALL_DONE, actions=[jump('branch_dark')]),
    ]
    guide = [G('收音機旁邊的東西', 'radio', [cond('letter', False)]), G('走廊盡頭的鋼琴聲', 'door', [cond('zhou', False)]),
             G('天黑之前，回到化妝間', 'dark', ALL_DONE)]
    return _map('m-dressing', '化妝間', 'dressing', events, guide,
                _env('#ff9a4d', 0.22, [('lamp-mirror', 3, 4, 4, '#ffd59a', 0.05), ('sunset', 8, 3, 7, '#ff8a3d', 0)]))


def backstage():
    p = P('backstage')
    events = [
        hero(*p['hero_start'], 'down'),   # 每張地圖都要剛好一位主角；實際位置由跳轉的 arrive 決定
        npc('zhou', *p['piano'], W('zhou'), direction='up', name='彈琴的人', conditions=[cond('zhou', False)],
            actions=[card('m_corridor'), setv('zhou', True)]),
        ev('to-dressing', *p['to_dressing'], name='化妝間', trigger='touch', actions=[jump('m-dressing', arrive={'x': 15, 'y': 4, 'direction': 'down'})]),
        ev('to-stage', *p['stage_door'], name='側台門', trigger='touch', actions=[jump('m-auditorium', arrive={'x': 2, 'y': 5, 'direction': 'right'})]),
        ev('to-alley', *p['back_door'], name='後門', trigger='touch', actions=[jump('m-alley', arrive={'x': 4, 'y': 4, 'direction': 'down'})]),
    ]
    guide = [G('彈琴的人', 'zhou', [cond('zhou', False)]), G('側台門：通觀眾席', 'to-stage', [cond('seat', False)]),
             G('後門：通巷子', 'to-alley', [cond('tao', False)]), G('回化妝間', 'to-dressing', ALL_DONE)]
    return _map('m-backstage', '後台', 'backstage', events, guide,
                _env('#ffb070', 0.18, [('wall-lamp-a', 4, 9, 4, '#ffcf8a', 0.06), ('wall-lamp-b', 11, 9, 4, '#ffcf8a', 0.06), ('stair-lamp', 18, 5, 3, '#ffd59a', 0.04)]))


def auditorium():
    p = P('auditorium')
    events = [
        hero(*p['hero_start'], 'right'),
        npc('azhe', *p['azhe'], W('azhe'), direction='up', name='阿哲', actions=[say('阿哲：余老師，聲音我會顧好。')]),
        look('seat314', *p['seat314'], '三排十四號', [card('m_auditorium'), setv('seat', True)], [cond('seat', False)]),
        ev('to-backstage', *p['side_door'], name='側台門', trigger='touch', actions=[jump('m-backstage', arrive={'x': 2, 'y': 12, 'direction': 'right'})]),
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
        ev('to-backstage', *p['door'], name='後門', trigger='touch', actions=[jump('m-backstage', arrive={'x': 21, 'y': 12, 'direction': 'left'})]),
    ]
    guide = [G('有人在叫你', 'tao', [cond('tao', False)]), G('回後台', 'to-backstage', [cond('tao', True)])]
    return _map('m-alley', '後門巷子', 'alley', events, guide,
                _env('#ff8a3d', 0.25, [('market', 16, 6, 6, '#ffb060', 0.08)], dark=0.3))


def all_maps():
    return [dressing(), backstage(), auditorium(), alley()]
