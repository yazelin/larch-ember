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

## 地圖結構（RPG 探索）

五張地圖，每張都是平的（沒有遮擋牆、隱藏格），18×12 格，設計檔在 `art/objects_<地圖>.yaml`：

| 地圖 | id | 內容 |
| --- | --- | --- |
| 化妝間 | `m-dressing` | 主地圖；門通後台二樓 |
| 後台二樓 | `m-backstage-2f` | 化妝間的門、鋼琴與周老師、拱門樓梯口（下樓） |
| 後台一樓 | `m-backstage` | 側台門（通觀眾席）、後門（通巷子）、拱門樓梯口（上樓） |
| 觀眾席 | `m-auditorium` | 從側台門進，回後台一樓門前 |
| 後門巷子 | `m-alley` | 從後門出，回後台一樓後門前 |

後台二樓與一樓只有北牆右上角一個拱門樓梯口（x15–16，拱門裡畫著階梯，地板上沒有階梯）：走到拱門前（第 3 列）就淡出，換到另一層拱門前（第 4 列，朝南）。導引文字：二樓「下樓：走到拱門樓梯口」、一樓「上樓：走到拱門樓梯口」。二樓偏走廊與衣物（服裝架、地毯、鋼琴、試衣鏡、一只箱子），一樓偏道具工作區（道具桌、箱子、長椅、電纜盤），同一種物件只在一層出現。兩層用同一首後台配樂（`src/build.py` 的 `MAP_TRACK`）。

美術管線 `art/mapgen.py`：`style`（整間房畫風定錨）→ `ground`（地面，樓梯要通過立面閘門）→ `gen`（逐物件，機械品質閘門）→ `cut` → `review`（合成預覽在 `art/check/maps-review/`）→ `audit`。檢查：

    python3 art/preview_build.py            # 預覽版導到 dist-maps/dist/project.json
    python3 tests/map_check.py dist-maps/dist/project.json   # 事件／導引／跳轉落點走得到、每個跳轉都有回程、arrive 離回程觸發格 ≤ 8 步
    node tests/map_walk.mjs                 # 實機走路：點「遊戲任務」讓主角自己走，含整條路線（化妝間→二樓→鋼琴→下樓→一樓→側台門→觀眾席）與回程
    python3 -c "import sys; sys.path.insert(0,'src'); import layout; print(layout.check(layout.load('backstage')))"   # 設計檔：佔地、門、空洞、物件不蓋住走得到的格子

## 分工

劇本方向、角色與設計由作者決定並審稿。文字由 AI 依作者的方向與審稿寫，美術由 AI 生圖、作者挑選，器樂配樂由 AI 生成，歌曲由作者在 Suno 製作，地圖與程式（含測試）由 AI 製作。這一版沒有配音。

## 授權

程式碼以 MIT 授權（`LICENSE`）。故事文字、美術與公開站內容以 CC BY-NC 4.0 授權（`LICENSE-CONTENT.md`）。
