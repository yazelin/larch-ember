// 把主角擺到指定格子再截圖（驗證遮擋：站到每個物件的前、後、旁，樓梯路線每一格）。
// node tests/map_cells.mjs <地圖 id> x,y x,y …  → art/check/maps-review/cells/<id>_<x>_<y>.png
import { serve, open, sleep } from './lib.mjs';
import fs from 'node:fs';
const [id, ...cells] = process.argv.slice(2);
const project = process.env.PROJECT || 'dist-maps/dist/project.json';
const dir = project.replace(/[^/]+$/, ''); fs.mkdirSync('art/check/maps-review/cells', { recursive: true });
const base = JSON.parse(fs.readFileSync(project, 'utf8')); const P = base.project || base;
const node = P.boards[0].nodes.find(n => n.id === id); const orig = node.data.pluginValues.map;
for (const c of cells) {
  const [x, y] = c.split(',').map(Number); const m = JSON.parse(orig);
  const h = m.events.find(e => e.actor === 'player'); h.x = x; h.y = y; h.direction = 'down';
  node.data.pluginValues.map = JSON.stringify(m); fs.writeFileSync(dir + '_variant.json', JSON.stringify(base));
  const s = await serve(dir + '_variant.json'); const ui = await open(s.base, { width: 1600, height: 900 });
  try {
    const v = await ui.page.$$eval('select option', (o, id) => o.find(e => e.value.includes(id) || e.textContent.includes(id))?.value, id);
    await ui.page.selectOption('select', v); await sleep(5500);
    await ui.page.keyboard.press('Space'); await sleep(700); await ui.page.keyboard.press('Space'); await sleep(1200);
    await ui.page.screenshot({ path: `art/check/maps-review/cells/${id}_${x}_${y}.png` }); console.log('ok', id, x, y);
  } finally { await ui.close(); s.kill(); }
}
process.exit(0);
