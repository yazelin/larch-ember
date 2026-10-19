"""白板卡片節點產生器：對話卡、選擇卡、變數卡與連線。"""
_x = [0]


def _pos():
    _x[0] += 1
    return {'x': (_x[0] % 8) * 360, 'y': (_x[0] // 8) * 260}


def dialogue(id, title, lines, bg='', start=False, speaker='', actors=None, voiceUrl=None, bgm=None):
    """lines：字串（旁白/預設講者）或 (講者, 文字)。"""
    dl = []
    if isinstance(lines, str):
        lines = [lines]
    for i, l in enumerate(lines):
        # (講者, 文字) 或 (講者, 文字, 這一句的配音網址)
        sp, tx, lv = (l + (None,))[:3] if isinstance(l, tuple) else (speaker, l, None)
        line_dict = {'id': f'{id}-l{i}', 'speaker': sp, 'text': tx}
        if lv:
            line_dict['voiceUrl'] = lv
        if actors:
            matched = next((a['id'] for a in actors if a['name'] == sp), None)
            if matched:
                line_dict['speakerActorId'] = matched
        if i == 0 and voiceUrl:
            line_dict['voiceUrl'] = voiceUrl
        dl.append(line_dict)
    
    first_speaker = dl[0]['speaker'] if dl else speaker
    first_text = dl[0]['text'] if dl else ''
    data = {
        'type': 'dialogue',
        'title': title,
        'speaker': first_speaker,
        'text': first_text,
        'dialogueLines': dl,
        'stage': {'actors': actors or []}
    }
    if bg: data['background'] = bg
    if start: data['start'] = True
    if voiceUrl: data['voiceUrl'] = voiceUrl
    if bgm: data.update(bgm=bgm, bgmVolume=0.5, bgmLoop=True)
    return {'id': id, 'type': 'story', 'position': _pos(), 'data': data}


def choice(id, title, text, choices, speaker='沈淮', bg=''):
    """choices: ['選項一', '選項二', ...]"""
    data = {
        'type': 'choice',
        'title': title,
        'speaker': speaker,
        'text': text,
        'choices': choices,
        'choiceMode': 'branch',
        'choicePlacement': 'center'
    }
    if bg: data['background'] = bg
    return {'id': id, 'type': 'story', 'position': _pos(), 'data': data}


def link(board, a, b):
    board['edges'].append({'id': f'{a}--{b}', 'source': a, 'target': b, 'sourceHandle': 'right', 'targetHandle': 'left'})


def choice_link(board, source, target, choice_index):
    board['edges'].append({
        'id': f'{source}--choice-{choice_index}',
        'source': source,
        'target': target,
        'sourceHandle': f'choice-{choice_index}',
        'targetHandle': 'left',
        'animated': True
    })


def setvar(id, title, ops):
    """設定變數卡：ops = [(變數, 值), ...]"""
    return {'id': id, 'type': 'story', 'position': _pos(), 'data': {
        'type': 'setVariable', 'title': title, 'text': '',
        'variableOps': [{'id': f'{id}-{i}', 'variable': k, 'kind': 'set',
                         'value': str(v).lower() if isinstance(v, bool) else str(v)} for i, (k, v) in enumerate(ops)]}}


def actor(name, url, slot='center', offsetX=0, offsetY=0, scale=1):
    return {'id': f'actor-{name}', 'name': name, 'url': url, 'slot': slot, 'offsetX': offsetX, 'offsetY': offsetY, 'scale': scale}
