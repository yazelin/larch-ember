#!/usr/bin/env python3
"""接歌結果檢查（build 之後跑）：python3 tests/songs_check.py
- 沒有 manifest：確認專案裡沒有任何 __song／__post 卡、也沒有 sfxUrl（負控制：沒放歌時 build 跟原本一樣）。
- 有 manifest：每個通過驗證的切段都接上了；歌卡有 autoAdvance、歌不循環、檔案在 dist/assets；
  劇本裡每一句非歌詞台詞都還在（前／後卡保留），每一句劇本歌詞都出現在歌卡；所有邊都連得上，從 start 走得到每張歌卡。
SONGS_DIR 跟 songs_cut.py 一樣可以換成替身資料夾。
"""
import json, os, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src'))
import script   # noqa: E402

P = json.loads((ROOT / 'dist/project.json').read_text(encoding='utf-8'))
P = P.get('project', P)
board = P['boards'][0]
nodes = {n['id']: n for n in board['nodes']}
edges = board['edges']
sd = pathlib.Path(os.environ.get('SONGS_DIR') or ROOT / 'assets/songs')
sd = (sd if sd.is_absolute() else ROOT / sd).resolve()
mf_path = sd / 'cuts/manifest.json'
fails = []


def check(cond, msg):
    print(('ok   ' if cond else 'FAIL ') + msg)
    if not cond:
        fails.append(msg)


def norm(s):
    return re.sub(r'[^一-鿿A-Za-z0-9]', '', s.replace('（唱）', ''))


bad = [e['id'] for e in edges if e['source'] not in nodes or e['target'] not in nodes]
check(not bad, f'所有邊兩端都存在 {bad}')
sfx_lines = [(n['id'], l) for n in nodes.values() for l in n['data'].get('dialogueLines', []) if l.get('sfxUrl')]
split = [i for i in nodes if i.endswith('__song') or i.endswith('__post')]

if not mf_path.exists():
    check(not split and not sfx_lines, '沒有 manifest：專案沒有歌卡與 sfxUrl（跟沒放歌時一樣）')
    sys.exit(1 if fails else 0)

mf = json.loads(mf_path.read_text(encoding='utf-8'))
# 從 start 可到達
start = [n['id'] for n in nodes.values() if n['data'].get('start')]
adj = {}
for e in edges:
    adj.setdefault(e['source'], []).append(e['target'])
seen, st = set(), list(start)
while st:
    x = st.pop()
    if x in seen:
        continue
    seen.add(x); st += adj.get(x, [])
for cut in mf['cuts']:
    if not cut['verify']['ok']:
        check(not any(cut['file'] in (l.get('sfxUrl') or '') for _, l in sfx_lines), f"{cut['id']} 驗證沒過，沒有被接進去")
        continue
    cid, li, role = cut['place']['card'], cut['place']['line'], cut['role']
    url = '/files/assets/' + (sd / 'cuts' / cut['file']).relative_to(ROOT / 'assets').as_posix()
    check((ROOT / 'dist' / url.replace('/files/', '')).exists(), f"{cut['id']} 檔案在 dist")
    if role == 'sfx':
        hit = [l for l in nodes[cid]['data']['dialogueLines'] if l.get('sfxUrl') == url]
        check(len(hit) == 1 and cut['place']['anchor'] in hit[0]['text'], f"{cut['id']}：{cid} 的「{cut['place']['anchor']}」那一句掛了 sfxUrl")
    elif role == 'line_bgm':
        hit = [l for l in nodes[cid]['data']['dialogueLines'] if l.get('bgm') == url]
        check(len(hit) == 1 and cut['place']['anchor'] in hit[0]['text'] and hit[0].get('bgmLoop') is False, f"{cut['id']}：{cid} 那一句起放、不循環")
    else:
        song = nodes.get(cid + '__song') or nodes[cid]
        d = song['data']
        check(d.get('bgm') == url and d.get('bgmLoop') is False, f"{cut['id']}：歌卡 {song['id']} 卡片層掛歌、不循環")
        aa = d.get('autoAdvance') or {}
        check(aa.get('enabled') and aa.get('mode') == 'delay' and aa.get('delayMs', 0) > 0, f"{cut['id']}：歌卡有 autoAdvance（{aa.get('delayMs')}ms）")
        reach, st2 = set(), [cid]
        while st2:
            x = st2.pop()
            if x not in reach:
                reach.add(x); st2 += adj.get(x, [])
        check(song['id'] in reach, f"{cut['id']}：從 {cid} 沿邊走得到歌卡")
        text = ''.join(norm(l['text']) for l in d['dialogueLines'])
        want = [t for spk, t, *_ in script.L[cid] if spk == '余靜' and t.startswith('（唱）')]
        miss = [t for t in want if norm(t) not in text]
        check(not miss, f"{cut['id']}：劇本的 {len(want)} 句歌詞都在歌卡（缺 {miss}）")
        check(all(not l['text'].startswith('（唱）') or l['speaker'] == '余靜' for l in d['dialogueLines']), f"{cut['id']}：歌詞畫面講者是余靜")
        # 非歌詞台詞在前／後卡
        outside = ''.join(norm(l['text']) for i in (cid, cid + '__post') if i in nodes for l in nodes[i]['data']['dialogueLines'] if i != song['id'])
        non = [t for spk, t, *_ in script.L[cid] if not (spk == '余靜' and t.startswith('（唱）'))]
        check(all(norm(t) in outside for t in non), f"{cut['id']}：{cid} 其餘 {len(non)} 句劇本台詞都還在前／後卡")
        # 只有歌卡有 autoAdvance
        check(all('autoAdvance' not in nodes[i]['data'] for i in (cid, cid + '__post') if i in nodes and i != song['id']), f"{cut['id']}：前／後卡沒有 autoAdvance")
print('全部通過' if not fails else f'{len(fails)} 項失敗')
sys.exit(1 if fails else 0)
