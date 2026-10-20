"""歌曲接線（Suno 的三首：餘燼、晚安台南、港邊的燈）。目前是空殼：assets/songs/cuts/manifest.json 不存在就什麼都不做。
build.py 在寫出 project.json 前呼叫 songs.apply(project, dist)。"""
import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
MANIFEST = ROOT / 'assets/songs/cuts/manifest.json'


def apply(project, dist=None):
    if not MANIFEST.exists():
        return
