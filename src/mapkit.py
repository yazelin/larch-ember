"""RPG 地圖事件與步驟的產生函式。格式照 Larch RPG 規格。"""
import json, itertools
import cards, variables

_ids = itertools.count(1)
INVISIBLE = {'url': '', 'width': 32, 'height': 32, 'frames': 1, 'rows': 1, 'offsetX': 0, 'offsetY': 0, 'idleFrame': 0}
TILESET = {
    'id': 'kn-dungeon',
    'name': '地城',
    'url': '/files/assets/tilesets/tiny-dungeon.webp',
    'tileSize': 16,
    'columns': 12,
    'rows': 11
}


def walker(url, scale=1.85):
    """3 欄 × 4 列、高解析度 192×256 每格，scale=1.85 符合手繪場景家具比例。"""
    return {'url': url, 'width': 192, 'height': 256, 'frames': 3, 'rows': 4, 'offsetX': 0, 'offsetY': 0, 'idleFrame': 1, 'scale': scale}


def A(kind, **kw):
    a = {'id': f'a{next(_ids)}', 'kind': kind, 'text': '', 'cardId': '', 'itemId': '', 'itemName': '', 'variable': '', 'value': '', 'amount': 1}
    a.update(kw)
    return a


def say(t, speaker='narrator', presentation='text'):
    return A('dialogue', text=t, presentation=presentation, speaker=speaker)


def card(card_id, presentation='text'):
    """把一張對話卡演在地圖上。"""
    return A('dialogue', cardId=card_id, presentation=presentation)


def setv(name, value):
    return A('variable', variable=name, value=str(value).lower() if isinstance(value, bool) else str(value))


def cond(name, value, op='eq'):
    return {'kind': 'variable', 'variable': name, 'op': op, 'value': str(value).lower() if isinstance(value, bool) else str(value), 'itemId': '', 'count': 1}


def item(item_id, name, amount=1):
    return A('item', itemId=item_id, itemName=name, amount=amount)


def remove(item_id, name, amount=1):
    return A('removeItem', itemId=item_id, itemName=name, amount=amount)


def jump(card_id, **kw):
    return A('jump', cardId=card_id, **kw)


def move(route, who='player', face=None, wait=True):
    m = {'who': who, 'route': [{'dir': d, 'steps': n} for d, n in route], 'wait': wait}
    if face: m['face'] = face
    return A('move', move=m)


def camera(x, y, hold=1500, back=True, ms=900):
    return A('camera', camera={'x': x, 'y': y, 'moveMs': ms, 'holdMs': hold, 'back': back})


def branch(conditions, then_steps, else_steps=None):
    b = {'conditions': conditions, 'then': then_steps}
    if else_steps:
        b['else'] = else_steps
    return A('if', **{'if': b})


def choice_action(text, options, speaker='narrator', variable='', look=None, color=None):
    """options: list of (label, actions) or dicts with {'id', 'label', 'actions'}"""
    opts = []
    for i, opt in enumerate(options):
        if isinstance(opt, dict):
            opts.append(opt)
        else:
            label, acts = opt
            opts.append({'id': f'opt_{i}', 'label': label, 'actions': acts})
    c = {'options': opts}
    if variable: c['variable'] = variable
    if look: c['look'] = look
    if color: c['color'] = color
    return A('choice', text=text, speaker=speaker, choice=c)


def input_action(text, variable, answer='', placeholder='', right=None, wrong=None, number=False, max_len=40):
    inp = {
        'variable': variable,
        'number': number,
        'max': max_len,
        'placeholder': placeholder,
        'answer': answer,
        'right': right or [],
        'wrong': wrong or [],
    }
    return A('input', text=text, input=inp)



def balloon(icon, target='player', event_id=None, ms=1600):
    b = {'icon': icon, 'target': target, 'durationMs': ms}
    if event_id: b['eventId'] = event_id
    return A('balloon', balloon=b)


def flash(color='#ffffff', strength=0.6, duration=300):
    return A('screen', screen={'effect': 'flash', 'strength': strength, 'durationMs': duration, 'color': color})


def wait(ms):
    return A('wait', amount=ms)


def sound(name, volume=0.7):
    return A('sound', audio={'url': '', 'sound': name, 'volume': volume})


def ev(id, x, y, **kw):
    e = {'id': id, 'name': id, 'x': x, 'y': y, 'actor': 'none', 'trigger': 'action', 'movement': 'still', 'solid': False,
         'once': False, 'conditions': [], 'actions': [], 'direction': 'down', 'sprite': INVISIBLE}
    e.update(kw)
    return e


def npc(id, x, y, sprite, **kw):
    kw.setdefault('direction', 'down')
    return ev(id, x, y, actor='npc', solid=True, sprite=sprite, **kw)


def page(id, conditions, actions, **kw):
    p = {'id': id, 'conditions': conditions, 'actor': 'none', 'sprite': INVISIBLE, 'movement': 'still', 'solid': False,
         'trigger': 'action', 'once': False, 'actions': actions}
    p.update(kw)
    return p


def collision_layer(width, height, walls):
    return {'id': 'walk', 'name': '通行設定', 'visible': False, 'locked': False, 'collision': True, 'damage': 0, 'above': False,
            'tiles': ['kn-dungeon:0' if (i % width, i // width) in walls else None for i in range(width * height)]}


def map_dict(name, width, height, picture, walls, events, guidance, environment=None, tile=48):
    m = {
        'version': 1,
        'name': name,
        'width': width,
        'height': height,
        'tileSize': tile,
        'tilesets': [TILESET],
        'layers': [collision_layer(width, height, walls)],
        'events': events,
        'hp': 100,
        'hpVariable': 'rpgHp',
        'bagVariable': 'inventory',
        'stateVariable': 'rpgState',
        'hideDesktopControls': False,
        'combat': 'none',
        'view': {'mode': '2d', 'tilt': 48, 'zoom': 1, 'depthOfField': 0, 'atmosphere': 'day'},
        'picture': {'url': picture},
        'guidance': guidance,
        'camera': 'normal'
    }
    if environment:
        m['environment'] = environment
    return m


def map_node(id, title, m, bgm=''):
    names = list(variables.VARS) + [n for _, n, _, _ in variables.RPG_VARS]
    data = {
        'type': 'plugin',
        'title': title,
        'text': '',
        'pluginId': 'larch-rpg-system',
        'pluginCardId': 'map',
        'pluginVersion': '0.4.0',
        'pluginName': 'RPG 系統',
        'pluginCardName': 'RPG 地圖',
        'pluginIcon': 'map',
        'pluginColor': '#4a7358',
        'pluginPresentation': 'fullscreen',
        'pluginFrame': {'showTitle': False, 'showButton': False},
        'pluginSkippable': False,
        'pluginReadVars': names,
        'pluginWriteVars': names,
        'pluginAssets': [],
        'platforms': ['web'],
        'pluginValues': {'map': json.dumps(m, ensure_ascii=False)}
    }
    if bgm:
        data.update(bgm=bgm, bgmVolume=0.4, bgmLoop=True)
    return {'id': id, 'type': 'story', 'position': cards._pos(), 'data': data}


def addv(name, n=1):
    """變數加減（引擎的 variable 動作 op=add）。"""
    return A('variable', variable=name, op='add', value=str(n))
