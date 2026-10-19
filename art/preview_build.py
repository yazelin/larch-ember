"""不動主對話的 dist：把 build 輸出導到 dist-maps/（地圖分身專用的預覽與測試）。
python3 art/preview_build.py   → dist-maps/dist/project.json；預覽：python3 ~/larch-preview/serve.py dist-maps/dist/project.json --port 0"""
import os, pathlib, sys
R = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / 'src'))
import build
tmp = R / 'dist-maps'; tmp.mkdir(exist_ok=True)
for n in ('skeleton', 'assets'):
    link = tmp / n
    if not link.exists(): link.symlink_to(R / n)
build.R = tmp
build.build()
