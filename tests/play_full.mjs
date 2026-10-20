// 全劇試玩：序幕 → 試音 → 換禮服 → 化妝間／後台／觀眾席／巷子 → 回化妝間天黑 → 分歧 → 結局。
// END=a|b|c 選結局（預設 a）。SPEED=16 node tests/play_full.mjs（先 python3 src/build.py；HEADED=1 看畫面）。截圖 art/check/full-<結局>-<n>.png
import { serve, open, sleep, assert } from './lib.mjs';
import { mkdirSync } from 'node:fs';
mkdirSync('art/check', { recursive: true });
const END = process.env.END || 'a';
const PICK = { a: '有人會坐在三排十四號。', b: '周老師在等我開口。', c: '阿爸一個人收不完。' }[END];
const END_RE = { a: /10 月 17 日/, b: /他沒有走/, c: /阿哲按下播放鍵/ }[END];
// 地圖任務：照順序點畫面上看得到的標籤（標籤就是地圖上的調查點／導引文字）。每個最多點 N 次，避免原地繞圈
const GUIDE = [['鏡子角落的照片', 2], ['筆記本', 2], ['化妝箱', 2], ['窗', 2], ['首飾盒', 2], ['阿爸的收音機', 3], ['走廊盡頭的鋼琴聲', 2], ['彈琴的人', 2], ['側台門：通觀眾席', 2], ['三排十四號', 2], ['回後台', 3],
  ['後門：通巷子', 2], ['有人在叫你', 2], ['回化妝間', 2], ['天黑之前，回到化妝間', 2]];
const MUST = [/這裡的燈起床慢/, /早發性阿茲海默症/, /我是你先生/, /魚我來處理/, /這件好舊/, /河岸留言那晚/, /2013，永明，空舞台/, /你是彈琴的|她記得我們的歌/, /她心裡聽見誰|天黑了/,
  { a: /程希，三排十四號/, b: /謝謝您，先生/, c: /淑靜仔，阮攏來矣|阮攏來矣/ }[END]];
// AUDIO=1：攔截所有音訊播放，結束時印出實際換曲順序（不含介面音效）
const hook = () => {
  window.__bgm = window.__bgm || [];
  const push = (kind, el) => { try { window.__bgm.push({ t: Math.round(performance.now()), kind, src: String(el?.currentSrc || el?.src || '').split('/').pop() }); } catch {} };
  document.addEventListener('play', e => push('play', e.target), true);
};
const s = process.env.LIVE ? { base: process.env.LIVE, kill() {} } : await serve('dist/project.json');
const ui = await open(s.base, { width: 1600, height: 900, init: process.env.AUDIO ? hook : null });
const { page } = ui;
// 預覽器的「跳到…」下拉選單有全部卡片標題，讀畫面文字時要拿掉，不然會把卡名當成任務提示
const text = async () => (await Promise.all(page.frames().map(f => f.evaluate(() => {
  const c = document.body.cloneNode(true); c.querySelectorAll('select, option, script, style').forEach(e => e.remove()); return c.textContent;
}).catch(() => '')))).join(' | ').replace(/\s+/g, ' ');
let seen = '', n = 0, it = 0; const dbg = (k, extra = '') => { if (process.env.DEBUG) console.log(String(it).padStart(4), k, extra); };
const shot = () => page.screenshot({ path: `art/check/full-${END}-${String(n++).padStart(2, '0')}.png` });
const boxOpen = async () => { for (const f of page.frames()) { const b = f.locator('.vn2-box'); if (await b.count() && await b.first().isVisible().catch(() => false)) return true; } return false; };
const clickVisible = async t => {
  const hit = async loc => { try { await loc.click({ timeout: 4000 }); } catch { await loc.dispatchEvent('click').catch(() => {}); } return true; };   // 被對話框蓋住時改送事件，不要等 30 秒
  for (const f of page.frames()) { const b = f.getByRole('button', { name: t }).filter({ visible: true }); if (await b.count()) return hit(b.first()); }
  for (const f of page.frames()) { const l = f.getByText(t, { exact: t.length === 1 }).filter({ visible: true }); if (await l.count()) return hit(l.last()); }
  return false;
};
const vis = async t => { for (const f of page.frames()) if (await f.getByText(t, { exact: t.length === 1 }).first().isVisible().catch(() => false)) return true; return false; };
const WAY = new Set(['鏡子角落的照片', '筆記本', '化妝箱', '窗', '首飾盒', '阿爸的收音機']);   // 地圖上的標示按鈕（主角不在附近時在畫面外）
const wayBtn = async t => { for (const f of page.frames()) { const b = f.locator('button.rpg-waypoint').filter({ hasText: t }); if (await b.count()) return b.first(); } return null; };
// 翻頁一律點畫面上的「下一句／繼續」按鈕。地圖上沒有對話框時不要按 Enter：那等於在調查點旁按「互動」，同一個事件會一再重新觸發。
const nextBtn = async () => { for (const f of page.frames()) for (const name of ['下一句', '繼續探索', '繼續']) { const b = f.getByRole('button', { name }).filter({ visible: true }); if (await b.count()) return b.first(); } return null; };
let idle = 0;
const introDone0 = () => /我在這裡工作/.test(seen);   // 進化妝間時自動播的開場對話要先播完，不然點調查點會被它吃掉
const used = new Map(), tries = new Map();
// 16 倍速會把地圖素材的載入逾時也縮短，跳出「地圖素材沒有完整載入」：這是加速造成的假象，按「仍然開始」繼續。
// 真正缺檔另外用 404 記錄抓（只看遊戲素材 /files/），最後必須是 0。
const bad404 = [], skipped = [];
page.on('response', r => { if (r.status() >= 400 && /\/files\//.test(r.url())) bad404.push(r.status() + ' ' + r.url()); });
try {
  await ui.clickText('開始遊戲'); await sleep(1500);
  const end = Date.now() + 40 * 60000;
  while (Date.now() < end) {
    try {
      const t = await text(); seen += t; it++;
      if (END_RE.test(seen)) break;
      if (t.includes('她心裡聽見誰') && await vis(PICK)) { dbg('choice', PICK); await sleep(400); await shot(); await clickVisible(PICK); await sleep(900); continue; }
      const nb = await nextBtn();
      if (nb) { idle = 0; dbg('next'); await sleep(250); seen += await text(); await nb.click({ timeout: 3000 }).catch(() => {}); await sleep(450); seen += await text(); continue; }
      if (await boxOpen()) { dbg('box', t.replace(/^.*?(旅途手記|冒險暫停)/, '').slice(-60)); await sleep(300); seen += await text(); await ui.advance(); await sleep(700); seen += await text(); continue; }
      if (skipped.length < 80 && t.includes('NOW LOADING') && await vis('仍然開始') && await clickVisible('仍然開始')) { dbg('load'); skipped.push(t.match(/NOW LOADING\s*(\S+)/)?.[1] || '?'); await sleep(1200); continue; }   // 用累積讀到的文字判斷：加速時最後一句可能只在畫面上一閃   // 沒有對話框時才處理載入畫面
      const introDone = introDone0();
      let g = null;
      for (const [x, max] of GUIDE) if ((used.get(x) || 0) < max && (WAY.has(x) ? introDone && !!(await wayBtn(x)) : await vis(x))) { g = x; break; }
      if (g) { dbg('guide', g); used.set(g, (used.get(g) || 0) + 1); await shot(); if (WAY.has(g)) await (await wayBtn(g)).dispatchEvent('click'); else await clickVisible(g); await sleep(5500); await page.keyboard.press('Space'); await sleep(900);
        if (WAY.has(g) && !(await nextBtn())) { tries.set(g, (tries.get(g) || 0) + 1); used.set(g, tries.get(g) > 6 ? 99 : Math.max(0, (used.get(g) || 1) - 1)); dbg('retry', g); }   // 調查點沒反應（例如剛好在載入或被別的對話佔住）就重點，不算一次
        continue; }
      dbg('idle', t.slice(-100)); if (++idle % 40 === 0) await page.keyboard.press('Space'); await sleep(500);
    } catch (e) {
      if (!/detached|Target closed|Execution context|has been closed/.test(e.message)) throw e;   // 換場時畫面框架會整個換掉
      await sleep(800);
    }
  }
  await shot();
  if (process.env.AUDIO) {
    const L = (await Promise.all(page.frames().map(f => f.evaluate(() => window.__bgm || []).catch(() => [])))).flat().sort((a, b) => a.t - b.t);
    const SFX = /^(press|hover|advance|open|close|use)\.mp3$/; let prev = '', out = [];
    for (const x of L) if (x.src && !SFX.test(x.src) && x.src !== prev) { out.push(x.src.replace('.mp3', '')); prev = x.src; }
    console.log('實際換曲順序：', out.join(' → '));
  }
  assert(END_RE.test(seen), '走到結局 ' + END.toUpperCase());
  for (const r of MUST) assert(r.test(seen), '有出現 ' + r);
  assert(bad404.length === 0, '遊戲素材沒有 404 ' + JSON.stringify(bad404.slice(0, 5)));
  console.log('載入逾時被略過的次數（加速假象）：', skipped.length, skipped.join(','));
  console.log(ui.errors.length ? ui.errors : '沒有頁面錯誤');
} catch (e) { await shot(); console.error(e.message, '\n畫面：', (await text()).slice(-500)); process.exitCode = 1; }
finally { await ui.close(); s.kill(); }
