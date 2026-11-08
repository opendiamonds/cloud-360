# Market Research Questions

來源意圖：`<record>/ideation/intent-capture/intent-statement.md`（story D：架構圖 → IaC 生成＋掃描＋Secret Manager；對齊 A／C；平台不代 apply）。

---

## Q1. 這次研究的競爭／替代視角要以誰為主？

A. 主要對標「架構圖／設計 → IaC」類產品或功能（例：雲端供應商 IaC 產生器、diagram-to-Terraform 工具）
B. 主要對標「IaC 平台＋安全掃描／Policy／Secrets」類（例：Terraform Cloud／Spacelift／Checkov／tfsec 生態）
C. 兩者都要：生成路徑＋安全交付路徑都做競品掃描
D. 以內部替代為主：現有手動 Terraform／既有腳本／外部顧問，不需要外部產品對標
E. Not yet defined
X. Other (please specify)

[Answer]: C

---

## Q2. 已知或應納入比較的競品／替代方案有哪些？

A. 雲端原生：AWS IaC Generator／Application Composer、Azure 匯出、GCP 相關匯出
B. 第三方：Pulumi AI、Firefly、Spacelift、env0、Terraform Cloud／HCP Terraform
C. 開源／掃描：OpenTofu＋Checkov／tfsec／Trivy；Secret 側為雲端 Secret Manager 原生
D. 以上多類皆納入（請在 Other 補你在意的名稱）
E. None / Not identified
X. Other (please specify)

[Answer]: D

---

## Q3. 相關產業趨勢或合規壓力中，哪些對本 intent 有意義？

A. Policy-as-Code／Shift-left 掃描成為 IaC 交付表態（table-stakes）
B. Secret 不得進版控、須走 Secret Manager 引用已成預設期待
C. AI 輔助產生 IaC 快速增加，但可信度／可審核性仍是疑慮
D. 以上多項
E. Not applicable（純內部工具，無外部趨勢壓力）
X. Other (please specify)

[Answer]: D

---

## Q4. 對目標使用者，什麼是 table-stakes，什麼是 Cloud-360 差異化？

A. Table-stakes：可下載的 Terraform／OpenTofu 草稿＋基本靜態掃描；差異化：從**既有架構圖**一鍵產出且 UI／agent 與 Design／Assessment／成本同一工作區
B. Table-stakes：完整多雲模組市集＋代 apply 管線；差異化：AI 對話式設計（注意：代 apply 與本 intent 邊界衝突）
C. Table-stakes：僅產生 HCL；差異化：內建 D2＋D3 與 RBAC
D. Not yet defined
X. Other (please specify)

[Answer]: A

---

## Q5. Build vs Buy vs Partner 的初步傾向？

A. **Build**：在 Cloud-360 內建 LangGraph agent＋既有 Workspace（對齊 A／C），掃描／SM 以整合既有工具為主
B. **Buy／Embed**：嵌入商業 IaC 平台或掃描 SaaS，Cloud-360 只做入口
C. **Partner／Wrap**：呼叫開源掃描 CLI／雲端 API，生成邏輯自建、掃描與 SM 外包邊界清楚
D. 混合：生成自建（A），掃描／SM 採 C
E. Not yet defined
X. Other (please specify)

[Answer]: A

---

## Q6. 可觸及對象（市場規模／內部受眾）怎麼看？

A. 僅 Cloud-360 現有／預期租戶內的架構師、平台工程、安全角色（內部產品能力，不做對外 TAM）
B. 需估算外部可服務市場（請在 Other 說明區隔）
C. Not applicable
X. Other (please specify)

[Answer]: A

---

## Q7. 本輪 Market Research 深度？

A. Standard：足夠支撐 build-vs-buy 與差異化敘事，不做大型市場規模模型
B. Minimal：只回答 build-vs-buy 與 2–3 個關鍵替代，其餘標 Not researched
C. Comprehensive：完整競品矩陣＋趨勢＋TAM／SAM／SOM
X. Other (please specify)

[Answer]: A

---

## Consolidated Summary Confirmation

依你的回答整理如下：

- **研究視角**：生成路徑（架構圖→IaC）＋安全交付路徑（掃描／Policy／Secrets）都做競品掃描。[Q1]=C
- **競品範圍**：雲端原生產生器、第三方 IaC／AI 平台、開源掃描與雲端 Secret Manager 皆納入。[Q2]=D
- **趨勢**：Policy-as-Code／shift-left、Secret 走 Manager、AI 產生 IaC 的可信度疑慮皆相關。[Q3]=D
- **定位**：Table-stakes＝可下載草稿＋基本靜態掃描；差異化＝從既有架構圖產出，且與 A／C 同一工作區體驗。[Q4]=A
- **Build vs Buy**：Build — Cloud-360 內建 LangGraph＋Workspace；掃描／SM 以整合既有工具為主。[Q5]=A
- **受眾**：僅租戶內架構師／平台／安全；不做對外 TAM。[Q6]=A
- **深度**：Standard（支撐 build-vs-buy 與差異化，不做大型市場規模模型）。[Q7]=A

Does this all look correct before I generate the artifact?

- Looks correct
- Request changes

[Answer]: Looks correct
