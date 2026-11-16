# Personas — C1 估價表上傳工作區（後補故事）

<!-- 補跑 user-stories：原 scope 將 user-stories SKIP，改以 FR fallback。
     本檔為 PR 契約補件，角色沿用 baseline／260819-cost-finops 的 Alex／David。 -->

## 上游輸入

- **requirements**（`../requirements-analysis/requirements.md`）— 尤其 FR1.7、FR12、FR13
- **baseline personas**（`260802-default/.../personas.md`）
- **cost-finops personas**（`260819-cost-finops/.../personas.md`）

## 優先序

| 順位 | Persona | RBAC | 本補件主要動作 |
|---|---|---|---|
| 1 | Alex | `Project_Architect`（C1 view／edit） | 填選填工作負載、開官方估價教學、上傳後看規格描述 |
| 2 | David | `FinOps_Analyst`（C1 view／edit） | 同上；關注明細規格是否可讀、建議是否吃到工作負載上下文 |

無 C1 `view` 者：看不到 `/cost` 入口；本補件不為其發明利益。

---

## P-1 Alex — 雲端架構師

- **情境**：要用官方計算機匯出的估價表上傳到 `/cost`，並讓 AI 建議知道這套系統的用途與預算限制。
- **本補件在意**：選填工作負載表單、三雲官方估價教學彈窗、明細規格欄的人類可讀描述。
- **核心痛點**：不知道各雲該匯出哪種格式；SKU 代碼看不懂；建議忽略業務上下文。
- **不做**：帳單／Cost Explorer 整合（ADR-0018 仍禁）。

## P-2 David — FinOps 分析師

- **情境**：審核上傳後的明細與 AI 建議是否可用於對內說明。
- **本補件在意**：規格欄優先顯示目錄描述、原始 SKU 仍可追溯；建議 prompt 含工作負載上下文。
- **核心痛點**：規格只顯示亂碼 SKU；缺金鑰時上傳整批失敗。
