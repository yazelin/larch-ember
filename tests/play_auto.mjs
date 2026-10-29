// 免點試玩（作者 10-29：一部不用點滑鼠的音樂小說）：只按「開始遊戲」，之後什麼都不點，要自己走到片尾字卷、跳進第二章公開站；按「略過」回標題。
// SPEED=16 node tests/play_auto.mjs（先 python3 src/build.py）。印出遊戲裡經過的時間（換算成真實速度）。
import { serve, open, sleep, assert, SPEED } from './lib.mjs';
const MUST = [/從頭到尾會自己播放/, /先生/, /港邊的燈/, /三排十四號/, /什麼演唱會/, /片尾曲/];
const s = await serve('dist/project.json');
const ui = await open(s.base, { width: 1600, height: 900 });
const text = async () => (await Promise.all(ui.page.frames().map(f => f.evaluate(() => document.body.innerText).catch(() => '')))).join(' | ');
let seen = '', back = false, site = false, t0 = Date.now();
try {
  await ui.clickText('開始遊戲'); await sleep(2000);
  const end = Date.now() + 90 * 60000 / SPEED + 20 * 60000;   // 插件卡（唱歌卡、片尾字卷）不吃 SPEED，照真實秒數走：歌約 7 分鐘、字卷約 3.5 分鐘
  while (Date.now() < end) {
    const t = await text(); seen += t;
    if (/片尾曲/.test(seen) && ui.page.frames().some(f => f.url().startsWith('https://yazelin.github.io/larch-ember/'))) { site = true; break; }
    await new Promise(r => setTimeout(r, 80));   // 16 倍速下提示卡只停兩百多毫秒
  }
  let at = 0;
  for (const r of MUST) { const m = r.exec(seen.slice(at)); assert(m, '自己播到 ' + r); if (m) at += m.index; }
  assert(site, '片尾字卷播完自己跳進第二章公開站');
  console.log('全劇約', Math.round((Date.now() - t0) * SPEED / 60000), '分鐘（真實速度）');
  await sleep(3000);
  const siteText = (await Promise.all(ui.page.frames().filter(f => f.url().startsWith('https://yazelin.github.io/')).map(f => f.evaluate(() => document.body.innerText).catch(() => '')))).join('');
  assert(/改編自真實故事/.test(siteText) && /參考資料/.test(siteText), '第二章看得到公開站的內容');
  await ui.clickText('略過').catch(() => {});
  for (let k = 0; k < 20 && !back; k++) { await sleep(1000); back = /開始遊戲/.test(await text()); }
  assert(back, '第二章按「略過」回到標題');
  console.log(ui.errors.length ? ui.errors : '沒有頁面錯誤');
} catch (e) { console.error(e.message, '\n畫面：', (await text()).slice(-300)); process.exitCode = 1; }
finally { await ui.close(); s.kill(); }
