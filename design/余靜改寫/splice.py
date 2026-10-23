"""把 b*.out.md 的場景換進劇本並檢查格式。python3 design/余靜改寫/splice.py [輸出檔，預設 /tmp 副本]"""
import re, sys, os
D = 'design/余靜改寫'
src = open('canon/劇本.md', encoding='utf-8').read()
head, tail = src.split('## 修改紀錄', 1) if '## 修改紀錄' in src else (src, None)
parts = re.split(r'\n(?=## )', head)
idx = {re.match(r'## ([A-Za-z0-9_]+)', p).group(1): i for i, p in enumerate(parts) if re.match(r'## ([A-Za-z0-9_]+)', p)}
MUST = {'prologue': ['我爸賣魚，整天'], 'card_dress': ['這件還在喔'], 'm_dressing_intro': ['鏡子裡多一個人'],
        'm_mirror': ['2013，永明，空舞台'], 'm_radio_on': ['一小段隔著雜訊的台語老歌', '鋼琴前奏響起', '余靜：（唱）燈一盞一盞暗下來', '余靜：（唱）掌聲退回了街上'],
        'm_letter': ['河岸留言那晚，你唱〈天烏烏〉，我沒走。', '程希，三排十四號'], 'm_note': ['今天有人坐在三排十四號，陪你唱歌。'],
        'm_corridor': ['把花那句唱得特別輕'], 'mem4_clinic': ['早發性阿茲海默症'], 'mem4_name': ['我是你先生'],
        'branch_dark': ['選項：\n- 有人會坐在三排十四號。 → ending_a\n- 周老師在等我開口。 → ending_b\n- 阿爸一個人收不完。 → ending_c']}
DL = lambda s: [l for l in s.splitlines() if re.match(r'^[^\s：〔#\-|]+：', l)]
bad = 0; new = {}
for k in sorted(f for f in os.listdir(D) if re.match(os.environ.get('OUTS', r'b\d\.out\.md$'), f)):
    txt = open(f'{D}/{k}', encoding='utf-8').read().strip().strip('`')
    for p in re.split(r'\n(?=## )', txt):
        m = re.match(r'## ([A-Za-z0-9_]+)', p.strip())
        if not m: continue
        new[m.group(1)] = p.strip()
for n, p in new.items():
    o = parts[idx[n]]
    if p.splitlines()[0] != o.splitlines()[0]: print('✗ 標題不同', n); bad += 1
    if re.findall(r'〔圖：[^〕]+〕', p) != re.findall(r'〔圖：[^〕]+〕', o): print('✗ 〔圖〕不同', n, re.findall(r'〔圖：[^〕]+〕', o), re.findall(r'〔圖：[^〕]+〕', p)); bad += 1
    if p.count('〔掉字〕') != o.count('〔掉字〕'): print('✗ 〔掉字〕數不同', n); bad += 1
    for s in MUST.get(n, []):
        if s not in p: print('✗ 缺必留', n, s[:30]); bad += 1
    if n == 'm_dressing_intro' and DL(p)[-1] != '余靜（心）：杯子放在右邊，線也沒壓到。': print('✗ 開場最後一句不對', DL(p)[-1]); bad += 1
    ol, nl = DL(o), DL(p)
    print(f'  {n:18s} 行 {len(ol):3d}→{len(nl):3d}  字 {sum(len(l.split("：",1)[1]) for l in ol):4d}→{sum(len(l.split("：",1)[1]) for l in nl):4d}')
    parts[idx[n]] = p + '\n'
missing = [n for n in 'prologue soundcheck card_dress m_dressing_intro m_window m_mirror m_notebook m_rose_dry m_jewelry m_radio m_radio_on m_letter m_note m_corridor m_auditorium m_alley branch_dark concert mem3_forget mem4_clinic mem4_letter mem4_name'.split() if n not in new]
if missing: print('✗ 缺場', missing); bad += 1
out = '\n'.join(x.rstrip('\n') + '\n' for x in parts).replace('\n\n\n', '\n\n')
if tail is not None: out = out.rstrip('\n') + '\n\n## 修改紀錄' + tail
dst = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('CLAUDE_JOB_DIR', '/tmp') + '/tmp/劇本-候選.md'
open(dst, 'w', encoding='utf-8').write(out)
print('格式問題', bad, '→', dst, '〔圖〕總數', out.count('〔圖：'))
