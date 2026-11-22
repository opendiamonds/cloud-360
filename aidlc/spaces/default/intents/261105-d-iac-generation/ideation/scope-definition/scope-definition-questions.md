# Scope Definition Questions

上游：intent-statement（D1＋D2＋D3 一次交付；三 agent；不代 apply）、feasibility（可行）、constraint-register。

---

## Q1. 最小可交付範圍（MVP slice）是什麼？

A. 僅 D1：從架構圖產出可下載 Terraform／OpenTofu 草稿（對齊 A／C UI／agent）
B. D1＋D2：草稿＋靜態掃描結果；D3 列 Won't / 另 intent
C. D1＋D2＋D3 全進本 intent（與 intent-capture 一致）— MVP＝三者皆有可演示路徑
D. Not yet defined
X. Other (please specify)

[Answer]: C

---

## Q2. Must / Should / Could / Won't（MoSCoW）怎麼切？

A. Must：D1＋D2＋D3＋三 agent＋RBAC／OpenAPI／不代 apply；Should：掃描引擎可配置；Could：多掃描引擎；Won't：代 apply、production 憑證、商業 IaC 平台嵌入
B. Must：僅 D1；Should：D2；Could：D3；Won't：同上平台禁制
C. Not yet defined
X. Other (please specify)

[Answer]: A

---

## Q3. 能力依賴順序？

A. D1（生成）→ D2（對草稿掃描）→ D3（SM 引用／去明文）；前端工作區與 RBAC 與 D1 並行可起
B. D2／D3 可與 D1 完全並行（無產出依賴）
C. 先做掃描／SM 基礎設施再生成
D. Not yet defined
X. Other (please specify)

[Answer]: A

---

## Q4. 排序偏好？

A. Dependency-first（依 Q3 依賴）
B. Value-first（先可下載草稿給架構師）
C. Risk-first（先打掃描／SM 或不確定的整合）
D. Not yet defined
X. Other (please specify)

[Answer]: A

---

## Q5. 有無綁在特定能力上的硬性 deadline？

A. 無（承接可行性 Q4）
B. 有（請說明能力與日期）
C. Not applicable
X. Other (please specify)

[Answer]: A

---

## Q6. 明確排除（Out of scope）還要再強調哪些？

A. 維持既有：代 apply、production credentials、direct production IaC、商業 IaC 平台整包嵌入、自研掃描引擎
B. 另排除多雲 provider 完整覆蓋保證（僅 best-effort 草稿）
C. A＋B
D. Not yet defined
X. Other (please specify)

[Answer]: A

---

## Consolidated Summary Confirmation

依你的回答整理如下：

- **MVP**：D1＋D2＋D3 全進本 intent；三者皆有可演示路徑。[Q1]=C
- **MoSCoW**：Must＝D1＋D2＋D3＋三 agent＋RBAC／OpenAPI／不代 apply；Should＝掃描引擎可配置；Could＝多掃描引擎；Won't＝代 apply、production 憑證、商業 IaC 平台嵌入。[Q2]=A
- **依賴**：D1 → D2 → D3；前端工作區與 RBAC 可與 D1 並行。[Q3]=A
- **排序**：Dependency-first。[Q4]=A
- **Deadline**：無硬性日期。[Q5]=A
- **Out of scope 強調**：代 apply、production credentials、direct production IaC、商業 IaC 平台整包嵌入、自研掃描引擎。[Q6]=A

Does this all look correct before I generate the artifact?

- Looks correct
- Request changes

[Answer]: Looks correct
