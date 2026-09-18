# Tech Stack Decisions — U4 `security-reviewer-permission`

> Stage: nfr-requirements（Construction 3.2）· Unit: `security-reviewer-permission`（kind: service）
> 上游來源：`../functional-design/business-logic-model.md`、`business-rules.md`、`domain-entities.md`、`../../../inception/requirements-analysis/requirements.md`（下稱 requirements）、`../../../inception/application-design/components.md` C-7、`component-methods.md`、`decisions.md`、`services.md`。
> 問答定案：Q1=A（high-risk 條款適用）、Q2=A（rollback 為管理員經介面撤銷）。

## 本單元的技術決策：零新增

**本單元不引入任何新的函式庫、框架、服務、工具或資料庫物件。**

| 面向 | 決策 | 依據 |
|---|---|---|
| 新增外部依賴 | **無** | `decisions.md` AD-5 |
| **新增資料庫物件** | **無** | 3.1 定案以**既有的最後異動者欄位**作為套用標記。上游初版曾要求新增一張標記表，被否決 |
| 遷移工具 | **不引入** | `decisions.md` AD-3 已將其列為獨立技術債。本單元沿用既有的啟動期補丁形狀 |
| 資料庫存取方式 | **自行提交的連線區塊**，比照既有三個補欄補丁的形狀 | 3.1 Q2=A |
| 測試框架 | 沿用既有內建測試框架 | `team.md ## Testing Posture` |

## 「不新增標記表」這個決策的價值（承 3.1）

新增一張表會連帶觸發三項成本，全部因改用既有欄位而消滅：

| 若新增表 | 成本 |
|---|---|
| requirements C-4 | 觸發「新增表」的 **blocking** 部署資產同步義務（schema 檔與部署文件） |
| 建表路徑 | 需要**另一個**補丁負責建立該表，而那個補丁自己也需要順序契約 |
| 清單維護 | 服務拓樸與元件依賴兩份清單都需更新 |

**在既有欄位已足夠的前提下，那些都是不必要的成本。**

## 本單元依賴但不改變的既有技術事實

| 事實 | 對本單元的意義 |
|---|---|
| 建立引擎時未帶連線池參數 | 啟動期的自有連線必須在區塊結束時釋放（見 `performance-requirements.md` P-3） |
| 初始化區塊的例外不重新拋出 | 本單元**必須**放在該區塊之後並自行提交（見 `reliability-requirements.md` R-2） |
| 種子資料模組的「勿手改」檔頭已失效（產生腳本不存在） | 本 intent 以**手動修改**同步兩處，並以 308 列全量比對測試鎖住一致性（3.1 Q1=A） |
| 依賴完全未釘版本、無鎖定檔 | 既有狀態；本單元不新增依賴，因此**不擴大**該問題，但也不修復它 |

## 明確不引入的東西

| 事項 | 為何 |
|---|---|
| 分散式鎖／領導者選舉 | 見 `scalability-requirements.md` S-2：競爭無實質後果 |
| 功能旗標系統 | 本單元的「開關」就是權限矩陣本身；引入第二套開關機制會製造兩個真實來源 |
| 告警／指標工具 | 見 `reliability-requirements.md`：以錯誤級日誌承接，與 AD-5 一致 |
