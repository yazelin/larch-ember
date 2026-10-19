"""台語配音：意傳（台語漢字→台羅→合成，唸法作者確認）＋ .11 Seed-VC 換聲（design/重寫.md「立繪與配音」）。
也處理 1988 年九歲余靜的台詞：華語走 larch-tts 的小孩聲；台語走意傳＋換成小孩聲。
意傳 demo 一分鐘 3 句，這支自己放慢。輸出 assets/voice/<id>.mp3（跟華語同一套檔名）。
python3 src/taigi.py
"""
import json, os, re, subprocess, sys, time, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(__file__))
import script

R = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(R, 'assets/voice')
WORK = os.path.join(R, 'art/voice-test/taigi')
UA = {'User-Agent': 'Mozilla/5.0'}
TTS = 'http://192.168.11.11:8072/tts'
KEY = open(os.path.expanduser('~/.config/larch-tts/key')).read().strip()
# 換聲的參考聲音（larch-tts 先產一段華語當參考）
REF = {'antie': 'Chinese (Mandarin)_Kind-hearted_Antie', 'aunt': 'Chinese (Mandarin)_Warm-HeartedAunt',
       'dad': 'Larch_Mandarin_Dad', 'child': 'Larch_Mandarin_Child'}
REF_TEXT = '來，坐下來，我跟你講。今天市場的魚很新鮮，你要不要帶一尾回去？天黑了，路上要小心喔。'
HANZI = re.compile(r'[一-鿿]')
TAIGI_MARK = re.compile(r'[欲袂矣恁阮佇遐遮咧閣攏毋𪜶跍啥按怎彼這尾仔]')   # 有這些字的當台語


def gloss_off(t):
    return re.sub(r'（[^）]*）', '', t).strip()


def tts(text, voice, path):
    body = json.dumps({'text': text, 'voice': voice, 'format': 'mp3', 'emotion': 'calm'}).encode()
    open(path, 'wb').write(urllib.request.urlopen(urllib.request.Request(TTS, data=body, headers={'Content-Type': 'application/json', 'X-API-Key': KEY}), timeout=300).read())


def _get(url, timeout):
    for k in range(5):   # 意傳 demo 限流時回 500：等 65 秒再試
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()
        except Exception as e:  # noqa: BLE001
            print('限流，等一下', repr(e)[:60], flush=True); time.sleep(65)
    raise RuntimeError('意傳一直失敗：' + url[:80])


def ithuan(text, path):
    # GET /tau 2026-10-19 起一直回 500，POST 正常（同一份結果）
    body = urllib.parse.urlencode({'taibun': text}).encode()
    kip = json.loads(urllib.request.urlopen(urllib.request.Request('https://hokbu.ithuan.tw/tau', data=body, headers=UA), timeout=60).read())['KIP']
    open(path, 'wb').write(_get('https://hapsing.ithuan.tw/bangtsam?' + urllib.parse.urlencode({'taibun': kip}), 90))
    return kip
    for k in range(4):
        try:
            open(path, 'wb').write(urllib.request.urlopen(urllib.request.Request('https://hapsing.ithuan.tw/bangtsam?' + urllib.parse.urlencode({'taibun': kip}), headers=UA), timeout=90).read())
            return kip
        except Exception as e:  # noqa: BLE001  限流 500：等 65 秒
            print('限流，等一下', e, flush=True); time.sleep(65)
    raise RuntimeError('意傳合成失敗：' + text)


def jobs():
    out = []
    for cid, lines in script.L.items():
        for spk, text, vid, tag in lines:
            if not vid or text.startswith('（哼）') or text.startswith('（唱）'):
                continue
            say = gloss_off(re.sub(r'^（[^）]*）', '', text))
            if spk in ('阿桃姨', '余伯'):   # 喊出來的華語（「舊的石階！護欄下面！」）直接用華語配
                ref = 'dad' if spk == '余伯' else ('aunt' if cid == 'mem0_market' else 'antie')
                out.append((vid, say, 'taigi' if TAIGI_MARK.search(say) else 'mandarin', ref))
            elif spk == '余靜' and cid == 'mem0_market':
                out.append((vid, say, 'taigi' if TAIGI_MARK.search(say) else 'mandarin', 'child'))
    return out


if __name__ == '__main__':
    os.makedirs(WORK, exist_ok=True)
    js = [j for j in jobs() if not os.path.exists(os.path.join(OUT, j[0] + '.mp3'))]
    print(len(js), '句', flush=True)
    for name, voice in REF.items():   # 參考聲音
        p = os.path.join(WORK, f'ref-{name}.wav')
        if not os.path.exists(p):
            tts(REF_TEXT, voice, p + '.mp3')
            subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', p + '.mp3', '-ar', '22050', '-ac', '1', p], check=True)
    todo = []
    for vid, say, kind, ref in js:
        if kind == 'mandarin':
            tts(say, REF[ref], os.path.join(OUT, vid + '.mp3')); print('華語', vid, say, flush=True); continue
        src = os.path.join(WORK, vid + '.mp3')
        if not os.path.exists(src):
            print('意傳', vid, ithuan(say, src), flush=True); time.sleep(21)
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', src, '-ar', '22050', '-ac', '1', src[:-4] + '.wav'], check=True)
        todo.append((vid, ref))
    if todo:   # .11 換聲：同一個參考聲音的句子接成一段，只載入一次模型（作者 2026-10-19 的點子），換完照秒數切回
        import wave
        SR, GAP = 22050, 0.6
        groups = {}
        for v, r in todo:
            groups.setdefault(r, []).append(v)
        subprocess.run(['ssh', 'ct@192.168.11.11', 'mkdir -p ~/seed-vc/ember/taigi'], check=True)
        cuts = {}
        for r, vids in groups.items():
            frames, pos, spans = b'', 0, []
            for v in vids:
                with wave.open(os.path.join(WORK, f'{v}.wav')) as w:
                    data = w.readframes(w.getnframes())
                spans.append((v, pos, pos + len(data) // 2))
                frames += data + b'\0\0' * int(SR * GAP)
                pos += len(data) // 2 + int(SR * GAP)
            long = os.path.join(WORK, f'long-{r}.wav')
            with wave.open(long, 'wb') as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(frames)
            cuts[r] = spans
            subprocess.run(['scp', '-q', long, os.path.join(WORK, f'ref-{r}.wav'), 'ct@192.168.11.11:~/seed-vc/ember/taigi/'], check=True)
        cmd = ' ; '.join(f'rm -rf ember/taigi/out-long-{r} ; .venv/bin/python inference.py --source ember/taigi/long-{r}.wav --target ember/taigi/ref-{r}.wav '
                         f'--output ember/taigi/out-long-{r} --diffusion-steps 30 --fp16 False >/dev/null 2>&1' for r in groups)
        print('換聲', list(groups), flush=True)
        subprocess.run(['ssh', 'ct@192.168.11.11', f'cd ~/seed-vc && {cmd}'], check=True)
        for r, spans in cuts.items():
            local = os.path.join(WORK, f'vc-long-{r}.wav')
            subprocess.run(f'scp -q "ct@192.168.11.11:~/seed-vc/ember/taigi/out-long-{r}/vc_*.wav" {local}', shell=True, check=True)
            out_sr = int(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=sample_rate', '-of', 'csv=p=0', local], capture_output=True, text=True).stdout.split()[0])
            k = out_sr / SR
            for v, a, b in spans:
                subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', local, '-ss', f'{a / SR:.3f}', '-to', f'{b / SR + 0.15:.3f}',
                                '-af', 'loudnorm=I=-18:TP=-2:LRA=9', '-b:a', '96k', os.path.join(OUT, v + '.mp3')], check=True)
            print('切好', r, len(spans), '句 sr', out_sr, flush=True)
    print('done')
