// 地圖標籤 hover 不能跳位：逐一 hover 每個 .rpg-waypoint，量前後位置差。node tests/hover_check.mjs
// PROJECT=預覽用的 project.json（先跑過 ui_inject）。負控制：PROJECT 換成 rpg 部位沒修過的版本，要抓得到跳位（退出碼 1）。
import { serve, open, sleep } from './lib.mjs';
const s = process.env.LIVE ? { base: process.env.LIVE, kill() {} } : await serve(process.env.PROJECT || 'dist/project.json');
const ui = await open(s.base, { width: 1600, height: 900 }); const { page } = ui;
let bad = 0, n = 0;
try {
  const v = await page.$$eval('select option', o => o.find(x => x.value.includes('m-dressing'))?.value); await page.selectOption('select', v); await sleep(6000);
  for (let i = 0; i < 6; i++) { await page.keyboard.press('Space'); await sleep(600); }
  await sleep(1500);
  for (const f of page.frames()) {
    const wps = f.locator('.rpg-waypoint');
    for (let i = 0; i < await wps.count(); i++) {
      const w = wps.nth(i); if (!await w.isVisible()) continue;
      const a = await w.boundingBox(); await w.hover(); await sleep(500); const b = await w.boundingBox(); await page.mouse.move(5, 450); await sleep(300);
      const d = Math.max(Math.abs(a.x - b.x), Math.abs(a.y - b.y)); n++;
      console.log(d > 2 ? 'FAIL' : 'ok  ', (await w.textContent()).trim(), `位移 ${d.toFixed(1)}px`); if (d > 2) bad++;
    }
  }
  console.log(n ? `${n} 個標籤，${bad} 個跳位` : 'FAIL 沒找到標籤');
} finally { await ui.close(); s.kill(); process.exit(bad || !n ? 1 : 0); }
