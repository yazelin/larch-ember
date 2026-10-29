#!/bin/bash
# 一場一個 codex：讀修稿包，改好的整場寫到 審稿/修稿/<場>.md
s=$1; cd ~/larch-ember
codex exec -m gpt-6.1-sol -C ~/larch-ember -s workspace-write -o 審稿/修稿/$s.report.md "你在 ~/larch-ember 修《最終遺忘的橘色餘燼》劇本的一場：$s。
讀 審稿/修稿/$s.packet.md（修稿包：準則、這一場、讀稿人挑出的問題、好句、別處引用的句子）。必要時參考 design/重製-分章.md 這一場的節拍、canon/劇本.md 前後場。
1. 逐條處理「必修」問題；「參考」問題自己判斷要不要改。只改被點到的句子，必要時可調整緊鄰的一兩句讓前後接得上；沒被點到的句子一字不動。
2. 準則第 14、16、17 條的句子（唱句、扣回物件、〔圖〕〔掉字〕標記、## 標題、選項）不動。長度不增加。
3. 把改好的整場寫到 審稿/修稿/$s.md：從 ## 那一行開始，格式照 canon/劇本.md，不要行號，不要加說明。
4. 不要改其他任何檔案（不要動 canon/劇本.md）。
5. 寫完跑 ~/speak-tw/bin/speak-tw 審稿/修稿/$s.md，把抓到的問題改掉（唱句與〈天烏烏〉除外）。
6. 最後回報：每條必修的 id，改成什麼或為什麼不改（一行一條）。" < /dev/null > 審稿/修稿/$s.log 2>&1
echo "$s done rc=$? $(test -s 審稿/修稿/$s.md && echo out-ok || echo NO-OUT)"
