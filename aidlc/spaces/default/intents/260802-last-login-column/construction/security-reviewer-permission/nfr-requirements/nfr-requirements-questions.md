# NFR Requirements — 釐清問題 · U4 `security-reviewer-permission`

> Stage: nfr-requirements（Construction 3.2）· Unit: `security-reviewer-permission`（kind: service）· Depth: Standard
> **成本揭露**：本題組 2 題。本站有 reviewer。
> **CONDITIONAL 判定**：**適用（EXECUTE）**。本單元是 requirements NFR-3（ADR-0006 四面向，hard constraint）的 **IAM 面向落點**，也是 NFR-4（授權矩陣雙向測試）的落點。

## 已由 3.1 定案、不重問

| 事項 | 來源 |
|---|---|
| 只更新不插入、在權限種子之後、條件式更新、四態記錄 | 3.1 的 R1〜R4 |
| 交易邊界：啟動流程的 try/finally 之後、自有連線、自行提交 | 3.1 Q2=A |
| 值已正確就不寫標記 | 3.1 Q3=A |
| 兩處預設值同步的全量比對測試 | 3.1 Q1=A |
| R2 的死角（部署前已被管理員動過則永不套用） | 3.1 承接上游 M1-a |

---

## Q1. high-risk action 條款是否適用

> `org.md ## Deployment` 逐字：「Any high-risk action — IaC apply, **IAM change**, destructive cloud operation — requires a plan + impact assessment + rollback path and a human approval gate before execution.」
> `project.md ## Mandated` 逐字：「ALWAYS 在任何 high-risk action（production write、IaC apply、**IAM 變更**）前先給 plan + impact + rollback，並通過 human approval gate。」
> 本單元變更權限矩陣，且本 intent 全程把它當作 ADR-0006 的 **IAM 面向**落點。

A. **適用，且把 plan／impact／rollback 寫進本站 artifact** — **（建議）**
   - 三項內容上游都已有，只是從未以這個形狀集中寫下。以 B1 這個 Bolt 的核可 gate 作為 human approval gate。
   - 成本極低，且一旦寫下，這條 hard 規則就不會在日後審計時突然變成缺口。

B. **不適用，但寫明區別理由** — 主張 `org.md` 該條的語境是雲端基礎設施。代價：同一個詞在 requirements 的四面向表與此處做不同解釋，需要很穩的理由，否則是雙標。

C. **適用，且要求獨立的核可關卡** — 代價：單一決策者、B1 本來就有 gate，額外關卡實質上是同一人再按一次。

D. Not yet defined
X. Other (please specify)

[Answer]: A

---

## Q2. rollback path 的定義

A. **管理員經介面撤銷** — **（建議）**
   - 這是設計**已經保證**的性質：撤銷後該列的最後異動者變成管理員帳號、不符補丁的更新條件，**後續重啟不會把它復原**。即時生效、不需部署、不需回滾程式碼。

B. **回滾部署（revert PR）** — 代價：回滾程式碼只能拿掉補丁與預設值，**不會**把已寫入資料庫的那一列改回關閉。對本單元而言，回滾部署**不等於**收回權限。

C. Not yet defined
X. Other (please specify)

[Answer]: A
