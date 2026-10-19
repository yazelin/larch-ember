// 介面截圖：標題、對話、地圖 HUD、暫停選單、背包。node tests/ui_shots.mjs → art/check/ui-*.png
import { serve, open, sleep } from './lib.mjs';
const s = process.env.LIVE ? { base: process.env.LIVE, kill() {} } : await serve('dist/project.json');
const ui = await open(s.base, { width: 1600, height: 900 });
const { page } = ui; const shot = n => page.screenshot({ path: `art/check/ui-${n}.png` });
try {
  await sleep(2500); await shot('title');
  await ui.clickText('開始遊戲'); await sleep(2500); await shot('dialogue');
  for (let i = 0; i < 40; i++) { await ui.advance(); await sleep(500); }
  await sleep(2000); await shot('map');
  await page.mouse.click(251, 45); await sleep(1500); await shot('pause');
  for (const f of page.frames()) for (const t of ['背包', '物品', '道具']) { const b = f.getByRole('button', { name: t }).filter({ visible: true }); if (await b.count()) { await b.first().click(); await sleep(1500); await shot('bag'); break; } }
} finally { await ui.close?.(); s.kill(); process.exit(0); }
