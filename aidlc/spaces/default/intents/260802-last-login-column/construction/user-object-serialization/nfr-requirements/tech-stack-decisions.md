# 技術選型決定 — user-object-serialization（U2）

> **上游輸入**：本單元的 `../functional-design/business-logic-model.md`（Revision 1 的 envelope 與分頁查詢邏輯）、`../functional-design/business-rules.md`（**BR-P1〜BR-P5**：分頁契約、`total` 獨立計數、`ORDER BY id` 保留、超出範圍非錯誤、不接受非分頁參數）、`../functional-design/domain-entities.md`（`UserListPage` 的四欄皆必填無預設值）。本檔的每一條 NFR 皆為上述功能規則的非功能面展開，不新增行為。

## 本單元不引入任何新的執行期依賴

AD-5「不新增服務、不改變架構風格、不引入新依賴」在本單元**維持成立**。分頁以既有的 ORM 查詢方法（`offset`／`limit`／`count`）與既有的 Web 框架查詢參數機制實作。

## T-1 為何用框架原生的查詢參數約束，而不是自訂驗證

見 `security-requirements.md` S-2 與 application-design 的 AD-11。四個理由：零自訂程式碼、非法值結構上到不了查詢層、約束進入 OpenAPI 規格因此被兩道漂移 gate 覆蓋、錯誤回應可觀察且不洩資料。

**實測驗證**（不是推論）：以最小可重現的探針確認四件事 —— 合法值回 200；`page=0`／`page=-1`／`page=abc`／`page_size=1000` 皆回 422；422 回應不含帳號資料；`minimum`／`maximum` 確實出現在 OpenAPI 規格的 parameter schema 中。

## T-2 `fastapi` 與 `pydantic` 的精確等值釘選（本 repo 的局部例外）

| 項目 | 內容 |
|---|---|
| 決定 | `requirements.txt` 對這兩支採 `==` 精確釘選 |
| 理由 | OpenAPI 規格輸出在同一組版本下是**位元決定性**的，但**跨版本會飄**。本 repo 的 12 支依賴全部未 pin、CI 每次重新解析最新版 —— 不釘會讓規格漂移 gate 在**完全無關的 PR** 上變紅，且該紅燈與真漂移在訊號上不可區分 |
| 為何不用 `~=` | 相容釋出形式仍會在次版本線上浮動，而觀測到的差異正是跨次版本產生的。形式選錯等於沒釘 |
| 代價 | 形成「全 repo 未 pin」的局部例外；升版這兩支時必須在**同一個 PR 內**重新 dump 規格檔並重產型別檔 |
| 附帶收益 | `team.md ## Code Style` 已記載「CI／Docker build／staging 部署三處各自解析最新版、可能彼此不同」為既有風險 —— 本項是對它的局部改善 |

## T-3 offset 分頁而非鍵集分頁

| 方案 | 判定 |
|---|---|
| **offset**（採用） | 支援**跳至特定頁次**，這是已核可的頁碼式控制的前提。實作為既有 ORM 方法，零新概念 |
| 鍵集（keyset） | 深頁效能較佳，但**不能跳頁** —— 直接推翻 rough-mockups 已核可的決定（該站逐條否決游標式，理由正是「不能跳頁，回到先前看過的帳號只能逐頁往回」，那是稽核者複核帳號的實際動作） |

深頁效能的已知代價記於 `scalability-requirements.md` S-1；以本系統的規模與使用型態判定可接受。

## T-4 不引入快取

分頁回應**不得**被快取為長期資料：`last_activity_at` 每 5 分鐘可能變動，`is_overdue` 是隨當下時間變動的衍生值 —— 快取一份「昨天算出來的逾期旗標」正好破壞本 intent 的核心價值。本單元不引入快取層，也不在回應上宣告可快取。
