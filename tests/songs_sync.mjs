// 歌卡的歌詞同步實測（真實時間，SPEED 不加速）：跳到歌卡，記下歌檔開始播的時間，與每一組歌詞出現的時間，
// 跟 manifest 裡該句的開唱時間比。負值 = 歌詞比人聲早出現。用法：先 build，再  node tests/songs_sync.mjs [卡代號,…]
import { readFileSync } from 'node:fs';
import { serve, open, sleep } from './lib.mjs';
import { hookInit, cutSizes, named } from './audiohook.mjs';

const SD = process.env.SONGS_DIR || 'assets/songs';
const mf = JSON.parse(readFileSync(`${SD}/cuts/manifest.json`, 'utf8'));
const proj = JSON.parse(readFileSync('dist/project.json', 'utf8')); const P = proj.project || proj;
const nodes = Object.fromEntries(P.boards[0].nodes.map(n => [n.id, n]));
const want = (process.argv[2] || 'soundcheck,concert,ending_a1,ending_a2,ending_b1').split(',');
const strip = t => t.replace(/^（唱）/, '').replace(/[\s]/g, '');
for (const card of want) {
  const cut = mf.cuts.find(c => c.role === 'sung_card' && c.place.card === card);
  const node = nodes[card + '__song'] || nodes[card];
  if (!cut || !node) { console.log('略過', card); continue; }
  const slots = node.data.dialogueLines.map(l => l.text);
  const s = await serve('dist/project.json');
  await fetch(s.base + '/api/lp/card', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ card, line: Math.max(0, (nodes[card].data.dialogueLines.length || 1) - 1) }) });   // 從歌卡前一張卡的最後一句開始，自己點進歌卡，才量得到進卡的瞬間
  const ui = await open(s.base, { width: 1280, height: 720, init: hookInit });
  const sizes = cutSizes();
  let t0wall = Date.now();
  let entered = false;
  const shown = [];   // [slot index, 時間]
  let k = -1, audioAt = null, endAt = null;
  const total = cut.duration + 12;
  while ((Date.now() - t0wall) / 1000 < total + 4) {
    const parts = await Promise.all(ui.page.frames().map(f => f.evaluate(() => { const b = document.body.cloneNode(true); b.querySelectorAll('select, option, script, style').forEach(e => e.remove()); return { t: b.textContent.replace(/\s+/g, ''), p: window.__bgm || [] }; }).catch(() => ({ t: '', p: [] }))));
    const t = parts.map(x => x.t).join('');
    const now = Date.now();
    if (audioAt === null) { const pl = named(parts.flatMap(x => x.p), sizes).find(x => x.src === cut.file); if (pl) audioAt = pl.ts; }
    if (!entered) { if (audioAt === null) { await ui.advance(); await sleep(450); continue; } entered = true; t0wall = now; }
    for (let j = k + 1; j <= Math.min(k + 2, slots.length - 1); j++) {
      const key = strip(slots[j]).slice(0, 5);
      if (t.includes(key)) { if (j > k) { shown.push([j, now]); k = j; } break; }
    }
    if (k === slots.length - 1 && endAt === null) endAt = now;
    if (endAt && now - endAt > 3000) break;
    await sleep(60);
  }
  console.log(`\n${card}：歌檔 ${cut.file}（${cut.duration}s），歌開始播 ${audioAt ? ((audioAt - t0wall) / 1000).toFixed(2) : '沒播到'}s（相對腳本開始）`);
  const errs = []; let li = 0;
  for (const [j, ts] of shown) {
    const txt = strip(slots[j]);
    if (txt.startsWith('♪')) continue;
    const first = cut.lines.findIndex((l, i) => i >= li && txt.startsWith(strip(l.text).slice(0, 5)));
    if (first < 0 || audioAt === null) continue;
    li = first + 1;
    const e = (ts - audioAt) / 1000 - cut.lines[first].t0;
    errs.push(e);
    console.log(`  畫面 ${String(j).padStart(2)}  ${((ts - audioAt) / 1000).toFixed(2).padStart(7)}s  該句開唱 ${cut.lines[first].t0.toFixed(2).padStart(6)}s  差 ${e >= 0 ? '+' : ''}${e.toFixed(2)}s  ${txt.slice(0, 12)}`);
  }
  if (errs.length) console.log(`  → ${errs.length} 組歌詞：平均絕對差 ${(errs.reduce((a, b) => a + Math.abs(b), 0) / errs.length).toFixed(2)}s，最晚 ${Math.max(...errs).toFixed(2)}s，最早 ${Math.min(...errs).toFixed(2)}s；最後一張換頁 ${endAt && audioAt ? ((endAt - audioAt) / 1000).toFixed(1) : '?'}s（歌 ${cut.duration}s）`);
  await ui.close(); s.kill();
}
