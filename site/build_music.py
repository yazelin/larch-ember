# -*- coding: utf-8 -*-
"""產生 docs/music.html（原聲帶頁）。
python3 site/build_music.py --draft      產生預覽版（歌詞署名那一行是紅色待確認標記）
python3 site/build_music.py              正式版：標記還在就失敗，不寫檔
MEDIA_BASE=https://cdn.jsdelivr.net/gh/yazelin/larch-ember@site-media-1/docs/ python3 site/build_music.py
  圖與音檔改走 jsDelivr 孤兒 tag（跟《十一分鐘》同做法；整個遊戲 repo 太大，不能直接走 jsDelivr）。預設是相對路徑。"""
import html as H, os, sys

G = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.environ.get('MEDIA_BASE', '')

# 歌詞署名：作者 2026-10-23 拍板「AI 協助撰寫，林亞澤審定」。
LYRICS_CREDIT = 'AI 協助撰寫，林亞澤審定。'
TODO_MARK = '【待確認：歌詞署名與人／AI 分工，作者還沒決定】'

SPOILERS = ['結局', '丈夫', '先生', '過世', '死別', '悲劇', '走失', '運河', '三排十四號', '程希', '玫瑰']

# file, cover, 曲名, 標籤, 一句話, 背景 CG（照劇情順序，一首 1 到 2 張）, 長度
TRACKS = [
    ('ember-studio', 'studio', '餘燼', '錄音室版', '錄音室收音的版本，收音乾淨。', ['bg-soundcheck-1', 'bg-soundcheck-2'], '4:10'),
    ('ember-audience', 'audience', '餘燼', '台下跟唱版', '台下的人跟著一起唱，收音比較遠，雜訊多一些。', ['bg-prologue-1', 'bg-prologue-3'], '3:56'),
    ('ember-harmony', 'harmony', '餘燼', '合聲版', '加了合聲的編曲。', ['bg-soundcheck-4'], '3:50'),
    ('ember-chorus', 'chorus', '餘燼', '演唱會大合唱', '演唱會現場的大合唱，台下收音很好，中間有一段只剩台下的人在唱。', ['bg-concert-2', 'bg-concert-3'], '4:06'),
    ('goodnight-tainan', 'night', '晚安，台南', '2023', '她停演前寫的最後一首新歌，寫給家鄉。', ['bg-dress-1', 'bg-canal-1'], '3:25'),
    ('harbor-lights', 'harbor', '港邊的燈', '台語老歌', '劇中是父親魚攤的收音機在放的那首台語老歌。', ['bg-canal-2'], '2:03'),
]
BG_WHY = {}

CSS = """:root{color-scheme:dark;--bg:#140b07;--panel:rgba(26,13,7,.66);--ink:#fbeedd;--muted:#d6bfa4;--amber:#ffab4d;--rose:#d9455a;--line:rgba(255,171,77,.28);
  --serif:"Noto Serif TC","Songti TC","PMingLiU",serif;--sans:"Noto Sans TC","PingFang TC","Microsoft JhengHei",system-ui,sans-serif}
*{box-sizing:border-box}
html{color-scheme:dark}
body{margin:0;background:var(--bg);color:var(--ink);font:400 17px/1.85 var(--sans);-webkit-font-smoothing:antialiased;overflow-x:hidden}
a{color:var(--amber);overflow-wrap:anywhere}
.stage{position:fixed;left:0;top:0;width:100%;height:100vh;height:100lvh;z-index:-2;overflow:hidden;background:var(--bg)}
.stage i{position:absolute;inset:0;background-size:cover;background-position:center;opacity:0;transition:opacity 1.6s ease;will-change:opacity,transform}
.stage i.on{opacity:1;animation:push 40s ease-out forwards}
@keyframes push{from{transform:scale(1)}to{transform:scale(1.09)}}
.shade{position:fixed;inset:0;z-index:-1;background:linear-gradient(180deg,rgba(20,11,7,.28),rgba(20,11,7,.4) 45%,rgba(20,11,7,.8))}
.top{display:flex;align-items:center;gap:18px;height:56px;padding:0 16px;max-width:1080px;margin:0 auto}
.top b{font:900 17px/1 var(--serif);letter-spacing:.08em;margin-right:auto;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.top a{font:500 14px/1 var(--sans);text-decoration:none;white-space:nowrap}
main{width:min(1080px,calc(100% - 32px));margin:0 auto;padding:24px 0 120px}
.tag{font:700 13px/1 var(--sans);letter-spacing:.3em;color:#ff6b80;text-shadow:0 1px 8px rgba(0,0,0,.9)}
h1{margin:12px 0 18px;font:900 clamp(30px,5vw,52px)/1.25 var(--serif);letter-spacing:.04em;text-shadow:0 2px 24px rgba(0,0,0,.6)}
h2{margin:44px 0 6px;font:900 clamp(22px,3vw,30px)/1.4 var(--serif)}
.lead{max-width:36em;margin:0 0 10px;text-shadow:0 1px 12px rgba(0,0,0,.7)}
.sub{max-width:40em;margin:0 0 18px;color:#ecd8bf;font-size:15.5px;text-shadow:0 1px 10px rgba(0,0,0,.85)}
.player{background:var(--panel);box-shadow:inset 0 0 0 1px var(--line);backdrop-filter:blur(10px);padding:22px;margin-top:26px}
.now{display:grid;grid-template-columns:160px 1fr;gap:22px;align-items:center}
.art{width:160px;height:160px;object-fit:cover;box-shadow:0 8px 30px rgba(0,0,0,.5)}
.player.playing .art{box-shadow:0 0 0 2px var(--amber),0 8px 30px rgba(0,0,0,.5)}
.meta{min-width:0}
.meta small{font:600 12px/1 var(--sans);letter-spacing:.22em;color:var(--rose)}
.meta b{display:block;margin:8px 0 2px;font:900 clamp(22px,3vw,30px)/1.3 var(--serif)}
.meta .ver{color:var(--amber);font-size:15px}
.meta .one{margin:6px 0 0;color:#ead7bf;font-size:15px;line-height:1.7}
.bar{display:flex;align-items:center;gap:12px;margin:18px 0 12px;font:500 13px/1 var(--sans);color:var(--muted)}
.bar input{flex:1;min-width:0;accent-color:var(--amber);height:4px;cursor:pointer}
.ctl{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.ctl button{min-width:44px;height:44px;border:1px solid var(--line);background:rgba(255,171,77,.08);color:var(--amber);font:16px/1 var(--sans);cursor:pointer;padding:0 12px}
.ctl button.big{width:60px;background:var(--amber);color:#1a0d05;font-size:18px}
.ctl button:hover{border-color:var(--amber)}
.ctl .clean{margin-left:auto;font-size:14px}
.list{list-style:none;margin:20px 0 0;padding:0;border-top:1px solid var(--line)}
.list button{display:grid;grid-template-columns:28px 56px minmax(0,1fr) auto;gap:14px;align-items:center;width:100%;padding:10px 6px;border:0;border-bottom:1px solid rgba(255,171,77,.12);background:none;color:var(--ink);text-align:left;cursor:pointer;font:inherit}
.list button:hover{background:rgba(255,171,77,.08)}
.list em{font:500 13px/1 var(--sans);color:var(--muted);font-style:normal;text-align:right}
.list img{width:56px;height:56px;object-fit:cover}
.list b{display:block;font:700 15.5px/1.4 var(--sans);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.list small{display:block;color:var(--muted);font-size:13px;line-height:1.5;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.list i{font:500 13px/1 var(--sans);color:var(--muted);font-style:normal}
.list li.on b,.list li.on em{color:var(--amber)}
.list li.live em::before{content:"▶ "}
.note{margin-top:22px;font-size:15px;color:var(--muted);max-width:44em}
.todo{display:inline-block;padding:4px 10px;background:#b3202f;color:#fff;font-weight:700}
footer.end{margin-top:70px;padding:30px 0 20px;border-top:1px solid var(--line);color:var(--muted);font-size:14px;text-align:center}
body.clean main>*:not(.player){display:none}
body.clean .player .list,body.clean .player .one{display:none}
body.clean .shade{background:linear-gradient(180deg,rgba(20,11,7,.05),rgba(20,11,7,.15) 60%,rgba(20,11,7,.6))}
@media (max-width:640px){
  body{font-size:16px}
  .player{padding:16px}
  .now{grid-template-columns:96px 1fr;gap:14px}
  .art{width:96px;height:96px}
  .list button{grid-template-columns:22px 48px minmax(0,1fr);gap:10px}
  .list button i{display:none}.list img{width:48px;height:48px}
  .ctl .clean{margin-left:0}
}
@media (prefers-reduced-motion:reduce){.stage i{transition:none}.stage i.on{animation:none}}"""


def u(p): return H.escape(BASE + p, quote=True)


def check_spoilers():
    text = '\n'.join(t[4] + t[3] + t[2] for t in TRACKS)
    hit = [w for w in SPOILERS if w in text]
    if hit: sys.exit(f'不產生：一句話裡有劇透字眼 {hit}')


def build(draft):
    check_spoilers()
    if LYRICS_CREDIT is None:
        if not draft:
            sys.exit('不產生：歌詞署名還沒決定（site/build_music.py 的 LYRICS_CREDIT）。預覽請加 --draft。')
        credit = f'<span class="todo">{H.escape(TODO_MARK)}</span>'
    else:
        credit = H.escape(LYRICS_CREDIT)
    items = []
    for i, (f, c, name, ver, line, bgs, dur) in enumerate(TRACKS):
        label = f'{name}　{ver}' if name == '餘燼' else name
        items.append(f'<li><button type="button" data-i="{i}"><em>{i + 1:02d}</em><img src="{u("media/cover-" + c + ".webp")}" alt="" loading="lazy"><span><b>{H.escape(label)}</b><small>{H.escape(line)}</small></span><i>{dur}</i></button></li>')
    data = [dict(f=u('music/' + t[0] + '.mp3'), c=u('media/cover-' + t[1] + '.webp'), n=t[2], v=t[3], l=t[4], bg=[u('media/' + b + '.webp') for b in t[5]], d=t[6]) for t in TRACKS]
    import json
    page = f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="color-scheme" content="dark">
<title>原聲帶 · 最終遺忘的橘色餘燼</title>
<meta name="description" content="《最終遺忘的橘色餘燼》的原聲帶：〈餘燼〉的四種版本、〈晚安，台南〉、〈港邊的燈〉。歌曲由 Suno 生成。">
<meta name="theme-color" content="#140b07">
<link rel="canonical" href="https://yazelin.github.io/larch-ember/music.html">
<meta property="og:title" content="原聲帶 · 最終遺忘的橘色餘燼">
<meta property="og:image" content="https://yazelin.github.io/larch-ember/media/og.jpg">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&family=Noto+Serif+TC:wght@500;700;900&display=swap">
<style>{CSS}</style>
</head>
<body>
<div class="stage" id="stage" aria-hidden="true"><i id="bgA"></i><i id="bgB"></i></div>
<div class="shade" aria-hidden="true"></div>
<header class="top"><b>最終遺忘的橘色餘燼</b><a href="index.html">故事與參考資料</a><a href="music.html" aria-current="page">原聲帶</a></header>
<main>
  <div class="tag">SOUNDTRACK</div>
  <h1>原聲帶</h1>
  <p class="lead">六首，三首歌。〈餘燼〉有四個版本，另外是〈晚安，台南〉與〈港邊的燈〉。</p>
  <p class="sub">四個〈餘燼〉是同一首歌的四種編曲，歌詞相同，是余靜 2008 年的成名曲。播放時背景會換成作品裡的畫面，按「收起介面」可以只留畫面與播放器。</p>
  <section class="player" id="player" aria-label="播放器">
    <div class="now">
      <img class="art" id="art" src="" alt="">
      <div class="meta">
        <small id="no">TRACK 01 / 06</small>
        <b id="title"></b><span class="ver" id="ver"></span>
        <p class="one" id="one"></p>
      </div>
    </div>
    <div class="bar"><span id="cur">0:00</span><input id="seek" type="range" min="0" max="1000" value="0" aria-label="播放進度"><span id="dur"></span></div>
    <div class="ctl">
      <button type="button" id="prev" aria-label="上一首">⏮</button>
      <button type="button" id="play" class="big" aria-label="播放">▶</button>
      <button type="button" id="next" aria-label="下一首">⏭</button>
      <button type="button" id="clean" class="clean" aria-pressed="false">收起介面</button>
    </div>
    <ol class="list" id="list">{''.join(items)}</ol>
  </section>
  <p class="note">歌曲：Suno 生成。歌詞：{credit}</p>
  <p class="note">故事、人物與參考資料在<a href="index.html">首頁</a>。這些歌是劇中的歌，劇中人物與事件都是虛構的。</p>
  <footer class="end">最終遺忘的橘色餘燼 · 林亞澤 · 2026 · <a href="index.html">回首頁</a></footer>
</main>
<script>
(function () {{
  var T = {json.dumps(data, ensure_ascii=False)};
  var $ = function (id) {{ return document.getElementById(id); }};
  var audio = new Audio(); audio.preload = "none";
  var cur = 0, loaded = -1, seeking = false, front = "bgA", slide = -1, lastKey = "";
  var fmt = function (t) {{ t = Math.max(0, Math.floor(t || 0)); return Math.floor(t / 60) + ":" + String(t % 60).padStart(2, "0"); }};
  var items = [].slice.call(document.querySelectorAll("#list button"));
  // 背景：兩層交叉淡化，一首歌 1 到 2 張，照劇情順序，過半換下一張
  function setBg(src) {{
    var key = src; if (key === lastKey) return; lastKey = key;
    var next = front === "bgA" ? "bgB" : "bgA", n = $(next), f = $(front);
    n.style.backgroundImage = 'url("' + src + '")'; n.classList.remove("on"); void n.offsetWidth; n.classList.add("on");
    f.classList.remove("on"); front = next;
  }}
  function bgFor(i, t) {{
    var bg = T[i].bg, k = 0;
    if (bg.length > 1 && audio.duration && loaded === i && t > audio.duration / 2) k = 1;
    setBg(bg[k]);
  }}
  function show(i) {{
    cur = i; var t = T[i];
    $("no").textContent = "TRACK " + String(i + 1).padStart(2, "0") + " / 06";
    $("title").textContent = t.n; $("ver").textContent = t.n === "餘燼" ? t.v : (t.v === "2023" ? "2023" : t.v);
    $("one").textContent = t.l; $("art").src = t.c; $("art").alt = t.n + " " + t.v + " 專輯封面";
    if (loaded !== i) {{ $("dur").textContent = t.d; $("cur").textContent = "0:00"; $("seek").value = 0; }}
    lastKey = ""; bgFor(i, 0); sync();
  }}
  function play(i) {{
    if (loaded !== i) {{ show(i); audio.src = T[i].f; loaded = i; }}
    audio.play().catch(function () {{}});
  }}
  function sync() {{
    var on = !audio.paused;
    $("play").textContent = on ? "❚❚" : "▶"; $("play").setAttribute("aria-label", on ? "暫停" : "播放");
    $("player").classList.toggle("playing", on);
    items.forEach(function (b, i) {{ var li = b.parentNode; li.classList.toggle("on", i === cur); li.classList.toggle("live", i === cur && on); }});
  }}
  items.forEach(function (b, i) {{ b.addEventListener("click", function () {{ if (i === cur && loaded === i && !audio.paused) audio.pause(); else {{ if (loaded !== i) show(i); play(i); }} }}); }});
  $("play").addEventListener("click", function () {{ if (!audio.paused) audio.pause(); else play(cur); }});
  $("prev").addEventListener("click", function () {{ if (audio.currentTime > 3 && loaded === cur) {{ audio.currentTime = 0; return; }} var i = (cur + T.length - 1) % T.length; show(i); if (!audio.paused || loaded === i) play(i); else if (loaded !== i) {{ }} }});
  $("next").addEventListener("click", function () {{ var i = (cur + 1) % T.length; var was = !audio.paused; show(i); if (was) play(i); }});
  audio.addEventListener("ended", function () {{ var i = (cur + 1) % T.length; show(i); play(i); }});
  audio.addEventListener("loadedmetadata", function () {{ $("dur").textContent = fmt(audio.duration); }});
  audio.addEventListener("timeupdate", function () {{
    if (seeking || !audio.duration) return;
    $("cur").textContent = fmt(audio.currentTime); $("seek").value = Math.round(audio.currentTime / audio.duration * 1000);
    bgFor(cur, audio.currentTime);
  }});
  $("seek").addEventListener("input", function () {{ seeking = true; if (audio.duration) $("cur").textContent = fmt(this.value / 1000 * audio.duration); }});
  $("seek").addEventListener("change", function () {{ seeking = false; if (loaded !== cur) {{ play(cur); return; }} if (audio.duration) audio.currentTime = this.value / 1000 * audio.duration; }});
  audio.addEventListener("play", sync); audio.addEventListener("pause", sync);
  $("clean").addEventListener("click", function () {{
    var on = !document.body.classList.contains("clean");
    document.body.classList.toggle("clean", on); this.setAttribute("aria-pressed", on); this.textContent = on ? "顯示介面" : "收起介面";
  }});
  show(0);
}})();
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
