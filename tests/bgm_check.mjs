// 配樂實測：記下所有音訊播放（<audio> 的 play 事件、audio.play()、Web Audio），看實際換曲的順序。
// 預期：標題曲 → 序幕 dress → 地圖 dressing → 點「鏡子角落的照片」→ mem_love（同一首不重播）→ 回地圖 dressing 接上
// SPEED=8 node tests/bgm_check.mjs（先 python3 src/build.py；測試時不要同時 build）
import { serve, open, sleep } from './lib.mjs';
const s = await serve('dist/project.json');
const hook = () => {
  window.__bgm = window.__bgm || [];
  const push = (kind, el) => { try { window.__bgm.push({ t: Math.round(performance.now()), kind, src: String(el?.currentSrc || el?.src || '').split('/').pop(), ct: Math.round((el?.currentTime || 0) * 10) / 10 }); } catch {} };
  document.addEventListener('play', e => push('play-event', e.target), true);
  const play = HTMLMediaElement.prototype.play;
  HTMLMediaElement.prototype.play = function (...a) { push('play()', this); return play.apply(this, a); };
  if (window.AudioBufferSourceNode) { const st = AudioBufferSourceNode.prototype.start; AudioBufferSourceNode.prototype.start = function (...a) { push('webaudio', null); return st.apply(this, a); }; }
};
const ui = await open(s.base, { width: 1600, height: 900, init: hook });
const { page } = ui;
const log = async () => (await Promise.all(page.frames().map(f => f.evaluate(() => window.__bgm || []).catch(() => [])))).flat().sort((a, b) => a.t - b.t);
const nextBtn = async () => { for (const f of page.frames()) for (const name of ['下一句', '繼續探索', '繼續']) { const b = f.getByRole('button', { name }).filter({ visible: true }); if (await b.count()) return b.first(); } return null; };
const wayBtn = async t => { for (const f of page.frames()) { const b = f.locator('button.rpg-waypoint').filter({ hasText: t }); if (await b.count()) return b.first(); } return null; };
const mark = async what => { const L = await log(); console.log('--', what, '（目前已記', L.length, '筆）'); };
try {
  await ui.clickText('開始遊戲'); await sleep(1500);
  let steps = 0, mirrored = false, idle = 0;
  while (steps++ < 600) {
    const nb = await nextBtn();
    if (nb) { idle = 0; await nb.click({ timeout: 3000 }).catch(() => {}); await sleep(500); continue; }
    if (!mirrored) { const w = await wayBtn('鏡子角落的照片'); if (w) { await mark('即將點鏡子（此前是標題、序幕、地圖）'); mirrored = true; await page.keyboard.press('Space'); await sleep(600); await w.dispatchEvent('click'); await sleep(5500); await page.keyboard.press('Space'); await sleep(900); continue; } }
    if (mirrored && ++idle > 10) break;
    await sleep(700);
  }
  await mark('結束');
  const L = await log();
  console.log('播放記錄（時間 ms、種類、曲、currentTime）：');
  for (const x of L) console.log(' ', String(x.t).padStart(8), x.kind.padEnd(11), (x.src || '').padEnd(18), 'ct=' + x.ct);
} finally { await ui.close(); s.kill(); }
