"""組出 dist/project.json：重製版（2026-10-29），單線、純劇情卡、一個結局（設計 design/重製.md）。
劇本 canon/劇本.md 的每個 `##` 是一張對話卡，依 ORDER 串起來；每句帶分鏡 CG（逐句換背景，不放立繪）。
有「選項：」的場在後面接一張只有一個選項的選擇卡（程希一次只問一個問題、只給一個選項）。
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
    return card, bg


def build():
    p = json.loads((R / 'skeleton/project.json').read_text(encoding='utf-8'))
    p = p.get('project', p)
    board = p['boards'][0]
    board['nodes'], board['edges'] = [], []
    p['nodes'], p['edges'] = board['nodes'], board['edges']
    p['description'] = ('改編自真實故事。歌手余靜得了早發性阿茲海默症，回到家鄉台南，在她第一次開售票演唱會的老戲院唱最後一場。'
                        '陪她來的男人替她遞水、提醒她下一句歌詞，她叫他「先生」。這是她和三排十四號那個人的二十二年。')
    board['description'] = '從 1988 年的魚攤，到 2026 年的最後一場。'
    p['variables'] = []
    p['settings']['plugins'] = {k: {**v, 'enabled': False} if k == 'larch-inventory' else v for k, v in p['settings'].get('plugins', {}).items()}
    p['settings']['showRpgHud'] = False
    N = board['nodes'].append
    missing = [c for c in ORDER if c not in script.L]
    assert not missing, f'劇本缺場：{missing}'
    prev, ptrack, bg = None, None, ''
    for cid in ORDER:
        t = TRACK.get(cid)
        c, bg = story_card(cid, bg, bgm=music(t) if t and t != ptrack else '')
        ptrack = t or ptrack
        if cid == ORDER[0]:
            c['data']['start'] = True
        if cid == ORDER[-1]:
            c['data']['stayOnCard'] = True
        N(c)
        if prev:
            cards.link(board, prev, cid)
        prev = cid
        if cid in script.CHOICES:   # 程希的問題：最後一句當題目，只有一個選項
            dl = c['data']['dialogueLines']
            q = dl.pop()
            assert len(script.CHOICES[cid]) == 1, (cid, script.CHOICES[cid])
            qid = f'{cid}_ask'
            N(cards.choice(qid, TITLES[cid] + '：' + q['text'], q['text'], [script.CHOICES[cid][0][0]], speaker=q['speaker'], bg=bg))
            cards.link(board, cid, qid)
            prev = qid
    # 選擇卡的出口要走 choice-0
    for e in board['edges']:
        if e['source'].endswith('_ask'):
            e['sourceHandle'] = 'choice-0'
    p['settings'].setdefault('titleScreen', {})['bgm'] = music('title') or p['settings'].get('titleScreen', {}).get('bgm', '')
    cover = A + 'art/cover.webp'
    p['settings']['titleCoverImage'] = cover
    p['settings']['projectThumbnail'] = cover
    p['projectThumbnail'] = cover
    p['settings']['cgGalleryEnabled'] = True
    p['settings']['cgGallerySource'] = 'picked'
    p['settings']['cgGalleryItems'] = [{'url': cover, 'title': '最終遺忘的橘色餘燼'}] + [{'url': shot_url(k), 'title': t, 'locked': True} for k, t in GALLERY if shot_url(k)]
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
