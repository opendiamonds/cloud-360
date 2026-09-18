# RAID Log — 帳號最後活動時間（稽核欄位）

<!-- Stage: feasibility（Ideation 1.3）· 來源標籤定義見 feasibility-questions.md 的 ## Sources。
     Likelihood／Impact 採 Low／Medium／High 三級；處置採 mitigate／avoid／accept／transfer。 -->

## 上游輸入

- 風險脈絡承襲 intent-capture 的 **intent-statement**（`../intent-capture/intent-statement.md`）；其 assumption A4（權限擴張與最小權限的張力）在本 log 落地為 R3 的正式風險處置。
- market-research 已依 scope 跳過，其可選產出 **competitive-analysis**、**market-trends**、**build-vs-buy** 不存在（scope 設計使然），無市場面風險輸入。

## Risks（風險）

| # | 風險 | Likelihood | Impact | 處置 | 說明 | Source |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | 「任何有效活動都記錄」使每個帶憑證的請求都可能觸發寫入，形成效能與寫入負載風險 | Medium | Medium | mitigate（設計階段） | 緩解手段（節流、彙整、非同步）屬設計決定，本階段不預作；設計階段必答 | [Q1] |
| R2 | 部署時誤用「重跑整份資料庫初始化腳本」，導致線上角色權限設定被重置 | Low | High | avoid | 已選定不重跑整份腳本的套用路徑；部署文件須明載本次變更的正確套用手段 | [Q3] [code:C5] [memory:M1] |
| R3 | 稽核角色取得整頁檢視權限，接觸面大於稽核欄位本身，與最小權限原則存在張力 | 已發生（決策既定） | Medium | **accept** | 依 [Q7] 決議：風險接受記入本 log，gate 核可即為證據；intent 既定決策不重開 | [Q7] [intent:Q10/Q12] [memory:M4] |
| R4 | 語意定錨為「最後活動」後，若稽核方日後堅持「最後登入」語意，需回頭重新定錨並調整已上線行為 | Low | Medium | accept＋monitor | 稽核方即決策者本人（單一決策者），風險有限；若情境改變，回到 [Q1] 重新定錨 | [Q8] [Q1] |

## Assumptions（假設）

| # | 假設 | 驗證時點 | Source |
| --- | --- | --- | --- |
| A1 | 「超過 N 天未活動」的門檻 N 未定義；成功指標在 N 決定前不可完整驗證 | requirements-analysis | [intent:Q3] |
| A2 | 活動資料保存上限存在，但值未定；單一欄位覆寫模式下的清除語意亦未定義 | requirements-analysis | [Q4] |
| A3 | 內部平台，無外部法規框架適用於活動時間資料（未經法務獨立確認） | 若適用情境改變時重驗 | [Q4] |
| A4 | 受控測試（比對任何活動的時刻）足以驗證正確性，不需第二資料來源 | build-and-test 階段實證 | [Q6] [Q6a] |

## Issues（議題）

| # | 議題 | 狀態 | Source |
| --- | --- | --- | --- |
| I1 | 上線前的歷史空窗為既成事實（無可回填來源） | 已解（接受空窗，空值顯示「無紀錄」） | [Q2] [code:C1] |

## Dependencies（依賴）

| # | 依賴 | 方向 | Source |
| --- | --- | --- | --- |
| D1 | `schema_rbac.sql` 與 `DEPLOY.md` 的同步更新（blocking）是相關 Construction／部署階段標示完成的前置 | 本功能 → 部署資產 | [memory:M1] [Q3] |
| D2 | N 值與保存上限值需在 requirements-analysis 定案，成功指標與清除語意才可驗證 | 本功能 → requirements-analysis | [intent:Q3] [Q4] |
| D3 | 既有環境的結構補齊依賴服務啟動時的自動機制；部署後服務必須完成一次重啟，變更才生效 | 本功能 → 既有部署慣例 | [Q3] [code:C4] |
