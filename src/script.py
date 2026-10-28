"""從 canon/劇本.md 讀台詞（作者改劇本就改那份）。每個 `## 代號（說明）` 是一段；每行「講者：台詞」。
- 「余靜（心）：」是心裡話，講者仍是余靜（配音同一個聲音、語氣放低）。
- 「旁白：」不配音。講者後面括號裡的舞台指示（例如「（唱）」「（念）」）留在台詞裡，配音前拿掉。
- 行尾 `〔掉字〕` 標記會被拿掉，記在 FADE 裡，建置時依落日替換。
- 「選項：」底下的 `- 文字 → 目標` 存在 CHOICES。
"""
import hashlib, pathlib, re

R = pathlib.Path(__file__).resolve().parent.parent
SRC = R / 'canon/劇本.md'
HEAD = re.compile(r'^## (\w+)')
LINE = re.compile(r'^([^：\s#>-][^：]{0,12})：(.+)$')
CHOICE = re.compile(r'^- (.+?) → (\w+)$')
SHOT = re.compile(r'^〔圖：(\w+)〕$')


def speaker_of(raw):
    """「余靜（心）」→ ('余靜', '心')；「年輕的程希」→ ('程希', '年輕')；「程希（筆記）」→ ('程希', '筆記')。"""
    m = re.match(r'^(.+?)（(.+)）$', raw)
    name, tag = (m.group(1), m.group(2)) if m else (raw, '')
    if name.startswith('年輕的'):
        name, tag = name[3:], '年輕'
    return name, tag


def parse(text=None):
    text = text if text is not None else SRC.read_text(encoding='utf-8')
    L, CHOICES, FADE, SHOTS, cur = {}, {}, set(), {}, None
    for raw in text.splitlines():
        s = raw.strip()
        if s.startswith('## 修改紀錄'):
            break
        h = HEAD.match(s)
        if h:
            cur = h.group(1); L[cur] = []; continue
        if cur is None or not s:
            continue
        g = SHOT.match(s)
        if g:   # 〔圖：s_xxx〕：從下一句起換這張 CG（連續動作一句一張，作者 2026-10-19）
            SHOTS[(cur, len(L[cur]))] = g.group(1); continue
        c = CHOICE.match(s)
        if c:
            CHOICES.setdefault(cur, []).append((c.group(1), c.group(2))); continue
        m = LINE.match(s)
        if not m or m.group(1) == '選項':
            continue
        name, tag = speaker_of(m.group(1))
        line = m.group(2).strip()
        fade = line.endswith('〔掉字〕')
        line = line.replace('〔掉字〕', '').strip()
        spk = '' if name == '旁白' else name
        vid = None if not spk else hashlib.md5(f'{cur}|{spk}|{line}'.encode()).hexdigest()[:10]
        if fade:
            FADE.add((cur, len(L[cur])))
        L[cur].append((spk, line, vid, tag))
    return L, CHOICES, FADE, SHOTS


L, CHOICES, FADE, SHOTS = parse()

if __name__ == '__main__':
    n = sum(len(v) for v in L.values())
    voiced = sum(1 for v in L.values() for x in v if x[2])
    print(len(L), '段', n, '行', voiced, '行要配音', len(FADE), '句會掉字')
    spk = {}
    for v in L.values():
        for x in v:
            spk[x[0] or '旁白'] = spk.get(x[0] or '旁白', 0) + 1
    print(spk)
    assert all(len(v) == 1 for v in CHOICES.values()), CHOICES
    assert all(L[k] for k in L), [k for k in L if not L[k]]
    t, c, f, sh = parse('## a（x）\n〔圖：s_a_1〕\n余靜（心）：好安靜。〔掉字〕\n〔圖：s_a_2〕\n旁白：燈。\n選項：\n- 走 → b\n')
    assert t == {'a': [('余靜', '好安靜。', t['a'][0][2], '心'), ('', '燈。', None, '')]} and c == {'a': [('走', 'b')]} and f == {('a', 0)}, (t, c, f)
    assert sh == {('a', 0): 's_a_1', ('a', 1): 's_a_2'}, sh
    print(len(SHOTS), '個換圖點')
    print('ok')
