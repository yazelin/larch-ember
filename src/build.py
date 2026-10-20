"""組出 dist/project.json：劇本（canon/劇本.md）→ 劇情卡，每句帶配音與分鏡 CG（逐句換背景，不放立繪，作者 2026-10-19）。
第一版：化妝間探索先用劇情卡依序串起來（地圖之後換上）。三條結局由 branch_dark 的選擇卡分開。
python3 src/build.py
"""
import json, pathlib, shutil, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import script, cards, maps, variables, mapkit, ui_inject, songs

R = pathlib.Path(__file__).resolve().parent.parent
PROJECT_ID = 'project-904c48a1-2797-4a7e-916a-75b1117e6211'
A = '/files/assets/'

# 劇情順序（地圖版會改成在化妝間自由探索這一段）
MAIN = ['prologue', 'soundcheck', 'card_dress']   # 之後進 m-dressing 地圖探索（maps.py），天黑由地圖跳到 branch_dark
MAP_CARDS = ['m_dressing_intro', 'm_window', 'm_alley', 'mem0_market', 'm_mirror', 'mem1_door', 'm_notebook', 'm_rose_dry',
             'mem2_monitor', 'mem2_rose', 'mem2_europe', 'mem2_stage', 'm_jewelry', 'm_radio', 'm_radio_on', 'm_corridor',
             'mem3_forget', 'mem4_clinic', 'm_letter', 'mem4_letter', 'mem4_name', 'm_note', 'm_auditorium']
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


GALLERY = [('s_prologue_2', '後台的門'), ('s_soundcheck_3', '三排十四號'), ('s_mem1_3', '2004，玫瑰與票根'), ('s_mem2_6', '票根的背面'),
           ('s_mem2_9', '2012，歐洲的化妝間'), ('s_mem2_11', '2013，空舞台上的一小段舞'), ('s_mem4_1', '2022，診間'), ('s_concert_1', '開演'),
           ('s_a_2', '結局 A'), ('s_a_8', '結局 A 尾聲'), ('s_b_3', '結局 B'), ('s_c_8', '結局 C'), ('s_c_10', '結局 C 尾聲')]
GAL = {k for k, _ in GALLERY}
# 配樂（assets/bgm/manifest.json 的 use_in：劇本代號 → 曲名）。地圖本身掛各自的曲子；同一首曲子的卡片不重複設定，避免重播
_BGM = json.loads((R / 'assets/bgm/manifest.json').read_text(encoding='utf-8')) if (R / 'assets/bgm/manifest.json').exists() else {'tracks': []}
TRACK = {c: t['name'] for t in _BGM['tracks'] for c in t.get('use_in', [])}
MAP_TRACK = {'m-dressing': 'dressing', 'm-backstage': 'backstage', 'm-auditorium': 'auditorium', 'm-alley': 'alley'}
CARD_MAP = {c: 'dressing' for c in ('m_dressing_intro', 'm_window', 'm_mirror', 'm_notebook', 'm_rose_dry', 'm_jewelry', 'm_radio', 'm_radio_on', 'm_letter', 'm_note')}
CARD_MAP.update({'m_corridor': 'backstage', 'm_auditorium': 'auditorium', 'm_alley': 'alley'})


def music(name):
    return A + f'bgm/{name}.mp3' if name and (R / f'assets/bgm/{name}.mp3').exists() else ''


def voice(vid):
    if not os.environ.get('VOICE'):   # 2026-10-19 作者：配音先全部拿掉，劇本與各場景過關後再決定（VOICE=1 才帶配音）
        return None
    p = R / f'assets/voice/{vid}.mp3'
    return A + f'voice/{vid}.mp3' if vid and p.exists() else None


def shot_url(shot):
    p = R / f'assets/art/cg/{shot}.webp'
    return A + f'art/cg/{shot}.webp' if p.exists() else ''


def story_card(cid, bg_carry, bgm=''):
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
    card = cards.dialogue(cid, TITLES.get(cid, cid), [(l['speaker'], l['text'], l.get('voiceUrl')) for l in lines], bg=first_bg or '', bgm=bgm or None)
    for src, dst in zip(lines, card['data']['dialogueLines']):
        dst['speaker'] = src['speaker']
        if 'background' in src:
            dst['background'] = src['background']
    ops = [{'id': f'cgop-{cid}-{sh}', 'mode': 'unlock', 'url': shot_url(sh)} for (c, _), sh in script.SHOTS.items() if c == cid and sh in GAL and shot_url(sh)]
    if ops:
        card['data']['cgOps'] = ops
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
    p['variables'] = variables.project_variables()
    db = {'version': 1, 'heroId': 'yu', 'leadSwitch': False,
          'actors': [{'id': 'yu', 'name': '余靜', 'title': '', 'profile': '', 'role': 'party', 'walk': mapkit.walker('/files/assets/art/walk/walk-yu-47.webp'),
                      'portrait': '/files/assets/art/p_yu_47.webp', 'join': 'stay', 'kit': 'none', 'rig': '', 'joinVariable': ''}]}
    p['settings'].setdefault('plugins', {})['larch-rpg-system'] = {'enabled': True, 'settings': {'database': json.dumps(db, ensure_ascii=False)}}
    for m in maps.all_maps():
        t = music(MAP_TRACK.get(m['id']))
        if t:
            m['data'].update(bgm=t, bgmVolume=0.4, bgmLoop=True)
        N(m)
    for cid in MAP_CARDS:   # 地圖事件播的卡：不接線；曲子跟所在地圖一樣就不重設（避免重播）
        t = TRACK.get(cid)
        c, _ = story_card(cid, '', bgm=music(t) if t and t != CARD_MAP.get(cid) else '')
        N(c); made.add(cid)
    c, bgb = story_card('branch_dark', shot_url('s_branch_1'), bgm=music(TRACK.get('branch_dark')))
    N(c); made.add('branch_dark')
    N(cards.choice('branch_choice', '天黑', '她心裡聽見誰？', [t for t, _ in script.CHOICES['branch_dark']], speaker='余靜', bg=bgb))
    cards.link(board, 'branch_dark', 'branch_choice')
    seqs = [MAIN] + list(ENDINGS.values())
    for seq in seqs:
        prev = None; ptrack = None
        bg = shot_url('s_branch_1') if seq is not MAIN else ''
        for cid in seq:
            if cid == 'concert' and 'concert' in made:   # A、B 共用開演
                prev = cid; ptrack = TRACK.get(cid); continue
            t = TRACK.get(cid)
            c, bg = story_card(cid, bg, bgm=music(t) if t and t != ptrack else '')
            ptrack = t or ptrack
            if cid == MAIN[0]:
                c['data']['start'] = True
            if cid not in made:
                N(c); made.add(cid)
            if prev:
                cards.link(board, prev, cid)
            prev = cid
    cards.link(board, 'card_dress', 'm-dressing')
    first = {'ending_a': 'concert', 'ending_b': 'concert', 'ending_c': 'ending_c1'}
    for i, (_, target) in enumerate(script.CHOICES['branch_dark']):
        cards.choice_link(board, 'branch_choice', first[target], i)
    # A、B 都從 concert 出發：concert 後面接哪一個由選擇決定 → 用變數分支
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
    p['settings'].setdefault('titleScreen', {})['bgm'] = music('title') or p['settings'].get('titleScreen', {}).get('bgm', '')
    cover = A + 'art/cover.webp'
    p['settings']['titleCoverImage'] = cover
    p['settings']['projectThumbnail'] = cover
    p['projectThumbnail'] = cover
    p['settings']['cgGalleryEnabled'] = True
    p['settings']['cgGallerySource'] = 'picked'
    p['settings']['cgGalleryItems'] = [{'url': cover, 'title': '最終遺忘的橘色餘燼'}] + [{'url': shot_url(k), 'title': t, 'locked': True} for k, t in GALLERY if shot_url(k)]
    songs.apply(p, R / 'dist')   # 有 assets/songs/cuts/manifest.json 才會接歌
    ui_inject.apply(p, R / 'dist')   # 介面「信紙與餘燼」；線上的 PUT 不更新介面，要另外推（見 ui/ 說明）
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
