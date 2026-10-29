"""歌曲接線（Suno 的三首：餘燼、晚安台南、港邊的燈）。build.py 在寫出 project.json 前呼叫 songs.apply(project, dist)。
讀 assets/songs/cuts/manifest.json（src/songs_cut.py 產的）；沒有 manifest 就什麼都不做（沒放歌時 build 照舊）。

三種接法（manifest 的 role）：
- sung_card：主線卡裡「余靜（唱）…」那一段，從原卡切出來變成獨立的「歌卡」。原卡拆成 前（原代號）／歌（代號__song）／後（代號__post）。
  歌卡卡片層掛歌（bgm、不循環），歌詞依 manifest 的每句時間分組，用卡片層 autoAdvance（固定間隔）一組一組自動往下。
  Larch 的 autoAdvance 只有卡片層一個固定 delayMs（逐句沒有自己的間隔），所以做法是：量好每組「打字時間＋delay」，
  挑一個 delay 讓各組換頁的時間貼近每句開唱的時間；前奏、間奏空檔用「♪」填充句撐時間。誤差見建置時印出的預測。
- line_bgm：不需要歌詞跟隨，在某一句開始放（結局 C 尾聲，阿哲按下播放鍵）。
- sfx：地圖調查點觸發的卡換不了曲（實測），只能用逐句 sfxUrl 播收音機版的歌；sfx 只在當句播，換句就停。
"""
import copy, json, os, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
_sd = pathlib.Path(os.environ.get('SONGS_DIR') or ROOT / 'assets/songs')
SONGS_DIR = (_sd if _sd.is_absolute() else ROOT / _sd).resolve()
CUT_DIR = SONGS_DIR / 'cuts'
MANIFEST = CUT_DIR / 'manifest.json'

BGM_VOL = 0.65          # 背景曲卡上 0.5、地圖 0.4；歌略大聲
SFX_VOL = 0.9           # 收音機版（檔本身已降到 -20 LUFS）
UNINTERRUPTIBLE = True  # 歌卡不讓玩家點掉：點了歌詞會跑到歌前面。想允許跳過就改成 False
AUDIO_LAG = 0.25        # 進卡到歌真的出聲的估計秒數
EARLY = 0.3             # 歌詞組偏好比開唱早出現幾秒
MAX_GROUP = 3           # 一組最多幾句歌詞
FILL = ['♪', '♪ ♪', '♪ ♪ ♪']
ALLOW_FAIL = bool(os.environ.get('SONGS_ALLOW_FAIL'))
REPORT = {}             # 卡代號 → 規劃結果（tests/songs_check.py 與建置輸出用）


POST_BGM = {}   # build.py 填：卡沒自己設 BGM（沿用前一場）時，歌唱完要接回哪一首


SONG_PLUGIN = 'ember-song-card'   # 唱歌卡插件（src/plugin/song_card.html；manifest 在 src/plugin/song_manifest.py，存成個人使用版草稿）
SONG_HTML = (ROOT / 'src/plugin/song_card.html').read_text(encoding='utf-8')
# 唱歌卡左上角的「正在播放」：manifest 的 song → (歌名, 版本, 封面)；封面跟公開站原聲帶頁同一批（assets/art/song/）
SONG_INFO = {'港邊的燈': ('港邊的燈', '台語老歌', 'harbor'), '餘燼@錄音室': ('餘燼', '錄音室版', 'studio'), '餘燼@台下': ('餘燼', '台下跟唱版', 'audience'),
             '晚安，台南': ('晚安，台南', '2023', 'night'), '餘燼@大合唱': ('餘燼', '演唱會大合唱', 'chorus')}


def _bgm_url(card_id):
    """assets/bgm/manifest.json 的 use_in：這張卡原本的背景曲。"""
    f = ROOT / 'assets/bgm/manifest.json'
    if not f.exists():
        return ''
    for t in json.loads(f.read_text(encoding='utf-8'))['tracks']:
        if card_id in t.get('use_in', []) and (ROOT / f"assets/bgm/{t['name']}.mp3").exists():
            return f"/files/assets/bgm/{t['name']}.mp3"
    return ''


def _norm(s):
    import re
    return re.sub(r'[^一-鿿A-Za-z0-9]', '', s.replace('（唱）', ''))


# ---------------------------------------------------------------- 歌詞分組與排時間

def _pen(x):
    """x = 實際換頁時間 - 想要的時間。晚了比早了糟。"""
    return -x if x < 0 else 3 * x


def simulate(lines, dur, D, ts):
    """用固定 delay=D(ms) 模擬卡片：每一組顯示時間 = 打字時間(字數×ts) + D。回傳 (組, 成本, 結束時間)。"""
    def sd(text):
        return len(text) * ts / 1000 + D / 1000 + 0.06
    want = [l['t0'] + AUDIO_LAG - EARLY for l in lines]
    c, i, slots, cost, nf = 0.0, 0, [], 0.0, 0
    while i < len(lines):
        ft = FILL[nf % 3]; fd = sd(ft)
        if _pen(c + fd - want[i]) < _pen(c - want[i]):
            slots.append({'text': ft, 'fill': True, 'start': c}); c += fd; nf += 1
            continue
        best = None
        for n in range(1, min(MAX_GROUP, len(lines) - i) + 1):
            text = '（唱）' + '\n'.join(l['text'] for l in lines[i:i + n])
            c2 = c + sd(text)
            nxt = want[i + n] if i + n < len(lines) else dur + AUDIO_LAG
            k = _pen(c2 - nxt) + 0.25 * sum(max(0.0, want[i + j] - c) for j in range(1, n))
            if best is None or k < best[0] - 1e-9:
                best = (k, n, text, c2)
        _, n, text, c2 = best
        cost += _pen(c - want[i])
        slots.append({'text': text, 'lines': list(range(i, i + n)), 'start': c})
        c = c2; i += n
    while True:   # 歌還沒結束就補 ♪，卡片不要比歌早結束（不然下一張卡的曲子會切掉歌的尾巴）
        ft = FILL[nf % 3]; fd = sd(ft)
        if c + 0.35 * fd < dur + AUDIO_LAG:
            slots.append({'text': ft, 'fill': True, 'start': c}); c += fd; nf += 1
        else:
            break
    cost += _pen(c - (dur + AUDIO_LAG)) * 0.5
    return slots, cost, c


def plan(lines, dur, ts):
    best = None
    for D in range(1500, 5001, 100):
        slots, cost, end = simulate(lines, dur, D, ts)
        cost += 0.4 * len(slots) + 0.6 * sum(1 for x in slots if x.get('fill'))
        if best is None or cost < best[0]:
            best = (cost, D, slots, end)
    _, D, slots, end = best
    errs = []   # 每句歌詞：換頁時間 - 該句開唱時間（卡片時間，已含 AUDIO_LAG 的補償）；負 = 比開唱早出現
    for s in slots:
        for j in s.get('lines', []):
            errs.append(round(s['start'] - (lines[j]['t0'] + AUDIO_LAG), 2))
    return {'delay_ms': D, 'slots': slots, 'end': round(end, 2), 'audio_end': round(dur + AUDIO_LAG, 2), 'line_errors': errs}


# ---------------------------------------------------------------- 套進卡

# 不是歌的逐句音效（分歧天黑的三個聲音之一、之三）：(卡, 劇本句子裡的字, assets 底下的檔, 音量)。檔不在就略過。
LINE_SFX = [('branch_dark', '敲了兩下', 'sfx/knock_door.mp3', 0.9),
            ('branch_dark', '水管沖地', 'sfx/market_closing.mp3', 0.9)]


def line_sfx(project):
    by_id = {n['id']: n for n in project['boards'][0]['nodes']}
    for cid, anchor, rel, vol in LINE_SFX:
        f = ROOT / 'assets' / rel
        node = by_id.get(cid)
        if not f.exists() or node is None:
            print(f'songs: 略過音效 {rel}（檔或卡不在）'); continue
        hit = [i for i, l in enumerate(node['data']['dialogueLines']) if anchor in l['text']]
        if len(hit) != 1:
            print(f'songs: 略過音效 {rel}（{cid} 找不到唯一的「{anchor}」）'); continue
        node['data']['dialogueLines'][hit[0]].update(sfxUrl='/files/assets/' + rel, sfxVolume=vol, sfxLoop=False)


def apply(project, dist=None):
    line_sfx(project)
    if not MANIFEST.exists():
        return
    mf = json.loads(MANIFEST.read_text(encoding='utf-8'))
    board = project['boards'][0]
    nodes, edges = board['nodes'], board['edges']
    by_id = {n['id']: n for n in nodes}
    ts = max(12, int(project.get('settings', {}).get('textSpeed') or 30))
    if project.get('settings', {}).get('typingEffect') is False:
        ts = 0
    resume_next = []
    done = []
    for cut in mf['cuts']:
        f = CUT_DIR / cut['file']
        if not f.exists():
            print(f"songs: 略過 {cut['id']}（檔案不在）"); continue
        if not cut.get('verify', {}).get('ok') and not ALLOW_FAIL:
            print(f"songs: 略過 {cut['id']}（切段驗證沒過；SONGS_ALLOW_FAIL=1 可強制）"); continue
        url = '/files/assets/' + f.relative_to(ROOT / 'assets').as_posix()
        cid, li = cut['place']['card'], cut['place']['line']
        node = by_id.get(cid)
        if node is None:
            print(f"songs: 略過 {cut['id']}（專案裡沒有卡 {cid}）"); continue
        if node['data'].get('type') == 'plugin' and li == 0 and cut['role'] == 'line_bgm':   # 片尾字卷插件卡：歌從進卡開始放
            node['data'].update(bgm=url, bgmVolume=BGM_VOL, bgmLoop=False); done.append(cut['id']); continue
        DL = node['data']['dialogueLines']
        if cut['place']['anchor'] == 'first_sung':   # 改稿會讓行號跑掉（roses 改稿後歌卡插錯位置、歌詞又在對話裡唱一遍）：照唱的人找第一句（唱）
            hit = [i for i, l in enumerate(DL) if l['speaker'] == cut.get('singer', '余靜') and l['text'].startswith('（唱）')]
            li = hit[0] if hit else len(DL)
            cut['place'] = {**cut['place'], 'line': li}
        if li >= len(DL) or (cut['place']['anchor'] not in ('first_sung', 'first') and cut['place']['anchor'] not in DL[li]['text']):
            print(f"songs: 略過 {cut['id']}（{cid} 第 {li} 句跟劇本對不上，重跑 songs_cut.py）"); continue
        role = cut['role']
        if role == 'sfx':
            DL[li].update(sfxUrl=url, sfxVolume=SFX_VOL, sfxLoop=False)
        elif role == 'line_bgm':   # 第 0 句的逐句 BGM 播放器不理，要設在卡上（製作名單的合聲版就是這樣沒播）
            (by_id[cid]['data'] if li == 0 else DL[li]).update(bgm=url, bgmVolume=BGM_VOL, bgmLoop=False)
        elif role == 'sung_card':
            last_id = _song_card(project, by_id, nodes, edges, cut, url, ts)
            if cut.get('resume') == 'next':
                resume_next.append((last_id, cid))
        done.append(cut['id'])
    # 歌後面的卡沒有自己的曲子時，接回這段原本的背景曲（歌結束後靜默一小段不會自己恢復）
    for last_id, cid in resume_next:
        base = REPORT[cid]['base_bgm']
        if not base:
            continue
        for e in edges:
            if e['source'] == last_id:
                t = by_id.get(e['target'])
                if t and t['data'].get('type') == 'dialogue' and not t['data'].get('bgm'):
                    t['data'].update(bgm=base, bgmVolume=0.5, bgmLoop=True)
    print('songs: 接了', len(done), '段 →', ', '.join(done))
    for cid, r in REPORT.items():
        e = r['line_errors']
        print(f"songs:   {cid}：delay {r['delay_ms']}ms、{len(r['slots'])} 張畫面（含 ♪ 填充 {sum(1 for s in r['slots'] if s.get('fill'))}）、"
              f"換頁比開唱 早/晚 平均 {sum(abs(x) for x in e)/max(1, len(e)):.2f}s 最晚 {max(e, default=0):+.2f}s、卡片結束 {r['end']}s / 歌結束 {r['audio_end']}s")


def _song_card(project, by_id, nodes, edges, cut, url, ts):
    cid, r0 = cut['place']['card'], cut['place']['line']
    node = by_id[cid]; data = node['data']; DL = data['dialogueLines']
    r1 = r0
    singer = cut.get('singer', '余靜')
    while r1 < len(DL) and DL[r1]['speaker'] == singer and DL[r1]['text'].startswith('（唱）'):
        r1 += 1
    lines = cut['lines']
    for k in range(r1 - r0):   # 劇本裡既有的歌詞要和歌詞檔一致
        if k >= len(lines) or _norm(DL[r0 + k]['text']) != _norm(lines[k]['text']):
            print(f"songs: 警告 {cid} 第 {r0 + k} 句「{DL[r0 + k]['text']}」和歌詞檔不一致")
    pl = plan(lines, cut['duration'], ts)
    base = data.get('bgm') or POST_BGM.get(cid) or _bgm_url(cid)
    REPORT[cid] = dict(pl, base_bgm=base, cut=cut['id'], n_script_lines=r1 - r0, n_lyrics=len(lines))

    def effective_bg(idx):
        bg = data.get('background')
        for j in range(1, idx + 1):
            if 'background' in DL[j]:
                bg = DL[j]['background']
        return bg

    def mk(nid, title, dl, first_idx, src_data):
        d = copy.deepcopy(src_data)
        d['title'] = title
        d['dialogueLines'] = dl
        d['speaker'], d['text'] = dl[0]['speaker'], dl[0]['text']
        bg = effective_bg(first_idx)
        if bg:
            d['background'] = bg
        return {'id': nid, 'type': 'story', 'position': {'x': node['position']['x'] + 40, 'y': node['position']['y'] + 40}, 'data': d}

    pre, post = DL[:r0], DL[r1:]
    orig_auto = data.get('autoAdvance')
    song_lines = [{'id': f'{cid}__song-l{k}', 'speaker': '旁白' if s.get('fill') else singer, 'text': s['text']} for k, s in enumerate(pl['slots'])]
    song_id = f'{cid}__song' if pre else cid
    song = mk(song_id, data.get('title', cid) + '（歌）', song_lines, r0, data)
    sd = song['data']
    for k in ('cgOps', 'start', 'stayOnCard') if pre else ():
        sd.pop(k, None)
    sd.update(bgm=url, bgmVolume=BGM_VOL, bgmLoop=False)
    sd['autoAdvance'] = {'enabled': True, 'mode': 'delay', 'delayMs': pl['delay_ms'], 'uninterruptible': UNINTERRUPTIBLE}
    chain = []
    if pre:
        data['dialogueLines'] = pre
        data['speaker'], data['text'] = pre[0]['speaker'], pre[0]['text']
        was_end = data.pop('stayOnCard', None)
        chain.append(node)
        nodes.append(song); by_id[song_id] = song
    else:   # 歌卡就是原卡（沒有前段）：沿用原代號，留著 cgOps／start
        was_end = data.get('stayOnCard')
        sd.pop('stayOnCard', None)
        node['data'] = sd
        song = node
    chain.append(song)
    last = song
    if post:
        pid = f'{cid}__post'
        pn = mk(pid, data.get('title', cid) + '（後）', post, r1, copy.deepcopy(data) if pre else sd)
        pd = pn['data']
        for k in ('cgOps', 'start', 'autoAdvance', 'bgm', 'bgmVolume', 'bgmLoop', 'stayOnCard'):
            pd.pop(k, None)
        if orig_auto:   # 唱完那段照這場原本的自動往下（作者 10-29：全程不用點）
            pd['autoAdvance'] = copy.deepcopy(orig_auto)
        if cut.get('resume') == 'post' and base:
            pd.update(bgm=base, bgmVolume=0.5, bgmLoop=True)
        if was_end:
            pd['stayOnCard'] = True
        nodes.append(pn); by_id[pid] = pn
        chain.append(pn); last = pn
    elif was_end:
        last['data']['stayOnCard'] = True
    # 歌卡換成「唱歌卡」插件（作者 10-29：用對話框拼的歌卡一點就對不上；插件照秒數亮歌詞、唱完才往下或按略過）
    bg_at = [(0.0, effective_bg(r0))] + [(lines[k]['t0'], DL[r0 + k]['background']) for k in range(min(r1 - r0, len(lines))) if 'background' in DL[r0 + k]]
    imgs, cues = [], []
    for tt, u in bg_at:
        if not u or (cues and imgs[cues[-1][1] - 1] == u): continue
        if u not in imgs and len(imgs) < 6: imgs.append(u)
        if u in imgs: cues.append((tt, imgs.index(u) + 1))
    sd = song['data']
    for k in ('dialogueLines', 'autoAdvance', 'speaker'):
        sd.pop(k, None)
    sd.update(type='plugin', text='', pluginId=SONG_PLUGIN, pluginCardId='sing', pluginVersion='1.1.1', pluginName='唱歌卡', pluginCardName='唱歌卡',
              pluginIcon='music', pluginColor='#b5532a', pluginPresentation='fullscreen', pluginFrame={'showTitle': False, 'showButton': False},
              pluginSkippable=False, pluginReadVars=[], pluginWriteVars=[], pluginAssets=[], platforms=['web'],
              pluginHtml=SONG_HTML + f'<!-- {song["id"]} -->',   # 相鄰兩張插件卡 html 一樣會沿用前一張的畫面，尾端加卡片 id 讓內容不同
              pluginValues={'lines': '\n'.join(f"{l['t0']:.2f}｜{l['text']}" for l in lines), 'duration': round(cut['duration'], 2), 'endHold': 1.5,
                            'offset': AUDIO_LAG, 'singer': singer, 'skipLabel': '略過',
                            **({'songTitle': SONG_INFO[cut['song']][0], 'songVersion': SONG_INFO[cut['song']][1],
                                'cover': f"/files/assets/art/song/cover-{SONG_INFO[cut['song']][2]}.webp"} if cut['song'] in SONG_INFO else {}),
                            'backgrounds': '\n'.join(f'{tt:.2f}｜{i}' for tt, i in cues), **{f'image{i + 1}': u for i, u in enumerate(imgs)}})
    # 邊：原卡的出邊改從最後一張出去；前→歌→後 依序連
    for e in edges:
        if e['source'] == cid and e['target'] not in {c['id'] for c in chain}:
            e['source'] = last['id']
    for a, b in zip(chain, chain[1:]):
        edges.append({'id': f"{a['id']}--{b['id']}", 'source': a['id'], 'target': b['id'], 'sourceHandle': 'right', 'targetHandle': 'left'})
    return last['id']
