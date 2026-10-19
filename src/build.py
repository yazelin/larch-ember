"""組出 dist/project.json：劇本（canon/劇本.md）→ 劇情卡，每句帶配音與分鏡 CG（逐句換背景，不放立繪，作者 2026-10-19）。
第一版：化妝間探索先用劇情卡依序串起來（地圖之後換上）。三條結局由 branch_dark 的選擇卡分開。
python3 src/build.py
"""
import json, pathlib, shutil, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import script, cards

R = pathlib.Path(__file__).resolve().parent.parent
PROJECT_ID = 'project-904c48a1-2797-4a7e-916a-75b1117e6211'
A = '/files/assets/'

# 劇情順序（地圖版會改成在化妝間自由探索這一段）
MAIN = ['prologue', 'soundcheck', 'card_dress', 'm_dressing_intro', 'm_window', 'm_alley', 'mem0_market',
        'm_mirror', 'mem1_door', 'm_notebook', 'm_rose_dry', 'mem2_monitor', 'mem2_rose', 'mem2_europe', 'mem2_stage',
        'm_jewelry', 'm_radio', 'm_radio_on', 'm_corridor', 'mem3_forget', 'mem4_clinic', 'm_letter', 'mem4_letter', 'mem4_name',
        'm_note', 'm_auditorium', 'branch_dark']
ENDINGS = {'ending_a': ['concert', 'ending_a1', 'ending_a2', 'ending_a3'],
           'ending_b': ['concert', 'ending_b1', 'ending_b2'],
           'ending_c': ['ending_c1', 'ending_c2', 'ending_c3', 'ending_c4']}
TITLES = {'prologue': '序：最後一場', 'soundcheck': '試音', 'card_dress': '換上那件禮服', 'm_dressing_intro': '化妝間', 'm_window': '窗',
          'm_alley': '後門巷子', 'mem0_market': '1988，黃昏市場', 'm_mirror': '鏡子角落的照片', 'mem1_door': '2004，後台門口',
          'm_notebook': '筆記本', 'm_rose_dry': '乾燥的玫瑰', 'mem2_monitor': '2009，兩秒半', 'mem2_rose': '2011，門口的玫瑰',
          'mem2_europe': '2012，C 排 14 號', 'mem2_stage': '2013，空舞台', 'm_jewelry': '首飾盒', 'm_radio': '阿爸的收音機',
          'm_radio_on': '晚安時間', 'm_corridor': '彈琴的人', 'mem3_forget': '2021，第一次忘詞', 'mem4_clinic': '2022，診間',
          'm_letter': '信', 'mem4_letter': '2022，沒開的收音機', 'mem4_name': '2024，先生', 'm_note': '紙條', 'm_auditorium': '三排十四號',
          'branch_dark': '天黑', 'concert': '開演', 'ending_a1': '三排十四號', 'ending_a2': '安可', 'ending_a3': '什麼演唱會',
          'ending_b1': '餘燼', 'ending_b2': '謝謝您，先生', 'ending_c1': '天黑以後', 'ending_c2': '天烏烏', 'ending_c3': '天亮', 'ending_c4': '一個星期後'}
END_CARDS = {'ending_a3', 'ending_b2', 'ending_c4'}


def voice(vid):
    p = R / f'assets/voice/{vid}.mp3'
    return A + f'voice/{vid}.mp3' if vid and p.exists() else None


def shot_url(shot):
    p = R / f'assets/art/cg/{shot}.webp'
    return A + f'art/cg/{shot}.webp' if p.exists() else ''


def story_card(cid, bg_carry):
    """一段台詞 → 一張對話卡；台詞前有〔圖〕的那一句換背景。回傳 (卡, 這段結束時的背景)。"""
    lines, bg = [], bg_carry
    first_bg = None
    for i, (spk, text, vid, tag) in enumerate(script.L[cid]):
        shot = script.SHOTS.get((cid, i))
        line = {'id': f'{cid}-l{i}', 'speaker': spk or '旁白', 'text': text}
        if shot and shot_url(shot):
            bg = shot_url(shot)
            line['background'] = bg
        if first_bg is None:
            first_bg = bg
        v = voice(vid)
        if v:
            line['voiceUrl'] = v
        lines.append(line)
    card = cards.dialogue(cid, TITLES.get(cid, cid), [(l['speaker'], l['text'], l.get('voiceUrl')) for l in lines], bg=first_bg or '')
    for src, dst in zip(lines, card['data']['dialogueLines']):
        dst['speaker'] = src['speaker']
        if 'background' in src:
            dst['background'] = src['background']
    card['data']['stage'] = {'actors': []}
    card['data']['characterLayers'] = []
    card['data']['voiceMode'] = 'ai'
    if cid in END_CARDS:
        card['data']['stayOnCard'] = True
    return card, bg


def build():
    p = json.loads((R / 'skeleton/project.json').read_text(encoding='utf-8'))
    p = p.get('project', p)
    board = p['boards'][0]
    board['nodes'], board['edges'] = [], []
    p['nodes'], p['edges'] = board['nodes'], board['edges']
    p['description'] = ('改編自真實故事。四十七歲的歌手余靜得了早發性阿茲海默症，回到家鄉台南，在她第一次開售票演唱會的老戲院唱最後一場。'
                        '陪她來的男人一路替她開燈、遞水，她叫他「先生」。她記得 2004 年三排十四號那個說不出話的年輕人，卻不知道那個人就是他。')
    board['description'] = '天黑之前的化妝間、二十二年的回憶、三個結局。'
    N = board['nodes'].append
    bg = ''
    made = set()
    seqs = [MAIN] + list(ENDINGS.values())
    for seq in seqs:
        prev = None
        bg = shot_url('s_branch_1') if seq is not MAIN else ''
        for cid in seq:
            if cid == 'concert' and 'concert' in made:   # A、B 共用開演
                prev = cid; continue
            if cid == 'branch_dark':
                c, bg = story_card(cid, bg)
                N(c); made.add(cid)
                ch = cards.choice('branch_choice', '天黑', '她心裡聽見誰？', [t for t, _ in script.CHOICES['branch_dark']], speaker='余靜', bg=bg)
                N(ch); cards.link(board, cid, 'branch_choice')
                if prev: cards.link(board, prev, cid)
                prev = None; break
            c, bg = story_card(cid, bg)
            if cid == MAIN[0]:
                c['data']['start'] = True
            if cid not in made:
                N(c); made.add(cid)
            if prev:
                cards.link(board, prev, cid)
            prev = cid
    first = {'ending_a': 'concert', 'ending_b': 'concert', 'ending_c': 'ending_c1'}
    for i, (_, target) in enumerate(script.CHOICES['branch_dark']):
        cards.choice_link(board, 'branch_choice', first[target], i)
    # A、B 都從 concert 出發：concert 後面接哪一個由選擇決定 → 用變數分支
    p.setdefault('variables', [])
    if not any(v['name'] == 'heard' for v in p['variables']):
        p['variables'].append({'id': 'heard', 'name': 'heard', 'type': 'string', 'label': '她心裡聽見誰', 'defaultValue': ''})
    for e in list(board['edges']):
        if e['source'] == 'concert':
            board['edges'].remove(e)
    for tgt, val in (('ending_a1', 'a'), ('ending_b1', 'b')):
        board['edges'].append({'id': f'e-concert-{tgt}', 'source': 'concert', 'target': tgt, 'sourceHandle': 'right',
                               'data': {'condition': {'kind': 'variable', 'variable': 'heard', 'op': 'eq', 'value': val}}})
    for i, val in enumerate(('a', 'b', 'c')):
        N(cards.setvar(f'set_heard_{val}', '她心裡聽見', [('heard', val)]))
    for e in board['edges']:
        if e['source'] == 'branch_choice':
            val = 'abc'[int(e['sourceHandle'].split('-')[1])]
            e['target'], old = f'set_heard_{val}', e['target']
            cards.link(board, f'set_heard_{val}', old)
    for n in board['nodes']:
        if n['id'].startswith('set_heard_'):
            n['data']['text'] = '天黑了。'
    p['settings']['cgGalleryEnabled'] = False
    (R / 'dist').mkdir(exist_ok=True)
    out = R / 'dist/project.json'
    out.write_text(json.dumps(p, ensure_ascii=False, indent=1), encoding='utf-8')
    shutil.rmtree(R / 'dist/assets', ignore_errors=True)
    shutil.copytree(R / 'assets', R / 'dist/assets')
    ids = {n['id'] for n in board['nodes']}
    bad = [e for e in board['edges'] if e['source'] not in ids or e['target'] not in ids]
    assert not bad, bad
    print(f'Build finished! {out} ({len(board["nodes"])} nodes, {len(board["edges"])} edges)')
    return p


if __name__ == '__main__':
    build()
