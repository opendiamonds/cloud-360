# Personas — Story D IaC 生成與安全交付

<!-- Stage: user-stories · Q5=A：Alex 主路徑（選圖／D1／下載）；Elena／Fiona 各 ≥1 Must。
     Round 1：Elena 掛 US2.1 模組樹；演示採多角色（種子無三角 edit）。 -->

## 上游輸入

- **requirements**（`../requirements-analysis/requirements.md`）
- **intent-statement**（目標客戶）
- **business-overview**（矩陣種子：D1／D2／D3 view／edit 分佈）
- **Q5=A**
- **Round 1 developer OBJECT**：無任一角色同時具 D1＋D2＋D3 `edit`

## 優先序

| 順位 | Persona | 典型 RBAC 對照（現行種子） | 本輪主要動作 |
|---|---|---|---|
| 1 | Alex | `Project_Architect`：D1 `edit`；D2／D3 `view` | 選圖／上傳、執行 D1、預覽、下載；**檢視**掃描／Secrets 步驟 |
| 2 | Elena | `Platform_Engineer`：D1／D2 `edit`；D3 `view` | 模組樹品質、切圖清空、可執行 D2、可下載 |
| 3 | Fiona | `Security_Reviewer`：D2／D3 `edit`；D1 `view` | 執行／閱讀掃描、執行 D3、下載前摘要、無權限入口 |

無對應故事權限者：入口 **disabled＋說明**；執行 API **403**（FR7）。端到端演示見 US6.2（多角色），**不**假設 Alex 一人可執行 D2／D3。

---

## P-1 Alex — 雲端架構師

- **情境**：架構圖已在 Workspace；需要變成可帶走的 Terraform／OpenTofu 草稿，且不要把密文寫死在檔裡。
- **職責**：維護架構圖；啟動 IaC 工作區；執行 **D1** 與下載；在授權允許下檢視後續步驟。
- **核心目標**：幾分鐘內拿到可預覽／可 zip 的 HCL；與有 D2／D3 `edit` 的同事協作完成掃描與改寫。
- **核心痛點**：Coming Soon；選圖不清；產物內嵌密鑰；誤以為 Architect 可單獨執行全柱。
- **使用場景**：點「生成 IaC」→ 自動帶入活躍圖或改選／上傳 → 執行 D1 → 檢視各步 →（協作）D2／D3 → 下載。
- **不做**：平台代 apply；寫入雲端 SM；在現行種子下單獨執行 D2／D3。

## P-2 Elena — 平台工程師

- **情境**：要標準化、模組化的 IaC 草稿，減少手寫開通。
- **職責**：檢視模組樹與變數／輸出是否可用；必要時以 D1 `edit` 重跑生成；可以 D2 `edit` 跑掃描。
- **核心目標**：多檔模組樹＋相容 HCL；切圖不會留下錯圖草稿。
- **核心痛點**：單檔難維護；切圖後草稿與脈絡不符。
- **使用場景**：主角故事 US2.1（模組樹預覽）、US1.3（切圖清空）；與 Alex 同一工作區。

## P-3 Fiona — 安全審查

- **情境**：產出必須附掃描可見性，且不明文留密。
- **職責**：執行／閱讀 findings；確認 HIGH／CRITICAL 在下載前被摘要；執行 D3 並確認改寫清單。
- **核心目標**：Advisory 下仍看得到風險；D3 改寫後下載物無明文；無權限時入口不可點成成功態。
- **核心痛點**：可跳過掃描執行就改 secrets（已由 Q3=A 禁止）；無權限卻看到可點入口。
- **使用場景**：US3.*、US4.1 執行、US5.2、US6.1；無權限時入口 disabled。
