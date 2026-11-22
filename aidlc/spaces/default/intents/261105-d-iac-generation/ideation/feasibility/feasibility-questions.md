# Feasibility Questions

上游：`intent-statement`、`competitive-analysis`、`market-trends`、`build-vs-buy`；專案規則含「D1／D2／D3 各一 agent」。

---

## Q1. 本 intent 必須整合的既有系統／介面有哪些？

A. Workspace 架構圖（既有圖資產）＋與 A／C 相同的 LangGraph／UI 工作區
B. 另含 RBAC（D1／D2 權限種子）、OpenAPI／前端型別管線
C. 另含外部掃描 CLI（Checkov／tfsec／Trivy 等）與雲端 Secret Manager API
D. A＋B＋C 皆須整合
E. Not yet defined
X. Other (please specify)

[Answer]: D

---

## Q2. 合規／監管要求（PCI、HIPAA、SOC2、資料駐留等）對本輪的約束？

A. 無額外外部合規專案；沿用既有 ADR-0006 security baseline（IAM、encryption、network、audit）即可
B. 有明確合規標的（請在 Other 說明框架與證據要求）
C. 僅內部政策：Secret 不得進版控／草稿明文；掃描結果需可審核
D. A＋C
E. Not applicable / Not yet defined
X. Other (please specify)

[Answer]: A

---

## Q3. 團隊技術棧與技能是否足以支撐 Build（三 agent＋掃描／SM 整合）？

A. 足夠：已有 LangGraph（A／C）、FastAPI、React／Vite、unittest／Playwright、自架部署
B. 足夠但掃描／SM 整合經驗不足，需 spike 或外援
C. 不足：LangGraph 多 agent 拆分或 IaC 產出品質有明顯風險
D. Not yet defined
X. Other (please specify)

[Answer]: A

---

## Q4. 時程與預算約束？

A. 無硬性外部 deadline；依 feature 正常節奏交付 D1＋D2＋D3
B. 有硬性日期／人力上限（請說明）
C. 可分期：若風險高可先 D1＋D2，D3 延後（注意與 intent 一次交付三者可能衝突）
D. Not yet defined
X. Other (please specify)

[Answer]: A

---

## Q5. 組織面阻礙（變更凍結、並行優先、核准瓶頸）？

A. 無已知阻礙
B. 有（請說明）
C. 決策者尚未識別（承接 intent-capture 假設）可能拖慢範圍收斂
D. Not identified
X. Other (please specify)

[Answer]: A

---

## Q6. 目前使用中的雲端／帳號與 IaC 工具現況？

A. 多雲（AWS／GCP／Azure）架構圖已存在於產品；本機／staging 為自架，**不**對雲端 production 代 apply
B. 需綁定特定雲帳號才能做掃描或 SM 整合（請說明）
C. 團隊已標準化 Terraform／OpenTofu；掃描工具尚未統一
D. A＋C
E. Not yet defined
X. Other (please specify)

[Answer]: A

---

## Q7. 技術可行性總判斷（初步）？

A. **可行**：在既有 A／C 框架上拆三 agent（D1／D2／D3）並整合掃描／SM，風險可控
B. **有條件可行**：需先解決列出的關鍵依賴／spike（請在 Other 點名）
C. **不可行／應縮範圍**：請說明
D. Not yet defined
X. Other (please specify)

[Answer]: A

---

## Consolidated Summary Confirmation

依你的回答整理如下：

- **整合面**：架構圖＋A／C LangGraph／UI、RBAC／OpenAPI 管線、外部掃描 CLI 與雲端 Secret Manager API 皆須整合。[Q1]=D
- **合規**：無額外外部合規專案；沿用 ADR-0006 security baseline。[Q2]=A
- **技能**：團隊棧足夠（LangGraph A／C、FastAPI、React、測試與自架部署）。[Q3]=A
- **時程／預算**：無硬性外部 deadline；正常節奏交付 D1＋D2＋D3。[Q4]=A
- **組織**：無已知阻礙。[Q5]=A
- **雲端現況**：多雲架構圖在產品內；本機／staging 自架；不對雲端 production 代 apply。[Q6]=A
- **總判**：可行 — 既有框架拆三 agent 並整合掃描／SM，風險可控。[Q7]=A

Does this all look correct before I generate the artifact?

- Looks correct
- Request changes

[Answer]: Looks correct
