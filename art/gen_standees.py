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
    # ── 第二輪（2026-10-19 作者挑定：余靜 47#4、33#2、25#2、程希 45#3）──
    'cheng_23': ('CHENG XI at 23, in 2004, the same man as Reference 3 but twenty-two years younger: no grey, smooth skin, messy black hair, thin. '
                 'Wearing a cheap oversized plaid flannel shirt over a white tee, damp from rain. Acting: holding a single deep crimson rose and a paper ticket stub out with both hands, '
                 'blushing hard, eyes down, mouth slightly open, unable to say a word. Lit by a warm backstage door lamp on a rainy night.'),
    'cheng_30': ('CHENG XI at 30, in 2009-2013, the same man as Reference 3 but fifteen years younger: no grey, short neat black hair. '
                 'Wearing a black crew T-shirt, a monitor headset hanging around his neck, a black wristwatch. Acting: one hand raised slightly as if just pulling a fader down, '
                 'calm focused eyes with a shy small smile. Warm stage side-light.'),
    'yu_9': (YU_FACE + 'YU SHU-JING at 9 years old, in 1988, the same girl as Reference 3 as a child: round cheeks, long light-brown hair in a ponytail, '
             'a Taiwanese elementary school uniform (white short-sleeve shirt, navy pleated skirt) with sleeves rolled, rubber rain boots. '
             'Acting: holding a green garden hose with both hands, laughing, water splashing. Lit by a warm dusk market light bulb.'),
    'zhou_62': ('ZHOU WEN-XIONG, 62, her pianist since 2004, called Teacher Zhou: kind face, neat white hair, thin gold-rimmed glasses, a grey cardigan over a white shirt. '
                'Acting: hands resting on an invisible keyboard edge, looking up with a gentle patient smile, as if waiting for her to sing. Warm stage light.'),
    'azhe_30': ('TSAI CHE-WEI "A-ZHE", 30, a young sound engineer, Cheng Xi\'s apprentice: short side-swept hair, earnest eyes, black crew T-shirt, a walkie-talkie and headset clipped on. '
                'Acting: one hand pressing the walkie-talkie button, nervous determined look. Warm backstage light.'),
    'tao_73': ('AH-TAO, 73, a vegetable vendor from the old Tainan market who watched the heroine grow up: short grey permed curls, a floral blouse, a small jade bracelet, '
               'deep laugh lines, tanned. Acting: holding a plastic bag of guavas, laughing warmly while calling out a name. Warm dusk light.'),
    'tao_35': ('AH-TAO at 35, in 1988, the same woman as tao_73 when young: black permed hair under a headscarf, a work apron over a floral blouse, sleeves pushed up. '
               'Acting: holding a bunch of leafy greens, laughing, splashed with water. Warm dusk market light bulb.'),
    'yu_father': ('YU BO, 45, in 1988, the heroine\'s father, a fishmonger at the Tainan evening market: tanned weathered face, short hair, a white towel around his neck, '
                  'a yellow rubber apron and rubber boots, strong forearms. Acting: holding up a big fish on ice with a proud tender grin, looking down at his daughter. Warm dusk market light bulb.'),
    'dr_lin': ('DR. LIN HUI-RU, 52, a neurologist in Taipei: shoulder-length black hair, a white coat over a navy blouse, a stethoscope, reading glasses pushed up. '
               'Acting: holding a tablet with brain scan images, a calm kind serious expression, about to deliver hard news gently. Cool clinical white light from a window, a warm tone on the face.'),
}
# 身分參考（第三張參考圖）：挑定的立繪
IDREF = {'cheng_23': 'p_cheng_45', 'cheng_30': 'p_cheng_45', 'yu_9': 'p_yu_25', 'tao_35': None}


def gen(job):
    import codex11
    name, n = job
    try:
        return _gen(codex11, name, n)
    except Exception as e:   # 一張失敗不要拖垮整批
        return f'FAIL {name}_{n}: {e}'


def _gen(codex11, name, n):
    refs = [str(STY / 'yu_cover_crop.png'), str(STY / 'cover_full.jpg')]
    if IDREF.get(name):
        refs.append(str(R / f'assets/art/{IDREF[name]}.webp'))
    return codex11.gen(BASE + ' Character: ' + WHO[name], str(RAW / f'{name}_{n}.png'), refs=refs, size='1024x1536')


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
