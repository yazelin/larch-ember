// 重製版全劇試玩（單線）：從標題一路點到製作名單。SPEED=16 node tests/play_linear.mjs（先 python3 src/build.py；HEADED=1 看畫面）
// 截圖 art/check/linear-<n>.png（每換一張卡截一次）。AUDIO=1 印出實際換曲順序。
import { serve, open, sleep, assert } from './lib.mjs';
import { mkdirSync } from 'node:fs';
import { hookInit, cutSizes, named } from './audiohook.mjs';
mkdirSync('art/check', { recursive: true });
const END_RE = /片尾曲/;
// 每一章至少要讀到一句（順序也要對）
const MUST = [/先生/, /港邊的燈/, /河岸留言/, /三排十四號/, /燈一盞一盞暗下來/, /程希/, /河岸留言那晚，你唱〈天烏烏〉，我沒走。/, /林醫師|林慧如/,
  /淑靜仔 叫我一聲|淑靜仔，叫我一聲/, /天還沒亮攤就開了/, /程希，三排十四號/, /淑靜仔/, /有他陪我 我不怕/, /不肯冷/, /什麼演唱會/, /片尾曲/];
const s = process.env.LIVE ? { base: process.env.LIVE, kill() {} } : await serve('dist/project.json');
const ui = await open(s.base, { width: 1600, height: 900, init: process.env.AUDIO ? hookInit : null });
const { page } = ui;
const text = async () => (await Promise.all(page.frames().map(f => f.evaluate(() => {
  const c = document.body.cloneNode(true); c.querySelectorAll('select, option, script, style').forEach(e => e.remove()); return c.textContent;
}).catch(() => '')))).join(' | ').replace(/\s+/g, ' ');
const bad404 = [], songReq = [];
page.on('response', r => { if (r.status() >= 400 && /\/files\//.test(r.url())) bad404.push(r.status() + ' ' + r.url()); if (/\/songs\/.*cuts\/.*\.mp3/.test(r.url())) songReq.push(decodeURIComponent(r.url().split('/').pop())); });
const nextBtn = async () => { for (const f of page.frames()) for (const name of ['下一句', '繼續']) { const b = f.getByRole('button', { name }).filter({ visible: true }); if (await b.count()) return b.first(); } return null; };
// 只有一個選項的選擇卡：點那個唯一的選項
const CHOICES = ['喝一口。', '要。'];
const choiceBtn = async () => { for (const f of page.frames()) for (const c of CHOICES) { const b = f.getByText(c, { exact: true }).filter({ visible: true }); if (await b.count()) return b.last(); } return null; };
let seen = '', n = 0, idle = 0, lastTitle = '';
try {
  await ui.clickText('開始遊戲'); await sleep(1500);
  const end = Date.now() + 40 * 60000;
  while (Date.now() < end) {
    try {
      const t = await text(); seen += t;
      if (END_RE.test(seen)) break;
      const head = (await Promise.all(page.frames().map(f => f.evaluate(() => document.body.innerText).catch(() => '')))).filter(x => !/白板|存檔/.test(x)).join('|').slice(0, 80);
      if (head !== lastTitle && n < 400) { lastTitle = head; await page.screenshot({ path: `art/check/linear-${String(n++).padStart(3, '0')}.png` }); }
      const cb = await choiceBtn();
      if (cb) { idle = 0; await sleep(300); await cb.click({ timeout: 3000 }).catch(() => cb.dispatchEvent('click')); await sleep(900); continue; }
      await sleep(250); seen += await text();
      await ui.advance().catch(() => {}); await sleep(400);
      if (process.env.DEBUG && ++idle % 20 === 0) console.log(head);
    } catch (e) {
      if (!/detached|Target closed|Execution context|has been closed/.test(e.message)) throw e;
      await sleep(800);
    }
  }
  await page.screenshot({ path: `art/check/linear-${String(n++).padStart(3, '0')}.png` });
  if (process.env.AUDIO) {
    const L = named((await Promise.all(page.frames().map(f => f.evaluate(() => window.__bgm || []).catch(() => [])))).flat().sort((a, b) => a.t - b.t), cutSizes());
    const SFX = /^(press|hover|advance|open|close|use)\.mp3$/; let prev = '', out = [];
    for (const x of L) if (x.src && !SFX.test(x.src) && x.src !== prev) { out.push(x.src.replace('.mp3', '')); prev = x.src; }
    console.log('實際換曲順序：', out.join(' → '));
    console.log('歌檔請求：', [...new Set(songReq)].join(', '));
  }
  assert(END_RE.test(seen), '走到製作名單');
  let at = 0;
  for (const r of MUST) { const m = r.exec(seen.slice(at)); assert(m, '依序出現 ' + r); if (m) at += m.index; }
  assert(bad404.length === 0, '遊戲素材沒有 404 ' + JSON.stringify(bad404.slice(0, 5)));
  console.log('截圖', n, '張');
  console.log(ui.errors.length ? ui.errors : '沒有頁面錯誤');
} catch (e) { console.error(e.message, '\n畫面：', (await text()).slice(-500)); process.exitCode = 1; }
finally { await ui.close(); s.kill(); }
