"""量劇本：每條路線行數字數、余靜 2026 下午三個數字。python3 design/余靜改寫/metrics.py [劇本檔]"""
import re, sys
t = open(sys.argv[1] if len(sys.argv) > 1 else 'canon/劇本.md', encoding='utf-8').read().split('## 修改紀錄')[0]
sec = {}
for p in re.split(r'\n(?=## )', t):
    m = re.match(r'## ([A-Za-z0-9_]+)', p)
    if m: sec[m.group(1)] = p
def lines(names):
    for n in names:
        for l in sec[n].splitlines():
            if re.match(r'^[^\s：〔#\-|]+：', l): yield n, l
def stat(names):
    L = list(lines(names)); return len(L), sum(len(l.split('：', 1)[1]) for _, l in L)
common = [n for n in sec if not n.startswith(('ending_', 'cheng_pov'))]
ends = {'A': ['ending_a1', 'ending_a2', 'ending_a3'], 'B': ['ending_b1', 'ending_b2'], 'C': ['ending_c1', 'ending_c2', 'ending_c3', 'ending_c4']}
c = stat(common); print('共同', c)
for k, v in ends.items():
    e = stat(v); print(f'路線{k} 行{c[0]+e[0]} 字{c[1]+e[1]}')
now = ['prologue','soundcheck','card_dress','m_dressing_intro','m_window','m_mirror','m_notebook','m_rose_dry','m_jewelry','m_radio','m_radio_on','m_letter','m_note','m_corridor','m_auditorium','m_alley','branch_dark','concert']
forget = re.compile(r'忘|想不起|想不出|不記得|記不|認不')
fear = re.compile(r'怕|慌|不安|對不起|抱歉|發抖|手在抖|哭|眼眶|害怕|不好意思')
joke = re.compile(r'喔|啦|耶|欸|最好是')
tot = f1 = f2 = j = 0
for n, l in lines(now):
    if re.match(r'^余靜(（[^）]*）)?：', l) and '（唱）' not in l and '（念）' not in l:
        x = l.split('：', 1)[1]; tot += 1
        f1 += bool(forget.search(x)); f2 += bool(fear.search(x)); j += bool(joke.search(x))
print(f'余靜2026下午 {tot} 句；忘／想不起類 {f1}；害怕／道歉類 {f2}；輕鬆語氣詞 {j}')
