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
const NAMES = { 'm-dressing': '化妝間', 'm-backstage': '後台', 'm-auditorium': '觀眾席', 'm-alley': '後門巷子' };
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

// [名稱, 起始地圖, 變數, 要點的任務文字, 預期（到達的卡／文字）, 連拍]
const SCENES = [
  ['化妝間→後台（走廊盡頭的鋼琴聲）', 'm-dressing', { letter: true }, '走廊盡頭的鋼琴聲', { card: 'm-backstage' }],
  ['後台 二樓→U 型樓梯→一樓→側台門→觀眾席', 'm-backstage', { zhou: true }, '側台門', { card: 'm-auditorium' }, true],
  ['觀眾席→三排十四號', 'm-auditorium', {}, '三排十四號', { text: /第三排，左邊數過來第十四個位子/ }, true],
  ['觀眾席→回後台（側台門）', 'm-auditorium', { seat: true }, '回後台', { card: 'm-backstage' }],
  ['後台→後門→巷子', 'm-backstage', { zhou: true, seat: true }, '後門', { card: 'm-alley' }, true],
  ['巷子→阿桃姨', 'm-alley', {}, '有人在叫你', { text: /巷子口站著一個頭髮花白的阿姨/ }, true],
  ['巷子→回後台（後門）', 'm-alley', { tao: true }, '回後台', { card: 'm-backstage' }],
  ['後台→回化妝間→天黑', 'm-backstage', { letter: true, zhou: true, seat: true, tao: true }, '回化妝間', { text: /窗外最後一道光/ }, false, 40000],
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
    const v = await page.$$eval('select option', (o, id) => o.find(e => e.value.includes(id) || e.textContent.includes(id))?.value, mapId);
    await page.selectOption('select', v); await sleep(5000);
    await page.keyboard.press('Space'); await sleep(600); await page.keyboard.press('Space'); await sleep(1200);
    let clicked = false;
    for (let k = 0; k < 14 && !clicked; k++) {   // 進場對話（化妝間開場）要先一句一句關掉，任務框才點得到
      for (const f of page.frames()) {
        const l = f.getByText(quest, { exact: false });
        if (await l.count() && await l.first().isVisible().catch(() => false)) { await l.first().click({ timeout: 4000 }).then(() => { clicked = true; }).catch(() => {}); if (clicked) break; }
      }
      if (!clicked) { await page.keyboard.press('Space'); await sleep(450); }
    }
    if (!clicked) throw new Error(`畫面上找不到任務「${quest}」`);
    const t0 = Date.now(); let n = 0, tick = 0, ok = false, blocked = false;
    while (Date.now() - t0 < limit) {
      await sleep(350);
      if (expect.text && Date.now() - t0 > 2500 && (tick++) % 3 === 0) await page.keyboard.press('Space');   // 等對話內容時順手推進（開場卡 once，從別的地圖進來才第一次播）
      if (shots) await page.screenshot({ path: `art/check/maps-review/walk/s${i + 1}-${String(n++).padStart(3, '0')}.png` });
      const t = await allText(page);
      if (/走不過去|無法前往|找不到路/.test(t)) { blocked = true; break; }
      if (expect.card && (await curCard(page)) === expect.card) { ok = true; break; }
      if (expect.text && expect.text.test(t)) { ok = true; break; }
    }
    verdict = ok ? `ok   ${Math.round((Date.now() - t0) / 100) / 10}s` : (blocked ? '✗ 引擎說走不過去' : `✗ 逾時（目前地圖 ${(await curCard(page)) || '?'}）`);
  } catch (e) { verdict = '✗ ' + e.message.slice(0, 120); }
  finally { await ui.close(); s.kill(); }
  if (!verdict.startsWith('ok')) fail++;
  console.log(`${i + 1}. ${name}：${verdict}`);
}
console.log(fail ? `不合格 ${fail}` : '全部走得到');
process.exit(fail ? 1 : 0);
