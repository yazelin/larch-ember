#!/usr/bin/env python3
"""劇本台詞機械檢查（作者 2026-10-20：旁白不要寫比喻、不要客服腔、不要 AI 腔）。
python3 tests/check_voice.py [檔案…]   預設 canon/劇本.md；有硬規則違反就 exit 1。
硬規則：旁白用比喻（像／彷彿／好像／似乎）、勉強的「X 得 Y」形容（亮得停不下來、酸得像…）、禁用詞、客服句型、破折號、不是…而是。
警告：連續一問一答 > 2、單場心聲 > 8、旁白情緒詞、對白書面語（2026-10-23 加，只警告不擋）。"""
import re, sys, pathlib
files = [pathlib.Path(a) for a in sys.argv[1:]] or [pathlib.Path(__file__).resolve().parent.parent / 'canon/劇本.md']
BAN = ['一個字都', '沒有放掉', '不肯放掉', '手很穩', '話很少', '先把燈', '想不起來為什麼', '理由不見', '——', '長出', '長成']
CS = ['我記住了', '謝謝你，', '慢慢來', '你先坐', '放在椅背', '好，我記', '謝謝你。']
SIM = re.compile(r'像|彷彿|好像|似乎|宛如|如同')
STRAIN = re.compile(r'[亮酸軟冷緊熱燙沉輕重脆][得][^，。！？]{0,8}(停不下來|像|要命|不得了|發亮|發抖)')
ALLOW = ('像在等人',)   # 作者看過、保留的畫面句（結局 C 舊石階）
# 唱詞必須逐字等於歌詞檔（作者要拿歌詞去 Suno，不能被悄悄改）
_LY = pathlib.Path(__file__).resolve().parent.parent / 'canon/歌詞.md'
_norm = lambda t: re.sub(r'[\s，。、！？「」…·\-—,.!?]', '', t)
LYRICS = _norm('\n'.join(l for l in _LY.read_text(encoding='utf-8').split('\n') if not l.startswith(('#', '```', '[', '-', '劇情', '遊戲裡', '台語', '一定', '加分')))) if _LY.exists() else ''
# 評分五（作者 2026-10-23）：旁白直接寫情緒的詞 → 警告。旁白只寫看得到的事，情緒交給動作與物件。
EMO = re.compile(r'難過|悲傷|傷心|心疼|感動|溫柔地|深情地|痛苦地|哀傷|心碎|不捨|欣慰|落寞|惆悵|黯然|悵然|無奈地|寵溺|愧疚|欣喜')
# 評分三之二（作者 2026-10-23）：對白（含心聲，不含旁白、（唱）、（念））裡念不出口的書面語 → 警告。
# 清單取台灣口語少用、讀起來像文章的連接詞與文言字；「而且」「然而」「之前」「其實」這類口語常用的排除。
WRITTEN = re.compile(r'並且|於是|以及|此刻|彷彿|宛如|何以|倘若|便是|已然|未曾|尚未|不禁|甚是|頗為|皆是|之所以|此時|故而|然後便'
                     r'|(?<![然因從反進繼幸偶忽時故])而(?![且已])'
                     r'|(?<![總前後類間一分])之(?![前後類間一中外內])'
                     r'|(?<![尤與極])其(?![實他它中餘次])')
hard = warn = 0
soft = {'旁白情緒詞': 0, '對白書面語': 0}
for f in files:
    sec = None; rows = []
    def flush():
        global warn
        if not rows: return
        run = best = 0
        for a, b in zip(rows, rows[1:]):
            if re.search(r'[？?]$', a) and re.match(r'\w+：', a) and re.match(r'\w+：', b) and a.split('：')[0] != b.split('：')[0]:
                run += 1; best = max(best, run)
            else: run = 0
        hearts = sum('（心）' in r for r in rows)
        if best > 2: warn += 1; print(f'  警告 [{sec}] 連續問答 {best} 組')
        if hearts > 8: warn += 1; print(f'  警告 [{sec}] 心聲 {hearts} 句')
    for line in f.read_text(encoding='utf-8').split('## 修改紀錄')[0].split('\n'):
        m = re.match(r'## (\w+)', line)
        if m: flush(); sec, rows = m.group(1), []; continue
        if not line.strip() or line.startswith(('〔', '<!--', '#', '|', '-', '選項')): continue
        rows.append(line)
        txt = line.split('：', 1)[-1]
        probs = []
        if line.startswith('旁白：') and SIM.search(txt) and not any(a in txt for a in ALLOW): probs.append('旁白用比喻')
        if STRAIN.search(txt): probs.append('勉強的形容')
        probs += [f'禁用詞「{b}」' for b in BAN if b in txt]
        probs += [f'客服句型「{c}」' for c in CS if c in txt]
        if re.search(r'不是[^。！？「」]{1,30}[，；、]?而是', txt): probs.append('不是…而是')
        if re.match(r'(余靜|程希)：（唱）', line):
            t = _norm(txt.replace('（唱）', ''))
            if t and LYRICS and t not in LYRICS and not any(k in txt for k in ('欲落雨', '阿公仔', '欲掘芋', '天烏烏', '天黑黑', '掘啊掘')):   # 〈天烏烏〉是公有童謠，不在歌詞檔
                probs.append('唱詞不在歌詞檔裡（必須逐字相同）')
        for p in probs: hard += 1; print(f'  ✗ [{sec}] {p}：{line[:70]}')
        if line.startswith('旁白：') and (m := EMO.search(txt)) and not any(a in txt for a in ALLOW):
            warn += 1; soft['旁白情緒詞'] += 1; print(f'  警告 [{sec}] 旁白情緒詞「{m.group(0)}」：{line[:70]}')
        if not line.startswith('旁白：') and re.match(r'[^：]{1,12}：', line) and not re.match(r'[^：]{1,12}：（[唱念]）', line) and not re.match(r'[^：]{1,12}（念）：', line):
            if (m := WRITTEN.search(re.sub(r'（[^）]*）', '', txt))):   # 台語字幕括號裡的華語不算
                warn += 1; soft['對白書面語'] += 1; print(f'  警告 [{sec}] 對白書面語「{m.group(0)}」：{line[:70]}')
    flush()
print(f'硬規則違反 {hard}，警告 {warn}（其中旁白情緒詞 {soft["旁白情緒詞"]}、對白書面語 {soft["對白書面語"]}）'); sys.exit(1 if hard else 0)
