// 地圖截圖：用預覽器的「跳到」直接進每張地圖。
// node tests/map_shots.mjs [地圖 id…]  → art/check/maps-review/shot-<id>.png（專案預設 dist-maps/dist/project.json，可用 PROJECT 指定）
import { serve, open, sleep } from './lib.mjs';
import fs from 'node:fs';
const ids = process.argv.slice(2).length ? process.argv.slice(2) : ['m-dressing', 'm-backstage', 'm-auditorium', 'm-alley'];
const project = process.env.PROJECT || 'dist-maps/dist/project.json';
fs.mkdirSync('art/check/maps-review', { recursive: true });
const s = await serve(project);
const ui = await open(s.base, { width: 1600, height: 900 }); const { page } = ui;
const missing = new Set();
page.on('response', r => { if (r.status() >= 400 && !/auth\/session|analytics-config/.test(r.url())) missing.add(r.status() + ' ' + r.url()); });
try {
  for (const id of ids) {
    const v = await page.$$eval('select option', (o, id) => o.find(x => x.value.includes(id) || x.textContent.includes(id))?.value, id);
    if (!v) { console.log('找不到', id); continue; }
    await page.selectOption('select', v); await sleep(6000);
    await page.keyboard.press('Space'); await sleep(800); await page.keyboard.press('Space'); await sleep(1500);
    await page.screenshot({ path: `art/check/maps-review/shot-${id}.jpg`, type: 'jpeg', quality: 88 });
    let err = '';
    for (const f of page.frames()) { const t = await f.evaluate(() => document.body ? document.body.innerText : '').catch(() => ''); const m = t.match(/(這張地圖的資料無法讀取|地圖素材沒有完整載入)[^\n]*|Error: [^\n]{0,80}/g); if (m) err += m.join(' / '); }
    console.log(err ? `✗ ${id} 讀取錯誤：${err}` : `ok ${id}`);
  }
  if (missing.size) console.log('缺檔：', [...missing]);
} finally { s.kill(); process.exit(0); }
