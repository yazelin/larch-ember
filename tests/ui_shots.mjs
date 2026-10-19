// 介面截圖：標題、對話、選擇卡、地圖（HUD、RPG 對話、任務提示）、暫停選單、背包、圖庫、手機直式。
// PROJECT=預覽用的 project.json（預設 dist/project.json，要先跑過 ui_inject）、OUT=輸出資料夾（預設 ui/shots）。node tests/ui_shots.mjs
// 每個畫面各開一個預覽伺服器與瀏覽器（預覽器會記住上次跳到哪一張，共用會互相汙染）。
import { serve, open, sleep } from './lib.mjs';
const OUT = process.env.OUT || 'ui/shots';
const jump = async (page, id) => { const v = await page.$$eval('select option', (o, id) => o.find(x => x.value === id)?.value, id); if (!v) throw new Error('找不到卡 ' + id); await page.selectOption('select', v); };
const inFrames = async (page, fn, ...a) => { for (const f of page.frames()) { const r = await f.evaluate(fn, ...a).catch(() => null); if (r) return r; } return null; };
const click = async (page, sel) => { for (const f of page.frames()) { const l = f.locator(sel).filter({ visible: true }); if (await l.count()) { await l.first().click(); return true; } } return false; };
let fails = 0;
const run = async (name, opts, fn) => {
  if (process.env.ONLY && !process.env.ONLY.split(',').includes(name)) return;
  const s = process.env.LIVE ? { base: process.env.LIVE, kill() {} } : await serve(process.env.PROJECT || 'dist/project.json');
  const ui = await open(s.base, opts); const { page } = ui; const shot = n => page.screenshot({ path: `${OUT}/ui-${name}${n ? '-' + n : ''}.png` });
  try { await fn({ ui, page, shot }); console.log('ok  ', name); } catch (e) { fails++; console.log('FAIL', name, e.message); } finally { await ui.close(); s.kill(); }
};
const toMap = async (page) => { await jump(page, 'm-dressing'); await sleep(6000); for (let i = 0; i < 6; i++) { await page.keyboard.press('Space'); await sleep(600); } await sleep(1500); };
const toChoices = async (ui, page) => { await jump(page, 'branch_choice'); await sleep(4000); for (let i = 0; i < 6; i++) { await ui.advance(); await sleep(700); } await sleep(1500); };
for (const [name, opts] of [['desktop', { width: 1600, height: 900 }], ['mobile', { mobile: true }]]) {
  const pre = name === 'desktop' ? '' : 'm-';
  await run(pre + 'title', opts, async ({ page, shot }) => { await sleep(3000); await shot(); });
  await run(pre + 'dialogue', opts, async ({ ui, shot }) => { await sleep(2500); await ui.clickText('開始遊戲'); await sleep(3500); await shot(); });
  await run(pre + 'choices', opts, async ({ ui, page, shot }) => { await toChoices(ui, page); await shot(); });
  await run(pre + 'map', opts, async ({ page, shot }) => { await toMap(page); await shot(); });
}
const D = { width: 1600, height: 900 };
await run('title-hover', D, async ({ page, shot }) => { await sleep(4000); for (const f of page.frames()) { const b = f.locator('button[data-larch-action="start"]'); if (await b.count()) { await b.hover(); break; } } await sleep(500); await shot(); });
await run('choices-hover', D, async ({ ui, page, shot }) => { await toChoices(ui, page); let a, b2; for (const f of page.frames()) { const b = f.locator('[data-larch-ui="choice"]').nth(1); if (await b.count()) { a = await b.boundingBox(); await b.hover(); await sleep(600); b2 = await b.boundingBox(); break; } }
  await shot(); const d = Math.max(Math.abs(a.x - b2.x), Math.abs(a.y - b2.y), Math.abs(a.width - b2.width)); console.log('   選項 hover 位移', d.toFixed(1), 'px'); if (d > 2) throw new Error('選項 hover 位移 ' + d.toFixed(1) + 'px'); });
await run('rpg-dialogue', D, async ({ page, shot }) => { await jump(page, 'm-dressing'); await sleep(6000); await page.keyboard.press('Space'); await sleep(900); await shot(); });
await run('rpg-notice', D, async ({ page, shot }) => {
  await toMap(page);
  // 往牆走，引擎會顯示「走不過去」之類的提示；沒觸發就手動塞一句，量版位
  await page.keyboard.down('ArrowDown'); await sleep(3500); await page.keyboard.up('ArrowDown'); await sleep(200);
  const r = await inFrames(page, () => { const n = document.querySelector('#notice'); if (!n) return null; if (!n.textContent.trim()) { n.textContent = '這裡走不過去。'; n.classList.add('show'); n.style.opacity = 1; }
    const box = e => { const b = e?.getBoundingClientRect(); return b && [b.left, b.top, b.right, b.bottom]; };
    return { notice: box(n), others: ['#quest-wrap', 'body > header', '#banner'].map(q => [q, box(document.querySelector(q))]), text: n.textContent }; });
  await sleep(300); await shot(); console.log('   通知', JSON.stringify(r));
  const ov = (a, b) => a && b && a[0] < b[2] && b[0] < a[2] && a[1] < b[3] && b[1] < a[3];
  const hit = r?.others.filter(([, b]) => ov(r.notice, b)).map(([q]) => q);
  if (!r || hit.length) throw new Error('任務提示被擋住：' + JSON.stringify(hit));
});
await run('pause', D, async ({ page, shot }) => { await toMap(page); if (!await click(page, '#menu')) throw new Error('找不到暫停鈕'); await sleep(1500); await shot(); });
await run('bag', D, async ({ page, shot }) => { await toMap(page); if (!await click(page, '#menu')) throw new Error('找不到暫停鈕'); await sleep(1200); if (!await click(page, 'button:has-text("查看背包")')) throw new Error('找不到背包分頁'); await sleep(1500); await shot(); });
await run('bag-button', D, async ({ ui, page, shot }) => { await sleep(2500); await ui.clickText('開始遊戲'); await sleep(3500); if (!await click(page, 'button:has-text("背包")')) throw new Error('找不到背包鈕'); await sleep(1500); await shot(); });
process.exit(fails ? 1 : 0);
