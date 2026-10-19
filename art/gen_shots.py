"""產分鏡鏡頭（art/storyboard.py）。主鏡頭（第五欄 None）先產；後續鏡頭拿「參考鏡頭已選定的那張」當參考，場景、服裝、光線才連貫。
沿用 gen_cg.py 的主鏡頭寫 'cg:<名>'，選定後用 install 放進 assets/art/cg/；'ORIGINAL_COVER' 直接用原版封面。
python3 art/gen_shots.py gen [鏡頭…]   → art/raw/shots/<鏡頭>_<n>.png（KS=1,2）；只產參考已就緒的
python3 art/gen_shots.py pick <鏡頭> <n> / pickcg <鏡頭> <cg 名> <n> → assets/art/cg/<鏡頭>.webp
python3 art/gen_shots.py status
"""
import os, sys, pathlib, concurrent.futures as cf
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import codex11, storyboard
from gen_cg import STYLE, WHO, STY
from PIL import Image

R = pathlib.Path(__file__).resolve().parent.parent
RAW = R / 'art/raw/shots'
OUT = R / 'assets/art/cg'
KS = [int(x) for x in os.environ.get('KS', '1,2').split(',')]


def chosen(shot):
    return OUT / f'{shot}.webp'


def ready(shot):
    card, start, cast, desc, ref = storyboard.SHOTS[shot]
    if desc.startswith('cg:') or desc == 'ORIGINAL_COVER':
        return False
    return ref is None or chosen(ref).exists()


def gen(job):
    shot, n = job
    card, start, cast, desc, ref = storyboard.SHOTS[shot]
    refs = [str(STY)]
    notes = []
    if ref:
        refs.append(str(chosen(ref)))
        notes.append('Reference 2 is the previous shot of this same scene: keep the same location, set dressing, lighting, outfits and color grade; this is the next moment.')
    for w in cast:
        refs.append(str(R / f'assets/art/{WHO[w][0]}.webp'))
        notes.append(f'Reference {len(refs)} is {WHO[w][1]}.')
    try:
        return codex11.gen(f'{STYLE} {" ".join(notes)} Scene: {desc}', str(RAW / f'{shot}_{n}.png'), refs=refs, size='1536x1024')
    except Exception as e:  # noqa: BLE001
        return f'FAIL {shot}_{n}: {e}'


def install(src, shot):
    OUT.mkdir(parents=True, exist_ok=True)
    im = Image.open(src).convert('RGB')
    im.thumbnail((1920, 1080))
    im.save(chosen(shot), quality=90)
    print(shot, '←', src)


if __name__ == '__main__':
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == 'gen':
        RAW.mkdir(parents=True, exist_ok=True)
        names = args or [s for s in storyboard.SHOTS if ready(s) and not chosen(s).exists()]
        print('產', names, flush=True)
        with cf.ThreadPoolExecutor(4) as ex:
            for f in ex.map(gen, [(s, k) for s in names for k in KS]):
                print(f, flush=True)
    elif cmd == 'pick':
        install(RAW / f'{args[0]}_{args[1]}.png', args[0])
    elif cmd == 'pickcg':
        install(R / f'art/raw/cg/{args[1]}_{args[2]}.png', args[0])
    elif cmd == 'cover':
        install(R / 'art/original/cover.png', args[0])
    elif cmd == 'status':
        for s, v in storyboard.SHOTS.items():
            print('✓' if chosen(s).exists() else ('可產' if ready(s) else '等'), s, v[3][:40])
