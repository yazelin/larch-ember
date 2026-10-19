"""「信紙與餘燼」：標題、對話框、選項三個部位手寫（ui/src/），選單、背包、收藏頁、地圖（RPG）四個部位從官方「晨霧玻璃」
原檔（ui/mist-original/）轉色：亮玻璃→泛黃信紙、藍灰字→褐墨、霧藍→餘燼橘。依色相與亮度對應，不是逐個色碼對照。
python3 ui/ember.py → ui/parts/*。設計 token 全集中在 TOKENS，改色改這裡。"""
import colorsys, json, pathlib, re
HERE = pathlib.Path(__file__).parent
SRC, ORIG, OUT = HERE / 'src', HERE / 'mist-original', HERE / 'parts'

# ---- 設計 token（顏色、字體、陰影都在這裡）----
TOKENS_MAP = {
    '--paper': 'rgba(236, 216, 182, 1)', '--paper-2': 'rgba(214, 186, 146, 1)', '--paper-edge': 'rgba(176, 124, 74, 1)',
    '--paper-line': 'rgba(120, 70, 30, .38)', '--rule': 'rgba(90, 60, 40, .13)', '--glow': 'rgba(232, 116, 59, .32)',
    '--ink': '#2b1d14', '--ink-soft': '#5a4434', '--pencil': '#6b5a4c',
    '--ember': '#e8743b', '--ember-deep': '#a8361f', '--rose': '#8e1f2a', '--ash': '#3a3330',
    '--serif': '"Noto Serif TC", "Songti TC", "Source Han Serif TC", "PMingLiU", Georgia, serif',
    '--sans': '"Noto Sans TC", "PingFang TC", "Microsoft JhengHei", system-ui, sans-serif',
}
TOKENS = ' '.join(f'{k}: {v};' for k, v in TOKENS_MAP.items())
ACCENT = '#e8743b'

# 介面 Skill 的網址只收 R2／larch.ink／相對路徑（jsDelivr 會被擋）。上傳過的音效記在 hosted.json（ui/host_audio.py 產生），
# 還沒上傳時退回 /files/ui-sfx/*.mp3：本機預覽讀得到（ui_inject 會複製過去），Larch 上則是無聲，不會播內建音效。
SFX_NAMES = ('hover', 'press', 'advance', 'open', 'close', 'use')
HOSTED = json.loads((HERE / 'hosted.json').read_text()) if (HERE / 'hosted.json').exists() else {}


def sfx_url(n):
    return HOSTED.get(n) or f'/files/ui-sfx/{n}.mp3'


# ---- 轉色 ----
def paper_of(r, g, b):
    """亮面（原本的白玻璃）→ 信紙：越亮越接近 (243,228,200)，稍暗的亮面落在 (234,214,180)。"""
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    t = min(1, max(0, (l - .88) / .12))
    return tuple(round(a + (c - a) * t) for a, c in zip((230, 210, 176), (243, 228, 200)))


def warm(r, g, b):
    """藍灰（墨、細線、陰影）→ 褐色，保留明度。亮面走 paper_of。"""
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    if l >= .88:
        return paper_of(r, g, b)
    if 0.45 < h < 0.75 or s < .22:   # 藍灰或近灰
        l2 = l * .78 if l < .4 else l * .95
        nr, ng, nb = colorsys.hls_to_rgb(.07, l2, .30 if l < .5 else .38)
        return round(nr * 255), round(ng * 255), round(nb * 255)
    return r, g, b


def conv_rgba(m):
    r, g, b, a = int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4)
    nr, ng, nb = warm(r, g, b)
    return f'rgba({nr}, {ng}, {nb}, {a})'


def conv_hex(m):
    h = m.group(0)
    if h.lower() == ACCENT or len(h) not in (4, 7):
        return h
    v = h[1:]
    if len(v) == 3:
        v = ''.join(c * 2 for c in v)
    r, g, b = int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)
    if (r, g, b) == (0, 0, 0):
        return h
    hh, ll, ss = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    if 0.45 < hh < 0.75 or ss < .22 or ll >= .88:   # 只轉藍灰、近灰與亮面；紅、綠、金保留
        nr, ng, nb = warm(r, g, b)
        return f'#{nr:02x}{ng:02x}{nb:02x}'
    return h


def convert(text):
    text = text.replace('#8fc3ea', ACCENT).replace('#a9d2f2', '#f0a070').replace('#ffe2a8', '#ffb066')
    def decl(m):
        v = re.sub(r'rgba\(\s*(\d+),\s*(\d+),\s*(\d+),\s*([\d.]+)\s*\)', conv_rgba, m.group(2))
        v = re.sub(r'#[0-9a-fA-F]{3,6}\b', conv_hex, v)
        return f'{m.group(1)}: {v}'
    text = re.sub(r'(?<![\w-])(--[\w-]+|[a-z-]+)\s*:\s*([^;{}]+?)(?=\s*(;|}|!important))', decl, text)
    text = text.replace('https: //', 'https://')
    for k in ('霧藍重點色',):
        text = text.replace(f'"label": "{k}"', '"label": "餘燼重點色"')
    return text


def fill(text):
    text = text.replace('/*TOKENS*/', TOKENS)
    text = re.sub(r'@SFX:(\w+)@', lambda m: sfx_url(m.group(1)), text)
    return text


# ---- 作品專屬覆寫（轉色之後接在檔尾）----
CHOICE_FOCUS = '''
{sel}:is(:hover, :focus-visible):not(:disabled) {{ border-color: var(--ember-deep); background: linear-gradient(90deg, #f6e6c6, #ecd2a6); color: var(--ink); outline: none; box-shadow: inset 0 0 0 2px var(--ember), 0 0 16px -2px rgba(232, 116, 59, .6); }}
'''
EXTRA = {
    'rpg.css': '\n'.join([
        # 官方原檔把 .rpg-waypoint:hover 也寫進 transform: none；引擎靠 transform 置中標籤，hover 會跳位。把它拿掉，hover 只換色
        '.rpg-waypoint:hover { border-color: var(--mg-deep); background: #f6e6c6; color: var(--mg-deep); box-shadow: none; }',
        # 地圖上的對話框：微透明、左右下留白（作者：不要貼齊）
        '#dialogue .dlg-box { padding: 20px clamp(26px, 3.8vw, 60px) 22px !important; min-height: 0 !important; border: 0; border-radius: 6px;'
        ' background: repeating-linear-gradient(180deg, transparent 0 33px, rgba(90, 60, 40, .12) 33px 34px), radial-gradient(60% 45% at 0% 100%, rgba(168, 54, 31, .2), transparent 70%),'
        ' radial-gradient(120% 140% at 50% 0%, rgba(236, 216, 182, .86), rgba(214, 186, 146, .82) 78%, rgba(176, 124, 74, .84));'
        ' -webkit-backdrop-filter: blur(4px); backdrop-filter: blur(4px); color: #2b1d14;'
        ' box-shadow: 0 0 0 1px rgba(120, 70, 30, .38), 0 0 26px 2px rgba(232, 116, 59, .3), inset 0 0 30px 4px rgba(110, 40, 15, .3), inset 0 -2px 0 rgba(232, 116, 59, .5), 0 22px 54px -18px rgba(0, 0, 0, .65); }',
        '#dialogue #text, #dialogue #speaker { font-family: "Noto Serif TC", "Songti TC", "Source Han Serif TC", "PMingLiU", Georgia, serif; }',
        '#dialogue #speaker { letter-spacing: .3em; }',
        '#dialogue .dlg-box { width: auto !important; margin-left: clamp(16px, 4vw, 64px) !important; margin-right: clamp(16px, 4vw, 64px) !important; margin-bottom: clamp(12px, 2.4vh, 24px) !important; }',
        # 任務通知不被左上任務卡擋住：移到上方正中
        '#notice { position: fixed !important; top: 84px !important; left: 50% !important; right: auto !important; bottom: auto !important; translate: -50% 0; }',
        # 沒有戰鬥：藏掉 HP、攻防魔、經驗與沒同行的夥伴格
        '.rpg-pause-menu :is(.pm-health, .pm-health-label, .pm-health-note, .pm-stat-row, .pm-exp, .pm-level, .pm-attributes),'
        ' .rpg-pause-menu .pm-section-title:has(+ .pm-attributes), .rpg-pause-menu .pm-party-member:disabled,'
        ' .rpg-pause-menu .pm-locked, body > header .hud-hp, body > header .hud-hp + * { display: none !important; }',
        CHOICE_FOCUS.format(sel='#dialogue :is(.dialogue-actions button, .dlg-choice)'),
    ]) + '\n',
    'choices.css': '',
    'gallery.css': (':scope { background: radial-gradient(ellipse 50% 45% at 88% 0%, rgba(255, 176, 102, .16), transparent 70%), '
                    'radial-gradient(ellipse 60% 55% at 0% 100%, rgba(168, 54, 31, .22), transparent 70%), '
                    'repeating-linear-gradient(90deg, rgba(255, 220, 170, .04) 0 1px, transparent 1px 160px), linear-gradient(180deg, #2a160d, #1c0f09 70%, #120a07) !important; color: #f1e2c6; }\n'
                    ':scope[data-larch-ui="gallery"] > header { border-bottom-color: rgba(255, 220, 170, .16); background: rgba(24, 12, 8, .6); }\n'
                    # 頁面是深色，標題字要淺；卡片是實心信紙（半透明疊在深底上會變成髒灰褐色，字讀不出來）
                    ':scope > header :is(h1, p, small) { color: #f1e2c6 !important; }\n:scope > header p { color: #d8c2a0 !important; }\n'
                    '[data-larch-ui="cg"] { border-radius: 8px; background: linear-gradient(170deg, #ecd8b6, #d9bd94); border-color: rgba(120, 70, 30, .5); }\n'
                    '[data-larch-ui="cg"] > img, [data-larch-ui="cg"][data-locked] > i { border-radius: 4px; }\n'
                    '[data-larch-ui="cg"]:not([data-locked]):hover { background: linear-gradient(170deg, #f4e3c2, #e6c99c); }\n'
                    '[data-larch-ui="cg"][data-locked] { background: linear-gradient(170deg, #d6bf9a, #c4a67c); }\n'
                    '[data-larch-ui="cg"][data-locked] figcaption :is(span, b) { color: #4a3626 !important; }\n'),
    'inventory.css': '\n[data-larch-ui="detail-effects"] li { background: transparent; border: 0; box-shadow: none; }\n',
}
MARK = {'.html': '<!-- larch-skill-part: {} -->', '.css': '/* larch-skill-part: {} */'}


def build():
    OUT.mkdir(exist_ok=True)
    made = {}
    for f in sorted(SRC.iterdir()):                     # 手寫的部位
        made[f.name] = fill(f.read_text())
    for f in sorted(ORIG.iterdir()):                    # 轉色的部位
        if f.name in made:
            continue
        t = convert(f.read_text())
        for n in SFX_NAMES:
            t = t.replace(f'/skills/morning-glass/sfx/{n}.mp3', f'@SFX:{n}@')
        if f.name == 'rpg.css':   # 官方原檔把 .rpg-waypoint:hover 也列進 transform: none 那條；引擎靠 transform 置中標籤，hover 會跳位
            assert ', .rpg-waypoint:hover,' in t
            t = t.replace(', .rpg-waypoint:hover,', ',', 1)
        made[f.name] = fill(t + '\n' + EXTRA.get(f.name, ''))
    for name, t in made.items():
        (OUT / name).write_text(t)
    assert 'morning-glass' not in ''.join(made.values()) and '#8fc3ea' not in ''.join(made.values())
    assert not re.search(r'https://[^"\' )]*(jsdelivr|githubusercontent)', ''.join(made.values()))
    print('ok', sorted(made))


if __name__ == '__main__':
    build()
