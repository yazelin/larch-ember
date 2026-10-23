# 劇本品質提升系統：接手手冊（餘燼版，2026-10-23）

這套是作者 2026-10-23 同意的：把「七項寫作練習」變成每一場都要過的評分（見 `流程.md` 的表），目的是讓這七項每一場都過關。從《續》的 `~/larch-taoyuan/xu/審稿/` 移植，決策規則相同。你不用問作者「接下來做什麼」，照這份做；只有標「升級」的條目要作者拍板。

## 三條原則

1. **寫的人不判自己的稿。** 要不要換進劇本、比賽哪一版勝出，看 `gate` 與 `contest.py judge` 的結果。
2. **送外部模型的提示詞一律由程式產生。** 不手寫，也不在提示詞裡放例句。
3. **回報作者的數字從工具輸出或檔案抄，不憑記憶。**

另外：作者要求劇本句子由 codex 寫。修稿時把修稿包交給 codex 產出，你負責套用、對照準則、跑閘門。

## 一場的流程（從 ~/larch-ember 跑）

```bash
python3 審稿/runner.py next canon/劇本.md                 # 各場狀態；照最後一行「下一步」打
python3 審稿/runner.py read canon/劇本.md m_letter         # 從沒審過：讀稿人＋查證，約 3 到 8 分鐘（run_in_background）
python3 審稿/runner.py packet canon/劇本.md m_letter       # 有必修：讀修稿包，照「走哪條路」做
python3 審稿/runner.py gate canon/劇本.md m_letter         # 改完一定要過（run_in_background）
python3 審稿/runner.py ship "提交訊息" canon/劇本.md        # 連帶掃描、重建、檢查、提交（不 push）
```

場代號就是 `##` 後面括號前的那串，例如 `m_letter`、`branch_dark`、`ending_c3`。

修稿包說「逐條改」時：只改被點到的句子；讀稿人的改法建議當線索；不改的用 `runner.py resolve <id> 不改 "理由"`。整場層級的必修（沒有好句、沒有真人痕跡、主編意見）沒有原句可對，下一次讀稿沒人再判定才自動結案，或用 resolve 手動結。

修稿包說「重寫比賽」時：`python3 審稿/contest.py write <場代號> canon/劇本.md`（run_in_background），同時自己寫一版存 `審稿/比賽/<場代號>/draft_claude.txt`（寫完之前不看別人的稿），再 `contest.py judge <場代號>`；換進劇本的是勝出那一版。同一場只比一次。

閘門不通過：照輸出的「新稿還有的共識問題」再改，最多三輪；三輪不過用 `runner.py restore canon/劇本.md <場代號>` 換回原稿。

ship 之後，照輸出最後一行用 run_in_background 跑 `END=a`、`b`、`c` 的 `play_full.mjs`，一次只跑一個，跑的時候不要 build。

## 七項評分在哪裡

| 評分 | 程式 |
|---|---|
| 一 好句（摘句本） | 讀稿提示的「好句」段；`runner.py good [場代號]` 印出 |
| 二 真人說話與痕跡 | 讀稿提示的類型「真人不會這樣說」與「痕跡」段 |
| 三 出聲念 | 讀稿提示的類型「念不出口的書面語」；`tests/check_voice.py` 對白書面語警告 |
| 四 比較練習 | `contest.py` |
| 五 限制寫作 | `tests/check_voice.py` 旁白情緒詞警告、旁白比喻硬規則 |
| 六 伏筆帳 | `tests/motif_check.py`（ship 會跑；回收沒有出處就擋） |
| 七 主編意見 | `runner.py editors`：`design/編輯意見/` 的 codex、gemini、deepseek 三份意見指到場代號的條目進問題單，兩位以上講到相近的事＝必修 |

## 決策規則（程式已實作）

| 規則 | 內容 | 在哪裡改 |
|---|---|---|
| 讀稿人 | 偏好 opus、codex、argon、deepseek 四家族各一位；額度用完的自動拿掉，google 家族缺席時用 gemini-web 補位。`READERS=codex,deepseek,geminiweb` 可強制 | `scene_review.py` 的 `PREFERRED`、`available()` |
| 共識問題 | 兩位以上讀稿人提到同一句 | `runner.py` 的 `same`、`clusters` |
| 閘門通過 | 新出現的共識問題比修掉的少且新稿兩兩比較不輸；或不比修掉的多且新稿多贏兩票以上 | `runner.py` 的 `verdict` |
| 閘門評審 | 排除 anthropic 家族與新稿作者的家族；A/B 對調各問一次 | `runner.py` 的 `pairwise` |
| 比賽勝出 | 去掉同家族票之後的平均名次前三名裡，共識問題最少的；同數比名次 | `contest.py` 的 `pick` |
| 走比賽的門檻 | 必修 6 條以上，或佔這一場台詞三成以上（沿用《續》初值） | `runner.py` 的 `CONTEST_MUST`、`CONTEST_RATIO` |

## 不要做

1. 憑感覺挑版本或補句子（《續》2026-10-20 的教訓：補進去的三句複審時都被點出問題）。
2. 用 `pgrep -f "某指令"` 寫等待迴圈；背景工作用 run_in_background 等通知。
3. 手寫提示詞給外部模型。
4. 改了劇本沒有重建就說「已同步」；`ship` 會重建並跑檢查。
5. 試玩還在跑時重建，或同時跑兩個試玩；`ship` 遇到試玩在跑會拒絕。
6. `git add -A`、push、推 Larch、發佈、改 `canon/歌詞.md`；前一項永遠不做，後面要作者點頭。

## 檔案

| 檔 | 內容 |
|---|---|
| `runner.py` | `next`、`read`、`packet`、`gate`、`restore`、`ship`；`editors`、`ingest`、`todo`、`resolve`、`facts`、`good`、`report`、`export`；`selftest` 不打外部模型的自我檢查 |
| `scene_review.py` | 讀稿人、提示詞、`sweep`、`status` |
| `contest.py` | 重寫比賽 `write`、`judge`；`selftest` |
| `ai_scan.py` | 全劇 AI 味機械掃描（固定句型與用詞） |
| `準則.md` | 寫稿準則，比賽與修稿包自動帶入 |
| `流程.md` | 七項評分與每場關卡 |
| `問題單.json`、`事實.json`、`好句.json`、`狀態.json` | 機器狀態，不要手改 |
| `紀錄/` | 每次讀稿（`sweep_*`，含當時原文）與閘門（`gate_*.md`）的原始輸出 |
| `比賽/` | 比賽稿與結果 |
