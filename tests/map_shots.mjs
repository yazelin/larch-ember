// 地圖截圖：用預覽器的「跳到」直接進每張地圖。node tests/map_shots.mjs [地圖 id…] → art/check/map-<id>.png
import { serve, open, sleep } from './lib.mjs';
const ids = process.argv.slice(2).length ? process.argv.slice(2) : ['m-dressing', 'm-backstage', 'm-auditorium', 'm-alley'];
const s = await serve('dist/project.json');
const ui = await open(s.base, { width: 1600, height: 900 }); const { page } = ui;
page.on('response', r => { if (r.status() >= 400) console.log('缺', r.status(), r.url()); });
try {
  for (const id of ids) {
    const v = await page.$$eval('select option', (o, id) => o.find(x => x.value.includes(id) || x.textContent.includes(id))?.value, id);
    if (!v) { console.log('找不到', id); continue; }
    await page.selectOption('select', v); await sleep(6000);
    await page.keyboard.press('Space'); await sleep(800); await page.keyboard.press('Space'); await sleep(1500);
    await page.screenshot({ path: `art/check/map-${id}.png` }); console.log('ok', id);
  }
} finally { s.kill(); process.exit(0); }
