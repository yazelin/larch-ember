"""全劇華語配音：讀 canon/劇本.md（script.L），走 .11 larch-tts 橋接服務，輸出 assets/voice/<id>.mp3。
- 檔名是台詞內容的雜湊：改了哪句只重配哪句，已存在的跳過；FORCE=1 繞過快取重產。
- 唱的、哼的句子不配（用歌曲音檔）；開頭的舞台指示（「（念）」「（對程希）」）配音前拿掉。
- 台語講者（阿桃姨、余伯）與 1988 年九歲的余靜另走意傳＋換聲，不在這支。
- 3 線並行：Larch 帳號並行太高會被凍結，不要調高。
python3 src/tts.py [段落代號…]
"""
import json, os, re, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
import script

URL = 'http://192.168.11.11:8072/tts'
KEY = open(os.path.expanduser('~/.config/larch-tts/key')).read().strip()
OUT = os.path.join(os.path.dirname(__file__), '..', 'assets', 'voice')
FORCE = bool(os.environ.get('FORCE'))

VOICE = {   # design/重寫.md「立繪與配音」
    '余靜': 'Chinese (Mandarin)_Warm_Bestie',
    '程希': 'Larch_Mandarin_Uncle',
    '周老師': 'Chinese (Mandarin)_Kind-hearted_Elder',
    '阿哲': 'Chinese (Mandarin)_Southern_Young_Man',
    '陳婉君': 'Chinese (Mandarin)_Wise_Women',
    '林醫師': 'Chinese (Mandarin)_Mature_Woman',
    '舞監': 'Chinese (Mandarin)_Reliable_Executive',
    '員警': 'Chinese (Mandarin)_Reliable_Executive',
    '提詞員': 'Chinese (Mandarin)_Southern_Young_Man',
    '小芳': 'Chinese (Mandarin)_Crisp_Girl',
    '年輕人': 'Chinese (Mandarin)_Straightforward_Boy',
}
TAIGI = {'阿桃姨', '余伯'}
CHILD_CARDS = {'mem0_market'}          # 九歲的余靜另外處理
SUNG = re.compile(r'^（[^）]*(唱|哼)[^）]*）')
DIRECTION = re.compile(r'^（[^）]*）')
EMO = {'心': 'calm', '筆記': 'calm', '年輕': 'calm'}


def jobs(cards=None):
    out = []
    for cid, lines in script.L.items():
        if cards and cid not in cards:
            continue
        for spk, text, vid, tag in lines:
            if not vid or spk in TAIGI or spk not in VOICE or SUNG.match(text):
                continue
            if spk == '余靜' and cid in CHILD_CARDS:
                continue
            say = DIRECTION.sub('', text).replace('……', '，').strip()
            if re.search(r'[\u4e00-\u9fffA-Za-z0-9]', say):   # 只有「……」的沉默不配
                out.append((f'{vid}.mp3', say, VOICE[spk], EMO.get(tag, 'calm')))
    return out


def one(job):
    fn, text, voice, emo = job
    path = os.path.join(OUT, fn)
    if not FORCE and os.path.exists(path):
        return None
    body = json.dumps({'text': text, 'voice': voice, 'format': 'mp3', 'emotion': emo, **({'force': True} if FORCE else {})}).encode()
    for k in range(3):
        try:
            data = urllib.request.urlopen(urllib.request.Request(URL, data=body, headers={'Content-Type': 'application/json', 'X-API-Key': KEY}), timeout=300).read()
            open(path, 'wb').write(data)
            return fn
        except Exception as e:  # noqa: BLE001
            print('retry', fn, k + 1, repr(e)[:80], flush=True)
    print('FAIL', fn, text[:20], flush=True)
    return None


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    js = jobs(set(sys.argv[1:]) or None)
    print(len(js), '句要配', flush=True)
    with ThreadPoolExecutor(3) as ex:
        done = [x for x in ex.map(one, js) if x]
    print('新配', len(done), '句')
