# Deployment Pipeline — 問題檔

> 本站以「精簡版」執行，比照已核可的 ci-pipeline 站：**不改任何部署設定**，只依證據記錄現有 CD，並為這一次發佈寫出可照做的前置與回滾 runbook。
> stage 檔五題中有四題是 repo 與規則層已定案的事實，依 `project.md`「上游已定案事項不重問」不向使用者重問，每題附可引用的來源。第 4 題（升版窗口內的回滾處置）是 `DEPLOY.md` §5.4 明文要求「請記下採用哪一個」的人為決定，交使用者裁決。

## 已由 repo／規則層定案、不重問

### Q1 — 部署策略？

- A. deploy-on-merge 到單一 staging，就地 `docker compose up -d --build`（無 blue/green、無 canary）
- B. blue/green
- C. canary
- D. rolling

[Answer]: A <!-- 來源：`org.md` `## Deployment`「We deploy on merge to staging」；`.github/workflows/deploy.yml`「Build and start the stack」步驟 -->

### Q2 — 環境晉升關卡？

- A. 本機 dev → CI 短生命週期 stack（`ui-regression`）→ staging（`192.168.10.10`，經 Cloudflare Tunnel 為 `cloud360.danniel.cc`）；production 不在範圍
- B. dev → staging → prod
- C. 只有 prod
- D. 其他

[Answer]: A <!-- 來源：`project.md` `## Scope Overrides`（雲端供應商 production 不在範圍，需新 ADR）；ADR-0007；`scripts/validate_env_contract.py` 檔頭的三環境表 -->

### Q3 — production 的核可流程？

- A. 不適用：production 不在範圍；staging 的核可即 PR 合併進 `ut`
- B. 需要人工核可 job
- C. 需要變更委員會
- D. 其他

[Answer]: A <!-- 來源：`project.md` `## Scope Overrides`；`org.md` `## Deployment`「There is no production deploy target to gate」 -->

### Q5 — feature flag 策略？

- A. 不使用 feature flag 服務；本機限定行為以 `APP_ENV`／`LLM_PROVIDER` 環境變數控制，部署設定不得出現本機限定值（`validate_env_contract.py` 鎖住）
- B. CloudWatch Evidently
- C. AppConfig
- D. 其他

[Answer]: A <!-- 來源：repo 內無任何 feature flag 服務的依賴；`backend/services/llm_provider.py` 的 `APP_ENV` 限定；`scripts/validate_env_contract.py` -->

## 需要使用者決定

### Q4 — 本次 PG 16 → 18 升版窗口內，自動回滾怎麼處理？

背景：`deploy.yml` 的 `rollback` job 只還原**程式碼**（last-good commit），**不還原 PGDATA**。升版窗口內一旦部署失敗觸發自動回滾，會讓上一版的 PG 16 映像對著已升級為 PG 18 的資料 volume，postgres 會拒絕啟動。`DEPLOY.md` §5.4「三條排序不變量」第 2 條列出三個處置，並要求記下採用哪一個；目前沒有任何機械檢查。

- A. 窗口內**暫時停用** rollback job（另一個 PR 停用，窗口結束後再以 PR 復原，並確認復原後第一次部署 rollback 已武裝）
- B. 維持現況：讓它只還原程式碼，接受窗口內回滾會造成 PG 版本不相容，出事時改走 runbook 的手動回滾
- C. 窗口內改為**人工部署**（不靠合併自動部署；合併前先手動在主機上部署並驗證）

[Answer]: B <!-- 2026-11-14 使用者以選單選定「B 維持現況，走手動回滾」。依 DEPLOY.md §5.4 不變量 2 記錄：本次升版採用的 rollback 處置 = b -->

