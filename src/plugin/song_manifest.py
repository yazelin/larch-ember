"""「唱歌卡」插件的 manifest：python3 src/plugin/song_manifest.py → src/plugin/song-card.json（存成 Larch 個人使用版草稿，不上架；作者 10-29）。
畫面在同資料夾的 song_card.html；遊戲裡跑的是 build 時塞進卡片的 pluginHtml，這份 manifest 只給編輯器認得這種卡。"""
import json, pathlib
HERE = pathlib.Path(__file__).resolve().parent
ID, CARD, VERSION = 'ember-song-card', 'sing', '1.1.1'   # 1.1.0：左上角加封面、歌名、版本；1.1.1：略過鈕照 Larch 介面樣式、補商城介紹
FIELDS = [
    {'key': 'lines', 'kind': 'longText', 'label': '歌詞', 'labelEn': 'Lyrics', 'defaultValue': '1.5｜第一句\n5.0｜第二句',
     'hint': '一行一句：「秒數｜歌詞」，秒數從進卡算起。間奏可以寫「♪」。'},
    {'key': 'duration', 'kind': 'number', 'label': '歌長（秒）', 'labelEn': 'Song length (s)', 'min': 1, 'max': 900, 'step': 0.1, 'defaultValue': 60,
     'hint': '歌唱完再停「結尾停留」秒才往下。'},
    {'key': 'endHold', 'kind': 'number', 'label': '結尾停留（秒）', 'labelEn': 'Hold at the end (s)', 'min': 0, 'max': 10, 'step': 0.5, 'defaultValue': 1.5},
    {'key': 'offset', 'kind': 'number', 'label': '校正（秒）', 'labelEn': 'Offset (s)', 'min': -2, 'max': 3, 'step': 0.05, 'defaultValue': 0.25,
     'hint': '進卡到歌真的出聲的延遲；歌詞比歌早就調大。'},
    {'key': 'singer', 'kind': 'text', 'label': '左上角小字（誰在唱）', 'labelEn': 'Singer label', 'defaultValue': ''},
    {'key': 'songTitle', 'kind': 'text', 'label': '歌名', 'labelEn': 'Song title', 'defaultValue': ''},
    {'key': 'songVersion', 'kind': 'text', 'label': '版本', 'labelEn': 'Version', 'defaultValue': ''},
    {'key': 'cover', 'kind': 'asset', 'assetKind': 'image', 'label': '封面（方形）', 'labelEn': 'Cover (square)'},
    {'key': 'skipLabel', 'kind': 'text', 'label': '略過鈕文字', 'labelEn': 'Skip label', 'defaultValue': '略過'},
    {'key': 'backgrounds', 'kind': 'longText', 'label': '換背景', 'labelEn': 'Background changes', 'defaultValue': '0｜1',
     'hint': '一行一次：「秒數｜第幾張圖」。'},
] + [{'key': f'image{i}', 'kind': 'asset', 'assetKind': 'image', 'label': f'背景圖 {i}', 'labelEn': f'Background {i}'} for i in range(1, 7)]

MANIFEST = {
    'id': ID, 'name': '唱歌卡', 'nameEn': 'Sing-along card', 'version': VERSION, 'author': '林亞澤', 'authorHandle': 'yaze',
    'pricing': 'free', 'icon': 'music', 'categories': ['card'], 'license': 'MIT · 林亞澤',
    'description': '全螢幕唱歌卡：卡片上的歌由播放器播，歌詞照進卡後的秒數一句一句亮起，背景圖可以照秒數換。點畫面不會讓歌詞往前跑；唱完自動往下，或按「略過」。',
    'descriptionEn': 'Fullscreen sing-along card: the player plays the card music, lyrics light up by elapsed seconds, backgrounds change on cue. Clicks never push the lyrics ahead; it continues when the song ends or when the skip button is pressed.',
    'permissions': ['assets:read', 'flow:control'],
    'overview': ('讓歌好好唱完的卡片。卡片上的歌交給播放器播，歌詞照「進卡後經過的秒數」一句一句亮起，正在唱的那句放大，上一句、下一句淡淡留著。\n\n'
                 '用對話框拼歌詞，玩家一點畫面字就跑到歌前面；這張卡不吃點擊，歌唱完才自動往下。想離開就按右下角的「略過」。\n\n'
                 '歌詞一行寫「秒數｜歌詞」，背景圖可以照秒數換，左上角可以放封面、歌名與版本。進卡到歌真的出聲的延遲，用「校正」秒數補。'),
    'features': '歌詞照秒數亮起，點畫面不會跑掉\n唱完自動往下，或按「略過」\n最多 6 張背景圖，照秒數換\n左上角封面、歌名、版本\n「校正」秒數補播放延遲\n手機直式也能用',
    'overviewEn': ('A card that lets a song play through. The player plays the card music; lyrics light up by elapsed seconds, the current line large with the previous and next lines faint.\n\n'
                   'Clicks never push the lyrics ahead. The card continues when the song ends, or when the skip button is pressed.\n\n'
                   'Write lyrics as one "seconds｜line" per row, change backgrounds on cue, and show a cover, title and version in the corner.'),
    'featuresEn': 'Lyrics follow the clock; clicks do not skip ahead\nContinues when the song ends, or on Skip\nUp to 6 backgrounds on cue\nCover, title and version in the corner\nOffset to cover playback latency\nWorks on phones',
    # 商城縮圖與截圖（作者 10-29：素材商城裡缺封面）；原檔在 src/plugin/song-card-*.webp，用 larch 的 plugins/images 上傳
    'cover': 'https://pub-4b20b43f5acf4dfaa3f6ab842daa51cf.r2.dev/2d3b0242-9a6d-4051-9825-46aa4efd064a/larch/plugins/ember-song-card/1793254259774_song-card-cover-111.webp',
    'gallery': [{'url': 'https://pub-4b20b43f5acf4dfaa3f6ab842daa51cf.r2.dev/2d3b0242-9a6d-4051-9825-46aa4efd064a/larch/plugins/ember-song-card/1793254280477_song-card-shot-desk-111.webp', 'caption': '桌機：歌詞照秒數亮起，左上角是正在播的歌'},
                {'url': 'https://pub-4b20b43f5acf4dfaa3f6ab842daa51cf.r2.dev/2d3b0242-9a6d-4051-9825-46aa4efd064a/larch/plugins/ember-song-card/1793254283818_song-card-shot-phone-111.webp', 'caption': '手機直式'}],
    'cards': [{'id': CARD, 'name': '唱歌卡', 'nameEn': 'Sing-along', 'icon': 'music', 'color': '#b5532a', 'presentation': 'fullscreen', 'skippable': False,
               'description': '歌詞跟著秒數亮起，唱完自動往下。', 'descriptionEn': 'Lyrics follow the clock; continues when the song ends.',
               'readVariables': [], 'writeVariables': [], 'fields': FIELDS, 'html': (HERE / 'song_card.html').read_text(encoding='utf-8')}],
}

if __name__ == '__main__':
    out = HERE / 'song-card.json'
    out.write_text(json.dumps(MANIFEST, ensure_ascii=False, indent=1), encoding='utf-8')
    print(out, out.stat().st_size, 'bytes')
