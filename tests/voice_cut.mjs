// 台語配音會不會被自動播放切掉（作者 10-29：阿桃姨、余伯的台語用聽的）：只按「開始遊戲」，記下每個 voice/ 音檔播了幾秒、是播完還是被停掉。
// SPEED=4 node tests/voice_cut.mjs（先 python3 src/build.py）
import { serve, open, sleep, SPEED } from './lib.mjs';
const init = () => {
  const log = window.__vlog = [];
  const P = HTMLMediaElement.prototype, play = P.play, pause = P.pause;
  const id = a => (a.currentSrc || a.src || '').match(/voice\/(\w+)\.mp3/)?.[1];
  P.play = function () { const v = id(this); if (v && !this.__hooked) { this.__hooked = 1; this.addEventListener('ended', () => log.push([v, 'ended', this.duration])); } return play.apply(this, arguments); };
  P.pause = function () { const v = id(this); if (v && !this.ended) log.push([v, 'cut', this.currentTime, this.duration]); return pause.apply(this, arguments); };
};
const s = await serve('dist/project.json');
const ui = await open(s.base, { width: 1280, height: 720, init });
const logs = async () => (await Promise.all(ui.page.frames().map(f => f.evaluate(() => window.__vlog || []).catch(() => [])))).flat();
try {
  await ui.clickText('開始遊戲');
  const want = Number(process.env.N) || 9, end = Date.now() + 40 * 60000 / SPEED;
  while (Date.now() < end && new Set((await logs()).map(l => l[0])).size < want) await sleep(4000);
  const L = await logs();
  for (const l of L) console.log(l[1] === 'cut' ? 'CUT ' : 'ok  ', l[0], l[1] === 'cut' ? `播到 ${l[2].toFixed(2)} / ${l[3].toFixed(2)} 秒` : `${l[2].toFixed(2)} 秒播完`);
  console.log(new Set(L.map(l => l[0])).size, '句有播到');
  if (L.some(l => l[1] === 'cut')) process.exitCode = 1;
} finally { await ui.close(); s.kill(); }
