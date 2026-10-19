// CG 收藏解鎖：新開遊戲時只有第一張開放；跳到有 cgOps 的卡（soundcheck）後再回收藏頁，要多解鎖一張。node tests/gallery_check.mjs
// PROJECT=要有開圖庫的預覽檔（旗標 gal）。負控制：換成旗標 nolock（圖庫全不鎖）的檔，第一步就要失敗（退出碼 1）。
import { serve, open, sleep } from './lib.mjs';
const s = process.env.LIVE ? { base: process.env.LIVE, kill() {} } : await serve(process.env.PROJECT || 'dist/project.json');
const ui = await open(s.base, { width: 1600, height: 900 }); const { page } = ui;
const count = async () => { for (const f of page.frames()) { const r = await f.evaluate(() => { const c = document.querySelectorAll('[data-larch-ui="cg"]'); return c.length ? [c.length, document.querySelectorAll('[data-larch-ui="cg"][data-locked]').length] : null; }).catch(() => null); if (r) return r; } return null; };
const gallery = async () => { for (const f of page.frames()) { const ok = await f.evaluate(() => { const b = document.querySelector('[data-larch-action="gallery"]'); if (!b || b.hidden) return false; b.click(); return true; }).catch(() => false); if (ok) break; } await sleep(2000); return count(); };
let bad = 0;
try {
  await sleep(4000);
  const a = await gallery(); console.log('新開遊戲：', a ? `${a[0]} 張，鎖住 ${a[1]}` : '打不開收藏頁');
  if (!a || a[1] !== a[0] - 1) { bad++; console.log('FAIL 新開遊戲應只開放一張'); }
  await page.screenshot({ path: `${process.env.OUT || 'ui/shots'}/ui-gallery.png` });
  const v = await page.$$eval('select option', o => o.find(x => x.value === 'soundcheck')?.value); await page.selectOption('select', v); await sleep(4000);
  await page.selectOption('select', { index: 0 }); await sleep(3500);
  const b = await gallery(); console.log('看過試音那張之後：', b ? `${b[0]} 張，鎖住 ${b[1]}` : '打不開收藏頁');
  if (!b || !a || b[1] !== a[1] - 1) { bad++; console.log('FAIL 看過後應多解鎖一張'); }
  console.log(bad ? 'FAIL' : 'ok   解鎖正常');
} finally { await ui.close(); s.kill(); process.exit(bad ? 1 : 0); }
