#!/usr/bin/env python3
"""讀者小組：請兩個模型家族（deepseek-v4.1-flash:1017 走 llmshare、gemini 走自架 gemini-web）當台灣讀者，逐句標「不像真人會講或會寫」的句子。
python3 src/panel.py flag <劇本檔> [場景代號,…]   → design/讀者反應/panel-<檔名>.json（被標的句子與原因）
python3 src/panel.py apply <修句.json> <檔案…>     → 把 codex 回的 [{舊,新}] 套進檔案（整行完全比對）
兩個模型的意見會有誤判（例如把對的台語、對的蓋章當成錯），所以標出來的句子要由編劇判斷成不成立，不是自動改。"""
import json, os, re, ssl, subprocess, sys, urllib.request, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
PROMPT = ('你是台灣人，也是挑剔的小說編輯。下面是一部視覺小說的台詞與旁白（每行前面是行號）。請逐行檢查，只標出「不像真人會講或會寫」的行：'
          '包括奇怪或不通的比喻、勉強的形容、硬湊的文藝句、客氣得像客服的對話、讀起來像 AI 寫的句子、動作或情緒描寫不合常理、用詞不是台灣習慣。'
          '只輸出一個 JSON 陣列，每個元素 {"行":行號,"原因":"一句話"}，沒有問題的行不要列。不要輸出其他文字。\n\n')


def sections(path, only=None):
    s = pathlib.Path(path).read_text(encoding='utf-8').split('## 修改紀錄')[0].split('## 編劇說明')[0].split('## 來源對照')[0]
    out = {}
    for x in re.split(r'(?=^## )', s, flags=re.M):
        m = re.match(r'## (\w+)', x)
        if m and (not only or m.group(1) in only):
            out[m.group(1)] = [l for l in x.split('\n')[1:] if l.strip() and not l.startswith(('〔', '<!--'))]
    return out


def parse(t):
    m = re.search(r'\[.*\]', t, re.S)
    try: return json.loads(m.group(0))
    except Exception: return None


def ask_deepseek(p):
    return parse(subprocess.run(['llmshare', 'raw', 'deepseek-v4.1-flash:1017', p], capture_output=True, text=True, timeout=400).stdout)


def ask_gemini(p):
    key = [l.split('=', 1)[1].strip().strip('"') for l in open(os.path.expanduser('~/.bashrc'), encoding='utf-8') if l.startswith('export GEMINI_IMAGE_KEY=')][0]
    req = urllib.request.Request('https://192.168.11.11/gemini-web/api/chat', json.dumps({'prompt': p}).encode(), {'Content-Type': 'application/json', 'x-goog-api-key': key})
    try: return parse(json.load(urllib.request.urlopen(req, timeout=400, context=ssl._create_unverified_context())).get('text', ''))
    except Exception: return None


def flag(path, only=None, chunk=90):
    secs = sections(path, only); lines = [(k, l) for k, ls in secs.items() for l in ls]
    flagged = {}
    for a in range(0, len(lines), chunk):   # 太長一次標不準，90 行一批
        part = lines[a:a + chunk]
        p = PROMPT + '\n'.join(f'{i + 1:3}｜{l}' for i, (_, l) in enumerate(part))
        for name, fn in (('deepseek', ask_deepseek), ('gemini', ask_gemini)):
            for x in fn(p) or []:
                try: k, l = part[int(x['行']) - 1]
                except Exception: continue
                flagged.setdefault(l, {'場景': k, '意見': []})['意見'].append(f"{name}：{x['原因']}")
    out = ROOT / f'design/讀者反應/panel-{pathlib.Path(path).stem}.json'
    out.write_text(json.dumps([{'行': l, **v} for l, v in flagged.items()], ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'{len(lines)} 行，被標 {len(flagged)} 行 → {out}')


def apply(fixes, files):
    d = json.load(open(fixes, encoding='utf-8'))
    for f in files:
        s = pathlib.Path(f).read_text(encoding='utf-8'); n = 0
        for x in d:
            if x['舊'] in s and x['新'] != x['舊']: s = s.replace(x['舊'], x['新']); n += 1
        pathlib.Path(f).write_text(s, encoding='utf-8'); print(f, n, '/', len(d))


if __name__ == '__main__':
    c = sys.argv[1]
    if c == 'flag': flag(sys.argv[2], sys.argv[3].split(',') if len(sys.argv) > 3 else None)
    elif c == 'apply': apply(sys.argv[2], sys.argv[3:])
