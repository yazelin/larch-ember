// 對話框佔掉 CG 多少（作者 11-02：對話框不要切到 CG，手機和桌機的高度比例不同）。
// node tests/layout_check.mjs（先 python3 src/build.py）→ 每種螢幕印出 CG 範圍與對話框蓋住 CG 的高度比例，截圖存 art/check/layout_<名>.png
import { chromium } from '/home/ct/larch-preview/node_modules/playwright-core/index.mjs';
import { serve, assert } from './lib.mjs';
const SIZES = [
  ['desktop', { viewport: { width: 1920, height: 1080 } }],
  ['laptop', { viewport: { width: 1366, height: 768 } }],
  ['phone_land', { viewport: { width: 844, height: 390 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 }],
  ['phone_port', { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 }],
];
const s = await serve('dist/project.json');
const browser = await chromium.launch({ executablePath: process.env.CHROME || '/usr/bin/google-chrome', args: ['--disable-gpu', '--no-sandbox', '--autoplay-policy=no-user-gesture-required'] });
const wait = ms => new Promise(r => setTimeout(r, ms));
try {
  for (const [name, opt] of SIZES) {
    const page = await (await browser.newContext({ ...opt, locale: 'zh-TW' })).newPage();
    await page.goto(s.base + '/play/market/local'); await wait(4000);
    for (const f of page.frames()) { const l = f.getByText('開始遊戲', { exact: true }); if (await l.count()) { await l.first().click(); break; } }
    await wait(11000);   // 停在冷開場的對話
    const m = await page.evaluate(() => {
      const rect = e => { const b = e.getBoundingClientRect(); return { x: b.x, y: b.y, w: b.width, h: b.height }; };
      const big = [...document.querySelectorAll('img,div')].filter(e => {
        const st = getComputedStyle(e); return (e.tagName === 'IMG' && /\/cg\//.test(e.src)) || /\/cg\//.test(st.backgroundImage);
      }).map(rect).filter(r => r.w > 100).sort((a, b) => a.w * a.h - b.w * b.h);
      const dlg = [...document.querySelectorAll('iframe')].map(f => ({ t: f.title, ...rect(f) })).filter(f => /對話/.test(f.t) || (f.h < innerHeight * .8 && f.w > innerWidth * .5));
      return { vw: innerWidth, vh: innerHeight, cg: big[0], dlg: dlg[0] };
    });
    await page.screenshot({ path: `art/check/layout_${name}.png` });
    const { cg, dlg } = m;
    if (cg && dlg) {
      const cover = Math.max(0, Math.min(cg.y + cg.h, dlg.y + dlg.h) - Math.max(cg.y, dlg.y));
      console.log(`${name.padEnd(10)} 視窗 ${m.vw}×${m.vh}  CG ${Math.round(cg.w)}×${Math.round(cg.h)} 從 y=${Math.round(cg.y)}  對話框 y=${Math.round(dlg.y)} 高 ${Math.round(dlg.h)}  蓋住 CG 高度 ${Math.round(cover / cg.h * 100)}%`);
    } else console.log(name, '量不到', JSON.stringify(m));
    await page.context().close();
  }
} finally { await browser.close(); s.kill(); }
