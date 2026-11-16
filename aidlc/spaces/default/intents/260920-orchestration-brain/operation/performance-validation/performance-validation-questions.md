# Performance Validation — 問題檔

> stage 檔要求在「類 production 環境」跑負載測試並以 CloudWatch／X-Ray 分析。本 repo 只有單台自架 staging（`192.168.10.10`），production 不在範圍（`project.md` `## Scope Overrides`），也沒有 CloudWatch／X-Ray（`observability-setup` [Q1]／[Q2]=A）。本站以 staging 為量測對象、以後端結構化日誌與容器內量測腳本為證據來源。
> build-and-test 把全部延遲目標標為 **Unverified**（`construction/build-and-test/build-and-test-summary.md:228-230`「未量測……計畫無 performance-validation」），NFR1 的 ≥ 50 筆**人工標註集從未產生**（`requirements.md` NFR1 指派給 user-stories／build-and-test，repo 內查無該檔）。本站是這兩件事的實際落點。

## 已由上游或規則層定案、不重問

### Q1 — 流量型態（穩態／尖峰／突發）？

- A. staging 為單台、少數使用者；不做 production 容量規劃，只驗證「單人與小量併發下延遲目標是否成立」
- B. 以 production 流量模型規劃
- C. 其他

[Answer]: A <!-- 來源：`project.md` `## Scope Overrides`（production 不在範圍）；`org.md` `## Deployment`（單一 staging） -->

### Q2 — 延遲目標（分位數）？

- A. 照上游：首字 `NFR3` P50 ≤ 2 秒；路由 `NFR3.60` P50 ≤ 800 ms（`NFR3.66` 併發下仍成立）；閘道分類前段 `NFR13.1(a)` P50 ≤ 400 ms、分類後到首則內容 `NFR13.1(b)` P50 ≤ 300 ms；記憶 `NFR3.20` search P95 ≤ 150 ms；session `NFR3.40`／`3.41` P95 ≤ 20 ms
- B. 另訂
- C. 其他

[Answer]: A <!-- 來源：`construction/build-and-test/performance-test-instructions.md:14-23` 的目標表；`construction/intent-router/nfr-requirements/performance-requirements.md`（NFR3.60） -->

### Q3 — 最可能的瓶頸？

- A. 路由層的模型呼叫（`NFR3` 逐字：「這條預算幾乎全部被路由層的 LLM 呼叫吃掉」）；ADR-0024 改用 Jev 1.14 Decisions API 後實測單次 389–664 ms
- B. 資料庫
- C. 其他

[Answer]: A <!-- 來源：`inception/requirements-analysis/requirements.md` NFR3；ADR-0024 實測表 -->

## 需要使用者決定

### Q4 — NFR1 的人工標註集怎麼產生？

背景：NFR1 要求 ≥ 50 筆「一句話 → 應交辦的能力」配對，且以準確率與**反問率同時呈現**（`intent-router:NFR1.60`）。目前不存在。路由已改為 Jev 1.14（ADR-0024），準確率必須重新量測。

- A. 我依 `stories.md` 的 Given/When/Then 起草 60 筆（單一意圖三類各 15、多意圖 8、應反問 7），**先給你過目**，確認後才實跑
- B. 我起草後直接實跑，結果出來再一起檢視
- C. 本輪不量 NFR1，列為待辦

[Answer]: A <!-- 2026-11-16T14:28:47Z 使用者以選單選定「我起草、你先過目」 -->

### Q5 — 延遲怎麼量？

背景：staging 只有少數真人流量，現有日誌樣本太少。路由與準確率可以在 backend 容器內以容器自己的金鑰直接呼叫路由層量測——金鑰不離開容器、輸出只有彙總數字（準確率、P50／P95、錯誤數），也不會建立 session 或交辦任何工作。以一次性分支的 workflow 在 staging runner 上執行（比照先前的診斷 workflow）。每輪路由費用約 2.9e-05 美元（ADR-0024），60 筆 × 2 輪（逐筆＋5 併發）約 0.004 美元。

- A. 容器內直接打路由層（逐筆＋5 併發，得到 `NFR3.60`／`NFR3.66` 與 NFR1）；閘道與首字延遲（`NFR3`、`NFR13.1`）取現有 `turn_end` 日誌的實際分佈並標明樣本數
- B. 同 A，另外在容器內以專用測試帳號開 WebSocket 跑 30 輪完整對話量首字延遲（較真實，但會建立 session 與對話紀錄）
- C. 只看現有日誌，不主動送任何請求

[Answer]: B <!-- 2026-11-16T14:28:47Z 使用者以選單選定「加跑完整對話」 -->

### Q6 — 若 NFR1 或延遲首次實測未達標？

背景：`requirements.md` NFR1 的校正程序規定**不得自動改寫門檻**，由決策者三選一：(a) 接受實測值為新門檻並記錄理由、(b) 維持原值並要求改善後重測、(c) 判定門檻本身設錯並重定；且調 NFR1 的 80% 必須同時處理 FR1.7 的信心門檻 0.7。

- A. 結果出來後在本站核可關卡由你逐項裁決（照校正程序）
- B. 先預設 (b)：維持原值、列為待改善
- C. 其他

[Answer]: A <!-- 2026-11-16T14:28:47Z 使用者以選單選定「結果出來由我逐項裁決」 -->
