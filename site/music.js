/* 原聲帶頁。TRACKS 由 site/build_music.py 注入。
   版面與歌詞行為照 neko-tensei/music.html；頻譜環、依段落換色、AnalyserNode 與節拍偵測照 omotenashi-hell；
   粒子是這個作品自己的：往上飄的餘燼與緩緩落下的深紅花瓣。 */
const $ = id => document.getElementById(id);
const root = document.documentElement;
const reduced = matchMedia('(prefers-reduced-motion:reduce)').matches;
const coarse = matchMedia('(pointer:coarse)').matches;
const lowEnd = coarse || (navigator.hardwareConcurrency || 4) <= 4 || (navigator.deviceMemory || 4) <= 2;
let quality = lowEnd ? .45 : 1;          // 粒子數量係數；下面會依實際幀間隔再往下調
const au = new Audio();
au.preload = 'none';
au.crossOrigin = 'anonymous';             // 接 AnalyserNode 需要 CORS；音檔改走 jsDelivr 時它也會回 ACAO *
let corsOk = true;
const linesEl = $('lines'), lyricsEl = $('lyrics'), art = $('art');
let ti = 0, lrc = [], active = -1, loaded = -1, secs = [], dynMode = false;

/* ── 段落 → 主色。CSS 用 var(--acc)，canvas 用同一組 RGB ── */
const SEC = {
  v: [255, 171, 77],    // Verse：暖橘
  p: [255, 200, 128],   // Pre-Chorus：淺橘
  c: [255, 104, 62],    // Chorus：亮橘紅
  b: [238, 198, 150],   // Bridge：柔和琥珀
  f: [255, 232, 160],   // Final Chorus：最亮
  o: [228, 142, 88],    // Outro：餘溫
};
const secKey = s => !s ? 'v' : s.startsWith('Pre-Chorus') ? 'p' : s.startsWith('Final') ? 'f' : s.startsWith('Chorus') ? 'c' : s.startsWith('Bridge') ? 'b' : s.startsWith('Outro') ? 'o' : 'v';
let accent = SEC.v.slice(), target = SEC.v, heat = 0, isChorus = false;

/* ── 歌詞 ── */
function parseLrc(text) {
  const out = [];
  for (const raw of text.split('\n')) {
    const m = raw.match(/^\[(\d+):(\d+(?:\.\d+)?)\](.*)$/);
    if (m) out.push({ t: +m[1] * 60 + parseFloat(m[2]), text: m[3].trim() });
  }
  return out.sort((a, b) => a.t - b.t);
}
function buildLyrics(i) {
  const t = TRACKS[i];
  linesEl.innerHTML = '';
  active = -1; lrc = []; secs = t.secs || [];
  linesEl.style.transform = 'translateY(0)';
  const staticMode = () => {
    dynMode = false; lyricsEl.classList.add('static'); lyricsEl.scrollTop = 0;
    t.text.forEach(tx => { const li = document.createElement('li'); li.textContent = tx; linesEl.appendChild(li); });
  };
  if (!t.dyn) return staticMode();
  lyricsEl.classList.remove('static'); dynMode = true;
  fetch(t.lrc).then(r => { if (!r.ok) throw 0; return r.text(); }).then(text => {
    if (ti !== i) return;
    lrc = parseLrc(text);
    if (!lrc.length) throw 0;
    linesEl.innerHTML = '';
    lrc.forEach((ln, k) => {
      const li = document.createElement('li');
      li.textContent = ln.text; li.className = 'link';
      li.onclick = () => { if (loaded !== i) load(i); au.currentTime = ln.t + .01; if (au.paused) au.play().catch(() => {}); wake(); };
      linesEl.appendChild(li);
    });
    paintLyrics(au.currentTime, true);
  }).catch(() => { if (ti === i) { linesEl.innerHTML = ''; staticMode(); } });
}
function paintLyrics(now, force) {
  if (!dynMode || !lrc.length) return;
  let i = -1;
  while (i + 1 < lrc.length && lrc[i + 1].t <= now) i++;
  if (i === active && !force) return;
  active = i;
  const kids = linesEl.children;
  for (let k = 0; k < kids.length; k++)
    kids[k].className = 'link' + (k === i ? ' on' : (Math.abs(k - i) === 1 ? ' near' : ''));
  const cur = kids[i];
  if (!cur) { linesEl.style.transform = 'translateY(0)'; return; }
  linesEl.style.transform = `translateY(${lyricsEl.clientHeight / 2 - cur.offsetTop - cur.offsetHeight / 2}px)`;
  const k = secKey(secs[i]);
  target = SEC[k]; isChorus = k === 'c' || k === 'f';
  if (!au.paused) { const [cx, cy] = artCenter(); burst(cx, cy, 5, .5); }
}

/* ── 背景：兩層交叉淡化＋慢推鏡 ── */
let front = 'bgA', lastBg = '';
function setBg(src) {
  if (src === lastBg) return; lastBg = src;
  const nxt = front === 'bgA' ? 'bgB' : 'bgA', n = $(nxt), f = $(front);
  n.style.backgroundImage = `url("${src}")`;
  n.classList.remove('on'); void n.offsetWidth; n.classList.add('on');
  f.classList.remove('on'); front = nxt;
}
function bgFor(i, force) {
  const bg = TRACKS[i].bg;
  const k = (bg.length > 1 && loaded === i && au.duration && au.currentTime > au.duration / 2) ? 1 : 0;
  if (force) lastBg = '';
  setBg(bg[k]);
}

/* ── 控制 ── */
const fmt = s => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;
const bar = $('bar');
const PLAY = 'M8 5v14l11-7z', PAUSE = 'M7 5h3.5v14H7zm6.5 0H17v14h-3.5z';
const setIcon = d => { document.querySelectorAll('.picon').forEach(p => p.setAttribute('d', d)); $('play').setAttribute('aria-label', d === PAUSE ? '暫停' : '播放'); };
const toggle = () => { if (au.paused) { if (loaded !== ti) load(ti); au.play().catch(() => {}); } else au.pause(); };
const trackBtns = [...document.querySelectorAll('#tracks button')];

function show(i) {
  ti = i; const t = TRACKS[i];
  $('no').textContent = `TRACK ${String(i + 1).padStart(2, '0')} / ${String(TRACKS.length).padStart(2, '0')}`;
  $('title').textContent = t.n; $('ver').textContent = t.v === '2023' ? '2023' : t.v;
  $('one').textContent = t.l; $('note').textContent = t.note || ''; $('note').style.display = t.note ? '' : 'none';
  $('artimg').src = t.c; $('artimg').alt = `${t.n} ${t.v} 專輯封面`;
  $('dur').textContent = t.d; $('cur').textContent = '0:00'; bar.value = 0;
  trackBtns.forEach((b, k) => b.parentNode.classList.toggle('on', k === i));
  t.bg.forEach(s => { const im = new Image(); im.src = s; });
  buildLyrics(i); bgFor(i, true);
}
function load(i) {
  if (loaded === i) return;
  show(i);
  corsOk = true; au.crossOrigin = 'anonymous';
  au.src = TRACKS[i].f; loaded = i;
}
function go(i, autoplay) { load(i); if (autoplay) au.play().catch(() => {}); }
trackBtns.forEach((b, i) => b.onclick = () => { if (i === ti && loaded === i) toggle(); else go(i, true); wake(); });
$('play').onclick = toggle; art.onclick = toggle;
$('prev').onclick = () => { if (au.currentTime > 3 && loaded === ti) { au.currentTime = 0; return; } go((ti + TRACKS.length - 1) % TRACKS.length, !au.paused); };
$('next').onclick = () => go((ti + 1) % TRACKS.length, !au.paused);
au.onplay = () => { setIcon(PAUSE); startAudioGraph(); wake(); };
au.onpause = () => { setIcon(PLAY); document.body.classList.remove('idle'); };
au.onended = () => go((ti + 1) % TRACKS.length, true);
au.onloadedmetadata = () => { $('dur').textContent = fmt(au.duration); };
au.onerror = () => {      // CORS 模式載入失敗就退回一般載入（頻譜改走模擬）
  if (corsOk && au.crossOrigin) { corsOk = false; au.removeAttribute('crossorigin'); au.src = TRACKS[ti].f; au.play().catch(() => {}); }
};
bar.oninput = () => { if (au.duration) { if (loaded !== ti) load(ti); au.currentTime = bar.value / 1000 * au.duration; } };
addEventListener('keydown', e => {
  if (e.target.tagName === 'INPUT') return;
  if (e.code === 'Space') { e.preventDefault(); toggle(); }
  else if (e.code === 'ArrowRight') au.currentTime = Math.min(au.duration || 0, au.currentTime + 5);
  else if (e.code === 'ArrowLeft') au.currentTime = Math.max(0, au.currentTime - 5);
  wake();
});
function toast(msg) {
  const h = $('hint'); h.textContent = msg; h.classList.add('show');
  clearTimeout(toast.t); toast.t = setTimeout(() => h.classList.remove('show'), 4800);
}
$('hide').onclick = () => { document.body.classList.add('hold'); $('show').hidden = false; };
$('show').onclick = () => { document.body.classList.remove('hold'); $('show').hidden = true; wake(); };

/* ── 音訊分析：只在桌機接 Web Audio（Android 關螢幕會掛起 AudioContext 直接斷音）；AudioContext 要在使用者手勢（播放）之後才建 ── */
let analyser = null, freq = null, graphTried = false;
function startAudioGraph() {
  if (graphTried || coarse || reduced || !corsOk) return;
  graphTried = true;
  try {
    const ac = new (window.AudioContext || window.webkitAudioContext)();
    const src = ac.createMediaElementSource(au);
    analyser = ac.createAnalyser(); analyser.fftSize = 256; analyser.smoothingTimeConstant = .75;
    src.connect(analyser); analyser.connect(ac.destination);
    freq = new Uint8Array(analyser.frequencyBinCount);
    ac.resume();
  } catch (_) { analyser = null; }
}
/* 接不上 analyser（手機、跨來源沒有 CORS）就用模擬的節拍，只隨播放狀態動 */
function fakeSpectrum(t) {
  const BEAT = .62, ph = (t % BEAT) / BEAT, env = Math.exp(-ph * 4);
  return { bass: env * .55, band: i => env * (.25 + .4 * Math.abs(Math.sin(i * 1.7 + t * 2.3))) };
}

/* ── 特效層：頻譜環、節拍衝擊波、餘燼與花瓣 ── */
const fx = $('fx'), g = fx.getContext('2d');
let W = 0, H = 0, dpr = 1;
function resize() {
  dpr = Math.min(devicePixelRatio || 1, lowEnd ? 1.5 : 2);
  W = innerWidth; H = innerHeight;
  fx.width = Math.round(W * dpr); fx.height = Math.round(H * dpr);
  g.setTransform(dpr, 0, 0, dpr, 0, 0);
}
addEventListener('resize', resize); resize();
const spr = document.createElement('canvas'); spr.width = spr.height = 48;
{ const c = spr.getContext('2d'), gr = c.createRadialGradient(24, 24, 0, 24, 24, 24);
  gr.addColorStop(0, 'rgba(255,236,190,1)'); gr.addColorStop(.25, 'rgba(255,168,70,.75)'); gr.addColorStop(1, 'rgba(255,110,30,0)');
  c.fillStyle = gr; c.fillRect(0, 0, 48, 48); }
const bits = [], waves = [];
const artCenter = () => { const r = art.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; };
const maxEmber = () => Math.round(70 * quality), maxPetal = () => Math.max(3, Math.round(9 * quality));
function ember(x, y, vx, vy, size, life) { bits.push({ k: 0, x, y, vx, vy, size, life, age: 0, ph: Math.random() * 6.28 }); }
function petal(x, y, vx, vy) { bits.push({ k: 1, x, y, vx: vx ?? (Math.random() - .5) * 20, vy: vy ?? 24 + Math.random() * 30, size: 7 + Math.random() * 7, life: 16, age: 0, ph: Math.random() * 6.28, rot: Math.random() * 6.28, vrot: (Math.random() - .5) * 1.6 }); }
function burst(x, y, n, power = 1) {      // 點一下、換一句：一小撮餘燼，偶爾夾一片花瓣
  if (reduced) return;
  n = Math.max(1, Math.round(n * (lowEnd ? .6 : 1)));
  for (let i = 0; i < n; i++) {
    const a = Math.random() * 6.28, s = (60 + Math.random() * 170) * power;
    ember(x, y, Math.cos(a) * s, Math.sin(a) * s - 50, 4 + Math.random() * 7, 1.6 + Math.random() * 1.4);
  }
  if (Math.random() < .5 && bits.length < 200) petal(x, y, (Math.random() - .5) * 90, -20 + Math.random() * 20);
  while (bits.length > 220) bits.shift();
}
const mouse = { x: -999, y: -999, down: false, last: 0 };
function wake() {
  document.body.classList.remove('idle');
  clearTimeout(wake.t);
  wake.t = setTimeout(() => { if (!au.paused) document.body.classList.add('idle'); }, 2600);
}
addEventListener('pointermove', e => {
  mouse.x = e.clientX; mouse.y = e.clientY;
  if (!reduced) {
    root.style.setProperty('--px', ((e.clientX / W) * 2 - 1).toFixed(3));
    root.style.setProperty('--py', ((e.clientY / H) * 2 - 1).toFixed(3));
  }
  const now = performance.now();
  if (mouse.down && now - mouse.last > 60) { mouse.last = now; burst(e.clientX, e.clientY, 2, .4); }
  wake();
});
addEventListener('pointerdown', e => {
  mouse.down = true;
  if (!e.target.closest('button,input,a')) {
    burst(e.clientX, e.clientY, 12);
    if (!reduced) waves.push({ x: e.clientX, y: e.clientY, r: 8, a: .5 });
  }
  wake();
});
addEventListener('pointerup', () => mouse.down = false);
addEventListener('pointerleave', () => { mouse.x = mouse.y = -999; mouse.down = false; });

const hist = []; let lastBeat = 0, kick = 1;
function detectBeat(bass, now) {
  hist.push(bass); if (hist.length > 60) hist.shift();
  const avg = hist.reduce((a, b) => a + b, 0) / hist.length;
  if (bass > avg * 1.32 && bass > .22 && now - lastBeat > 240) { lastBeat = now; return true; }
  return false;
}

let prev = performance.now(), bassS = 0, slow = 0, frames = 0;
function tick(now) {
  const dt = Math.min((now - prev) / 1000, .05); prev = now;
  const playing = !au.paused;
  if (playing && au.duration) {
    bar.value = au.currentTime / au.duration * 1000;
    $('cur').textContent = fmt(au.currentTime);
    bgFor(ti, false);
  }
  paintLyrics(au.currentTime);
  /* 主色與強度用同一個係數逼近：換段是滑過去，不是跳過去 */
  const ease = Math.min(1, dt * 1.8);
  for (let i = 0; i < 3; i++) accent[i] += (target[i] - accent[i]) * ease;
  heat += ((isChorus && playing ? 1 : 0) - heat) * Math.min(1, dt * 1.2);
  const A = accent.map(Math.round);
  root.style.setProperty('--acc', `rgb(${A[0]},${A[1]},${A[2]})`);
  root.style.setProperty('--acc-rgb', `${A[0]},${A[1]},${A[2]}`);

  let bass = 0, band = () => 0;
  if (analyser && playing) {
    analyser.getByteFrequencyData(freq);
    for (let i = 0; i < 6; i++) bass = Math.max(bass, freq[i] / 255);
    band = i => freq[Math.min(freq.length - 1, 2 + i * 2)] / 255;
  } else if (playing) { const f = fakeSpectrum(au.currentTime); bass = f.bass; band = f.band; }
  bassS += (bass - bassS) * Math.min(1, dt * 10);
  root.style.setProperty('--pulse', (reduced ? 0 : bassS + heat * .15).toFixed(3));

  if (reduced) { requestAnimationFrame(tick); return; }

  const [cx, cy] = artCenter();
  if (playing && detectBeat(bass, now)) {
    kick = 1.04;
    waves.push({ x: cx, y: cy, r: art.offsetWidth * .52, a: .3 });
    burst(cx, cy, 2 + Math.round(heat * 3), .5);
  }
  kick += (1 - kick) * Math.min(1, dt * 9);
  root.style.setProperty('--kick', kick.toFixed(4));

  g.clearRect(0, 0, W, H);
  /* 頻譜環：繞著封面往外長，左右對稱；宽螢幕上封面靠左，不夾住整圈會被畫面左緣切掉 */
  const aw = art.offsetWidth, room = Math.min(cx, cy) - 8;
  const R = Math.max(aw * .52, Math.min(aw * .72, room - aw * .22 - 5)), N = lowEnd ? 48 : 72;
  g.save(); g.translate(cx, cy);
  g.beginPath(); g.arc(0, 0, R - 5, 0, 6.283);
  g.strokeStyle = `rgba(${A[0]},${A[1]},${A[2]},${.07 + bassS * .15})`; g.lineWidth = 1; g.stroke();
  g.lineCap = 'round'; g.lineWidth = lowEnd ? 4 : 5;
  for (let i = 0; i < N; i++) {
    const v = band(Math.round((i < N / 2 ? i : N - 1 - i) * 72 / N * .5));
    const len = 4 + v * aw * .24;
    g.save(); g.rotate((i / N) * 6.283 - 1.5708);
    if (lowEnd) g.strokeStyle = `rgba(${A[0]},${A[1]},${A[2]},${.25 + v * .5})`;
    else { const gr = g.createLinearGradient(0, -R, 0, -R - len); gr.addColorStop(0, `rgba(${A[0]},${A[1]},${A[2]},${.22 + v * .55})`); gr.addColorStop(1, `rgba(255,120,50,${.05 + v * .5})`); g.strokeStyle = gr; }
    g.beginPath(); g.moveTo(0, -R); g.lineTo(0, -R - len); g.stroke(); g.restore();
  }
  g.restore();
  for (let i = waves.length - 1; i >= 0; i--) {
    const w = waves[i]; w.r += dt * 480; w.a -= dt * .8;
    if (w.a <= 0) { waves.splice(i, 1); continue; }
    g.beginPath(); g.arc(w.x, w.y, w.r, 0, 6.283); g.strokeStyle = `rgba(${A[0]},${A[1]},${A[2]},${w.a})`; g.lineWidth = 2; g.stroke();
  }

  /* 餘燼往上飄、花瓣往下落。播放時才全速，暫停時放慢（不是停格） */
  const sp = playing ? 1 : .22;
  let ne = 0, np = 0;
  for (const b of bits) b.k ? np++ : ne++;
  if (ne < maxEmber() && Math.random() < dt * (playing ? 9 + bassS * 40 + heat * 10 : 2.5) * quality)
    ember(Math.random() * W, H + 12, (Math.random() - .5) * 18, -(28 + Math.random() * 60), 3 + Math.random() * 5, 7 + Math.random() * 5);
  if (np < maxPetal() && Math.random() < dt * (playing ? .5 : .15))
    petal(Math.random() * W, -20);
  g.globalCompositeOperation = 'lighter';
  for (let i = bits.length - 1; i >= 0; i--) {
    const p = bits[i];
    if (p.age > p.life || p.y < -60 || p.y > H + 60) { bits.splice(i, 1); continue; }
    p.age += dt * sp; p.ph += dt * sp * 1.6;
    const dx = p.x - mouse.x, dy = p.y - mouse.y, d2 = dx * dx + dy * dy;
    if (d2 < 22000) { const d = Math.max(24, Math.sqrt(d2)), f = (1 - d / 150) * 700; p.vx += (dx / d) * f * dt; p.vy += (dy / d) * f * dt; }
    if (!p.k) {
      p.vx *= 1 - dt * .6; p.vy += (-34 - p.vy) * dt * .35;                 // 打出去的力道會散掉，再慢慢往上飄
      p.x += (p.vx + Math.sin(p.ph) * 14) * dt * sp; p.y += p.vy * dt * sp;
      const fade = Math.min(1, p.age / .4) * Math.min(1, (p.life - p.age) / 1.2);
      g.globalAlpha = Math.max(0, fade) * (.55 + bassS * .45);
      const s = p.size * (1 + bassS * .5) * 2.4;
      g.drawImage(spr, p.x - s / 2, p.y - s / 2, s, s);
    } else {
      p.vx *= 1 - dt * .5; p.vy += (30 - p.vy) * dt * .5;
      p.x += (p.vx + Math.sin(p.ph) * 26) * dt * sp; p.y += p.vy * dt * sp; p.rot += p.vrot * dt * sp;
    }
  }
  g.globalCompositeOperation = 'source-over';
  for (const p of bits) if (p.k) {      // 花瓣用一般混合，深紅才不會被洗成橘白
    const fade = Math.min(1, p.age / .8) * Math.min(1, (p.life - p.age) / 1.2);
    g.save(); g.translate(p.x, p.y); g.rotate(p.rot); g.scale(1, .55 + .45 * Math.abs(Math.sin(p.ph * .8)));
    g.globalAlpha = Math.max(0, fade) * .85; g.fillStyle = '#9b1b2e';
    g.beginPath(); g.ellipse(0, 0, p.size * .55, p.size, 0, 0, 6.283); g.fill();
    g.globalAlpha *= .6; g.fillStyle = '#d6475a'; g.beginPath(); g.ellipse(-p.size * .12, -p.size * .2, p.size * .25, p.size * .5, 0, 0, 6.283); g.fill();
    g.restore();
  }
  g.globalAlpha = 1;

  /* 幀間隔太長就把粒子數量往下調（低階手機不能卡） */
  frames++; if (dt > .034) slow++;
  if (frames >= 90) { if (slow > 30 && quality > .25) quality = Math.max(.25, quality * .6); frames = slow = 0; }
  requestAnimationFrame(tick);
}
requestAnimationFrame(tick);

show(0); wake();
setTimeout(() => toast('點畫面會飄起一小撮餘燼，點歌詞可以跳到那一句，空白鍵播放或暫停'), 1200);
