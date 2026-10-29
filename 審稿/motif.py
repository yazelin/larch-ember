#!/usr/bin/env python3
"""意象替換提案（作者 10-29：每次留一朵玫瑰感覺不浪漫，像噁男、恐怖，要調整或換掉）：各寫手各提一個做法，存 比賽/意象_<詞>/提案_<人>.md，作者挑。
  python3 審稿/motif.py 玫瑰 "作者的話"
提示詞由程式從劇本、角色設定、歌詞抓出所有提到這個詞的地方，不放例句。"""
import sys, pathlib, re, concurrent.futures as cf
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import scene_review as sr, contest
REPO = pathlib.Path(__file__).resolve().parent.parent
P = """你是互動小說（視覺小說）的編劇顧問。作者試玩後說：「{said}」
下面是這部作品裡所有提到「{word}」的地方（檔名:行號｜內容），以及每一場的標題。請提出一個你最推薦的做法，讓這條線在台灣讀者眼中是浪漫、讓人喜歡這兩個人的，不會覺得被跟蹤、不舒服。可以保留「{word}」只改送的方式，也可以換成別的信物或別種形式，由你判斷。
請用這個格式回答，不要客套：
一、為什麼現在讓人不舒服（三句以內）
二、做法（一段話講清楚：誰、什麼時候、怎麼做，她當下知不知道是誰）
三、每一場怎麼改（列出場代號，每場一兩句；沒提到的場不動）
四、歌詞〈餘燼〉要不要改、改哪幾句（歌已經錄好，改就要重錄）
五、要重畫的 CG 與要改的道具
六、這個做法的風險
【各場標題】
{titles}
【提到「{word}」的地方】
{hits}"""

if __name__ == '__main__':
    word, said = sys.argv[1], sys.argv[2]
    files = ['canon/劇本.md', 'design/角色.md', 'design/重製.md']
    hits = '\n'.join(f'{f}:{n}｜{l.strip()}' for f in files for n, l in enumerate((REPO / f).read_text().splitlines(), 1) if word in l or '一朵紅' in l)
    titles = '\n'.join(l for l in (REPO / 'canon/劇本.md').read_text().splitlines() if l.startswith('## '))
    out = contest.D / f'意象_{word}'; out.mkdir(parents=True, exist_ok=True)
    p = P.format(said=said, word=word, titles=titles, hits=hits); (out / 'prompt.txt').write_text(p)
    with cf.ThreadPoolExecutor(3) as ex:
        for k, t in zip(contest.WRITERS, ex.map(lambda f: sr.call(f, p), contest.WRITERS.values())): (out / f'提案_{k}.md').write_text(t); print('寫完', k, len(t))
