# Intent Capture Questions

## Sources

- [desc] Initial description: "User story D：標準化 IaC 生成與安全交付（D1 模板化 Terraform/OpenTofu、D2 靜態掃描、D3 Secret Manager）。架構與執行框架須與 A（Design／Assessment）及 C（成本）對齊——同一套 LangGraph agent 框架；UI 風格須與現有 A／C 工作區一致（同一套 layout／元件語彙）。Brownfield，從現有架構圖產出 IaC。"
- [scope] Workflow-selected scope: `feature`.
- [memory:M1] `aidlc/spaces/default/memory/project.md#Scope Overrides`: "✅ **In scope**：SRS、architecture diagrams、user stories、ADRs、IaC generator design、agent routing design、MCP/skill management spec、validation scripts、baseline CI、自有 staging 的部署與維運。"
- [memory:M2] `aidlc/spaces/default/memory/project.md#Scope Overrides`: "❌ **Out of scope（除非經新 ADR 核可）**：雲端供應商 production 環境、production credentials、environment-specific secrets、direct production IaC、destructive cloud operations、native iOS/Android app。"
- [memory:M3] `aidlc/spaces/default/memory/project.md#Testing Posture`: "**Property-based testing 為 hard constraint**（ADR-0006）。下列核心模組的測試必須包含 property-based 測試，不得只有 example-based：IaC generator、cost calculator、agent routing。其餘模組沿用 `org.md` 的預設門檻。"
- [memory:M4] `aidlc/spaces/default/memory/project.md#Forbidden`: "NEVER 在未取得 human approval 的情況下執行 production write、IaC apply 或 IAM 變更。"

---

## Q1. 這次要解決的核心業務問題是什麼？

A. 架構師／平台工程師手動把架構圖轉成 Terraform／OpenTofu 耗時且不一致，需要標準化生成
B. 產出的 IaC 缺少靜態掃描與 Secret 管控，交付不安全，需要 D1＋D2＋D3 一條龍安全交付
C. Workspace 上「生成 IaC」仍是 Coming Soon，產品能力缺口，須補齊對齊 A／C 的工作區體驗
D. 以上多項同時成立（請在 Other 說明優先序）
E. Not yet defined
X. Other (please specify)

[Answer]: B C

---

## Q2. 主要服務對象與痛點是誰？

A. Elena（平台工程師）：需要標準化、不含 production secrets 的模組化 IaC，減少手動開通
B. Alex／架構師：確認後的架構圖要能轉成完整 Terraform 模組草稿
C. Fiona（安全審查）：產出須內建靜態掃描，避免危險 IAM／設定流入交付
D. 以上多個角色皆為主要對象（請說明主次）
E. Not identified
X. Other (please specify)

[Answer]: BAC

---

## Q3. 成功長什麼樣子？哪些指標算達標？

A. 使用者可從既有架構圖產出可下載／可檢視的 Terraform／OpenTofu 草稿，且 UI／agent 體驗對齊 A／C
B. 產出物通過（或附帶）靜態掃描結果，且不內嵌 production secrets
C. D1＋D2＋D3 在本 intent 內皆有可演示的端到端路徑
D. Not yet defined（稍後再定具體指標）
E. Other (please specify)
X. Other (please specify)

[Answer]: AB

---

## Q4. 啟動這次意圖的觸發是什麼？

A. 產品路線圖／user story D 到期，Workspace Coming Soon 須落地
B. 客戶或內部使用者明確要求從架構圖產出 IaC
C. 安全／合規壓力（掃描與 Secret Manager）
D. 技術債／與 A、C LangGraph 對齊的一致性壓力
E. Not yet defined
X. Other (please specify)

[Answer]: B

---

## Q5. 關鍵利害關係人各自在意什麼？

A. 產品／架構決策者：能力邊界與和 A／C 的一致性；平台工程：模板品質；安全：掃描與 secrets；最終使用者：可用草稿
B. 僅產品 owner 與實作工程師；其他角色本輪不納入
C. Not identified
D. None（本輪無須利害關係人圖）
X. Other (please specify)

[Answer]: A

---

## Q6. 誰決定範圍／優先序？誰影響決策？

A. 開此 workflow 的使用者（luojingting）決定範圍；團隊／審閱者影響優先序
B. 產品／架構 lead 決定；實作者僅建議
C. Not identified
X. Other (please specify)

[Answer]: C

---

## Q7. 本 intent 的產品邊界：D1／D2／D3 要涵蓋到哪？

（對照 [desc] 與 [memory:M1]/[memory:M2]：IaC generator design 在範圍內；direct production IaC／production credentials 在範圍外。）

A. 本 intent 一次交付 D1＋D2＋D3（生成＋靜態掃描＋Secret Manager 整合）
B. 本 intent 以 D1（模板化 Terraform／OpenTofu 生成）為主；D2／D3 僅定義介面或 stub，實作另開 intent
C. 本 intent 交付 D1＋D2；D3 另開
D. Not yet defined
X. Other (please specify)

[Answer]: A

---

## Q8. 工作流程選定的 scope 是 `feature`。這是否符合你要的產品邊界？

A. 確認：維持 `feature` — 在既有 Cloud-360 上新增／補齊 story D（LangGraph＋對齊 A／C 的 UI），不另定產品邊界
B. 產品邊界不同：應改為更窄（例如僅 D1 原型／PoC）
C. 產品邊界不同：應改為更廣（例如跨多雲 production 交付管線）— 可能與 [memory:M2] 衝突，需另開 ADR
D. Not applicable
X. Other (please specify)

[Answer]: A

---

## Q9. 產出物的消費方式（誰拿、拿去做什麼）？

A. 使用者在 Workspace 下載／複製 Terraform 草稿，於 Cloud-360 外自行 apply（平台不代 apply）
B. 產出僅供 Workspace 內預覽與掃描報告；下載為次要
C. 期望平台代為 plan／apply（注意 [memory:M2]/[memory:M4]：production IaC apply 預設禁制）
D. Not yet defined
X. Other (please specify)

[Answer]: A

---

## Consolidated Summary Confirmation

依你的回答，本意圖整理如下：

- **問題**：安全交付缺口（缺靜態掃描與 Secret 管控）＋ Workspace「生成 IaC」仍為 Coming Soon，需補齊並對齊 A／C 體驗。[Q1]=B C
- **主要對象（主→次）**：Alex／架構師 → Elena／平台工程 → Fiona／安全審查。[Q2]=BAC
- **成功標準**：可從既有架構圖產出可下載／可檢視的 Terraform／OpenTofu 草稿，且 UI／agent 對齊 A／C；產出附靜態掃描結果且不內嵌 production secrets。[Q3]=AB
- **觸發**：客戶或內部使用者明確要求從架構圖產出 IaC。[Q4]=B
- **利害關係人**：產品／架構（能力邊界與 A／C 一致性）、平台工程（模板品質）、安全（掃描與 secrets）、最終使用者（可用草稿）。[Q5]=A
- **範圍／優先決策者**：尚未識別。[Q6]=C
- **本 intent 邊界**：一次交付 D1＋D2＋D3；維持 `feature` scope；平台不代 apply，使用者下載後自行 apply。[Q7]=A，[Q8]=A，[Q9]=A
- **既定護欄**：IaC generator design 在範圍內；direct production IaC／credentials／未核准的 apply 在範圍外。[memory:M1–M4]

備註：成功指標未要求「D1＋D2＋D3 皆可演示的端到端路徑」（未選 Q3=C），但範圍選定一次交付三者（Q7=A）— 以交付三者為準，演示深度可在後續 requirements 再細化。

Does this all look correct before I generate the artifact?

- Looks correct
- Request changes

[Answer]: Looks correct

---

## Assumption Confirmation

下列假設仍標為 `[assumption]`，尚未成為事實：

1. 範圍／優先序的最終決策者與影響者尚未識別（Q6＝Not identified）。
2. 成功指標未要求「D1＋D2＋D3 皆可演示的端到端路徑」，但產品邊界選定一次交付三者；演示深度與驗收粒度留待 requirements 細化。
3. 溝通節奏與管道未在本輪問答中確認。

A. Accept assumptions
B. Convert to follow-up questions

[Answer]: A. Accept assumptions
