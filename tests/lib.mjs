// 測試共用：開 larch-preview、讀所有 frame 的文字、按鍵
import { chromium, devices } from '/home/ct/larch-preview/node_modules/playwright-core/index.mjs';
import { spawn } from 'node:child_process';
export { devices };
// SPEED=16：遊戲裡的時間（計時器、動畫、配音）加速 16 倍，測試這邊的固定等待也除以 16
export const SPEED = Math.max(1, Number(process.env.SPEED) || 1);
export const sleep = ms => new Promise(r => setTimeout(r, Math.max(30, ms / SPEED)));

// 注入每個 frame：計時器縮短、時鐘跑快、CSS/WAAPI 動畫與音訊加速
function timewarp(S) {
  if (S <= 1) return;
  const pn = performance.now.bind(performance), dn = Date.now, p0 = pn(), d0 = dn();
  performance.now = () => p0 + (pn() - p0) * S;
  Date.now = () => d0 + (dn() - d0) * S;
  const st = window.setTimeout, si = window.setInterval, raf = window.requestAnimationFrame;
  window.setTimeout = (f, d = 0, ...a) => st(f, d / S, ...a);
  window.setInterval = (f, d = 0, ...a) => si(f, Math.max(1, d / S), ...a);
  window.requestAnimationFrame = cb => raf(t => cb(p0 + (t - p0) * S));
  const play = HTMLMediaElement.prototype.play;
  HTMLMediaElement.prototype.play = function (...a) { try { this.playbackRate = Math.min(S, 16); } catch {} return play.apply(this, a); };
  si(() => { try { document.getAnimations().forEach(x => { if (x.playbackRate !== S) x.playbackRate = S; }); } catch {} }, 50);
}

export async function serve(json) {
  const proc = spawn('python3', ['/home/ct/larch-preview/serve.py', json, '--port', '0'], { stdio: ['ignore', 'pipe', 'inherit'] });
  const base = await new Promise((ok, bad) => {
    proc.stdout.on('data', d => { const m = d.toString().match(/預覽：(http:\/\/127\.0\.0\.1:\d+)/); if (m) ok(m[1]); });
    proc.on('exit', c => bad(new Error('serve.py exit ' + c)));
  });
  return { base, kill: () => proc.kill() };
}

export async function open(base, { mobile = false, width = 1280, height = 800 } = {}) {
  const browser = await chromium.launch({
    executablePath: process.env.CHROME || '/usr/bin/google-chrome',
    headless: process.env.HEADED ? false : true,
    args: ['--disable-gpu', '--disable-dev-shm-usage', '--autoplay-policy=no-user-gesture-required', '--no-sandbox']
  });
  const ctx = await browser.newContext(mobile ? { ...devices['iPhone 13'], locale: 'zh-TW' } : { viewport: { width, height }, deviceScaleFactor: 1, locale: 'zh-TW' });
  if (SPEED > 1) await ctx.addInitScript(timewarp, SPEED);
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('crash', () => console.log('PAGE CRASH'));
  await page.goto(base.startsWith('http') && base.includes('/preview/') ? base : base + '/');
  await new Promise(r => setTimeout(r, 3500));   // 首次載入是網路時間，不跟著加速
  const text = async () => (await Promise.all(page.frames().map(f => f.locator('body').innerText().catch(() => '')))).join(' | ').replace(/\s+/g, ' ');
  const waitText = async (re, ms = 15000) => {
    const end = Date.now() + ms;
    while (Date.now() < end) { const t = await text(); if (re.test(t)) return t; await sleep(250); }
    throw new Error('等不到 ' + re + '；畫面：' + (await text()).slice(0, 400));
  };
  const clickText = async (s, ms = 30000) => {
    const end = Date.now() + ms;
    while (Date.now() < end) {
      for (const f of page.frames()) { const l = f.getByText(s, { exact: false }); if (await l.count()) { await l.first().click(); return; } }
      await sleep(300);
    }
    throw new Error('找不到可點的「' + s + '」');
  };
  const frameWith = async (sel) => { for (const f of page.frames()) if (await f.locator(sel).count()) return f; return null; };
  const advance = async () => {
    for (const f of page.frames()) { const b = f.locator('.vn2-box'); if (await b.count() && await b.first().isVisible()) { await b.first().click(); return; } }
    await page.keyboard.press('Enter');
  };
  return { advance, browser, page, errors, text, waitText, clickText, frameWith, close: () => browser.close() };
}

export function assert(cond, msg) { if (!cond) throw new Error('FAIL: ' + msg); console.log('ok  ', msg); }
