// 攔音訊播放（給 play_full.mjs 與 songs_sfx.mjs 用）。
// 播放器對逐句 sfx 會先 fetch 成 blob 再丟給「重複使用的 Audio 元素」，play() 時 currentSrc 可能還是上一首、src 是 blob:uuid，
// 所以另外攔 URL.createObjectURL 記下每個 blob 的位元組數，play() 時用位元組數對回歌檔（切段檔大小各不相同）。
import { readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';

export const hookInit = () => {
  window.__bgm = window.__bgm || [];
  window.__blobs = window.__blobs || {};
  const co = URL.createObjectURL;
  URL.createObjectURL = function (b) { const u = co.call(this, b); try { window.__blobs[u] = b.size; } catch {} return u; };
  const push = (kind, el) => { try { const src = String(el?.src || el?.currentSrc || ''); window.__bgm.push({ t: Math.round(performance.now()), ts: Date.now(), kind, src: src.split('/').pop(), size: window.__blobs[src] || 0 }); } catch {} };
  document.addEventListener('play', e => push('play', e.target), true);
  const play = HTMLMediaElement.prototype.play;   // 沒掛進 DOM 的 new Audio() 不會冒泡到 document，直接攔 play()
  HTMLMediaElement.prototype.play = function (...a) { push('play', this); return play.apply(this, a); };
};

/** dist/assets 底下所有 cuts/*.mp3 與 sfx/*.mp3（逐句音效）的 {位元組數: 檔名} */
export function cutSizes(root = 'dist/assets') {
  const m = {};
  const walk = d => { for (const f of readdirSync(d)) { const p = join(d, f); if (statSync(p).isDirectory()) walk(p); else if (/\/(cuts|sfx)\/[^/]+\.mp3$/.test(p)) m[statSync(p).size] = f; } };
  try { walk(root); } catch {}
  return m;
}

/** 把記錄裡 blob 的名字換回歌檔名 */
export function named(list, sizes) {
  return list.map(x => ({ ...x, src: (x.size && sizes[x.size]) || x.src }));
}
