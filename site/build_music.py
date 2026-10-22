# -*- coding: utf-8 -*-
"""產生 docs/music.html（原聲帶頁：逐句動態歌詞、滿版 CG 背景、餘燼粒子、頻譜環）。
python3 site/music_assets.py      # 音檔、封面、背景 CG
python3 site/make_lrc.py          # 動態歌詞 docs/music/*.lrc 與 lyrics.json
python3 site/build_music.py       # 產生頁面（歌詞署名沒填就失敗；預覽可加 --draft）
MEDIA_BASE=https://cdn.jsdelivr.net/gh/yazelin/larch-ember@site-media-1/docs/ python3 site/build_music.py
  圖與音檔改走 jsDelivr 孤兒 tag（跟《十一分鐘》同做法）。預設是相對路徑。
版面照 ~/neko-tensei/music.html（左封面與控制、右逐句歌詞、不動就收起介面、點歌詞跳句），
頻譜環與依段落換色照 omotenashi-hell，背景改成每首配的劇情 CG（交叉淡化＋慢推鏡）。"""
import html as H, json, os, sys

G = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.environ.get('MEDIA_BASE', '')

# 歌詞署名：作者 2026-10-23 定「AI 協助撰寫，林亞澤審定」。填 None 會讓正式版 build 失敗。
LYRICS_CREDIT = 'AI 協助撰寫，林亞澤審定'
TODO_MARK = '【待確認：歌詞署名與人／AI 分工，作者還沒決定】'

# 劇透字眼只擋「一句話」與曲名；歌詞本身是作者要放的，不受限。
SPOILERS = ['結局', '丈夫', '先生', '過世', '死別', '悲劇', '走失', '運河', '三排十四號', '程希', '玫瑰']

# id, 封面, 曲名, 標籤, 一句話, 背景 CG（照劇情順序，一首 1 到 2 張）, 長度, 補充說明
TRACKS = [
    ('ember-studio', 'studio', '餘燼', '錄音室版', '錄音室收音的版本，收音乾淨。', ['bg-soundcheck-1', 'bg-soundcheck-2'], '4:10', ''),
    ('ember-audience', 'audience', '餘燼', '台下跟唱版', '台下的人跟著一起唱，收音比較遠，雜訊多一些。', ['bg-prologue-1', 'bg-prologue-3'], '3:56', ''),
    ('ember-harmony', 'harmony', '餘燼', '合聲版', '加了合聲的編曲。', ['bg-soundcheck-4'], '3:50', ''),
    ('ember-chorus', 'chorus', '餘燼', '演唱會大合唱', '演唱會現場的大合唱，台下收音很好，中間有一段只剩台下的人在唱。', ['bg-concert-2', 'bg-concert-3'], '4:06', ''),
    ('goodnight-tainan', 'night', '晚安，台南', '2023', '她停演前寫的最後一首新歌，寫給家鄉。', ['bg-dress-1', 'bg-canal-1'], '3:25', ''),
    ('harbor-lights', 'harbor', '港邊的燈', '台語老歌', '劇中是父親魚攤的收音機在放的那首台語老歌。', ['bg-canal-2'], '2:03', '歌詞只標到第一次副歌，後半重複的副歌沒有逐句時間。'),
]


def u(p): return BASE + p


def check_spoilers():
    text = '\n'.join(t[4] + t[3] + t[2] + t[7] for t in TRACKS)
    hit = [w for w in SPOILERS if w in text]
    if hit: sys.exit(f'不產生：一句話裡有劇透字眼 {hit}')


CSS = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'music.css'), encoding='utf-8').read()
JS = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'music.js'), encoding='utf-8').read()


def build(draft):
    check_spoilers()
    if LYRICS_CREDIT is None:
        if not draft:
            sys.exit('不產生：歌詞署名還沒決定（site/build_music.py 的 LYRICS_CREDIT）。預覽請加 --draft。')
        credit = f'<span class="todo">{H.escape(TODO_MARK)}</span>'
    else:
        credit = H.escape(LYRICS_CREDIT)
    ly = json.load(open(os.path.join(G, 'docs/music/lyrics.json'), encoding='utf-8'))
    data = []
    for t in TRACKS:
        sid = t[0]; info = ly[sid]
        dyn = info['mode'].startswith('dynamic')
        data.append(dict(id=sid, f=u('music/' + sid + '.mp3'), c=u('media/cover-' + t[1] + '.webp'), n=t[2], v=t[3], l=t[4],
                         bg=[u('media/' + b + '.webp') for b in t[5]], d=t[6], note=t[7], dyn=dyn,
                         lrc=u('music/' + sid + '.lrc') if dyn else '', secs=info.get('secs', []),
                         text=[x['text'] for x in info['text']], tsec=[x['sec'] for x in info['text']]))
    items = ''.join(
        f'<li><button type="button" data-i="{i}" aria-label="{H.escape(t[2] + " " + t[3])}"><em>{i + 1:02d}</em>'
        f'<span>{H.escape(t[2])}<small>{H.escape(t[3])}</small></span></button></li>' for i, t in enumerate(TRACKS))
    page = f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="color-scheme" content="dark">
<title>原聲帶 · 最終遺忘的橘色餘燼</title>
<meta name="description" content="《最終遺忘的橘色餘燼》的原聲帶：〈餘燼〉的四種版本、〈晚安，台南〉、〈港邊的燈〉，附逐句動態歌詞。歌曲由 Suno 生成。">
<meta name="theme-color" content="#140b07">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%23140b07'/%3E%3Ccircle cx='16' cy='16' r='7' fill='%23ff9a3c'/%3E%3C/svg%3E">
<link rel="canonical" href="https://yazelin.github.io/larch-ember/music.html">
<meta property="og:title" content="原聲帶 · 最終遺忘的橘色餘燼">
<meta property="og:image" content="https://yazelin.github.io/larch-ember/media/og.jpg">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&family=Noto+Serif+TC:wght@500;700;900&display=swap">
<style>{CSS}</style>
</head>
<body>
<div class="stage-bg" id="bgwrap" aria-hidden="true"><i id="bgA"></i><i id="bgB"></i></div>
<div class="shade" aria-hidden="true"></div>
<div class="glow" id="glow" aria-hidden="true"></div>
<canvas id="fx" aria-hidden="true"></canvas>

<nav class="top">
  <a href="index.html">‹ 故事與參考資料</a>
  <span class="sp"></span>
  <button id="hide" type="button">收起介面</button>
</nav>
<button id="show" type="button" hidden>顯示介面</button>

<main class="stage">
  <div class="side">
    <div class="art" id="art" title="點一下播放或暫停">
      <img id="artimg" src="" width="600" height="600" alt="">
      <div class="art-hover" aria-hidden="true"><svg viewBox="0 0 24 24"><path class="picon" d="M8 5v14l11-7z"/></svg></div>
    </div>
    <div class="meta">
      <small id="no">TRACK 01 / 06</small>
      <h1 id="title"></h1>
      <span class="ver" id="ver"></span>
      <p class="one" id="one"></p>
      <p class="one note" id="note"></p>
    </div>
    <div class="ctrl">
      <button type="button" id="prev" class="sm" aria-label="上一首"><svg viewBox="0 0 24 24"><path d="M6 5h2v14H6zm3.5 7L19 5v14z"/></svg></button>
      <button class="play" id="play" type="button" aria-label="播放"><svg viewBox="0 0 24 24" aria-hidden="true"><path class="picon" d="M8 5v14l11-7z"/></svg></button>
      <button type="button" id="next" class="sm" aria-label="下一首"><svg viewBox="0 0 24 24"><path d="M16 5h2v14h-2zM5 5l9.5 7L5 19z"/></svg></button>
      <div class="seek"><span class="t" id="cur">0:00</span><input id="bar" type="range" min="0" max="1000" value="0" step="1" aria-label="播放進度"><span class="t" id="dur">0:00</span></div>
    </div>
    <ol class="tracks" id="tracks" aria-label="曲目">{items}</ol>
    <p class="credit">歌曲：Suno 生成。歌詞：{credit}。動態歌詞的文字是官方歌詞，時間由辨識對齊後校正。</p>
  </div>
  <section class="lyrics" id="lyrics" aria-label="歌詞"><ol id="lines"></ol></section>
</main>
<div id="hint" role="status"></div>
<script>
const TRACKS = {json.dumps(data, ensure_ascii=False)};
{JS}
</script>
</body>
</html>
"""
    open(os.path.join(G, 'docs/music.html'), 'w', encoding='utf-8').write(page)
    ap = os.path.expanduser('~/promo-footer-skill/apply.py')   # 推廣 footer（公開頁一定要有）
    if os.path.exists(ap):
        import subprocess
        subprocess.run([sys.executable, ap, os.path.join(G, 'docs/music.html'), 'larch-ember', '--inject'], check=True)
    print('docs/music.html', '（預覽版，含待確認標記）' if LYRICS_CREDIT is None else '')


if __name__ == '__main__':
    build('--draft' in sys.argv[1:])
