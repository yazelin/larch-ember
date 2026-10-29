"""阿桃姨、余伯、程希的台語台詞（作者 10-30：程希 canal 場的台語也要配） → voice/taigi/lines.json，給 taigi-voice-desk 產音與確認（作者 10-29：台語用聽的）。
id 用劇本的台詞 id；已經有的句子保留台羅、狀態、備註，劇本改了字才清空台羅重轉。唱的（〈天烏烏〉）不配。
python3 src/taigi_lines.py
產音：python3 ~/taigi-voice-desk/voice.py voice/taigi --vc 'HOST=ct@192.168.11.11 ~/taigi-voice-desk/vc/seed-vc-ssh.sh {src} {ref} {dst}'
確認頁開 voice/taigi 資料夾。標通過的句子 build 時掛上配音。
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import script

R = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
F = os.path.join(R, 'voice/taigi/lines.json')
VOICES = {'阿桃姨': {'ref': 'refs/antie.wav', 'note': '2026 年的阿桃姨：Kind-hearted_Antie'},
          '阿桃姨（1988）': {'ref': 'refs/aunt.wav', 'note': '1988 年的阿桃姨，比較年輕：Warm-HeartedAunt'},
          '余伯': {'ref': 'refs/dad.wav', 'note': 'Larch_Mandarin_Dad'},
          '程希': {'ref': 'refs/chengxi.wav', 'note': 'Larch_Mandarin_Uncle（跟 src/tts.py 華語同一個聲音）'}}
OLD_SCENES = ('market',)   # 1988 年的場


def lines():
    for cid, ls in script.L.items():
        for spk, text, vid, tag in ls:
            if spk not in VOICES or not vid or text.startswith(('（唱）', '（哼）')):
                continue
            m = re.match(r'^(.*?)（([^）]*)）\s*$', text)   # 「台語。（華語。）」
            if spk == '程希' and not m:   # 程希平常講華語，只配有括號翻譯的台語句
                continue
            hanzi, zh = (m.group(1).strip(), m.group(2)) if m else (text, '')
            who = '阿桃姨（1988）' if spk == '阿桃姨' and cid in OLD_SCENES else spk
            yield {'id': vid, 'speaker': who, 'scene': cid, 'hanzi': hanzi, 'zh': zh}


if __name__ == '__main__':
    old = {l['id']: l for l in json.load(open(F, encoding='utf-8'))['lines']} if os.path.exists(F) else {}
    out = []
    for l in lines():
        o = old.get(l['id'], {})
        same = o.get('hanzi') == l['hanzi']
        l.update(kip=o.get('kip', '') if same else '', seg=o.get('seg', '') if same else '',
                 status=o.get('status', 'todo') if same else 'todo', note=o.get('note', ''), audio=o.get('audio', '') if same else '')
        out.append(l)
    os.makedirs(os.path.dirname(F), exist_ok=True)
    open(F, 'w', encoding='utf-8').write(json.dumps({'title': '《餘燼》台語', 'voices': VOICES, 'lines': out}, ensure_ascii=False, indent=1) + '\n')
    print(F, len(out), '句', sum(1 for l in out if l['kip']), '句已有台羅')
