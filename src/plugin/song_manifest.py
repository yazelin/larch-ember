"""「唱歌卡」插件的 manifest：python3 src/plugin/song_manifest.py → src/plugin/song-card.json（存成 Larch 個人使用版草稿，不上架；作者 10-29）。
畫面在同資料夾的 song_card.html；遊戲裡跑的是 build 時塞進卡片的 pluginHtml，這份 manifest 只給編輯器認得這種卡。"""
import json, pathlib
HERE = pathlib.Path(__file__).resolve().parent
ID, CARD, VERSION = 'ember-song-card', 'sing', '1.1.0'   # 1.1.0：左上角加封面、歌名、版本
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
    'cards': [{'id': CARD, 'name': '唱歌卡', 'nameEn': 'Sing-along', 'icon': 'music', 'color': '#b5532a', 'presentation': 'fullscreen', 'skippable': False,
               'description': '歌詞跟著秒數亮起，唱完自動往下。', 'descriptionEn': 'Lyrics follow the clock; continues when the song ends.',
               'readVariables': [], 'writeVariables': [], 'fields': FIELDS, 'html': (HERE / 'song_card.html').read_text(encoding='utf-8')}],
}

if __name__ == '__main__':
    out = HERE / 'song-card.json'
    out.write_text(json.dumps(MANIFEST, ensure_ascii=False, indent=1), encoding='utf-8')
    print(out, out.stat().st_size, 'bytes')
