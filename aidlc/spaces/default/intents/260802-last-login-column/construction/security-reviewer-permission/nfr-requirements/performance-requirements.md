# Performance Requirements — U4 `security-reviewer-permission`

> Stage: nfr-requirements（Construction 3.2）· Unit: `security-reviewer-permission`（kind: service）
> 上游來源：`../functional-design/business-logic-model.md`、`business-rules.md`、`domain-entities.md`、`../../../inception/requirements-analysis/requirements.md`（下稱 requirements）、`../../../inception/application-design/components.md` C-7、`component-methods.md`、`decisions.md`、`services.md`。
> 問答定案：Q1=A（high-risk 條款適用）、Q2=A（rollback 為管理員經介面撤銷）。

## 本單元不在請求路徑上

**這是本單元與 U1 的根本差異**：U1 的邏輯在每個認證請求上執行，本單元**只在服務啟動時執行一次**。

## P-1 啟動期成本上界

| 面向 | 內容 |
|---|---|
| **執行次數** | 每次服務啟動**一次** |
| **資料庫操作** | 一次單列主鍵查詢，加上**至多**一次單列更新 |
| **為何是至多** | 依 3.1 的 R3，值已正確時不寫入；穩定狀態下每次啟動只有一次查詢 |
| **相對量級** | 同一啟動流程中，既有的權限種子在空表時寫入 308 列。本單元的成本比它小兩個數量級 |

**不訂啟動時間預算**：與 U1 同理，repo 無任何量測機制（見 U1 的 S1／S5），訂了無法驗證。此處以「相對於同流程既有工作的量級」表述，該比較不需儀表即可論證。

## P-2 不影響請求路徑

| 面向 | 需求 |
|---|---|
| **需求** | 本單元**不得**在任何請求路徑上執行 |
| **機制** | 觸發點為啟動流程，位於初始化區塊之後（3.1 Q2=A） |
| **後果** | 對線上請求的延遲影響為**零** —— 不是「很小」，是結構上不存在 |

## P-3 自有連線不影響請求期的連線池

| 面向 | 需求 |
|---|---|
| **需求** | 本單元自有的資料庫連線必須在啟動期取得並釋放，**不得**跨越到服務開始接受請求之後 |
| **依據** | 3.1 Q2=A 定案使用自行提交的連線區塊，該區塊在離開時關閉連線 |
| **為何重要** | 依 U1 的 S2，建立引擎時未帶連線池參數。啟動期若洩漏連線，會直接減少請求期可用的連線數 |

## 明確不承諾的事

| 事項 | 為何 |
|---|---|
| 啟動時間預算 | 無量測機制，無法驗證 |
| 「不影響啟動時間」這個結論 | 需要量測才能宣稱。本檔只論證成本的量級與相對比較 |
