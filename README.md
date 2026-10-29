# 餘燼

改編自真實故事的 Larch 視覺小說。歌手余靜得了早發性阿茲海默症，回到台南老戲院唱最後一場。從 1988 年阿爸的魚攤、2004 年三排十四號那個說不出話的年輕人，一路走到 2026 年的告別演唱會。

**2026-10-29 起是重製版**：單線、純劇情卡、一個結局，順序照劇中的歌走（設計 `design/重製.md`、分章大綱 `design/重製-分章.md`）。舊版（RPG 地圖、三個結局）的劇本留在 `canon/劇本-三結局版.md`，地圖與相關程式留在 git 歷史與 `art/`、`src/maps.py` 等檔，重製版的建置不再使用。

原型是兩位罹患阿茲海默症、仍然站上舞台唱完最後一場的歌手：Tony Bennett 與 Lady Gaga 的最後兩場演唱會、Glen Campbell 的告別巡演。主角改成女歌手。所有參考資料（原型與醫學研究）與出處在公開站與 `canon/研究.md`。

- 公開站：<https://yazelin.github.io/larch-ember/>（原始檔 `docs/index.html`）
- 原聲帶頁：`docs/music.html`（〈餘燼〉四個版本、〈晚安，台南〉、〈港邊的燈〉；逐句動態歌詞、播放時背景換成作品裡的 CG、餘燼與花瓣粒子、頻譜環）
- 試玩：上線後補
- MV 頁：`docs/mv.html?song=ember-b&embed=1`（〈餘燼〉台下跟唱版，給遊戲結局 B 用小遊戲卡全螢幕嵌入；含結局劇透，不放進首頁導覽，原聲帶頁也不連過去）。分鏡表在 `site/mv_storyboard.json`，`python3 site/build_mv.py` 產生頁面與 `docs/media/mv/`

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
| `site/music_assets.py`、`site/make_lrc.py`、`site/verify_lrc.py`、`site/build_music.py`（加 `music.css`、`music.js`） | 原聲帶頁：音檔重編 128kbps 放 `docs/music/`、封面與背景 CG 放 `docs/media/`；動態歌詞 `docs/music/*.lrc`（只取時間，文字一律用官方歌詞）與抽查；再產生 `docs/music.html` |
| `docs/` | 公開站（GitHub Pages） |
| `審稿/` | 劇本審稿閘門（從《續》移植，作者 2026-10-23 同意）：讀稿人找問題與好句、修稿包、改前改後閘門、重寫比賽、主編意見併入；七項評分與流程見 `審稿/README.md`、`審稿/流程.md` |

## 指令

    python3 src/build.py            # 產出 dist/project.json
    python3 site/media.py           # 重做 docs/media（長邊 1600 以內、webp 品質 85）
    python3 src/songs_cut.py --build   # 歌檔（assets/songs/*.mp3）→ 對齊歌詞、切段、收音機版、manifest → 接進 build；沒放歌時 build 照舊
    python3 tests/songs_check.py       # 接歌結果檢查（build 之後）
    node tests/songs_sfx.mjs           # 逐句音效依序播出：收音機的歌、天黑分歧的三個聲音（敲兩下、走廊前奏）、1988 魚攤
    node tests/songs_sync.mjs          # 歌卡歌詞跟歌的同步實測（真實時間）
    node tests/play_linear.mjs      # 重製版全劇試玩（單線）
    node tests/map_shots.mjs        # 地圖截圖到 art/check/（舊版）
    node tests/ui_shots.mjs         # 介面截圖
    node tests/gallery_check.mjs    # CG 收藏解鎖
    node tests/hover_check.mjs      # 地圖標籤 hover 不跳位
    python3 site/music_assets.py    # 原聲帶音檔（來源在 ~/下載/有封面/）、封面、背景 CG
    python3 site/make_lrc.py        # 動態歌詞：openai-whisper 字詞時間對齊官方歌詞，輸出 docs/music/*.lrc 與 lyrics.json（要有 GPU 與 openai-whisper）
    python3 site/verify_lrc.py      # 抽查：每首取 8 行，辨識該行時間前後各 2 秒的音檔
    python3 site/build_music.py     # 產生 docs/music.html（歌詞署名 LYRICS_CREDIT 沒填會失敗，預覽可加 --draft）
    ~/speak-tw/bin/speak-tw --public docs/index.html docs/music.html README.md   # 對外文字檢查
    python3 tests/check_voice.py    # 劇本台詞機械檢查（硬規則擋；旁白情緒詞、對白書面語只警告）
    python3 tests/motif_check.py    # 伏筆帳：三條路線上每個回收之前都有出處
    python3 審稿/runner.py next canon/劇本.md   # 審稿閘門：各場狀態與下一步（流程見 審稿/README.md）

歌曲工具用共用 whisper-server（`~/.mori`）取時間、ffmpeg 處理、opencc 轉簡繁比對；沒有歌檔時可用 `src/songs_fixture.py` 做語音替身測流程（見 `assets/songs/README.md`）。

`tests/` 需要本機預覽器 `~/larch-preview` 與 Playwright。`python3 art/*.py` 與 `src/tts.py` 要連自架服務，金鑰從環境變數讀，不放進 repo。

## 重製版的結構

`src/build.py` 的 `ORDER` 依序串 18 張卡：open（2026 冷開場）→ market（1988）→ livehouse（2001）→ door2004 → roses（2006–2008，錄音室唱〈餘燼〉）→ monitor（2009 耳返爆音）→ confess（2011、2013）→ forget（2021–2022）→ song2023（寫〈晚安，台南〉、2024）→ soundcheck → letter → dark（天黑走失）→ canal（運河石階）→ concert → verse3 → encore → kitchen（「什麼演唱會？」）→ credits。

- letter 與 canal 結尾各接一張只有一個選項的選擇卡（程希一次只問一個問題）。
- 〔掉字〕只在 letter、dark、canal 三場，比例在 `FADE_RATIO`。
- 歌的位置在 `src/songs_cut.py` 的 `CUTS`：〈港邊的燈〉收音機版（market）、〈餘燼〉錄音室版（roses）、台下跟唱版副歌起悶住三秒（monitor，耳返爆音）、〈晚安，台南〉試音／開演／第三段、大合唱版（encore）、合聲版當片尾曲（credits）。
- 試玩：`SPEED=16 AUDIO=1 node tests/play_linear.mjs`（從標題點到製作名單，檢查每一章的關鍵句依序出現、沒有缺檔）。

## 分工

劇本方向、角色與設計由作者決定並審稿。文字由 AI 依作者的方向與審稿寫，美術由 AI 生圖、作者挑選，器樂配樂由 AI 生成，歌曲由作者在 Suno 製作，地圖與程式（含測試）由 AI 製作。這一版沒有配音。

## 授權

程式碼以 MIT 授權（`LICENSE`）。故事文字、美術與公開站內容以 CC BY-NC 4.0 授權（`LICENSE-CONTENT.md`）。

## 公開站的素材網址

整個遊戲 repo 的 `.git` 超過 600MB，jsDelivr 對超過 50MB 的 repo 會 403，Pages 又慢。做法照《十一分鐘》：把 `docs/media/` 與 `docs/music/` 放進一個只有素材的孤兒 tag（例如 `site-media-1`），頁面圖與音檔走 jsDelivr。

    MEDIA_BASE=https://cdn.jsdelivr.net/gh/yazelin/larch-ember@site-media-1/docs/ python3 site/build_music.py

`index.html` 目前用相對路徑；要改成 jsDelivr 時，把 `media/` 前綴換成同一個網址。建 tag 與 push 要等作者點頭。

## 余靜的改寫（2026-10-23）

作者認為女主角「隨便、讓人喜歡不起來」「忘了也不會傷心難過」。依 `design/失智症反應研究.md`（29 筆來源）寫成 `design/余靜改寫方向.md`，作者拍板三件事：用笑遮羞、笑完安靜；病識感時有時無；程希離開的九十秒加一段她獨處的戲，並讓「三個聲音」（敲兩下、走廊的〈餘燼〉前奏、窗外收攤聲）依序出現再接選項。句子由 codex 寫，提示詞與原始輸出在 `design/余靜改寫/`，`design/余靜改寫/metrics.py` 量每條路線的行數字數與余靜的察覺句數。

天黑分歧的音效：敲兩下用 Larch 內建 knock（`assets/sfx/knock_door.mp3`，加大到約 -22 LUFS）、走廊前奏是 `songs_cut.py` 的 `ember_corridor`（錄音室版前奏，低通加短殘響，-23 LUFS）。窗外收攤聲沒有音檔，只有文字（gemini-web 的音樂端點做不出環境音）；`src/songs.py` 的 `LINE_SFX` 已留位置，放進 `assets/sfx/market_closing.mp3` 就會接上。

