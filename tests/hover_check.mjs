// 地圖標籤 hover 不能跳位：逐一 hover 每個 .rpg-waypoint，量前後位置差。node tests/hover_check.mjs（LIVE= 量線上版）
import { serve, open, sleep } from './lib.mjs';
const s = process.env.LIVE ? { base: process.env.LIVE, kill() {} } : await serve('dist/project.json');
const ui = await open(s.base, { width: 1600, height: 900 }); const { page } = ui;
let bad = 0, n = 0;
try {
  await sleep(2500); await ui.clickText('開始遊戲'); await sleep(2500);
  for (let i = 0; i < 40; i++) { await ui.advance(); await sleep(500); }
  await sleep(2000);
  for (const f of page.frames()) {
    const wps = f.locator('.rpg-waypoint');
    for (let i = 0; i < await wps.count(); i++) {
      const w = wps.nth(i); if (!await w.isVisible()) continue;
      const a = await w.boundingBox(); await w.hover(); await sleep(400); const b = await w.boundingBox(); await page.mouse.move(5, 450); await sleep(300);
      const d = Math.max(Math.abs(a.x - b.x), Math.abs(a.y - b.y)); n++;
      console.log(d > 2 ? 'FAIL' : 'ok  ', (await w.textContent()).trim(), `位移 ${d.toFixed(1)}px`); if (d > 2) bad++;
    }
  }
  console.log(n ? `${n} 個標籤，${bad} 個跳位` : 'FAIL 沒找到標籤');
} finally { s.kill(); process.exit(bad || !n ? 1 : 0); }
