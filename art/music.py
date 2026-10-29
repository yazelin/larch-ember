# -*- coding: utf-8 -*-
"""《餘燼》配樂：走 .11 gemini-web /api/music，切 60 秒循環、-16 LUFS、量接縫，再用 Gemini 2.5 flash 代聽驗收。
沿用 larch-eleven-minutes/art/music.py 與 larch-taoyuan/bgm.py（find_start／make／seam_score）。內網 IP、不驗憑證。
  python3 art/music.py run|resume [名字…]       → 全流程（產→切→代聽→不合格自動重產，最多 3 次），狀態寫 art/music_state/
  python3 art/music.py control           → 負控制：拿不符的場景描述去問代聽，應該要打低分
  python3 art/music.py manifest          → 彙整 assets/bgm/manifest.json
金鑰只從 ~/.bashrc 與 ~/gemini/.env 讀，不寫進任何檔案。"""
import base64, importlib.util, json, os, re, ssl, subprocess, sys, threading, urllib.request, urllib.error
H = os.path.dirname(os.path.abspath(__file__)); G = os.path.dirname(H)
RAW, OUT, ST = os.path.join(H, 'music_raw'), os.path.join(G, 'assets/bgm'), os.path.join(H, 'music_state')
URL = 'https://192.168.11.11/gemini-web/api/music'
CTX = ssl._create_unverified_context()
TAIL = 'instrumental, no vocals, no singing, no choir, no humming, loopable, steady texture without a big ending'
# name: (prompt 主體, 場景一句話（給代聽）, 建議劇本代號, 情緒)
T = {
 'title': ('Warm dusk-orange main theme for an old Taiwanese theatre, a gentle solo piano melody with a touch of sadness, a faint vintage radio hiss and tape warmth underneath, soft sustained strings far behind, 68 BPM, major with minor colouring',
           '視覺小說封面：台南老戲院黃昏橘的溫暖，鋼琴主題帶一點悲傷，底下像舊收音機的雜訊', ['title'], '黃昏橘、溫暖帶悲'),
 'dress': ('Very slow, breathing piano and sustained strings, the hush of an empty theatre backstage, long reverb tails, tender and still, 56 BPM, sparse notes',
           '序幕與換禮服：戲院後台很靜，緩慢的鋼琴與弦像呼吸', ['prologue', 'soundcheck', 'card_dress'], '靜、呼吸感'),
 'dressing': ('Gentle low-density solo piano, a few soft notes drifting like window light in a dressing room, faint distant market chatter and street ambience far away, warm and tender, 72 BPM',
              '化妝間探索：窗光，稀疏溫柔的鋼琴，遠處有市場的聲音', ['m_dressing_intro', 'm_window', 'm_mirror', 'm_notebook', 'm_rose_dry', 'm_jewelry', 'm_radio', 'm_radio_on', 'm_letter', 'm_note'], '溫柔、低密度'),
 'backstage': ('Spacious backstage ambience, a soft deep bass drone and sparse slow piano notes with natural room echo, like footsteps on old stairs and a long corridor, calm and not tense, 60 BPM',
               '後台樓梯與走廊：有空間感的低音與鋼琴，平靜不緊張', ['m_corridor'], '空間感、平靜'),
 'auditorium': ('Extremely quiet empty concert hall, very light reverb-drenched long sustained tones, a few high soft piano notes echoing in a huge room, a thousand empty red velvet seats, hushed and reverent',
                '空無一人的觀眾席，一千張紅色絨布椅子，很輕的迴響與長音', ['m_auditorium'], '空曠、肅靜'),
 'alley': ('Nostalgic Taiwanese old-song style accordion waltz in 3/4, warm and wistful, with light upright bass and soft brushed percussion, an original melody, evening back-alley and dusk market atmosphere, 96 BPM',
           '後門巷子與黃昏市場：台語老歌風的手風琴華爾滋，溫暖懷舊', ['m_alley'], '懷舊、溫暖'),
 'mem_1988': ('Innocent warm accordion with a small-radio lo-fi feel, a simple childlike tune, gentle fish-market dusk by a canal, light plucked bass and soft hand percussion, naive and cozy, 88 BPM, major key',
              '1988 年黃昏市場魚攤與運河，九歲小孩的天真溫暖，手風琴與小收音機感', ['mem0_market'], '天真、溫暖'),
 'mem_2004': ('Young, shy, unspoken tension after rain at a theatre back door, glistening wet asphalt at night, delicate piano arpeggios with a thin string pad, hesitant and tender, 76 BPM, minor to major',
              '2004 年雨後的後台門口，柏油路黑亮，青澀說不出口的緊張，鋼琴與弦', ['mem1_door'], '青澀、欲言又止'),
 'mem_love': ('Light, warm, romantic piano trio feel with gentle jazz piano voicings, brushed drums and soft upright bass, two people meeting, falling in love and marrying, bright but intimate, 100 BPM',
              '2009 到 2013 年兩人相遇、相愛到結婚，輕巧溫暖，帶一點爵士鋼琴', ['mem2_monitor', 'mem2_rose', 'mem2_europe', 'mem2_stage'], '輕巧、甜'),
 'mem_clinic': ('Extremely minimal restrained solo piano, very few notes with long silences, cold white fluorescent clinic light, emotionally withheld and quiet, a hint of cold sustained pad, 54 BPM',
                '2021 到 2022 年忘詞與診間，冷白燈，極簡克制的鋼琴', ['mem3_forget', 'mem4_clinic', 'mem4_letter', 'mem4_name'], '冷、克制'),
 'branch': ('Quiet suspended ambience of nightfall, deep low sustained drone notes with a little vinyl or radio static noise, unresolved, one person alone in a dressing room as the last light fades, no clear melody, slow and uneasy but soft',
            '18:00 天黑，化妝間只剩她一個人，安靜、懸著、未解決，低音長音與一點雜訊', ['branch_dark'], '懸著、孤單'),
 'concert': ('Hushed anticipation before a concert, a thousand people holding their breath, slowly building piano ostinato with gentle strings swelling, restrained forward motion, no drums, 80 BPM, hopeful and nervous',
             '開演前一千人屏息的等待，鋼琴與輕弦緩緩推進，緊張又懷抱希望', ['concert'], '屏息、推進'),
 'end_a': ('Warm reconciliation, slowly opening up, gentle piano melody in a major key joined by warm strings and soft glowing pad, tender and uplifting, tears of joy, golden dawn light, 70 BPM',
           '結局 A：溫暖的和解，情緒慢慢打開，被記得的幸福', ['ending_a1', 'ending_a2', 'ending_a3'], '溫暖、和解'),
 'end_b': ('Bittersweet piano-led piece that ends softly, a tender melody with a quiet ache, a little sweetness, sparse light strings, an empty theatre after the show, 64 BPM, minor with a warm turn',
           '結局 B：苦中帶甜，鋼琴為主，散場後空戲院，收得很輕', ['ending_b1', 'ending_b2'], '苦中帶甜'),
 'end_c': ('Sorrowful, very sparse solo piano with the sound of water lapping at canal stone steps in the dark, long gaps, lonely and heartbreaking, quiet grief, 52 BPM, minor',
           '結局 C：悲傷，非常稀疏的鋼琴與水聲，夜裡運河石階邊', ['ending_c1', 'ending_c2', 'ending_c3', 'ending_c4'], '悲傷、稀疏'),
 'cheng': ('Restrained and delicate, a gentle same-afternoon-from-another-angle feeling, soft felt piano with subtle warm strings and a quiet clarinet-like line, observant, caring and quietly sad, 66 BPM',
           '程希的視角：同一個下午換個角度，克制細膩的守望，帶著照顧與隱忍', ['cheng_pov'], '克制、細膩'),
}
PROMPT = {n: f'{v[0]}, {TAIL}' for n, v in T.items()}


def bashrc_key():
    for line in open(os.path.expanduser('~/.bashrc'), encoding='utf-8'):
        if line.startswith('export GEMINI_IMAGE_KEY='): return line.split('=', 1)[1].strip().strip('"')
    raise RuntimeError('找不到 GEMINI_IMAGE_KEY')


def audit_key():
    for line in open(os.path.expanduser('~/gemini/.env'), encoding='utf-8'):
        if line.startswith('NANOBANANA_GEMINI_API_KEY='): return line.split('=', 1)[1].strip().strip('"')
    raise RuntimeError('找不到 NANOBANANA_GEMINI_API_KEY')


def gen(name, k, tries=4, extra=''):
    os.makedirs(RAW, exist_ok=True)
    for n in range(tries):
        req = urllib.request.Request(URL, method='POST', data=json.dumps({'prompt': PROMPT[name] + extra, 'timeout': 720}).encode(),
                                     headers={'Content-Type': 'application/json', 'x-goog-api-key': k})
        try: d = json.load(urllib.request.urlopen(req, timeout=900, context=CTX))
        except Exception as e: print(f'{name} 產生第{n + 1}次 例外 {e!r}', flush=True); continue
        if d.get('success'):
            open(os.path.join(RAW, f'{name}.mp3'), 'wb').write(base64.b64decode(d['audio']))
            print(f"{name} 產好 worker={d.get('worker_id')} {d.get('elapsed_seconds', 0):.0f} 秒", flush=True); return True
        print(f"{name} 產生第{n + 1}次 失敗 {d.get('message') or d.get('error')}", flush=True)
    return False


def loudness(path):
    err = subprocess.run(['ffmpeg', '-i', path, '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'], capture_output=True, text=True).stderr
    return float(json.loads(err[err.rindex('{'):err.rindex('}') + 1])['input_i'])


def loop(name):
    spec = importlib.util.spec_from_file_location('tybgm', os.path.expanduser('~/larch-taoyuan/bgm.py'))
    B = importlib.util.module_from_spec(spec); spec.loader.exec_module(B)
    src = os.path.join(RAW, f'{name}.mp3'); os.makedirs(OUT, exist_ok=True); out = os.path.join(OUT, f'{name}.mp3')
    dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', src], capture_output=True, text=True).stdout)
    B.LEN = min(62, int(dur) - 4)   # make() 會扣掉 1.5 秒交叉淡化 → 成品約 60.5 秒
    base, best = B.find_start(src), None
    for off in [0, .5, -.5, 1, -1, 1.5, -1.5, 2, -2, 3, -3]:
        s = max(0.0, base + off); B.make(src, s, out); z, d = B.seam_score(out)
        if best is None or abs(z) < abs(best[0]): best = (z, s, d)
        if abs(z) < 3: break
    z, s, d = best; B.make(src, s, out)
    return {'seam_score': round(float(z), 2), 'seconds': round(float(d), 1), 'lufs': round(loudness(out), 1), 'src_seconds': round(dur), 'start': round(float(s), 1), 'bytes': os.path.getsize(out)}


ASK = ('你是配樂審聽員。聽這段音樂，只回 STRICT JSON（不要 markdown），欄位：'
       '{"has_vocals": bool（有任何人聲、哼唱、合唱就 true）, "instruments": [字串], "mood": "一句話情緒", '
       '"fits_scene": 0到10的整數（對下面這個場景描述的適配度，要誠實，不合就給低分）, "fit_reason": "一句話", '
       '"loopable_background": bool（像可以循環的背景音樂，沒有明顯結尾或大高潮）, "tempo_feel": "慢/中/快", "melody_prominence": 0到10}\n場景描述：')


AUD_MODELS = ['gemini-3.5-flash', 'gemini-3.6-flash', 'gemini-3-flash-preview']   # 每個模型免費日額度只有 20 次，2.5-flash 與 flash-latest 已被首輪燒光；429 就換下一個
AUD_MODEL = AUD_MODELS[0]
AUD_I = [0]
AUD = threading.Lock()


def listen(path, scene, k):
    with AUD:
        return _listen(path, scene, k)


def _listen(path, scene, k):
    tmp = '/tmp/ember_audit.mp3'
    tmp = f'/tmp/ember_audit_{os.getpid()}_{threading.get_ident()}.mp3'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', path, '-ac', '1', '-b:a', '64k', tmp], check=True)
    b64 = base64.b64encode(open(tmp, 'rb').read()).decode(); os.remove(tmp)
    body = {'contents': [{'parts': [{'text': ASK + scene}, {'inline_data': {'mime_type': 'audio/mp3', 'data': b64}}]}],
            'generationConfig': {'responseMimeType': 'application/json', 'temperature': 0}}
    for n in range(4):
        req = urllib.request.Request('https://generativelanguage.googleapis.com/v1beta/models/' + AUD_MODELS[AUD_I[0] % len(AUD_MODELS)] + ':generateContent',
                                     data=json.dumps(body).encode(), headers={'Content-Type': 'application/json', 'x-goog-api-key': k})
        try:
            r = json.load(urllib.request.urlopen(req, timeout=180))
            t = r['candidates'][0]['content']['parts'][0]['text']
            return json.loads(re.sub(r'^```json|```$', '', t.strip()).strip())
        except Exception as e:
            if getattr(e, 'code', 0) == 429: AUD_I[0] += 1   # 日額度滿了換模型
            print('代聽例外', AUD_MODELS[AUD_I[0] % len(AUD_MODELS)], repr(e)[:100], flush=True); import time; time.sleep(20 * (n + 1))
    return None


def verdict(a, loopres):
    bad = []
    if a is None: bad.append('代聽失敗')
    else:
        if a.get('has_vocals'): bad.append('有人聲')
        if int(a.get('fits_scene', 0)) < 7: bad.append(f"場景適配 {a.get('fits_scene')}")
        if not a.get('loopable_background'): bad.append('不像可循環背景')
    if abs(loopres['seam_score']) >= 3: bad.append(f"接縫 z={loopres['seam_score']}")
    if abs(loopres['lufs'] + 16) > 1.5: bad.append(f"響度 {loopres['lufs']}")
    if loopres['bytes'] > 1_500_000: bad.append('超過 1.5MB')
    return bad


SEM = threading.Semaphore(4)


# 第一輪腳本有 bug（代聽 503/429 被當成「曲子不合格」而白白重產）。resume 時用 BASE 記下「真正因內容不合格而重產」的次數，
# WASTED 記下被代聽故障浪費的重產次數（報告要誠實列出）。
BASE = {'branch': 1, 'end_a': 1, 'end_b': 1, 'mem_1988': 1}
WASTED = {'mem_love': 1, 'mem_clinic': 1, 'cheng': 1, 'dress': 1, 'alley': 1, 'mem_2004': 1, 'title': 1}


def listen_sure(path, scene, ak):
    import time
    for i in range(8):
        a = listen(path, scene, ak)
        if a is not None: return a
        time.sleep(60)
    return None


def run_one(name, bk, ak, resume=False):
    os.makedirs(ST, exist_ok=True); sp = os.path.join(ST, f'{name}.json')
    hist, real = [], BASE.get(name, 0) if resume else 0
    if resume and os.path.exists(sp) and not json.load(open(sp))['final_bad']: return   # 已通過的不重聽，省額度
    first = True
    while real <= 3:   # real = 因內容不合格而重產的次數，最多 3
        if not (first and os.path.exists(os.path.join(RAW, f'{name}.mp3'))):
            with SEM:
                if not gen(name, bk, extra='' if real == 0 else ', absolutely no human voice of any kind, only instruments'):
                    hist.append({'fail': '產生失敗'}); real += 1; continue
        first = False
        lr = loop(name); a = listen_sure(os.path.join(OUT, f'{name}.mp3'), T[name][1], ak); bad = verdict(a, lr)
        hist.append({'retries_so_far': real, 'loop': lr, 'audit': a, 'bad': bad})
        print(f"{name} 重試{real} {lr} fit={a and a.get('fits_scene')} vocals={a and a.get('has_vocals')} 問題={bad}", flush=True)
        json.dump({'name': name, 'retries': real, 'wasted_regens_from_auditor_outage': WASTED.get(name, 0) if resume else 0,
                   'history': hist, 'final_bad': bad}, open(sp, 'w'), ensure_ascii=False, indent=1)
        if not bad: return
        real += 1
    print(f'{name} 重試用完仍有問題', flush=True)


def control():
    ak = audit_key(); r = {}
    wrong = {'branch': T['end_a'][1], 'end_c': T['mem_love'][1], 'mem_love': T['end_c'][1], 'alley': T['mem_clinic'][1]}
    for n, scene in wrong.items():
        a = listen(os.path.join(OUT, f'{n}.mp3'), scene, ak); r[n] = {'wrong_scene': scene, 'audit': a}
        print('負控制', n, '→', a and a.get('fits_scene'), a and a.get('fit_reason'), flush=True)
    os.makedirs(ST, exist_ok=True); json.dump(r, open(os.path.join(ST, '_control.json'), 'w'), ensure_ascii=False, indent=1)


def manifest():
    items = []
    for n, v in T.items():
        sp = os.path.join(ST, f'{n}.json')
        if not os.path.exists(sp): continue
        s = json.load(open(sp)); last = s['history'][-1]
        lr, a = last.get('loop', {}), last.get('audit')
        items.append({'name': n, 'file': f'assets/bgm/{n}.mp3', 'mood': v[3], 'scene': v[1], 'use_in': v[2],
                      'seconds': lr.get('seconds'), 'lufs': lr.get('lufs'), 'seam_score': lr.get('seam_score'),
                      'audition': a, 'retries': s['retries'], 'unresolved': s['final_bad'], 'prompt': PROMPT[n]})
    ctl = os.path.join(ST, '_control.json')
    json.dump({'tracks': items, 'negative_control': json.load(open(ctl)) if os.path.exists(ctl) else None}, open(os.path.join(OUT, 'manifest.json'), 'w'), ensure_ascii=False, indent=1)
    print('manifest', len(items), '首')


if __name__ == '__main__':
    cmd, names = sys.argv[1], sys.argv[2:] or list(T)
    if cmd == 'run':
        bk, ak = bashrc_key(), audit_key(); ts = [threading.Thread(target=run_one, args=(n, bk, ak, False)) for n in names]
        for t in ts: t.start()
        for t in ts: t.join()
    elif cmd == 'resume':
        bk, ak = bashrc_key(), audit_key(); ts = [threading.Thread(target=run_one, args=(n, bk, ak, True)) for n in names]
        for t in ts: t.start()
        for t in ts: t.join()
    elif cmd == 'control': control()
    elif cmd == 'manifest': manifest()
