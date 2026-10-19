"""立繪候選（每人 4 張給作者挑）。照雨幕學到的：半身、戲劇性的光、有表演；畫風與光照原版封面（作者 2026-10-19：要電影高品質感，原封面算不錯）。
參考圖：Reference 1 = 封面裁切（余靜的臉與畫法），Reference 2 = 封面全圖（光與色調）。
python3 art/gen_standees.py gen [名…] / cut [名…]   → art/raw/standee/<名>_<n>.png；KS=1,2,3,4 指定第幾張
"""
import os, sys, pathlib, subprocess, concurrent.futures as cf
sys.path.insert(0, str(pathlib.Path(__file__).parent))
R = pathlib.Path(__file__).resolve().parent.parent
RAW = R / 'art/raw/standee'
STY = R / 'art/raw/styleref'
CUT = pathlib.Path.home() / '.claude/skills/cutout/cutout.py'
BASE = ('A premium visual-novel character standee, HALF BODY from mid-thigh up, the figure fills the height of the image, face large and highly detailed. '
        'Cinematic anime feature-film rendering in exactly the painting style of the references: painterly light and shadow, glowing warm sunset backlight, '
        'a strong golden-orange rim light outlining the hair and shoulders, soft amber bounce light on the face, rich hand-painted fabric texture and lace detail, '
        'subtle film color grading in amber, deep crimson and ash grey, a few tiny glowing ember particles near the figure. '
        'An East Asian (Taiwanese) person, drawn as a beautiful lead of a mature romance anime film: refined, well-proportioned features, '
        'expressive deep eyes with layered irises, natural skin, appealing and memorable, emotionally real. '
        'Background: a completely flat, uniform pure magenta #FF00FF, no gradient, no scenery, no particles on the background, nothing touches the left, right or top border. '
        'No text, no letters, no logos.')
YU_FACE = 'Her face must be clearly the same woman as in Reference 1 (the singer on the original cover): same eyes, nose, lips, face shape. '
WHO = {
    'yu_47': (YU_FACE + 'YU JING, 47, a famous singer with early-onset Alzheimer\'s, today the day of her farewell concert. The same face clearly aged to 47: '
              'visible fine lines at the eye corners and soft smile lines, slightly thinner cheeks, a few silver strands in her hair, still strikingly beautiful with a gentle tiredness. '
              'Her hair is now SHORT: a soft wavy light-brown bob that ends just above the shoulders, worn down, NOT pinned up, NOT long, one side tucked behind the ear. '
              'Wearing the same off-shoulder black lace evening gown as Reference 1, a single long drop earring on her LEFT ear. '
              'Acting: her left fingertips touching the earring, a soft uncertain smile, eyes turned slightly aside as if trying to remember someone she loves.'),
    'yu_33': (YU_FACE + 'YU JING, 33, in 2012 backstage at a European opera house, the night on the original cover: long light-brown wavy hair pinned up loosely with strands falling, '
              'the off-shoulder black lace evening gown, long drop earring on her left ear. Acting: chin lifted, a confident calm gaze toward the viewer, '
              'one hand holding a single deep crimson rose against her chest; at the height of her career, glamorous and a little lonely.'),
    'yu_25': (YU_FACE + 'YU JING, 25, in 2004 on the night of her first ticketed concert in her hometown: younger, fresher face, long light-brown wavy hair down, '
              'a simple dark-red velvet slip dress with a thin black cardigan, a long drop earring on her left ear. Acting: holding a sheet of music folded in four against her chest with both hands, '
              'nervous bright eyes, biting back a hopeful smile.'),
    'cheng_45': ('CHENG XI, 45, her husband and former concert sound engineer, now her full-time caregiver. A quiet, steady, handsome mature man: short black hair with a little grey at the temples, '
                 'calm dark eyes, faint lines at the eye corners, clean jaw. Wearing a plain dark navy shirt with sleeves rolled to the forearm, a black wristwatch. '
                 'Acting: holding out a glass of warm water with both hands toward the viewer, a patient gentle half smile that hides grief; '
                 'steady hands, the look of someone who has been forgotten by the person he loves and stays anyway.'),
}


def gen(job):
    import codex11
    name, n = job
    try:
        return _gen(codex11, name, n)
    except Exception as e:   # 一張失敗不要拖垮整批
        return f'FAIL {name}_{n}: {e}'


def _gen(codex11, name, n):
    return codex11.gen(BASE + ' Character: ' + WHO[name], str(RAW / f'{name}_{n}.png'),
                       refs=[str(STY / 'yu_cover_crop.png'), str(STY / 'cover_full.jpg')], size='1024x1536')


def cut(name, n):
    subprocess.run([sys.executable, str(CUT), 'key', str(RAW / f'{name}_{n}.png'), '-o', str(RAW / f'{name}_{n}_cut.png'), '--key', 'magenta'], check=True, capture_output=True)


KS = [int(x) for x in os.environ.get('KS', '1,2,3,4').split(',')]

if __name__ == '__main__':
    cmd, names = sys.argv[1], sys.argv[2:] or list(WHO)
    if cmd == 'gen':
        with cf.ThreadPoolExecutor(4) as ex:
            for f in ex.map(gen, [(nm, k) for nm in names for k in KS]): print(f, flush=True)
    else:
        for nm in names:
            for k in KS: cut(nm, k)
