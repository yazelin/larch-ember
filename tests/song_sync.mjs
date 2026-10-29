// 唱歌卡同步測試（作者 10-29：點畫面歌詞不能跑掉）：從一張唱歌卡開始，量「歌開始播」到「每句歌詞亮起」的時間，跟卡片上寫的秒數比；
// 第二輪每 0.3 秒點一下畫面，誤差要一樣。node tests/song_sync.mjs [卡片 id]（先 python3 src/build.py；真實速度，約 1 分鐘）
import { serve, open, assert } from './lib.mjs';
import { hookInit } from './audiohook.mjs';
import { readFileSync, writeFileSync } from 'node:fs';
const CARD = process.argv[2] || 'soundcheck__song';
const p = JSON.parse(readFileSync('dist/project.json', 'utf8'));
let want = [], file = '';
for (const b of p.boards) for (const n of b.nodes) { n.data.start = n.id === CARD; if (n.id === CARD) file = n.data.bgm.split('/').pop(), want = n.data.pluginValues.lines.split('\n').map(l => [Number(l.split('｜')[0]), l.split('｜')[1]]); }
writeFileSync('dist/_sync.json', JSON.stringify(p));
const s = await serve('dist/_sync.json');
const worst = [];
try {
  for (const click of [false, true]) {
    const ui = await open(s.base, { width: 1280, height: 720, init: hookInit });
    await ui.clickText('開始遊戲');
    const seen = new Map(), t0 = Date.now();
    while (Date.now() - t0 < 40000 && seen.size < want.length) {
      for (const f of ui.page.frames()) {
        const c = await f.evaluate(() => document.getElementById('cur')?.textContent).catch(() => null);
        if (c && !seen.has(c)) seen.set(c, Date.now());
      }
      if (click) await ui.page.mouse.click(640, 300).catch(() => {});
      await new Promise(r => setTimeout(r, click ? 300 : 40));
    }
    const bgm = (await Promise.all(ui.page.frames().map(f => f.evaluate(() => window.__bgm || []).catch(() => [])))).flat().find(x => x.src === file);
    if (!bgm) throw new Error('沒抓到歌開始播放：' + file);
    const a0 = bgm.ts;
    const errs = want.filter(([, s]) => seen.has(s)).map(([t, s]) => (seen.get(s) - a0) / 1000 - t);
    const m = Math.max(...errs.map(Math.abs));
    console.log(click ? '狂點' : '不點', `：${errs.length}/${want.length} 句，誤差 ${errs.map(e => e.toFixed(2)).join(' ')}（最大 ${m.toFixed(2)} 秒）`);
    worst.push(m); await ui.close();
  }
  assert(worst.every(m => m < 0.6), '每句歌詞跟歌的誤差都在 0.6 秒內');
  assert(Math.abs(worst[0] - worst[1]) < 0.4, '點畫面不會讓歌詞跑掉');
} catch (e) { console.error(e.message); process.exitCode = 1; }
finally { s.kill(); }
