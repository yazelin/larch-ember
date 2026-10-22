// 地圖卡的收音機歌：直接跳到 m_radio_on／mem0_market，一句一句翻，記錄哪一句播了哪個歌檔（攔 HTMLMediaElement.play）。
// 用法：先 build（SONGS_DIR=… python3 src/build.py），再 node tests/songs_sfx.mjs。
// 要看到：m_radio_on 的三句各自播出對應的收音機歌檔，mem0_market 最後一句播出一個檔；沒掛歌的句子不播歌檔。
import { serve, open, sleep, assert } from './lib.mjs';
import { hookInit, cutSizes, named } from './audiohook.mjs';
const CASES = [
  { card: 'm_radio_on', end: /底座歪了一邊/, expect: [['一小段隔著雜訊的台語老歌', /harbor_open/], ['鋼琴前奏響起', /ember_radio_a/], ['（唱）燈一盞一盞暗下來', /ember_radio_b/], ['（唱）掌聲退回了街上', /ember_radio_c/]], none: ['九八點七', '你唱錯了'] },
  { card: 'mem0_market', end: /刷子掛回水龍頭旁/, expect: [['播著〈港邊的燈〉', /harbor_market/]], none: ['水莫噴甲阿桃姨'] },
];
for (const c of CASES) {
  const s = await serve('dist/project.json');
  await fetch(s.base + '/api/lp/card', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ card: c.card, line: 0 }) });
  const ui = await open(s.base, { width: 1280, height: 720, init: hookInit });
  const sizes = cutSizes();
  const snap = async () => {
    const parts = await Promise.all(ui.page.frames().map(f => f.evaluate(() => { const b = document.body.cloneNode(true); b.querySelectorAll('select, option, script, style').forEach(e => e.remove()); return { t: b.textContent, p: window.__bgm || [] }; }).catch(() => ({ t: '', p: [] }))));
    return { t: parts.map(x => x.t).join(' ').replace(/\s+/g, ' '), plays: named(parts.flatMap(x => x.p).sort((a, b) => a.t - b.t), sizes).map(x => x.src) };
  };
  const SFX = /^(press|hover|advance|open|close|use)\.mp3$/;
  const marks = {};   // 文字第一次出現時，已經播了幾個非介面音效
  let all = [];
  for (let i = 0; i < 150; i++) {
    const { t, plays } = await snap();
    all = plays.filter(x => !SFX.test(x) && Object.values(sizes).includes(x));   // 只看歌檔（背景曲不算）
    for (const k of [...c.expect.map(e => e[0]), ...c.none]) if (!(k in marks) && t.includes(k)) marks[k] = all.length;
    if (process.env.DEBUG) console.log(i, all.length, all.slice(-2).join(','), (t.match(/旋鈕喀|九八點七|港邊的燈。阿爸|音量留|指針停|這裡是台南|她本名|2004 年|二十二年後|鋼琴前奏響起|（唱）燈一盞|你唱得很好|阿爸這句|這首播完|我聽完|底座歪/g) || []).join(','));
    if (c.end.test(t)) break;
    await ui.advance(); await sleep(700);
  }
  const seq = all.filter((x, i) => x !== all[i - 1]);   // 同一個檔連續兩次（重新渲染）算一次
  c.expect.forEach(([needle, re], k) => {
    assert(needle in marks, `${c.card}：翻到「${needle}」`);
    // 第 k 句歌詞出現時，已經播出（或馬上播出）第 k 個檔：播出數在 k 到 k+1 之間
    assert(re.test(seq[k] || '') && marks[needle] >= k && marks[needle] <= k + 2, `${c.card}：「${needle}」那一句播出 ${re}（第 ${k + 1} 個非介面音效是 ${seq[k]}）`);
  });
  assert(seq.length === c.expect.length, `${c.card}：沒掛歌的句子沒有多播歌檔（共 ${seq.length} 個：${seq.join(' → ')}）`);
  for (const k of c.none) assert(k in marks, `${c.card}：翻過沒掛歌的「${k}」`);
  console.log(c.card, '非介面音效播放順序：', all.join(' → '));
  await ui.close(); s.kill();
}
