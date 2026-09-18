# Tech Stack Decisions — U1 `backend-activity-policy`

> Stage: nfr-requirements（Construction 3.2）· Unit: `backend-activity-policy`（kind: service）
> 上游來源：`../functional-design/business-logic-model.md`、`business-rules.md`、`../../../inception/requirements-analysis/requirements.md`（下稱 requirements）、`../../../inception/application-design/component-methods.md`、`decisions.md`。
> 問答定案：Q1=A（設計上界）、Q2=A（不額外加密，寫明理由）、Q3=A（**僅「不要求告警」部分生效**；級別沿用 3.1 Q2=A 的警告級，見 R-1 的更正說明）。事實查證 S1〜S5 見 `nfr-requirements-questions.md`。

## 本單元的技術決策：零新增

**本單元不引入任何新的函式庫、框架、服務或工具。**

| 面向 | 決策 | 依據 |
|---|---|---|
| 新增外部依賴 | **無** | `decisions.md` AD-5（不新增外部依賴）。C-8 的型別產生工具是該原則的**唯一具名例外**，且屬 U5，不屬本單元 |
| 資料庫存取層 | **沿用既有的物件關聯對應層** | 既成事實；本單元只更新既有表的既有欄位 |
| 時間處理 | **沿用標準函式庫** | 依 S1，repo 無任何日期函式庫；本單元的需求（取得當下時刻、補時區、比較）標準函式庫已足夠 |
| 測試框架 | **沿用既有的內建測試框架 + property-based 函式庫** | `team.md ## Testing Posture` 已載明；本單元的純函式判定正是既有 property-based 實踐的同型落點 |
| 觀測性工具 | **不引入** | 見 `reliability-requirements.md` R-1 的理由 |
| 快取 | **不引入** | 見 `scalability-requirements.md` S-3 |
| 排程／佇列 | **不引入** | 見 `scalability-requirements.md` 的不適用判定表 |

## 為何「零新增」在此是實質決策而非預設

本單元有兩個地方**看起來**需要新工具，實際不需要：

| 誘因 | 為何不需要 |
|---|---|
| 節流可以用快取或速率限制中介層做 | 節流的狀態**就是要寫入的那個欄位本身**。引入外部狀態會製造一致性問題，而不解決任何問題 |
| 失敗可偵測性可以用指標函式庫做 | Q3=A 已定案以錯誤級日誌承接。引入指標函式庫需要同時引入收集與展示端，那是完整的觀測性專案 |

## 已釘選的既有技術事實（本單元依賴但不改變）

| 事實 | 對本單元的意義 |
|---|---|
| 建立引擎時未帶連線池參數（S2） | 本單元因此**必須**沿用請求既有的工作階段，不另開連線（見 `performance-requirements.md` P-3） |
| 測試路徑走記憶體內資料庫、時間值讀回不帶時區 | 本單元的時區正規化契約因此是**必要**的，不是防禦性程式碼 |
| 依賴完全未釘版本、無鎖定檔 | 這是 repo 的既有狀態（`team.md` 已如實記載為待補承載機制）。本單元不新增依賴，因此**不擴大**這個問題，但也不修復它 |

最後一列如實記載：本單元對該既有風險是**中性**的 —— 既不加劇也不改善。
