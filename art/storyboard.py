"""分鏡：劇情卡每一個鏡頭（作者 2026-10-19：多人互動畫成整張 CG，連續動作一句一張）。
SHOTS[鏡頭] = (段落, 從哪一句開始（台詞開頭的字）, 在場角色, 畫面描述, 參考的前一個鏡頭或 None)
- 每一幕的第一個鏡頭是主鏡頭，後面的鏡頭拿主鏡頭當參考，場景、服裝、光線才連貫。
- 主鏡頭沿用 gen_cg.py 已經產的那張時，第四欄寫 'cg:<名>'。
python3 art/storyboard.py mark  → 把〔圖：〕標記插進 canon/劇本.md（已存在的不重複插）
"""
import pathlib, re, sys

R = pathlib.Path(__file__).resolve().parent.parent
SHOTS = {
    # 序幕
    's_prologue_1': ('prologue', '2026 年 10 月 14 日', [], 'Wide establishing shot: the arcade of an old 1950s Tainan theater at 15:30, warm afternoon light, a hand-painted farewell poster of a woman singer on the wall (no readable text), scooters parked, an old neon sign off.', None),
    's_prologue_2': ('prologue', '一個穿深藍襯衫的男人推開後台的門', ['yu_47_day', 'cheng_45'], 'Wide three-quarter view from the arcade, afternoon. The heavy old wooden side door of the theater swings INWARD (away from the viewer) and stands open, showing a warm dim lit hallway inside. He stands outside beside the door frame, body turned sideways to leave the passage free, one hand holding the open door leaf by its edge, the other hand carrying the black makeup case by its handle. She is stepping over the threshold INTO the doorway: her body and her front foot point into the building; we see her in three-quarter side view looking ahead into the warm interior with curious wide eyes and a faint smile, while he watches her go in. She is NOT walking away from the door and NOT standing outside beside it: her feet face the doorway.', 's_prologue_1'),
    's_prologue_3': ('prologue', '小時候我阿爸帶我來看電影', ['yu_47_day'], 'Inside the old theater lobby: she touches the armrest of an old red folding seat, smiling at a childhood memory; dust in the light from the door.', 's_prologue_2'),
    's_prologue_4': ('prologue', '那我們算是同鄉', ['yu_47_day', 'cheng_45'], 'Backstage corridor: she walks ahead looking around; he follows half a step behind carrying her makeup case, watching her back with a quiet ache.', 's_prologue_2'),
    # 試音
    's_soundcheck_1': ('soundcheck', '舞台上只開了一排燈', [], 'cg:cg_soundcheck', None),
    's_soundcheck_2': ('soundcheck', '周老師：靜，〈晚安，台南〉', ['yu_47', 'zhou'], 'On stage during soundcheck: the old pianist at a grand piano, she stands by the piano in a casual cardigan, about to sing; one row of stage lights.', 's_soundcheck_1'),
    's_soundcheck_3': ('soundcheck', '穿深藍襯衫的男人走下台', ['cheng_45'], 'From the stage looking down into the empty hall: in the third row a man sits holding a deep crimson rose, listening, his face lit faintly by the stage.', 's_soundcheck_1'),
    's_soundcheck_4': ('soundcheck', '余靜：老師，那個位子', ['yu_47_day', 'zhou'], 'She stands at the front edge of the stage looking toward the third row, puzzled, one hand at her chest; the pianist looks up at her.', 's_soundcheck_2'),
    # 換禮服
    's_dress_1': ('card_dress', '二樓的化妝間', [], 'cg:bg_dressing', None),
    's_dress_2': ('card_dress', '她換好禮服出來', ['yu_47', 'cheng_45'], 'In the dressing room she stands in the black lace gown; he gently holds her left wrist and unbuckles a black wristwatch, close two-shot, sunset light through the window.', 's_dress_1'),
    's_dress_3': ('card_dress', '他把手錶放在梳妝台上', ['yu_47', 'cheng_45'], 'He hands her a glass of warm water; she drinks, then folds a sheet of music in four and slips it into the pocket of her gown.', 's_dress_2'),
    's_dress_4': ('card_dress', '門口探進一個年輕人', ['yu_47', 'cheng_45', 'azhe'], 'A young sound engineer with a walkie-talkie leans in at the dressing room door, grinning nervously; she turns to greet him politely; he stands by the window.', 's_dress_1'),
    's_dress_5': ('card_dress', '阿哲跑下樓', ['yu_47', 'cheng_45'], 'He switches on a lamp by the window while the sky is still bright orange; she watches him from the mirror.', 's_dress_1'),
    # 回憶一：2004 門口
    's_mem1_1': ('mem1_door', '2004 年 10 月 14 日，晚上十點', ['cheng_23'], 'Wide: the backstage door of the old theater at night right after rain, glossy black asphalt, one warm door lamp; a young man waits alone holding a deep crimson rose.', None),
    's_mem1_2': ('mem1_door', '余靜：你……在等誰嗎', ['yu_25', 'cheng_23'], 'She steps out of the door in a dark-red velvet dress and cardigan, asking him something; he freezes, blushing, unable to speak.', 's_mem1_1'),
    's_mem1_3': ('mem1_door', '他把玫瑰和一張票根塞到她手上', ['yu_25', 'cheng_23'], 'cg:cg_2004_door', None),
    's_mem1_4': ('mem1_door', '雨後的巷子裡，只有他的腳步聲', ['yu_25'], 'He is gone; she stands alone under the door lamp holding the rose and a ticket stub, looking down the empty wet alley.', 's_mem1_1'),
    # 回憶二
    's_mem2_1': ('mem2_monitor', '2009 年，台北的一場演唱會', ['yu_33'], 'On a concert stage mid-song, she flinches with one hand clutching her in-ear monitor, pain on her face; spotlights and haze.', None),
    's_mem2_2': ('mem2_monitor', '她回頭。側台的燈下', ['yu_33', 'cheng_30'], 'cg:cg_2009_monitor', None),
    's_mem2_3': ('mem2_monitor', '余靜：（下台）剛剛側台那個是誰', ['yu_33', 'cheng_30'], 'Backstage after the show: he stands in front of her with his headset around his neck, bowing slightly in apology; she looks at him with sharp curious eyes.', 's_mem2_2'),
    's_mem2_4': ('mem2_rose', '2011 年，高雄', ['yu_33', 'cheng_30'], 'cg:cg_2011_rose', None),
    's_mem2_5': ('mem2_rose', '余靜：為什麼不說', ['yu_33', 'cheng_30'], 'Night, by the backstage door: he has stood up, embarrassed, scratching the back of his neck; she faces him close, eyes shining.', 's_mem2_4'),
    's_mem2_6': ('mem2_rose', '她從歌譜的透明夾層裡抽出', ['yu_33', 'cheng_30'], 'Close-up: her hands turning over a yellowed orange ticket stub stamped with a seat number; on the back a line of faint pencil handwriting (not readable); his hand near hers.', 's_mem2_4'),
    's_mem2_7': ('mem2_rose', '余靜：程希。', ['yu_33', 'cheng_30'], 'Close two-shot under the street lamp: she says his name; he answers with hers for the first time; both smiling, almost touching foreheads.', 's_mem2_4'),
    's_mem2_8': ('mem2_europe', '2012 年，一座歐洲的歌劇院', ['yu_33'], 'ORIGINAL_COVER', None),
    's_mem2_9': ('mem2_europe', '門被輕輕敲了兩下', ['yu_33', 'cheng_30'], 'The dressing room door of the European opera house slightly open: on the floor a deep crimson rose and a ticket; she kneels to pick them up, smiling; through the gap, his shoulder in the corridor.', 's_mem2_8'),
    's_mem2_10': ('mem2_stage', '2013 年，永明戲院休館的那一天', ['yu_33', 'cheng_30', 'zhou'], 'The empty old theater stage under one warm spotlight: she (simple cream dress) and he (white shirt) pose side by side, shy; the old pianist in the empty front row holds up a camera.', None),
    's_mem2_11': ('mem2_stage', '他牽起她的手', ['yu_33', 'cheng_30', 'zhou'], 'cg:cg_2013_stage', None),
    # 回憶三
    's_mem3_1': ('mem3_forget', '2021 年 12 月', ['yu_42', 'cheng_45'], 'cg:cg_2021_forget', None),
    's_mem3_2': ('mem3_forget', '觀眾席後方的音控台', ['cheng_45'], 'At the mixing desk at the back of a dark concert hall: he presses a walkie-talkie to his mouth, eyes fixed on the stage far away, the console glowing.', 's_mem3_1'),
    's_mem3_3': ('mem3_forget', '台下沒有人發現', ['yu_42', 'cheng_45'], 'A dressing room after the show: she sits at the mirror still in full makeup, staring at nothing; he crouches beside her chair holding her hand.', 's_mem3_1'),
    # 回憶四
    's_mem4_1': ('mem4_clinic', '2022 年 3 月', ['yu_43', 'cheng_45', 'dr_lin'], 'cg:cg_2022_clinic', None),
    's_mem4_2': ('mem4_clinic', '余靜：我還能唱歌嗎', ['yu_43', 'dr_lin'], 'Close: she (long wavy light-brown hair) leans forward asking the doctor a question, her own hands clasped together in her lap; the doctor, a clearly different woman with straight black chin-length hair and thin black-framed glasses on her nose, answers gently.', 's_mem4_1'),
    's_mem4_3': ('mem4_clinic', '余靜：程希，你剛剛為什麼不說話', ['yu_43', 'cheng_45'], 'Close on him writing every word into a small notebook, his jaw tight; she looks at him.', 's_mem4_1'),
    's_mem4_4': ('mem4_letter', '當天晚上，台北的家', ['yu_43'], 'cg:cg_2022_home', None),
    's_mem4_5': ('mem4_letter', '她把信摺好', ['yu_43'], 'Close: her hands slipping a folded letter into the open base of an old plastic portable radio on the dining table.', 's_mem4_4'),
    's_mem4_6': ('mem4_letter', '程希：（從廚房）你在做什麼', ['yu_43', 'cheng_45'], 'He stands in the kitchen doorway drying his hands with a towel, looking at her; she sits by the radio with an innocent small smile.', 's_mem4_4'),
    's_mem4_7': ('mem4_name', '2024 年，台南的老家', ['yu_47', 'cheng_45'], 'cg:cg_2024_name', None),
    's_mem4_8': ('mem4_name', '程希：我是你先生', ['yu_47_home', 'cheng_45'], 'Close two-shot in the dawn kitchen: he says it gently; she repeats the word, tears in her eyes, a small relieved smile.', 's_mem4_7'),
    # 分歧
    's_branch_1': ('branch_dark', '窗外最後一道光', [], 'The dressing room window gone black, every lamp in the room on, the mirror bulbs glowing; the room suddenly feels unfamiliar. Same room as Reference 2, after dark.', 's_dress_1'),
    's_branch_2': ('branch_dark', '余靜：你去。', ['yu_47', 'cheng_45'], 'He stands at the door with a walkie-talkie, hesitating, looking back at her; she sits at the dressing table and nods at him to go.', 's_branch_1'),
    's_branch_3': ('branch_dark', '他看了她三秒，出去了', ['yu_47'], 'The open empty doorway; she sits alone in the bright dressing room, one hand on the folded paper in her pocket, the old radio beside her, the black window behind.', 's_branch_1'),
    # 開演
    's_concert_1': ('concert', '19:30。永明戲院', ['cheng_45'], 'Wide from the back of the hall: the old theater full, a thousand red seats, warm stage light; in the third row a man in a navy shirt holds a rose.', None),
    's_concert_2': ('concert', '周老師的鋼琴彈得很慢', ['yu_47', 'zhou'], 'On stage: she sings in the black lace gown in a warm spotlight, the old pianist at the grand piano behind her; embers of light in the air.', 's_concert_1'),
    's_concert_3': ('concert', '第一段、第二段，她都唱完了', ['yu_47'], 'The teleprompter screen at the front edge of the stage flickers and goes black; she stops, mouth open, in the spotlight.', 's_concert_2'),
    's_concert_4': ('concert', '她的手摸上左耳的耳墜', ['yu_47'], 'Close: in the silent spotlight her fingertips touch the long earring on her left ear, her eyes lost.', 's_concert_2'),
    # 結局 A
    's_a_1': ('ending_a1', '她把手伸進禮服口袋', ['yu_47'], 'Close: her hands unfolding a sheet of music folded in four; on the back, handwriting and a small orange ticket stub (text not readable).', 's_concert_2'),
    's_a_2': ('ending_a1', '她抬起頭', ['yu_47', 'cheng_45'], 'cg:cg_climax', None),
    's_a_3': ('ending_a1', '余靜：（唱）有人坐在我身邊', ['yu_47', 'zhou'], 'She sings with tears running down, smiling, looking at the third row; the pianist plays again behind her, light blooming.', 's_concert_2'),
    's_a_4': ('ending_a2', '安可。周老師彈起〈餘燼〉', ['yu_47', 'zhou'], 'Encore: the whole audience on its feet, roses in the air, she sings in the spotlight.', 's_concert_1'),
    's_a_5': ('ending_a2', '下台的時候，他在側台等她', ['yu_47', 'cheng_45'], 'Side stage in dim light: he holds out a deep crimson rose; she takes it and tucks it into the breast pocket of his navy shirt, smiling up at him.', 's_concert_2'),
    's_a_6': ('ending_a3', '三天後，台南的老家', ['yu_47_home'], 'Early morning old Tainan kitchen: she stands at the fridge reading a folded sheet of music held by a magnet, lips moving, morning light.', None),
    's_a_7': ('ending_a3', '門鈴響', ['yu_47_home', 'tao_73'], 'At the open front door the old neighbor woman holds up a newspaper with a stage photo on the front page, beaming; she looks at it, puzzled and smiling.', 's_a_6'),
    's_a_8': ('ending_a3', '她拉起他的手', ['yu_47', 'cheng_45'], 'cg:cg_a_kitchen', None),
    's_a_9': ('ending_a3', '那天晚上，筆記本翻到新的一頁', ['cheng_45'], 'Night, close on his hand writing in a notebook under a desk lamp, a cup of tea, the sheet of music beside it.', 's_a_6'),
    # 結局 B
    's_b_1': ('ending_b1', '她轉頭，對周老師說', ['yu_47', 'zhou'], 'On stage she turns to the pianist and speaks; he nods, hands rising to the keys.', 's_concert_2'),
    's_b_2': ('ending_b1', '周老師彈起那段前奏', ['yu_47', 'zhou', 'cheng_45'], 'She sings with her eyes closed in a warm spotlight, the old pianist at the grand piano watching her; the whole audience standing, roses raised; in the third row a man stands holding a rose, the only one not singing.', 's_concert_2'),
    's_b_3': ('ending_b1', '全場站了起來', ['yu_47', 'cheng_45'], 'She bows to the standing audience; rising, her polite smile passes over the man in the third row exactly as over every stranger.', 's_concert_1'),
    's_b_4': ('ending_b2', '下台的時候，側台有一個人', ['yu_47', 'cheng_45'], 'Side stage: he hands her a glass of warm water; she bows to him politely like to a stranger; his face holds still.', 's_concert_2'),
    's_b_5': ('ending_b2', '散場以後', ['cheng_45'], 'The empty theater after the show, stage lights going out one by one; he sits alone in the third row, a rose on the empty seat beside him.', 's_concert_1'),
    # 結局 C
    's_c_1': ('ending_c1', '化妝間的門開著', [], 'The backstage stairs and the open back door to an alley at dusk; staff carrying boxed dinners in, their backs turned; the alley glows with market lights.', None),
    's_c_2': ('ending_c1', '九十秒後，程希回到化妝間', ['cheng_45'], 'He stands in the doorway of the empty bright dressing room; on the dressing table the black wristwatch lies beside the notebook.', 's_branch_1'),
    's_c_3': ('ending_c1', '他打開手機上的定位', ['cheng_45'], 'Close: his phone screen showing a map with a red dot blinking right where he stands; his face behind, going pale.', 's_c_2'),
    's_c_4': ('ending_c2', '黃昏市場在收攤', ['yu_47'], 'cg:cg_c_market', None),
    's_c_5': ('ending_c2', '運河邊新修了步道', ['yu_47'], 'cg:cg_c_steps', None),
    's_c_6': ('ending_c3', '18:05，程希、阿哲、小芳分頭找', ['cheng_45'], 'cg:cg_c_search', None),
    's_c_7': ('ending_c3', '天快亮的時候', ['cheng_45', 'tao_73'], 'Blue dawn on the canal walkway: the old woman grabs his hand, pointing below the railing, shouting; volunteers exhausted in the background.', 's_c_6'),
    's_c_8': ('ending_c3', '她坐在最下面那一階', ['yu_47'], 'Blue dawn, seen from above the railing: the old stone steps; on the lowest step she sits leaning her head against the stone wall as if asleep, the hem of the black lace gown in the still water. Peaceful, not graphic.', 's_c_5'),
    's_c_9': ('ending_c3', '阿桃姨趕到，跪了下來', ['cheng_45', 'tao_73'], 'On the steps at dawn: he kneels, the old woman kneels beside him with her hand over her mouth; the water quiet; we do not see her face.', 's_c_7'),
    's_c_10': ('ending_c4', '一個星期後', ['cheng_45', 'tao_73'], 'cg:cg_c_roses', None),
}


def mark():
    p = R / 'canon/劇本.md'
    lines = p.read_text(encoding='utf-8').split('\n')
    have = {m.group(1) for l in lines for m in [re.match(r'^〔圖：(\w+)〕$', l.strip())] if m}
    out, cur, todo = [], None, {k: v for k, v in SHOTS.items() if k not in have}
    for l in lines:
        h = re.match(r'^## (\w+)', l)
        if h:
            cur = h.group(1)
        if l.startswith('## 修改紀錄'):
            cur = None
        for k, (card, start, *_rest) in list(todo.items()):
            body = l.split('：', 1)[-1] if '：' in l else l
            if cur == card and (l.startswith(start) or body.startswith(start)):
                out.append(f'〔圖：{k}〕'); del todo[k]
        out.append(l)
    assert not todo, ('找不到起始句', {k: v[:2] for k, v in todo.items()})
    p.write_text('\n'.join(out), encoding='utf-8')
    print('插入', len(SHOTS) - len(have), '個標記')


if __name__ == '__main__':
    if sys.argv[1:] == ['mark']:
        mark()
