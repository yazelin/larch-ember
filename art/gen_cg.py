"""餘燼全劇 CG（劇本第二稿）：電影感、照原版封面的畫風與光；每張帶在場角色挑定的半身立繪當參考（作者 2026-10-19：要電影高品質感，不要亂作）。
python3 art/gen_cg.py <名…>  （KS=1,2 指定第幾張）→ art/raw/cg/<名>_<n>.png
"""
import os, sys, pathlib, concurrent.futures as cf
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import codex11

R = pathlib.Path(__file__).resolve().parent.parent
STY = R / 'art/raw/styleref/cover_bg.jpg'   # 封面右半邊，沒有人（全圖會讓模型把托腮的她畫進每一張，2026-10-19）
STYLE = ('Reference 1 is ONLY a style and lighting reference: do not copy any person, pose, furniture layout or composition from it. '
         'Cinematic anime feature-film still in exactly the painting style of Reference 1: painterly, rich warm light, glowing rim light, '
         'drifting ember particles where it fits, anamorphic lens feel, shallow depth of field, soft bokeh, subtle film grain, motivated light only. '
         'Setting is Tainan, Taiwan unless told otherwise: Chinese characters on signs only and never readable, no Japanese text. '
         'Faces, hair and outfits must match the character references exactly; hands with five fingers; mature, emotionally real acting. '
         'No text, no letters, no logos, no watermark. 16:9.')
WHO = {   # 名字 → (挑定立繪, 描述)
    'yu_47': ('p_yu_47', 'YU JING at 47: shoulder-length wavy light-brown bob with a few silver strands, off-shoulder black lace evening gown, a pair of long drop earrings'),
    'yu_47_day': ('p_yu_47', 'YU JING at 47 in the afternoon BEFORE changing: shoulder-length wavy light-brown bob with a few silver strands, a soft grey knit cardigan over a plain long cream dress, flat shoes, a pair of long drop earrings, NOT the black evening gown'),
    'yu_47_home': ('p_yu_47', 'YU JING at 47 at home: shoulder-length wavy light-brown bob with a few silver strands, wearing a cream knit cardigan over a simple floral house dress, NOT the evening gown, no earrings'),
    'yu_33': ('p_yu_33', 'YU JING at 33: long light-brown wavy hair pinned up loosely, off-shoulder black lace evening gown, long drop earrings'),
    'yu_25': ('p_yu_25', 'YU JING at 25: long light-brown wavy hair down, dark-red velvet slip dress with a thin black cardigan, long drop earring'),
    'yu_42': ('p_yu_47', 'YU JING at 42: the same woman as the reference but younger, long light-brown wavy hair, a dark stage dress'),
    'yu_43': ('p_yu_47', 'YU JING at 43: the same woman as the reference, hair to the shoulders, a plain grey sweater'),
    'yu_9': ('p_yu_9', 'YU SHU-JING at 9: a small child, short ponytail, white school shirt, navy skirt, blue plastic apron, yellow rubber boots'),
    'cheng_45': ('p_cheng_45', 'CHENG XI at 45: short black hair with grey temples, dark navy shirt with rolled sleeves, black wristwatch'),
    'cheng_23': ('p_cheng_23', 'CHENG XI at 23: messy black hair, oversized plaid flannel shirt over a white tee'),
    'cheng_30': ('p_cheng_30', 'CHENG XI at 30: short neat black hair, black crew T-shirt, monitor headset around his neck'),
    'zhou': ('p_zhou_62', 'TEACHER ZHOU, pianist: neat white hair, thin gold-rimmed glasses, grey cardigan'),
    'azhe': ('p_azhe_30', 'A-ZHE, young sound engineer: side-swept black hair, black crew T-shirt, walkie-talkie and headset'),
    'tao_73': ('p_tao_73', 'AH-TAO at 73: short grey permed curls, floral blouse, jade bracelet'),
    'father': ('p_yu_father', 'YU BO, her father, fishmonger: tanned, white towel around the neck, yellow rubber apron'),
    'dr_lin': ('p_dr_lin', 'DR. LIN, neurologist: white coat, stethoscope, glasses pushed up'),
}
CG = {
    'cg_1988_canal': (['father', 'yu_9'],
        '1988, dusk, old stone steps going down into a Tainan canal, the water glowing orange with the sunset. The father and his 9-year-old daughter crouch side by side on the lowest step, '
        'scrubbing blue plastic fish crates with brushes; he is singing to her, she sings back, both laughing. A small old plastic portable radio sits on the step above. Warm, safe, tender.'),
    'cg_2004_door': (['yu_25', 'cheng_23'],
        '2004, 10 pm, right after rain, the backstage door of an old Tainan theater, glossy black asphalt reflecting a single warm door lamp. The young man thrusts a deep crimson rose and a paper ticket stub '
        'into her hands, blushing, eyes down, already turning to run; she holds them, surprised, her lips parted to ask his name. Night, steam, wet light.'),
    'cg_2009_monitor': (['yu_33', 'cheng_30'],
        '2009, a concert stage seen from the side: in the foreground she turns her head back mid-song, one hand on her in-ear monitor; behind her, in the dim side stage, '
        'he has one hand pulling a fader down to the bottom and the other switching a channel on a monitor console, lit by the console glow. Stage haze, warm spotlights.'),
    'cg_2011_rose': (['yu_33', 'cheng_30'],
        '2011, night, outside a backstage door. He crouches on the ground placing a single deep crimson rose by the door; she has just opened the door and stands above him, '
        'holding a yellowed ticket stub, a soft stunned smile. A street lamp, a puddle.'),
    'cg_2013_stage': (['yu_33', 'cheng_30', 'zhou'],
        '2013, an empty old theater stage with a single warm spotlight, red seats empty in the dark. She (in a simple cream dress, hair down) and he (white shirt) slowly dance in the light without music, '
        'he is humming; in the empty front row the old pianist lowers a camera, smiling. Dust in the light beam.'),
    'cg_2021_forget': (['yu_42', 'cheng_45'],
        'December 2021, a big concert hall in Taichung full of audience in the dark. On stage she stands frozen in a spotlight, mouth half open, one hand at her ear; '
        'at the front edge of the stage a large teleprompter screen glows with huge blurred white characters (not readable). Far back, at the mixing desk, a small figure presses a walkie-talkie.'),
    'cg_2022_clinic': (['yu_43', 'cheng_45', 'dr_lin'],
        '2022, a neurology consulting room in Taipei, white window light, a brain MRI on a monitor. She sits very still with her hands in her lap; the doctor speaks gently; '
        'he sits beside her writing every word in a small notebook, his jaw tight. Quiet, clinical, devastating.'),
    'cg_letter': (['yu_47', 'cheng_45'],
        'Today, 17:40, a small old theater dressing room on the second floor, a west window full of sunset over old Tainan rooftops, a dressing table with a lit bulb mirror. '
        'She sits reading a handwritten letter, a yellowed ticket stub fallen on the table, an old plastic portable radio with its base cover open; '
        'in the background by the door he is switching on another lamp, his back to her. Golden light turning to dusk.'),
    'cg_climax': (['yu_47', 'cheng_45'],
        'The farewell concert in the old theater, every red seat full, the stage dark except one warm spotlight. She stands holding an unfolded sheet of music with handwriting on the back, '
        'looking down into the audience; in the third row a man in a navy shirt has stood up from his seat holding a deep crimson rose, singing to her. The whole hall silent. Wide, emotional.'),
    'cg_a_kitchen': (['yu_47_home', 'cheng_45'],
        'Three days later, early morning in an old Tainan house kitchen, soft white-gold morning light, sparrows at the window, a folded sheet of music held on the fridge by a magnet. '
        'She is barefoot in a cardigan over a simple dress, laughing, pulling him by both hands into a slow little dance; he is surprised and smiling. Warm, intimate.'),
    'cg_b_encore': (['yu_47', 'cheng_45', 'zhou'],
        'The farewell concert: she sings with her eyes closed in a warm spotlight, the old pianist at the grand piano watching her; the whole audience standing, phones and roses raised; '
        'in the third row a man stands among them, holding a rose, the only one not singing. Triumphant and quietly sad.'),
    'cg_c_steps': (['yu_47'],
        'Night, old stone steps below a modern canal walkway railing in Tainan, no light except distant street lamps on the walkway above. She crouches on the lowest step in her black lace gown, '
        'like a child, hugging her knees, humming, the dark water close to her feet, reflecting the walkway lamps. Lonely, hushed, not frightening.'),
    'cg_c_roses': (['cheng_45', 'tao_73'],
        'One week later, night, the old theater full of people, every seat full, everyone holding a single deep crimson rose, the stage empty with one spotlight on an empty microphone stand. '
        'In the third row a man sits alone with the seat beside him empty except for a sheet of music folded in four; an old woman in the row behind rests her hand on his shoulder.'),
    # ── 作者 2026-10-19：劇情卡不用 Larch 立繪，每一幕都要有自己的 CG／背景 ──
    'cg_prologue': (['yu_47', 'cheng_45'],
        'Today 15:30, the arcade in front of an old 1950s Tainan theater, a hand-painted farewell poster of a woman singer on the wall (no readable text), warm afternoon light. '
        'He holds the side door open with one hand, carrying a makeup case in the other; she steps over the threshold, looking up at the old building with a faint smile of recognition.'),
    'cg_soundcheck': ([],
        'The view from the stage of an old Tainan theater during soundcheck: one row of stage lights on, a thousand empty red seats in rows, dust in the light. '
        'In the third row, the fourteenth seat from the left holds a single deep crimson rose; far at the back, a small glowing mixing desk. Quiet, waiting.'),
    'bg_dressing': ([],
        'A small old theater dressing room on the second floor, a big west-facing window full of orange sunset over old Tainan rooftops and a distant tower, '
        'a dressing table with a bulb-framed mirror (a small photo tucked in its corner), an old plastic portable radio on a side table under the window, an open notebook and a black wristwatch on the table, '
        'an empty clothes rack, a carved jewelry box. No people. Warm golden light with long shadows.'),
    'cg_2022_home': (['yu_43'],
        'Night, 2022, a Taipei apartment dining table under a pendant lamp; in the background kitchen a man\'s back washing dishes, steam. '
        'She sits writing a letter by hand, pausing with the pen above the paper; an old plastic portable radio beside her with its base cover open. Quiet and heavy.'),
    'cg_2024_name': (['yu_47_home', 'cheng_45'],
        'Early morning, 2024, an old Tainan house kitchen doorway, pale dawn light. She stands in the doorway in a cardigan, one hand reaching toward him, her mouth open on a word that will not come; '
        'he stands by the stove holding a cup, looking at her with endless patience. Soft, aching.'),
    'cg_c_market': (['yu_47'],
        'Night, a Tainan evening market closing: stall bulbs going out one by one, a young man hosing the wet concrete floor, the floor glossy with water reflecting the last lights. '
        'She stands in the middle in her black lace evening gown, lost, looking at a fish stall that is no longer her father\'s. Melancholic.'),
    'cg_c_search': (['cheng_45'],
        'Night, a modern canal walkway in Tainan with railings and street lamps; police and volunteers with flashlights searching along the walkway, beams sweeping. '
        'He stands at the railing shouting a name, phone in hand. Below the railing, out of the light, old dark stone steps lead down to the water, unseen by anyone.'),
}


def gen(job):
    name, n = job
    who, scene = CG[name]
    cast = ' '.join(f'Reference {i + 2} is {WHO[w][1]}.' for i, w in enumerate(who))
    refs = [str(STY)] + [str(R / f'assets/art/{WHO[w][0]}.webp') for w in who]
    try:
        return codex11.gen(f'{STYLE} {cast} Scene: {scene}', str(R / f'art/raw/cg/{name}_{n}.png'), refs=refs, size='1536x1024')
    except Exception as e:  # 一張失敗不要拖垮整批
        return f'FAIL {name}_{n}: {e}'


KS = [int(x) for x in os.environ.get('KS', '1,2').split(',')]

if __name__ == '__main__':
    (R / 'art/raw/cg').mkdir(parents=True, exist_ok=True)
    names = sys.argv[1:] or list(CG)
    with cf.ThreadPoolExecutor(4) as ex:
        for f in ex.map(gen, [(nm, k) for nm in names for k in KS]):
            print(f, flush=True)
