# SLAM 實驗紀錄

實作順序與架構以根目錄 [`README.md`](../README.md) 為準。本文件只記錄自己的 SLAM 實驗，不再保存 Cartographer、Slam Toolbox 或 Nav2 的啟動指令。

每次實驗至少記錄：

```text
日期：
版本/commit：
bag：
參數：
ATE / RPE / loop gap：
latency p50 / p95 / max：
accepted/rejected scans：
accepted/rejected loops：
觀察：
下一個假設：
```

只改一組變因，並用同一個 bag 和 baseline 比較。RViz 截圖可作除錯證據，但不能取代數值指標與 regression test。
