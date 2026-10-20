# 最終遺忘的橘色餘燼

改編自真實故事的 Larch 視覺小說＋RPG。台南老戲院，歌手余靜得了早發性阿茲海默症，告別演唱會當天的下午，三個結局。

原型是兩位罹患阿茲海默症、仍然站上舞台唱完最後一場的歌手：Tony Bennett 與 Lady Gaga 的最後兩場演唱會、Glen Campbell 的告別巡演。主角改成女歌手。所有參考資料（原型與醫學研究）與出處在公開站與 `canon/研究.md`。

- 公開站：<https://yazelin.github.io/larch-ember/>（原始檔 `docs/index.html`）
- 試玩：上線後補

## 資料夾

| 路徑 | 內容 |
|---|---|
| `canon/` | 原文、劇本（`劇本.md`）、歌詞與 Suno 提示、`研究.md`（原型與醫學研究，附出處） |
| `design/` | 重寫設計（`重寫.md`）、人物、地圖、審稿與讀者反應 |
| `src/` | `build.py` 把劇本、地圖、變數組成 `dist/project.json`；`script.py`、`cards.py`、`maps.py`、`mapkit.py`、`layout.py`、`variables.py` 是各部分 |
| `art/` | 生圖與後製腳本（CG、立繪、行走圖、地圖物件）、`check/` 驗收截圖 |
| `assets/` | 正式素材：立繪、CG、地圖、行走圖；`assets/songs/` 放作者的三首 Suno 歌，說明見 `assets/songs/README.md` |
| `tests/` | Playwright 檢查（地圖截圖、介面截圖、CG 收藏、hover 跳位） |
| `site/media.py` | 公開站素材：把 `assets/`、`art/` 的圖縮成小檔放進 `docs/media/` |
| `docs/` | 公開站（GitHub Pages） |

## 指令

    python3 src/build.py            # 產出 dist/project.json
    python3 site/media.py           # 重做 docs/media（長邊 1600 以內、webp 品質 85）
    python3 src/songs_cut.py --build   # 歌檔（assets/songs/*.mp3）→ 對齊歌詞、切段、收音機版、manifest → 接進 build；沒放歌時 build 照舊
    python3 tests/songs_check.py       # 接歌結果檢查（build 之後）
    node tests/songs_sfx.mjs           # 地圖卡的收音機歌逐句播出
    node tests/songs_sync.mjs          # 歌卡歌詞跟歌的同步實測（真實時間）
    node tests/map_shots.mjs        # 地圖截圖到 art/check/
    node tests/ui_shots.mjs         # 介面截圖
    node tests/gallery_check.mjs    # CG 收藏解鎖
    node tests/hover_check.mjs      # 地圖標籤 hover 不跳位
    ~/speak-tw/bin/speak-tw --public docs/index.html README.md   # 對外文字檢查

歌曲工具用共用 whisper-server（`~/.mori`）取時間、ffmpeg 處理、opencc 轉簡繁比對；沒有歌檔時可用 `src/songs_fixture.py` 做語音替身測流程（見 `assets/songs/README.md`）。

`tests/` 需要本機預覽器 `~/larch-preview` 與 Playwright。`python3 art/*.py` 與 `src/tts.py` 要連自架服務，金鑰從環境變數讀，不放進 repo。

## 分工

劇本方向、角色與設計由作者決定並審稿。文字由 AI 依作者的方向與審稿寫，美術由 AI 生圖、作者挑選，器樂配樂由 AI 生成，歌曲由作者在 Suno 製作，地圖與程式（含測試）由 AI 製作。這一版沒有配音。

## 授權

程式碼以 MIT 授權（`LICENSE`）。故事文字、美術與公開站內容以 CC BY-NC 4.0 授權（`LICENSE-CONTENT.md`）。
