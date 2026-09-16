# Constraint Register — AI-DLC 與 GitHub Projects 的進度同步

<!-- Stage: feasibility（Ideation 1.3）· 來源標籤定義見 feasibility-questions.md 的 ## Sources。 -->

## 上游輸入

- 必要上游為 intent-capture 的 **intent-statement**（`../intent-capture/intent-statement.md`）；其 `## Initial Scope Signal` 的邊界約束是本登錄表的起點。
- market-research 依 scope 設計跳過，其可選產出 **competitive-analysis**、**market-trends**、**build-vs-buy** 不存在，本登錄表不依賴市場面輸入。

## 技術約束

| # | 約束 | 性質 | 來源 |
| --- | --- | --- | --- |
| C-T1 | 平台預設的工作流程憑證對看板讀寫皆無效，且失敗形式是回傳空清單而非報錯 | 不可協商（平台行為） | [ext:E1] |
| C-T2 | CI 端必須以組織擁有的應用程式身分認證，其識別碼與私鑰以框架規定的變數與 secret 名稱承載 | 已定案 | [Q1] [ext:E2] |
| C-T3 | 遠端只看得到已推送的進度紀錄；本機尚未推送的 stage 推進對 CI 不可見 | 不可協商（架構事實） | [repo:R1] [repo:R2] |
| C-T4 | 設定看板欄位必須指名既有的追蹤項目編號，無編號即無法寫入 | 不可協商（框架契約） | [ext:E3] |
| C-T5 | 框架的看板更新輸出有預設的單次操作次數上限 | 可設定但有上限 | [ext:E3] |
| C-T6 | 狀態欄位維持既有 6 個選項不變動；本 intent 只使用其中三格 | 已定案（可改但選擇不改） | [Q4] [repo:R6] |
| C-T7 | 不得以 repo 內新增的實作程式承載本機制；一律以代理式工作流程或 Actions 工作流程承載 | 硬性規則 | [memory:M1] |
| C-T8 | 同步延遲上限為推送後 5 分鐘；PR 事件的寫入優先於推送事件 | 已定案 | [Q9] |
| C-T9 | 寫入前必須回讀目標項目並與預期比對，不符即中止 | 已定案 | [Q10] |

## 組織與流程約束

| # | 約束 | 性質 | 來源 |
| --- | --- | --- | --- |
| C-O1 | 單一決策者；其他 repo 協作者為受影響方，告知即可，不需取得同意 | 已定案 | [intent:Q5] |
| C-O2 | 建立與安裝組織層應用程式需要組織管理權限，且只能由人工在網頁介面完成 | 外部依賴 | [Q1] |
| C-O3 | 每個 intent 的 construction 必經 `tcms-test-cases` 且為 blocking：需覆蓋盤點、手動測案、實際跑綠的自動化（含突變驗證）與同步報告 | 硬性規則 | [memory:M3] |
| C-O4 | 既有 CI 四道關卡不得因本變更而破壞；新增的工作流程須與其並存 | 硬性規則 | [memory:M4] |
| C-O5 | 分支命名、commit 與 PR 標題須符合團隊規範（branch 用英文 type、commit 用中文 type） | 硬性規則 | `team.md ## Way of Working` |
| C-O6 | 本 repo 從未使用過任何 GitHub API 憑證；私鑰保管、輪替與撤銷皆無既有慣例可沿用 | 缺口 | [repo:R4] |

## 法規與政策約束

| # | 約束 | 性質 | 來源 |
| --- | --- | --- | --- |
| C-R1 | 無適用的外部法規框架：本機制不處理個人資料、健康資料或持卡資料，不涉及資料落地或跨境傳輸 | 判定為不適用 | 本階段判定（見 feasibility-assessment 的四面向表） |
| C-R2 | ADR-0006 security baseline 為 hard constraint，四面向須逐項判定並附理由 | 硬性規則 | [memory:M2] |
| C-R3 | 不得於版控中留存任何憑證字串；亦不得新增 path part 含 `prod`／`production`／`secrets` 的檔案 | 硬性規則（CI 會擋） | `project.md ## Forbidden` |
| C-R4 | 雲端供應商 production 環境與 environment-specific secrets 不在專案範圍內 | 範圍邊界 | `intent-statement ## Initial Scope Signal` |

## Assumptions & Open Questions

- C-O2 的組織管理權限假設成立但未經實際嘗試；若組織政策限制第三方應用程式安裝，C-T2 需改回個人憑證，並連帶推翻 [Q1] 的解耦目的。 [assumption]
- C-T5 的實際上限值與超限時的行為（截斷、報錯或靜默略過）尚未確認。 [assumption]
- C-T2 所依賴的憑證鑄造行為是否實際帶有組織層看板寫入權未經驗證，見 feasibility-assessment 的 R-7。 [assumption]
- C-O3 與 C-T7 在本 intent 相交：blocking 的自動化要求與「不得以 repo 內程式承載」的禁令必須同時滿足，落點已由 [Q6] [Q10] 指定，但其產物是否構成 `tcms-test-cases` 所認可的「實際跑綠的自動化腳本」尚未與該 stage 的驗證關卡對照確認。 [assumption]
