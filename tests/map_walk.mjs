// 實機走路：點左上角「遊戲任務」讓主角自己走過去（作者回報「走不過去」就是這個功能），一條一條驗證任務點走得到。
// node tests/map_walk.mjs [情境編號…]    專案預設 dist-maps/dist/project.json（PROJECT 可指定）
// 走樓梯那條會每 0.35 秒截圖一張到 art/check/maps-review/walk/，用來看人在轉折被擋住又出現。
import { serve, open, sleep } from './lib.mjs';
import fs from 'node:fs';
const project = process.env.PROJECT || 'dist-maps/dist/project.json';
const dir = project.replace(/[^/]+$/, '');
fs.mkdirSync('art/check/maps-review/walk', { recursive: true });
const base = JSON.parse(fs.readFileSync(project, 'utf8')); const P = base.project || base;

function variant(vars, hero, mapId) {
  const v = JSON.parse(JSON.stringify(P)); const b = base.project ? { ...base, project: v } : v;
  for (const x of v.variables) if (x.name in vars) x.defaultValue = vars[x.name];
  if (hero) {   // 把主角擺到指定格子（驗長距離走回門口）
    const n = v.boards[0].nodes.find(n => n.id === mapId); const m = JSON.parse(n.data.pluginValues.map);
    const h = m.events.find(e => e.actor === 'player'); h.x = hero[0]; h.y = hero[1]; n.data.pluginValues.map = JSON.stringify(m);
  }
  fs.writeFileSync(dir + '_walk.json', JSON.stringify(b)); return dir + '_walk.json';
}
const NAMES = { 'm-dressing': '化妝間', 'm-backstage-2f': '後台二樓', 'm-backstage': '後台一樓', 'm-auditorium': '觀眾席', 'm-alley': '後門巷子' };
// 目前在哪張地圖：看左上角 HUD 的地圖名稱（排除預覽器的下拉選單；遊戲內跳轉不會更新網址）
async function curCard(page) {
  for (const [id, nm] of Object.entries(NAMES)) for (const f of page.frames()) {
    const n = await f.evaluate(name => [...document.querySelectorAll('div,span,p,b,strong')].filter(e => !e.closest('select') && e.children.length === 0 && e.textContent.trim() === name && e.getBoundingClientRect().top < 120).length, nm).catch(() => 0);
    if (n) return id;
  }
  return '';
}
// 畫面上看得到的字（排除下拉選單與 script）
const allText = async page => (await Promise.all(page.frames().map(f => f.evaluate(() => { const c = document.body.cloneNode(true); c.querySelectorAll('select,script,style').forEach(e => e.remove()); return c.innerText; }).catch(() => '')))).join(' | ').replace(/\s+/g, ' ');

// [名稱, 起始地圖, 變數, 要點的任務文字（陣列＝同一次遊玩依序點，一路接下去）, 預期（到達的卡／文字；陣列要跟任務一一對應）, 連拍, 逾時毫秒, 主角起點]
const SCENES = [
  ['化妝間→後台二樓（走廊盡頭的鋼琴聲）', 'm-dressing', { letter: true }, '走廊盡頭的鋼琴聲', { card: 'm-backstage-2f' }],
  ['整條路線：化妝間→二樓→鋼琴→下樓→一樓→側台門→觀眾席', 'm-dressing', { letter: true }, ['走廊盡頭的鋼琴聲', '彈琴的人', '下樓：走到拱門樓梯口', '側台門：通觀眾席'],
   [{ card: 'm-backstage-2f' }, { text: /走廊盡頭有一台直立鋼琴/ }, { card: 'm-backstage' }, { card: 'm-auditorium' }], true, 90000],
  ['後台二樓：從左下角走到樓梯口下樓（長距離）', 'm-backstage-2f', { zhou: true }, '下樓：走到拱門樓梯口', { card: 'm-backstage' }, true, 40000, [1, 10]],
  ['後台一樓：從右下角走到側台門（長距離）', 'm-backstage', { zhou: true }, '側台門', { card: 'm-auditorium' }, true, 40000, [16, 10]],
  ['觀眾席→三排十四號', 'm-auditorium', {}, '三排十四號', { text: /第三排左邊第十四個位子放著一朵深紅玫瑰/ }, true],
  ['觀眾席→回後台一樓（側台門）', 'm-auditorium', { seat: true }, '回後台', { card: 'm-backstage' }],
  ['後台一樓→後門→巷子', 'm-backstage', { zhou: true, seat: true }, '後門', { card: 'm-alley' }, true],
  ['巷子→阿桃姨', 'm-alley', {}, '有人在叫你', { text: /巷口有一個白髮阿姨/ }, true],
  ['巷子→回後台一樓（後門）', 'm-alley', { tao: true }, '回後台', { card: 'm-backstage' }],
  ['整條回程：一樓→上樓→二樓→回化妝間→天黑', 'm-backstage', { letter: true, zhou: true, seat: true, tao: true }, ['上樓：走到拱門樓梯口', '回化妝間'],
   [{ card: 'm-backstage-2f' }, { text: /窗外最後一道光/ }], true, 60000],
  ['觀眾席：從三排十四號走回舞台後牆的門（長距離）', 'm-auditorium', { seat: true }, '回後台', { card: 'm-backstage' }, true, 40000, [15, 13]],
  ['巷子：從巷子盡頭走回後門（長距離）', 'm-alley', { tao: true }, '回後台', { card: 'm-backstage' }, true, 40000, [15, 8]],
  ['化妝間→鋼琴聲以外的任務：旋鈕與收音機', 'm-dressing', {}, '收音機旁邊的東西', { text: /舊塑膠殼手提收音機/ }, true],
];
const only = process.argv.slice(2).map(Number); let fail = 0;
for (let i = 0; i < SCENES.length; i++) {
  if (only.length && !only.includes(i + 1)) continue;
  const [name, mapId, vars, quest, expect, shots, limit = 30000, hero] = SCENES[i];
  const s = await serve(variant(vars, hero, mapId)); const ui = await open(s.base, { width: 1600, height: 900 }); const { page } = ui; let verdict = '';
  try {
    const v = await page.$$eval('select option', (o, id) => { const re = new RegExp('(^|[^A-Za-z0-9_-])' + id + '($|[^A-Za-z0-9_-])'); return o.find(e => re.test(e.value) || re.test(e.textContent))?.value; }, mapId)   // m-backstage 不能配到 m-backstage-2f;
    await page.selectOption('select', v); await sleep(5000);
    await page.keyboard.press('Space'); await sleep(600); await page.keyboard.press('Space'); await sleep(1200);
    const quests = [].concat(quest), expects = [].concat(expect); let ok = false, blocked = false, t0 = Date.now(), n = 0, tick = 0, stepNo = 0;
    for (let q = 0; q < quests.length; q++) {
      const qt = quests[q], ex = expects[q]; let clicked = false;
      for (let k = 0; k < (q ? 70 : 14) && !clicked; k++) {   // 進場對話（化妝間開場、上一站的劇情卡）要先一句一句關掉，任務框才點得到
        for (const f of page.frames()) {
          const l = f.getByText(qt, { exact: false });
          if (await l.count() && await l.first().isVisible().catch(() => false)) { await l.first().click({ timeout: 4000 }).then(() => { clicked = true; }).catch(() => {}); if (clicked) break; }
        }
        if (!clicked) { await page.keyboard.press('Space'); await sleep(450); }
      }
      if (!clicked) throw new Error(`畫面上找不到任務「${qt}」`);
      if (q === 0) t0 = Date.now(); ok = false; const ts = Date.now();
      while (Date.now() - ts < limit) {
        await sleep(350);
        if (ex.text && Date.now() - ts > 2500 && (tick++) % 3 === 0) await page.keyboard.press('Space');   // 等對話內容時順手推進（開場卡 once，從別的地圖進來才第一次播）
        if (shots) await page.screenshot({ path: `art/check/maps-review/walk/s${i + 1}-${String(n++).padStart(3, '0')}.png` });
        const t = await allText(page);
        if (/走不過去|無法前往|找不到路/.test(t)) { blocked = true; break; }
        if (ex.card && (await curCard(page)) === ex.card) { ok = true; break; }
        if (ex.text && ex.text.test(t)) { ok = true; break; }
      }
      if (!ok) break; stepNo++;
      if (quests.length > 1) console.log(`   步驟 ${q + 1}/${quests.length}「${qt}」ok ${Math.round((Date.now() - ts) / 100) / 10}s`);
    }
    verdict = ok ? `ok   ${Math.round((Date.now() - t0) / 100) / 10}s` : (blocked ? '✗ 引擎說走不過去' : `✗ 逾時（目前地圖 ${(await curCard(page)) || '?'}）`);
  } catch (e) { verdict = '✗ ' + e.message.slice(0, 120); }
  finally { await ui.close(); s.kill(); }
  if (!verdict.startsWith('ok')) fail++;
  console.log(`${i + 1}. ${name}：${verdict}`);
}
console.log(fail ? `不合格 ${fail}` : '全部走得到');
process.exit(fail ? 1 : 0);
