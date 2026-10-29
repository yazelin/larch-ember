"""組出 dist/project.json：重製版（2026-10-29），單線、純劇情卡、一個結局（設計 design/重製.md）。
劇本 canon/劇本.md 的每個 `##` 是一張對話卡，依 ORDER 串起來；每句帶分鏡 CG（逐句換背景，不放立繪）。
全劇沒有選項（作者 10-29：像看一部短片）。開頭一張提示卡請玩家按「自動」。
python3 src/build.py
"""
import json, math, pathlib, shutil, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import script, cards, ui_inject, songs

R = pathlib.Path(__file__).resolve().parent.parent
PROJECT_ID = 'project-904c48a1-2797-4a7e-916a-75b1117e6211'
A = '/files/assets/'

ORDER = ['open', 'market', 'livehouse', 'door2004', 'roses', 'monitor', 'confess', 'forget', 'song2023',
         'soundcheck', 'letter', 'dark', 'canal', 'concert', 'verse3', 'encore', 'kitchen', 'credits']
TITLES = {'open': '先生', 'market': '1988，收攤', 'livehouse': '2001，河岸留言', 'door2004': '2004，三排十四號',
          'roses': '2008，門內右邊', 'monitor': '2009，三秒', 'confess': '2011，票根的背面', 'forget': '2021，第一次忘詞',
          'song2023': '2023，晚安，台南', 'soundcheck': '2026，試音', 'letter': '信', 'dark': '天黑', 'canal': '運河',
          'concert': '開演', 'verse3': '第三段', 'encore': '安可', 'kitchen': '什麼演唱會', 'credits': '製作名單'}
# 配樂（assets/bgm/*.mp3）。同一首曲子連續的卡不重設，避免重播
TRACK = {'open': 'dressing', 'market': 'mem_1988', 'livehouse': 'mem_2004', 'door2004': 'mem_2004', 'roses': 'mem_love',
         'monitor': 'mem_love', 'confess': 'mem_love', 'forget': 'mem_clinic', 'song2023': 'mem_clinic', 'soundcheck': 'dress',
         'letter': 'dressing', 'dark': 'branch', 'canal': 'end_c', 'concert': 'concert', 'kitchen': 'end_a'}
# 〔掉字〕：落日以後，標記的句子只留前面一部分，後面變成「……」。數字是掉掉的比例
SITE = 'https://yazelin.github.io/larch-ember/'
POST_TRACK = {'encore': 'end_b'}   # 歌卡唱完後改用的配樂（沒列的沿用這場的 TRACK）
# 全程自動往下（作者 10-29：一部可以邊聽歌邊看、不用點滑鼠的音樂小說）。打字 TEXT_MS 毫秒一個字，打完停 AUTO 的 delayMs；點畫面仍可加快
TEXT_MS = 55   # 作者 10-29：90 太慢
AUTO = {'enabled': True, 'mode': 'delay', 'delayMs': 2000}
HINT = ['這是一部有歌的小說，從頭到尾會自己播放。', '戴上耳機，不用點滑鼠，看到最後。想快一點，點一下畫面。']
FADE_RATIO = {'letter': 0.35, 'dark': 0.55, 'canal': 0.6}
GALLERY = [('s_mem1_3', '2004，玫瑰與票根'), ('s_mem2_6', '票根的背面'), ('s_mem2_11', '2013，空舞台上的一小段舞'),
           ('s_mem4_1', '2022，診間'), ('s_soundcheck_3', '三排十四號'), ('s_concert_1', '開演'), ('s_a_2', '程希'),
           ('s_a_8', '什麼演唱會')]
GAL = {k for k, _ in GALLERY}


def music(name):
    return A + f'bgm/{name}.mp3' if name and (R / f'assets/bgm/{name}.mp3').exists() else ''


def shot_url(shot):
    p = R / f'assets/art/cg/{shot}.webp'
    return A + f'art/cg/{shot}.webp' if p.exists() else ''


def fade(text, ratio):
    """「深紅的玫瑰。」→「深紅的……」：去掉句尾標點後，留前面 (1-ratio) 的字。"""
    body = text.rstrip('。，！？…')
    keep = max(1, math.ceil(len(body) * (1 - ratio)))
    return body if keep >= len(body) else body[:keep] + '……'


def story_card(cid, bg_carry, bgm=''):
    """一段台詞 → 一張對話卡；台詞前有〔圖〕的那一句換背景。回傳 (卡, 這段結束時的背景)。"""
    lines, bg = [], bg_carry
    for i, (spk, text, vid, tag) in enumerate(script.L[cid]):
        if (cid, i) in script.FADE and cid in FADE_RATIO:
            text = fade(text, FADE_RATIO[cid])
        shot = script.SHOTS.get((cid, i))
        line = (spk or '旁白', text)
        if shot and shot_url(shot):
            bg = shot_url(shot)
        lines.append((line, bg if shot and shot_url(shot) else None))
    first_bg = next((b for _, b in lines if b), bg_carry)
    card = cards.dialogue(cid, TITLES.get(cid, cid), [l for l, _ in lines], bg=first_bg or '', bgm=bgm or None)
    for (l, b), dst in zip(lines, card['data']['dialogueLines']):
        dst['speaker'] = l[0]
        if b:
            dst['background'] = b
    ops = [{'id': f'cgop-{cid}-{sh}', 'mode': 'unlock', 'url': shot_url(sh)} for (c, _), sh in script.SHOTS.items() if c == cid and sh in GAL and shot_url(sh)]
    if ops:
        card['data']['cgOps'] = ops
    card['data']['stage'] = {'actors': []}
    card['data']['characterLayers'] = []
    card['data']['autoAdvance'] = dict(AUTO)
    return card, bg


# 片尾字卷（作者 2026-10-29：故事結束後用素材裡的「片尾字卷」插件，不要對話框）。速度 16px/s：1600×900 約 215 秒捲完、停 8 秒自動回標題，對齊 230 秒的合聲版。內容在 src/credits.txt，合聲版由 songs.apply 掛在這張卡上
ROLL_IMAGES = ['art/cg/s_mem2_11', 'art/p_yu_47', 'art/p_cheng_45', 'art/p_yu_father', 'art/p_tao_73', 'art/p_zhou_62', 'art/p_azhe_30', 'art/cg/s_a_8']


def credits_card():
    content = (R / 'src/credits.txt').read_text(encoding='utf-8').strip()
    for i, n in enumerate(ROLL_IMAGES, 1):
        assert (R / f'assets/{n}.webp').exists(), n
        assert f'@{i}' in content, f'credits.txt 沒用到圖片 {i}'
    card = {'id': 'credits', 'type': 'story', 'position': {'x': 0, 'y': 0}, 'data': {
        'type': 'plugin', 'title': TITLES['credits'], 'text': '', 'voiceMode': 'off', 'stage': {'actors': []}, 'characterLayers': [],
        'background': shot_url('s_a_9'),
        'pluginId': 'credits-roll', 'pluginCardId': 'roll', 'pluginVersion': '1.0.0', 'pluginName': '片尾字卷', 'pluginCardName': '片尾字卷',
        'pluginIcon': 'scroll', 'pluginColor': '#8a6d2a', 'pluginPresentation': 'fullscreen', 'pluginFrame': {'showTitle': False, 'showButton': False},
        'pluginSkippable': True, 'pluginReadVars': [], 'pluginWriteVars': [], 'pluginAssets': [], 'platforms': ['web'],
        'pluginHtml': (R / 'src/plugin/credits_roll_card.html').read_text(encoding='utf-8'),
        'pluginValues': {'content': content, **{f'image{i}': A + f'{n}.webp' for i, n in enumerate(ROLL_IMAGES, 1)},
                         'speed': 16, 'autoContinue': True, 'endHold': 8, 'continueLabel': '回到標題', 'bgColor': '#0a0c0e', 'bgOpacity': 0.8,
                         'textColor': '#f2ead6', 'accentColor': '#e8743b', 'font': 'serif'}}}
    return card, card['data']['background']


def build():
    p = json.loads((R / 'skeleton/project.json').read_text(encoding='utf-8'))
    p = p.get('project', p)
    board = p['boards'][0]
    board['nodes'], board['edges'] = [], []
    p['nodes'], p['edges'] = board['nodes'], board['edges']
    p['name'] = '餘燼'   # 作者 10-29：改名，原名《最終遺忘的橘色餘燼》太長
    p['description'] = ('改編自真實故事。歌手余靜得了早發性阿茲海默症，回到家鄉台南，在她第一次開售票演唱會的老戲院唱最後一場。'
                        '陪她來的男人替她遞水、提醒她下一句歌詞，她叫他「先生」。'
                        '從 1988 年阿爸的魚攤、2004 年三排十四號那朵深紅玫瑰，一路到 2026 年的最後一首歌。'
                        '單線劇情、一個結局，三首歌：〈餘燼〉〈晚安，台南〉〈港邊的燈〉。'
                        '原型、醫學資料出處與原聲帶：https://yazelin.github.io/larch-ember/')
    board['name'] = '第一章・餘燼'
    board['description'] = '從 1988 年的魚攤，到 2026 年的最後一場。'
    p['variables'] = []
    p['settings']['plugins'] = {k: {**v, 'enabled': False} if k == 'larch-inventory' else v for k, v in p['settings'].get('plugins', {}).items()}
    p['settings']['showRpgHud'] = False
    p['settings']['plugins']['credits-roll'] = {'enabled': True}
    p['settings']['plugins']['ember-song-card'] = {'enabled': True}   # 唱歌卡（個人使用版草稿，不上架）
    N = board['nodes'].append
    missing = [c for c in ORDER if c not in script.L and c != 'credits']
    assert not missing, f'劇本缺場：{missing}'
    p['settings']['textSpeed'] = TEXT_MS
    hint = cards.dialogue('hint', '開始之前', HINT, bg=A + 'art/cover.webp')
    hint['data'].update(start=True, autoAdvance=dict(AUTO), stage={'actors': []}, characterLayers=[])
    for d in hint['data']['dialogueLines']:
        d['speaker'] = '旁白'
    N(hint)
    prev, ptrack, bg = 'hint', None, ''
    for cid in ORDER:
        t = TRACK.get(cid)
        c, bg = credits_card() if cid == 'credits' else story_card(cid, bg, bgm=music(t) if t and t != ptrack else '')
        ptrack = t or ptrack
        N(c)
        if prev:
            cards.link(board, prev, cid)
        prev = cid
    assert not script.CHOICES, f'全劇不放選項（作者 10-29）：{script.CHOICES}'
    # 第二章＝公開站（作者 10-29：照《仙泉．香布纏．續》的製作手記章）：片尾字卷捲完跳過去，全螢幕嵌公開站，看完按「略過」結束回標題
    board['nodes'][-1]['data']['chapterEnd'] = True
    N({'id': 'to-site', 'type': 'story', 'position': {'x': 0, 'y': 0}, 'data': {
        'type': 'boardJump', 'title': '第二章・公開站', 'text': '', 'start': False, 'voiceMode': 'off', 'stage': {'actors': []},
        'jumpNodeId': 'site', 'jumpBoardId': 'board-site', 'characterLayers': []}})
    cards.link(board, 'credits', 'to-site')
    shell = ('<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><style>html,body{margin:0;height:100%;background:#140b07}'
             f'iframe{{width:100%;height:100%;border:0;display:block}}</style><iframe src="{SITE}" allow="fullscreen; autoplay"></iframe>'
             "<script>parent.postMessage({type:'larch:ready'},'*');</script></html>")
    p['boards'].append({'id': 'board-site', 'kind': 'story', 'mode': 'story', 'name': '第二章・公開站',
                        'description': '公開站：故事、改編自真實故事的原型、參考資料、原聲帶', 'edges': [], 'nodes': [{
        'id': 'site', 'type': 'story', 'position': {'x': 100, 'y': 200}, 'data': {
            'type': 'miniGame', 'start': True, 'title': '第二章・公開站', 'text': '原型、參考資料與原聲帶。看完按「略過」回到標題。', 'voiceMode': 'off',
            'miniGameHtml': shell, 'miniGameNote': f'薄殼而已，內容在 {SITE}', 'miniGameReadVars': [], 'miniGameSkippable': True,
            'miniGameWriteVars': [], 'miniGamePresentation': 'fullscreen'}}]})
    p['settings'].setdefault('titleScreen', {})['bgm'] = music('title') or p['settings'].get('titleScreen', {}).get('bgm', '')
    cover = A + 'art/cover.webp'
    p['settings']['titleCoverImage'] = cover
    p['settings']['projectThumbnail'] = cover
    p['projectThumbnail'] = cover
    p['settings']['cgGalleryEnabled'] = True
    p['settings']['cgGallerySource'] = 'picked'
    p['settings']['cgGalleryItems'] = [{'url': cover, 'title': '餘燼'}] + [{'url': shot_url(k), 'title': t, 'locked': True} for k, t in GALLERY if shot_url(k)]
    cur = None   # 歌卡唱完接回這一場的配樂（作者 10-29：歌盡量不斷，斷的地方用原本的 BGM）；encore 下台後換 end_b
    for cid in ORDER:
        cur = TRACK.get(cid, cur)
        songs.POST_BGM[cid] = music(POST_TRACK.get(cid, cur))
    songs.apply(p, R / 'dist')   # 有 assets/songs/cuts/manifest.json 才會接歌
    ui_inject.apply(p, R / 'dist')
    p['settings']['menuUi']['buttons'] = [b for b in p['settings']['menuUi']['buttons'] if b != 'bag']
    (R / 'dist').mkdir(exist_ok=True)
    out = R / 'dist/project.json'
    out.write_text(json.dumps(p, ensure_ascii=False, indent=1), encoding='utf-8')
    shutil.rmtree(R / 'dist/assets', ignore_errors=True)
    shutil.copytree(R / 'assets', R / 'dist/assets', ignore=shutil.ignore_patterns('voice', 'maps', 'objects', 'tilesets', '_fixture'))
    ids = {n['id'] for n in board['nodes']}
    bad = [e for e in board['edges'] if e['source'] not in ids or e['target'] not in ids]
    assert not bad, bad
    print(f'Build finished! {out} ({len(board["nodes"])} nodes, {len(board["edges"])} edges)')
    return p


if __name__ == '__main__':
    assert fade('深紅的玫瑰。', 0.4) == '深紅的……' and fade('好。', 0.5) == '好', fade('深紅的玫瑰。', 0.4)
    build()
