# Intent Capture — 釐清問題

> Stage: intent-capture（Ideation 1.1）· Depth: Standard · Scope: aidlc-github-projects-sync
> 作答方式：在每題的 `[Answer]:` 後面填入選項字母（可含說明）。X 為自由填答。

## Sources

- [desc] Initial description: "建立 AI-DLC 與 GitHub Projects 的整合機制：以 repo 根目錄的 README.md 作為所有 intent 的需求來源，並讓 AI-DLC 各 stage 的進展定時同步更新 opendiamonds 組織 Project #16「Cloud-360 開發計劃」中 issue 的 Status 欄位（Backlog / Nice to have / Ready / In progress / In review / Done）。"
- [scope] Workflow-selected scope: `aidlc-github-projects-sync`.
- [memory:M1] `aidlc/spaces/default/memory/project.md#Scope Overrides`: "✅ **In scope**：SRS、architecture diagrams、user stories、ADRs、IaC generator design、agent routing design、MCP/skill management spec、validation scripts、baseline CI、自有 staging 的部署與維運。"
- [memory:M2] `aidlc/spaces/default/memory/project.md#Scope Overrides`: "❌ **Out of scope（除非經新 ADR 核可）**：雲端供應商 production 環境、production credentials、environment-specific secrets、direct production IaC、destructive cloud operations、native iOS/Android app。"
- [memory:M3] `aidlc/spaces/default/memory/project.md#Forbidden`: "NEVER 直接編輯 `.claude/` 下的 upstream 框架檔來表達專案規則 — 專案規則一律寫在 `aidlc/spaces/<space>/memory/{team,project}.md`，否則下次升級會被整批覆蓋。"
- [memory:M4] `aidlc/spaces/default/memory/project.md#Decided`: "DECIDED: 所有 AIDLC artifacts（含 v2 之前的歷史文件）都在作用中 intent 的 record 目錄 `<record>/` 下；baseline record 為 `aidlc/spaces/default/intents/260802-default/`。(ADR-0011)"

## 出題前的唯讀查證（背景說明，非來源）

下列事實是出題前對 repo 與 GitHub 的唯讀查證結果，用來讓題幹與選項貼近現況。依本 stage 的 grounding contract，它們**不是**可引用的來源，不會出現在 artifact 的來源標籤中；artifact 只引用上面 `## Sources` 的四類與已作答的 `[Q<n>]`。

- Project #16「Cloud-360 開發計劃」屬於 `opendiamonds` org，Status 欄位共 6 個選項（Backlog / Nice to have / Ready / In progress / In review / Done），目前 71 個 item，分布為 Done 66、In progress 2、In review 1、Backlog 1、Nice to have 1。
- repo 目前 3 個 open issue（#463、#487、#488）、0 個 open PR；Project 上的 #365 標記為 In review，但它已不在 open issue 清單中。
- README.md 共 174 行，內容是平台總覽（Vision、8 個 Core Modules、文件索引），沒有 issue 編號、沒有驗收條件、沒有狀態欄。
- `gh` 目前 active 帳號 `opendiamonds` 缺少 `project` scope；使用者已決定為該帳號補上授權（此項已定案，不在本輪提問範圍）。
- AI-DLC 目前編譯後共 33 個 stage，本 intent 的 scope 執行其中 19 個。

## Q1. 這個整合要解決的業務問題是什麼？

A. 狀態失真 — Project 板上的狀態靠人工維護，實際進度與板上顯示對不起來，看板失去可信度
B. 重複記帳 — 同一件事的進度要在 AI-DLC 的 record 與 Project 板各記一次，雙份維護必有一份過期
C. 需求來源分散 — 要做什麼散落在對話、issue、README 與各 intent record，沒有單一入口
D. 對外可視性 — 需要讓不看 repo 的人（管理層／其他團隊）從 Project 板就能看到 AI-DLC 的實際進度
E. Not yet defined — 尚未定義，先做再說
X. Other (please specify)

[Answer]:A, B, C, D

## Q2. 誰會實際受益？他們現在的痛點是什麼？

（可複選，用逗號分隔，例如 `A, C`）

A. 你自己（唯一開發者）— 每跑完一個 stage 還要記得回去手動改 Project 狀態，常常忘記
B. 專案的其他協作者（doreen、luojingting 等）— 看板上的狀態不準，不知道別人在做什麼
C. 不參與開發的觀看者 — 只看 Project 板，看不到 AI-DLC 內部的 stage 進度
D. 未來的自己 — 事後回溯某個功能當初走過哪些 stage、卡在哪裡時無跡可循
E. Not identified — 還沒有明確的受益對象
X. Other (please specify)

[Answer]:A, B, D
>
> **⚠️ 本答案已由 Q10=A 補充**：受益者加入 C（不參與開發的觀看者）。原答案保留作為決策軌跡，不改寫。

## Q3. 成功長什麼樣子？用什麼衡量？

A. 零人工更新 — 任何 intent 跑完一個 stage 後，對應 Project item 的 Status 不需要人去改就已經正確
B. 狀態一致率 — 可以隨時比對「Project 板狀態」與「AI-DLC record 實際狀態」，兩者不一致的 item 數為 0
C. 可追溯 — 每次 Status 變更都能說出是哪個 intent、哪個 stage、什麼時間觸發的
D. 不要求量化 — 只要「大致上會自己更新」就算成功，不設可量測的門檻
E. Not yet defined
X. Other (please specify)

[Answer]: A, B, C

## Q4. 為什麼是現在做這件事？觸發點是什麼？

A. 已經被咬到 — 板上狀態實際已經跟現實脫節（例如 #365 標 In review 但 issue 已關閉），再不處理會繼續累積
B. 流程剛穩定 — AI-DLC v2 已落地、intent 記錄格式穩定，現在才有東西可以拿來同步
C. 準備擴大協作 — 接下來會有更多人／更多 intent 並行，人工維護撐不住
D. 沒有外部壓力 — 純粹是想把工作流補完整，時間點沒有特別意義
E. Not yet defined
X. Other (please specify)

[Answer]: A, B, C

## Q5. 誰是利害關係人？誰對範圍與優先序有最終決定權？

A. 只有你 — 你同時是唯一利害關係人與唯一決策者，沒有需要對齊的第三方
B. 你決定，但其他 repo 協作者是受影響方，改動需要讓他們知道（告知，非同意）
C. 你決定，但某些改動需要協作者同意（例如改到他們也在用的 workflow 或 branch 流程）
D. 有你之外的決策者（例如客戶／指導者）對這件事有否決權
E. Not identified
X. Other (please specify)

[Answer]: B

## Q6. 「定時同步」的節奏該由什麼決定？另外需要什麼形式的回報？

A. 事件驅動 — 每次 stage 狀態變動就同步一次，不用排程；沒有變動就不動作
B. 排程驅動 — 固定間隔（例如每小時／每天）掃一次目前狀態並補齊差異，不管中間發生什麼
C. 兩者都要 — 事件驅動即時更新，另加一個低頻排程做對帳，補掉漏掉的
D. 手動觸發 — 只在你明確要求時才同步，不自動跑
E. Not yet defined — 節奏還沒想清楚，留給後續階段定案
X. Other (please specify)

補充：不論選哪一項，請一併說明「同步失敗時你希望怎麼知道」（例如：開 issue、workflow 紅燈、寫進 record、完全不用通知）。

[Answer]: C

## Q7. 「以 README.md 作為所有 intent 的需求來源」具體是什麼意思？

A. README 成為需求清單本身 — 在 README 增設一個可機器解析的需求／功能區塊，日後每個 intent 都必須對應到其中一條
B. README 是索引，Project 是清單 — README 只維持現在的總覽敘述，實際的需求逐項清單放在 Project #16，intent 對應到 Project item
C. README 是唯一入口的宣告 — 不改 README 結構，只是立下一條規則：開 intent 前必須先讀 README 確認它落在既有的 Core Module 範圍內
D. README 需求化改寫 — 把現有的 8 個 Core Module 拆成可追蹤的條目（帶編號與驗收條件），等於一次 README 重寫
E. Not yet defined
X. Other (please specify)

[Answer]: B

## Q8. 工作流選定的 scope 是 `aidlc-github-projects-sync`（33 個 stage 中執行 19 個，16 個核可閘）。這個範圍與你心中的產品邊界一致嗎？

A. 一致 — 本次就做「README 作為需求來源」＋「stage 進度同步到 Project #16」這兩件事，範圍剛好
B. 範圍偏大 — 本次只想做其中一半（請在答案中說明是哪一半），另一半另開 intent
C. 範圍偏小 — 還要包含其他東西（請在答案中說明，例如反向同步、issue 自動開立、跨 repo 支援）
D. 範圍對，但要先做一個能跑的最小版本驗證可行性，再決定要不要做完整版
E. Not yet defined
X. Other (please specify) 

[Answer]: A

---

## 追問（第一輪答案分析後）

下列四題來自對 Q1–Q8 的矛盾偵測與完整性檢查，編號延續 Q1–Q8。

## Q9. Q6 選了 C（事件驅動＋排程對帳），但題目要求一併說明的「同步失敗時你希望怎麼知道」沒有填。要哪一種？

A. Workflow 紅燈就好 — GitHub Actions run 失敗即可，我自己會在 Actions 頁看到
B. 自動開 issue — 失敗時開一張 issue（repo 內 `daily-digest.md` 已用 `safe-outputs: create-issue` 這個做法）
C. 只寫進 record／log — 不主動通知，事後查得到就好
D. 紅燈＋開 issue 兩者都要 — 排程對帳發現不一致時也算一種需要通知的失敗
E. Not yet defined — 留給後續階段定案
X. Other (please specify)

[Answer]:D. 紅燈＋開 issue 兩者都要 — 排程對帳發現不一致時也算一種需要通知的失敗

## Q10. Q1 選了 D（對外可視性：讓不看 repo 的人從板上看到進度），但 Q2 的受益者沒有選 C（不參與開發的觀看者）。這兩者指的是同一群人，需要對齊。

A. 以 Q1-D 為準 — 觀看者確實是受益者，Q2 漏選，請把 C 補進 Q2
B. 以 Q2 為準 — Q1-D 的「不看 repo 的人」實際上就是協作者（Q2-B）在不進 repo 時的視角，沒有第三方觀看者
C. 兩者都不完全 — 觀看者存在，但不是本次要服務的對象；列為未來考量，不進本次的成功標準
D. 有真實的第三方觀看者且很重要（請在答案中說明是誰）
X. Other (please specify)

[Answer]:A. 以 Q1-D 為準 — 觀看者確實是受益者，Q2 漏選，已把 C 補進 Q2

## Q11. Q7 選了 B（README 維持現狀、需求清單放 Project #16），這與最初描述的「以 README.md 作為所有 intent 的需求來源」以及 Q8-A 認定的「兩件事」有張力——在 B 之下，README 這一半可能沒有任何交付物，本次實質只剩同步機制一項。

A. README 只加一段指路文字 — 指向 Project #16 是需求清單的正本；本次交付物實質就是同步機制一項
B. README 要加對照區塊 — 清單雖在 Project，README 仍需維護「Core Module ↔ Project item」的對照，讓只看 repo 的人找得到
C. README 完全不動 — 把「開 intent 前先看 Project #16」寫成 `project.md` 的團隊規則即可，不碰 README
D. 我要改 Q7 的答案（請在答案中說明改成哪一個）
X. Other (please specify)

[Answer]:A. README 只加一段指路文字 — 指向 Project #16 是需求清單的正本；本次交付物實質就是同步機制一項

## Q12. Q3 選了 B（不一致的 item 數為 0），但目前板上 71 個 item 大多沒有對應的 AI-DLC record（66 個已 Done、且多數早於本流程）。這個指標的分母是什麼？

A. 只算綁定到 AI-DLC intent 的 item — 沒有對應 record 的既有 item 不進分母
B. 全部 71 個都要算 — 沒有 record 的 item 也要有明確的狀態來源（例如以 issue 開／關狀態為準）
C. 分階段 — 本次只算新綁定的；既有 71 個的盤點與對正另開一件事處理
D. 不設分母 — B 當方向不當指標，實際只看「有沒有漏同步」
X. Other (please specify)

[Answer]:A. 只算綁定到 AI-DLC intent 的 item — 沒有對應 record 的既有 item 不進分母

---

## Consolidated Summary Confirmation

在依這些答案產出 intent-statement.md 與 stakeholder-map.md 之前，請確認彙整內容正確。

A. Looks correct — 依這些答案產出 artifact
B. Request changes — 先修改一個以上的答案再產出
X. Other (please specify)

[Answer]: A. Looks correct

---

## Assumption Confirmation

兩份 artifact 的 `## Assumptions & Open Questions` 共保留 9 條假設，逐條列出如下。接受不會讓假設變成事實，只是確認它們可以以假設的身分帶往下一階段。

來自 `intent-statement.md`：

- Project #16 的寫入權限問題將由作用中的 GitHub 帳號補上授權解決，不需要改變同步機制的設計；此項在問題檔建立前的對話中定案，未登錄為本 stage 的來源 [assumption]
- 看板上既有的 item 數量與狀態分布是出題當下的唯讀觀察值，會隨時間變動；下游若需要精確數字應重新查證 [assumption]
- 「其他 repo 協作者」的具體成員以問題檔選項中列出的名字為例，未經逐一確認其對本功能的實際需求 [assumption]
- 一個 AI-DLC intent 與一個 Project item 之間如何綁定尚未定義，屬於後續階段要解的問題 [assumption]
- AI-DLC 的 stage 進展如何對應到 6 個 Status 選項尚未定義，屬於後續階段要解的問題 [assumption]

來自 `stakeholder-map.md`：

- 「其他 repo 協作者」的具體成員以問題檔選項中列出的名字為例，未經逐一確認其偏好的通知方式 [assumption]
- 「不參與開發的觀看者」的具體身分未被指名；其人數、身分與查看頻率均未定義 [assumption]
- 對協作者的告知採用什麼載體（PR 描述、issue、口頭或不特別處理）尚未定義，屬於後續階段要解的問題 [assumption]
- 自動開立的失敗 issue 由誰處理、多久內處理，尚未定義 [assumption]

A. Accept assumptions
B. Convert to follow-up questions

[Answer]: A. Accept assumptions