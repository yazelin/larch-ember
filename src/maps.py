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
    evs = events + [dict(e, id=e['id'].replace(f"obj-{d['map']['id']}", f'obj-{mid}')) for e in layout.events(d, urls)]
    return map_node(mid, title, map_dict(title, d['map']['w'], d['map']['h'], ground, layout.walls(d), evs, guidance, env))


def _env(tint, strength, lights, dark=0.15):
    return {'weather': 'clear', 'intensity': 0, 'darkness': dark, 'shake': 0,
            'lights': [dict(zip(('id', 'x', 'y', 'radius', 'color', 'flicker'), l)) for l in lights],
            'ambience': {'tint': tint, 'tintStrength': strength, 'vignette': 0.4, 'particles': 'embers', 'density': 0.08}}


def P(a):
    return {k: tuple(v) for k, v in layout.load(a)['points'].items()}


def hero(x, y, d='up'):
    return ev('hero', x, y, actor='player', direction=d, sprite=W('yu-47'), actorId='yu')


def look(eid, x, y, label, actions, conds=None):
    return ev(eid, x, y, name=label, marker={'label': label, 'kind': 'quest'}, conditions=conds or [], actions=actions)


ALL_DONE = [cond('letter', True), cond('zhou', True), cond('seat', True), cond('tao', True)]


def dressing():
    p = P('dressing')
    events = [
        hero(*p['hero_start']),
        npc('cheng', *p['cheng'], W('cheng-45'), direction='up', name='先生', actions=[card('m_dressing_intro')]),
        ev('intro', 1, 9, trigger='auto', once=True, actions=[card('m_dressing_intro')]),
        look('window', 11, 2, '窗', [card('m_window')]),
        look('mirror', 3, 3, '鏡子角落的照片', [card('m_mirror'), card('mem2_monitor'), card('mem2_rose'), card('mem2_europe'), card('mem2_stage')]),
        look('notebook', 5, 3, '筆記本', [card('m_notebook'), card('mem3_forget')]),
        look('rose', 3, 6, '化妝箱', [card('m_rose_dry'), card('mem1_door')]),
        look('jewel', 7, 3, '首飾盒', [card('m_jewelry'), setv('knob', True)], [cond('knob', False)]),
        look('radio', 12, 4, '阿爸的收音機',
             [branch([cond('knob', True)],
                     [card('m_radio_on'), card('m_letter'), card('mem4_clinic'), card('mem4_letter'), card('mem4_name'), card('m_note'), setv('letter', True)],
                     [card('m_radio')])], [cond('letter', False)]),
        ev('door', *p['door'], name='門', trigger='touch', actions=[jump('m-backstage', arrive={'x': 4, 'y': 2, 'direction': 'down'})]),
        # 四條線都走過、回到化妝間：天黑
        ev('dark', 1, 8, trigger='auto', once=True, conditions=ALL_DONE, actions=[jump('branch_dark')]),
    ]
    guide = {'title': '天黑之前', 'text': '在化妝間、走廊、觀眾席、後門巷子，把自己找回來。'}
    return _map('m-dressing', '化妝間', 'dressing', events, guide,
                _env('#ff9a4d', 0.22, [('lamp-mirror', 4, 2, 4, '#ffd59a', 0.05), ('sunset', 11, 1, 6, '#ff8a3d', 0)]))


def backstage():
    p = P('backstage')
    events = [
        npc('zhou', *p['piano'], W('zhou'), direction='up', name='彈琴的人', conditions=[cond('zhou', False)],
            actions=[card('m_corridor'), setv('zhou', True)]),
        ev('to-dressing', 4, 1, name='化妝間', trigger='touch', actions=[jump('m-dressing', arrive={'x': 8, 'y': 9, 'direction': 'up'})]),
        ev('to-stage', 1, 8, name='側台門', trigger='touch', actions=[jump('m-auditorium', arrive={'x': 1, 'y': 3, 'direction': 'right'})]),
        ev('to-alley', 16, 11, name='後門', trigger='touch', actions=[jump('m-alley', arrive={'x': 2, 'y': 3, 'direction': 'down'})]),
    ]
    guide = {'title': '後台', 'text': '樓梯下去是一樓：側台門通觀眾席，後門通巷子。'}
    return _map('m-backstage', '後台', 'backstage', events, guide,
                _env('#ffb070', 0.18, [('wall-lamp', 7, 5, 4, '#ffcf8a', 0.06), ('stair-lamp', 14, 3, 3, '#ffd59a', 0.04)]))


def auditorium():
    p = P('auditorium')
    events = [
        npc('azhe', *p['azhe'], W('azhe'), direction='up', name='阿哲', actions=[say('阿哲：余老師，聲音我會顧好。')]),
        look('seat314', *p['seat314'], '三排十四號', [card('m_auditorium'), setv('seat', True)], [cond('seat', False)]),
        ev('to-backstage', 0, 3, name='側台門', trigger='touch', actions=[jump('m-backstage', arrive={'x': 2, 'y': 8, 'direction': 'right'})]),
    ]
    guide = {'title': '觀眾席', 'text': '第三排，左邊數過來第十四個位子。'}
    return _map('m-auditorium', '觀眾席', 'auditorium', events, guide,
                _env('#ff9a5a', 0.15, [('stage', 12, 1, 9, '#ffd59a', 0.03)], dark=0.25))


def alley():
    p = P('alley')
    events = [
        npc('tao', *p['tao'], W('tao-73'), direction='left', name='阿桃姨', conditions=[cond('tao', False)],
            actions=[card('m_alley'), card('mem0_market'), setv('tao', True)]),
        ev('to-backstage', 1, 2, name='後門', trigger='touch', actions=[jump('m-backstage', arrive={'x': 15, 'y': 11, 'direction': 'left'})]),
    ]
    guide = {'title': '後門巷子', 'text': '巷子盡頭是黃昏市場的燈。'}
    return _map('m-alley', '後門巷子', 'alley', events, guide,
                _env('#ff8a3d', 0.25, [('market', 17, 5, 6, '#ffb060', 0.08)], dark=0.3))


def all_maps():
    return [dressing(), backstage(), auditorium(), alley()]
