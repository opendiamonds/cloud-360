# 安全設計 — `U7 hierarchy-service`

## 一、安全設計已完成，但落點在 `functional-design`

本單元的安全設計**不在本檔**，且這是刻意的：授權是**行為規則**，
寫在規則層才會被實作與測試引用。完整落點見
`construction/hierarchy-service/nfr-requirements/security-requirements.md` §一 的
對照表——12 條規則（`BR1.1`–`BR1.5`、`BR5.6`、`BR6.1`–`BR6.6`）
＋ `functional-spec.md` §七之三 的 ADR-0006 四面向判定表。

本站**不複寫**它們。複寫會製造第二份真實來源，而 `team.md` 的「單一真實來源」
規則明訂：同一份事實已存在於產出中時，新增第二份物化前必須先確認是否有既有
來源可直接使用；無法避免時，新增副本的同一個 PR 必須一併新增鎖住兩者一致的
測試。本站無法提供那個測試，故不新增副本。

## 一之二、契約來源與本站須設計的兩項

授權模型的每一條約束都來自 `contract-summary.md` 的契約 `K-07`
（`sole_entry`、`consumers.in_process`、`identity_passing`、`resource_context`、
`on_denied`、`hard_rule`、`residual_gap`），不是本站的發明；
`contract-summary.md:1551` 的消費端擴充表是四個同進程呼叫端的來源。

上游 `security-requirements.md` §四 另列出兩項**本站須設計**的契約閘門需求：
`NFR5.1`（第五個 path 落地後須進 `openapi.json`）與
`NFR5.2`（409 須顯式宣告 `responses={409: {...}}`）。
兩者的設計落點都是 `logical-components.md` 的 `hierarchy_router` 列——
409 的來源是 facade 拋出的 `HierarchyConflictError`（`BR6.6`），
由 router 轉譯並在 decorator 顯式宣告。下方邊界圖已標明這條轉譯分工。

## 二、本站的唯一增量：把授權模型畫成一張呼叫邊界圖

```
   HTTP 請求                        同進程呼叫端
       │                     ┌──── U10 session-store
       ▼                     ├──── U12 work-orchestrator
  FastAPI router             ├──── U19 membership-service
  （取身分 → 呼叫 facade     ├──── U20 requirement-field-service
    → 轉譯例外；不得自行     │
    呼叫底層 service）       │
       │                     │
       └──────┬──────────────┘
              ▼
    ┌─────────────────────────┐
    │  HierarchyFacade        │  ← K-07 sole_entry：唯一授權入口
    │  ・principal 為第一參數 │     BR1.2（禁藏 payload）
    │  ・K2 判定在此          │     BR1.1（不在 router）
    │  ・principal 不可偽造   │     BR1.4（型別層事實）
    │  ・列舉型 → BR6.1 範圍  │
    │  ・判定支援型 → BR6.4   │     最小欄位、同進程、呼叫端自檢
    │  ・寫入 → BR6.5 擁有者  │
    │  ・拒絕 → HierarchyForbidden（**不是** HTTPException）
    └───────────┬─────────────┘
                ▼
         底層 service 層
    （**無第二道角色檢查** —— BR1.3 的誠實宣告；
      故 BR1.5「無任何單元繞過 facade」是唯一防線，
      而它本單元無法自驗 → OPEN-H2）
```

**文字 fallback**：HTTP 請求與四個同進程呼叫端都必須經 `HierarchyFacade`；
facade 內完成 `K2` 判定與列範圍判定後才呼叫底層 service；底層 service 沒有
第二道檢查，故「沒有人繞過 facade」是整個授權強度的前提，而驗證落點在
`U10`／`U12`／`U19`／`U20` 各自的 `code-generation`（`OPEN-H2`）。

## 二、判定的依據與失效條件

本面向**不適用**的部分（無新 pattern）綁在上游 `nfr-requirements` 的對應判定上，不是獨立產生的：
該站把本面向判為**不適用且無新增需求**，故本站**沒有待設計的 pattern**。
`nfr-design` 的 condition 逐字為「NFR Requirements was executed and
**NFR patterns need design**」——前半成立（上游已執行，非 skip），後半不成立。

失效條件同上游：把本單元拆成獨立進程、引入任何外部呼叫、
或列舉端點的資料規模由「單一使用者自有的專案數」變成「全體使用者的專案數」。
任一成立時本站須重開。
