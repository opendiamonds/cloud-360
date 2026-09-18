# Story Generation Plan — User Stories Restructuring

> AIDLC Inception Phase → User Stories Stage
> Branch: `doreen/docs/user-stories-restructure`

### 執行摘要

將 `core-pillars.md`（26 個 stories、9 個 pillars）拆分為：
- `personas.md`：角色定義文件
- `stories.md`：user story 內容文件

### 現有 Persona 分析（來自 core-pillars.md）

| Persona ID | 角色名稱 | 出現的 Story |
|---|---|---|
| P1 | 雲端架構師 / Cloud Architect | A1, A2（implied）, A3, E2, H1 |
| P2 | SRE | A2, B2, C2, E1, F1, F3, H2, I5 |
| P3 | 技術決策者 / Technical Decision Maker | B1 |
| P4 | FinOps 分析師 / FinOps Analyst | C1 |
| P5 | 架構師 / Architect | C3 |
| P6 | 平台工程師 / Platform Engineer | D1, F2, G3, I1 |
| P7 | 安全性審查員 / Security Reviewer | D2, G1, G3（implied）, I3 |
| P8 | 運維負責人 / Operations Lead | F3 |
| P9 | AI 平台操作員 / AI Platform Operator | I2 |
| P10 | 平台管理員 / Platform Admin | G2 |
| P11 | 平台擁有者 / Platform Owner | H3, I4 |

---

## 執行計畫（Checklist）

### Phase 1：釐清問題（等待使用者回答）

- [x] **Q1**：Persona 文件格式 -> **C) 豐富格式**
- [x] **Q2**：Stories 文件的排列方式 -> **D) 混合：保留 Pillar 分組，但標注 persona**
- [x] **Q3**：Persona 描述深度 -> **C) 完整定義（含工作流程、使用頻率）**
- [x] **Q4**：既有 Persona 補充或調整 -> **B) 接受合併（P1+P5, P6+P9）＋新增 Engineering Manager 與 End User**
- [x] **Q5**：語言與雙語要求確認 -> **A) 完整雙語（## 中文版 + ## English Version）**

### Phase 2：產出 personas.md

- [ ] 整理所有 persona（P1~P11）
- [ ] 為每個 persona 撰寫：名稱、職責、目標、痛點
- [ ] 加入中英雙語區塊

### Phase 3：產出 stories.md

- [ ] 依核准的排列方式搬移 26 個 user stories
- [ ] 標記每個 story 對應的 persona
- [ ] 加入中英雙語區塊

### Phase 4：清理

- [ ] git rm `core-pillars.md`
- [ ] 更新 README.md / aidlc-state.md 中的連結
- [ ] 更新 scripts/validate_repo_contract.py 的 REQUIRED_FILES（若 core-pillars.md 在列）
- [ ] 執行 `python scripts/validate_repo_contract.py` 確認通過

---

## 問題清單（請填入 [Answer]: 後面）

### Q1：Persona 文件格式

每個 persona 應包含哪些欄位？

A) 簡單格式：`名稱 + 職責描述`（1–2 句話）
B) 標準格式：`名稱 + 職責 + 核心目標（3 條）+ 核心痛點（3 條）`
C) 豐富格式：`名稱 + 職責 + 目標 + 痛點 + 技術背景 + 使用場景`
D) 其他格式（請說明）

[Answer]:

---

### Q2：Stories 文件排列方式

26 個 stories 在 stories.md 中如何組織？

A) 依 Pillar 分組（A~I，維持現有結構，只是搬到新檔案）
B) 依 Persona 分組（同一角色的 stories 放在一起）
C) 依優先級排列（核心功能優先，輔助功能次之）
D) 混合：保留 Pillar 分組，但每個 story 標注對應 persona

[Answer]:

---

### Q3：Persona 描述深度

目前 core-pillars.md 中 persona 只是 story 裡的「身為 X」，沒有獨立描述。產出 personas.md 時：

A) 直接從現有 story 萃取，不新增額外描述
B) 為每個 persona 補充簡短背景（職責、使用 Cloud-360 的情境）
C) 完整定義（包含技術背景、日常工作流程、使用 Cloud-360 的頻率與場景）

[Answer]:

---

### Q4：是否需要新增、合併或調整現有 Persona？

現有分析識別出 11 個 persona。請確認：

A) 直接使用現有 11 個，不做調整
B) 合併部分角色（例如：「架構師」與「雲端架構師」是否為同一人？「平台管理員」與「平台工程師」是否合併？）
C) 新增缺少的角色（例如：Engineering Manager、End User 等）
D) B + C（同時合併與新增）

[Answer]:

---

### Q5：語言確認

依 bilingual-docs extension，所有 `aidlc-docs/**/*.md` 必須雙語。請確認：

A) personas.md 與 stories.md 皆需完整雙語（`## 中文版` + `## English Version`）
B) 只有 `## English Version` 需要完整，中文版保持現有程度即可
C) 其他（請說明）

[Answer]:
