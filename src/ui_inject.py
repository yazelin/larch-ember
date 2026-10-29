"""把「信紙與餘燼」介面塞進 project：build.py 最後呼叫 ui_inject.apply(project)。
只給本機預覽與 dist 用；線上的 PUT 不會更新 customInterfaces（要另外 push_ui／編輯器匯入 ui/信紙與餘燼.html）。
音效：Larch 的介面 Skill 只收 R2／larch.ink 網址。ui/hosted.json 有上傳過的網址就用它；沒有就用 /files/ui-sfx/*.mp3
（本機預覽讀得到，apply 會把 ui/sfx 複製到 dist/ui-sfx；Larch 上是無聲，不會落回內建音效）。"""
import pathlib, shutil, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'ui'))
import ember
SURFACES = ('title', 'dialogue', 'choices', 'menu', 'inventory', 'gallery', 'rpg')


def apply(project: dict, dist=None) -> None:
    dist = pathlib.Path(dist) if dist else ROOT / 'dist'
    ember.build()   # 每次都從 ui/src 與 ui/mist-original 重產 ui/parts，不會用到過期的部位
    ci = project['settings'].setdefault('customInterfaces', {})
    for k in SURFACES:
        f = next((ember.OUT).glob(f'{k}.*'))
        ci[k] = {'html': f.read_text(encoding='utf-8'), 'enabled': True}
    if not ember.HOSTED:
        (dist / 'ui-sfx').mkdir(parents=True, exist_ok=True)
        for f in (ROOT / 'ui/sfx').glob('*.mp3'):
            shutil.copy2(f, dist / 'ui-sfx' / f.name)
    project['settings']['menuUi'] = {'preset': 'paper', 'accent': '#e8743b', 'title': '餘燼', 'eyebrow': '余靜的黃昏', 'buttons': ['bag', 'save', 'load', 'title']}
