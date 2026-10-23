/* 〈餘燼〉MV。MV 由 site/build_mv.py 從 site/mv_storyboard.json 注入。
   網址參數：song=ember-b|ember-c|ember-a，embed=1（嵌進遊戲：不顯示署名、沒有任何連結、右下「繼續」）。
   播完或按「繼續」送 {type:'larch:mv:done', song} 給父層；載入時送 {type:'larch:mv:ready', song}。
   父層是 Larch 的小遊戲卡（沙盒 iframe），來源會是 'null'，所以一律用 '*' 送。 */
const Q = new URLSearchParams(location.search);
const KEY = MV[Q.get('song')] ? Q.get('song') : 'ember-b';
const SONG = MV[KEY];
const EMBED = Q.get('embed') === '1';
const reduced = matchMedia('(prefers-reduced-motion:reduce)').matches;
const lowEnd = matchMedia('(pointer:coarse)').matches || (navigator.hardwareConcurrency || 4) <= 4;
const $ = id => document.getElementById(id);
if (EMBED) document.body.classList.add('embed');
$('stitle').textContent = SONG.title;
$('sub').textContent = SONG.status === 'done' ? '' : '分鏡排列中';
const tell = type => { if (window.parent !== window) try { parent.postMessage({ type, song: KEY }, '*'); } catch (_) {} };
tell('larch:mv:ready');

const au = new Audio(); au.preload = 'auto'; au.src = SONG.audio;
SONG.shots.forEach(s => { const im = new Image(); im.src = s.img; });
let lines = [];
fetch(SONG.lrc).then(r => r.text()).then(t => {
  for (const raw of t.split('\n')) { const m = raw.match(/^\[(\d+):(\d+(?:\.\d+)?)\](.*)$/); if (m) lines.push({ t: +m[1] * 60 + parseFloat(m[2]), text: m[3].trim() }); }
}).catch(() => {});

/* ── 畫面：一鏡一張，交叉淡化，推鏡方向照分鏡表 ── */
const MOVES = {
  in: ['scale(1.02)', 'scale(1.13)'], out: ['scale(1.13)', 'scale(1.02)'],
  left: ['translateX(2.5%) scale(1.09)', 'translateX(-2.5%) scale(1.09)'], right: ['translateX(-2.5%) scale(1.09)', 'translateX(2.5%) scale(1.09)'],
};
let shot = -1, front = 'fA';
function showShot(i) {
  if (i === shot) return; shot = i;
  const s = SONG.shots[i], nxt = front === 'fA' ? 'fB' : 'fA', n = $(nxt), f = $(front);
  n.style.backgroundImage = `url("${s.img}")`;
  n.getAnimations().forEach(a => a.cancel());
  if (!reduced) n.animate([{ transform: MOVES[s.move][0] }, { transform: MOVES[s.move][1] }], { duration: (s.t1 - s.t0 + 2) * 1000, easing: 'linear', fill: 'forwards' });
  else n.style.transform = 'scale(1.04)';
  n.classList.add('on'); f.classList.remove('on'); front = nxt;
  document.body.dataset.shot = s.cg;
}
/* ── 歌詞：一次一句，兩層交替淡入；留白那一鏡不上字 ── */
let lyr = -2, lfront = 'lA';
function showLine(text) {
  const nxt = lfront === 'lA' ? 'lB' : 'lA';
  $(lfront).classList.remove('on');
  if (text) { $(nxt).textContent = text; $(nxt).classList.add('on'); lfront = nxt; }
}
function frame() {
  const t = au.currentTime;
  let i = 0; while (i + 1 < SONG.shots.length && SONG.shots[i + 1].t0 <= t) i++;
  showShot(i);
  let k = -1; while (k + 1 < lines.length && lines[k + 1].t <= t) k++;
  const blank = SONG.shots[i].blank;
  const key = blank ? -1 : k;
  if (key !== lyr) { lyr = key; showLine(key >= 0 ? lines[key].text : ''); }
  document.body.dataset.line = key;
  if (SONG.dur - t < 3 && !au.paused) $('black').classList.add('on');
}

/* ── 餘燼：比原聲帶頁克制，數量少、慢慢往上飄 ── */
const fx = $('fx'), g = fx.getContext('2d');
let W = 0, H = 0;
function resize() { const d = Math.min(devicePixelRatio || 1, 1.5); W = innerWidth; H = innerHeight; fx.width = Math.round(W * d); fx.height = Math.round(H * d); g.setTransform(d, 0, 0, d, 0, 0); }
addEventListener('resize', resize); resize();
const spr = document.createElement('canvas'); spr.width = spr.height = 32;
{ const c = spr.getContext('2d'), gr = c.createRadialGradient(16, 16, 0, 16, 16, 16); gr.addColorStop(0, 'rgba(255,230,180,1)'); gr.addColorStop(.3, 'rgba(255,160,60,.6)'); gr.addColorStop(1, 'rgba(255,110,30,0)'); c.fillStyle = gr; c.fillRect(0, 0, 32, 32); }
const bits = [], MAX = lowEnd ? 10 : 22;
let prev = performance.now();
function tick(now) {
  const dt = Math.min((now - prev) / 1000, .05); prev = now;
  if (!au.paused) frame();
  if (!reduced) {
    g.clearRect(0, 0, W, H);
    const sp = au.paused ? .3 : 1;
    if (bits.length < MAX && Math.random() < dt * 2.2 * sp) bits.push({ x: Math.random() * W, y: H + 10, vy: -(18 + Math.random() * 30), s: 2 + Math.random() * 4, ph: Math.random() * 6.3, life: 9 + Math.random() * 5, age: 0 });
    g.globalCompositeOperation = 'lighter';
    for (let i = bits.length - 1; i >= 0; i--) {
      const p = bits[i]; p.age += dt * sp; p.ph += dt * sp;
      if (p.age > p.life || p.y < -20) { bits.splice(i, 1); continue; }
      p.y += p.vy * dt * sp; p.x += Math.sin(p.ph) * 10 * dt * sp;
      g.globalAlpha = .5 * Math.min(1, p.age / .8) * Math.min(1, (p.life - p.age) / 1.5);
      const s = p.s * 2.4; g.drawImage(spr, p.x - s / 2, p.y - s / 2, s, s);
    }
    g.globalAlpha = 1; g.globalCompositeOperation = 'source-over';
  }
  requestAnimationFrame(tick);
}
requestAnimationFrame(tick);
showShot(0);

/* ── 播放、繼續、結束 ── */
let done = false;
function finish() { if (done) return; done = true; tell('larch:mv:done'); if (!EMBED) $('again').hidden = false; }
$('go').onclick = () => {
  au.play().then(() => { $('start').classList.add('gone'); if (EMBED) $('next').hidden = false; }).catch(() => { $('sub').textContent = '音樂載入不了，請再按一次'; });
};
$('next').onclick = () => { au.pause(); finish(); };
$('again').onclick = () => { done = false; $('again').hidden = true; $('black').classList.remove('on'); au.currentTime = 0; shot = -1; lyr = -2; au.play(); };
au.onended = () => { $('black').classList.add('on'); finish(); };
addEventListener('keydown', e => {
  if (e.code === 'Space' || e.key === 'Enter') { e.preventDefault(); if ($('start').classList.contains('gone')) { au.paused ? au.play() : au.pause(); } else $('go').click(); }
  else if (['Backspace', 'BrowserBack'].includes(e.key) || (e.altKey && e.key.startsWith('Arrow'))) e.preventDefault();   // 按鍵不能把畫面帶離這頁
});
