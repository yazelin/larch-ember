#!/usr/bin/env python3
"""劇本台詞機械檢查（作者 2026-10-20：旁白不要寫比喻、不要客服腔、不要 AI 腔）。
python3 tests/check_voice.py [檔案…]   預設 canon/劇本.md；有硬規則違反就 exit 1。
硬規則：旁白用比喻（像／彷彿／好像／似乎）、勉強的「X 得 Y」形容（亮得停不下來、酸得像…）、禁用詞、客服句型、破折號、不是…而是。
警告：連續一問一答 > 2、單場心聲 > 8。"""
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
hard = warn = 0
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
            if t and LYRICS and t not in LYRICS and not any(k in txt for k in ('欲落雨', '阿公仔', '欲掘芋', '天烏烏', '天黑黑')):   # 〈天烏烏〉是公有童謠，不在歌詞檔
                probs.append('唱詞不在歌詞檔裡（必須逐字相同）')
        for p in probs: hard += 1; print(f'  ✗ [{sec}] {p}：{line[:70]}')
    flush()
print(f'硬規則違反 {hard}，警告 {warn}'); sys.exit(1 if hard else 0)
