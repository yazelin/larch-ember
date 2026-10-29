"""公開站的圖與音樂走 jsDelivr（HTML 放 GitHub Pages：Pages 從作者的網路只有 50–90KB/s，大檔改走 jsDelivr）。
repo 一個 commit 幾百 MB，jsDelivr 有 50 MB 上限，所以把 docs/media、docs/music 打成孤兒 tag（tag 名帶樹的雜湊，沒改就沿用）。
做的事：打 tag 並推上 GitHub → 用這個 tag 重產 music.html → index.html、mv.html 的 media/、music/ 換成 jsDelivr → 每個網址 GET 一次。
docs/media、docs/music 要先 commit 並 git push。

    python3 site/cdn.py
"""
import os, re, pathlib, subprocess, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parent.parent
REPO = 'yazelin/larch-ember'
DIRS = ('docs/media', 'docs/music')
PAGES = ('index.html', 'mv.html')
OLD = re.compile(r'(["\'(])(?:https://cdn\.jsdelivr\.net/gh/' + re.escape(REPO) + r'@[\w.-]+/docs/)?((?:media|music)/)')


def git(*a, **k):
    return subprocess.run(['git', *a], cwd=ROOT, capture_output=True, text=True, check=True, **k).stdout


def tag():
    dirty = [l for l in git('status', '--porcelain', '--', *DIRS).splitlines() if l.strip()]
    if dirty: raise SystemExit(f'docs/media、docs/music 有沒 commit 的檔：{dirty[:5]}')
    if not git('branch', '-r', '--contains', 'HEAD').strip(): raise SystemExit('HEAD 還沒推上 GitHub；先 git push')
    idx = ROOT / '.git' / 'jsd-site.index'
    idx.unlink(missing_ok=True)
    env = {**os.environ, 'GIT_INDEX_FILE': str(idx)}
    run = lambda *a, **k: subprocess.run(['git', *a], cwd=ROOT, env=env, capture_output=True, text=True, check=True, **k).stdout
    run('update-index', '-z', '--index-info', input=git('ls-tree', '-r', '-z', 'HEAD', '--', *DIRS))
    tree = run('write-tree').strip()
    size = sum(int(l.split()[3]) for l in git('ls-tree', '-r', '-l', tree).splitlines())
    if size > 45e6: raise SystemExit(f'公開站素材 {size / 1e6:.1f} MB，快到 jsDelivr 的 50 MB 上限，要拆包')
    name = f'site-media-{tree[:8]}'
    if not git('tag', '-l', name).strip():
        git('tag', name, run('commit-tree', tree, '-m', 'jsDelivr：餘燼公開站素材').strip())
    if not git('ls-remote', '--tags', 'origin', name).strip():
        git('push', '-q', 'origin', name)
    print(f'jsDelivr {name}：{size / 1e6:.1f} MB')
    return name


def main():
    base = f'https://cdn.jsdelivr.net/gh/{REPO}@{tag()}/docs/'
    subprocess.run(['python3', 'site/build_music.py'], cwd=ROOT, check=True, env={**os.environ, 'MEDIA_BASE': base})
    for n in PAGES:
        p = ROOT / 'docs' / n
        p.write_text(OLD.sub(lambda m: m.group(1) + base + m.group(2), p.read_text(encoding='utf-8')), encoding='utf-8')
    urls = sorted({u for n in ('index.html', 'mv.html', 'music.html')
                   for u in re.findall(re.escape(base) + r'[^"\'()\s]+', (ROOT / 'docs' / n).read_text(encoding='utf-8'))})
    def get(u):
        for _ in range(3):
            try:
                with urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'}), timeout=120) as r:
                    if r.status == 200: return 200
            except urllib.error.HTTPError as e:
                code = e.code
                if code in (403, 404): urllib.request.urlopen(u.replace('//cdn.', '//purge.', 1), timeout=60).close()
            except Exception: pass
        return 0
    with ThreadPoolExecutor(3) as ex: codes = list(ex.map(get, urls))
    bad = [u for u, c in zip(urls, codes) if c != 200]
    print(f'jsDelivr：{len(urls) - len(bad)}/{len(urls)} 個網址回 200')
    if bad: raise SystemExit(f'抓不到：{bad[:5]}')


if __name__ == '__main__':
    main()
