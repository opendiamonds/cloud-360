# Intent Capture — 釐清問題

> Stage: intent-capture（Ideation 1.1）· Depth: Standard · Scope: mvp
> 作答方式：在每題的 `[Answer]:` 後面填入選項字母（可含說明）。X 為自由填答。

## Sources

- [desc] Initial description: "Implement Cost Estimation and FinOps from user stories C1 TCO budget forecast, starting with C1 then C2 pricing models and C3 data egress. First-pass MVP: extract resources from architecture diagrams, query cloud pricing, show TCO breakdown pie chart, and allow daily hours override."
- [scope] Workflow-selected scope: `mvp`.
- [memory:M1] `aidlc/spaces/default/memory/project.md#Testing Posture`: "**Property-based testing 為 hard constraint**（ADR-0006）。下列核心模組的測試必須包含 property-based 測試，不得只有 example-based：IaC generator、cost calculator、agent routing。其餘模組沿用 `org.md` 的預設門檻。"
- [memory:M2] `aidlc/spaces/default/memory/project.md#Scope Overrides`: "❌ **Out of scope（除非經新 ADR 核可）**：雲端供應商 production 環境、production credentials、environment-specific secrets、direct production IaC、destructive cloud operations、native iOS/Android app。"
- [memory:M3] `aidlc/spaces/default/memory/project.md#Decided`: "DECIDED: `extensions/security/baseline/` 預設啟用，為 hard constraint（IAM、encryption、network exposure、audit logging）。requirements analysis 階段不需再詢問。(ADR-0006)"
- [memory:M4] `aidlc/spaces/default/memory/project.md#Forbidden`: "NEVER commit 私鑰或 AWS / Azure / GCP 的 credential 字串。實際被擋的樣式列在 `scripts/validate_repo_contract.py` 的 `FORBIDDEN_CONTENT_PATTERNS`（涵蓋私鑰 PEM 標頭與三雲的 secret 環境變數）。**不要把那些樣式照字面複製到任何 contract 檔案裡** — 掃描器不分辨「示範」與「洩漏」，會直接紅燈。"
- [memory:M5] `aidlc/spaces/default/memory/project.md#Way of Working`: "Sidebar 導覽依 user story 大類分層（例如 A、J）；故事層（A1／A3、J3a／J3b）為第二層。既有 A／J 先套用，後續功能比照。 (learned 2026-08-06)"
- [memory:M6] `aidlc/spaces/default/memory/team.md#Mandated`: "✅ **小步前進**：每個 stage 完成後產出 stage-completion summary，附 extension compliance（compliant / non-compliant / N/A 與理由），等使用者確認再進下一階段。"

## Q1. 這個功能要解決什麼業務問題？

A. 預算失控 — 架構變更後不知道每月會花多少，常常超支才發現
B. 報價不可信 — 目前靠試算表／口頭估，無法對到實際架構圖上的資源
C. 決策無據 — 跨雲或方案比較時缺少可重算的成本數字
D. 隱性費用 — 主要痛在流量／Egress，不是運算本身
E. Not yet defined — 尚未定義驅動問題
X. Other (please specify)

[Answer]: B. 報價不可信 — 目前靠試算表／口頭估，無法對到實際架構圖上的資源

## Q2. 誰會實際使用「查看預估成本」？他們現在的痛點是什麼？

A. FinOps 分析師 — 需要可拆解的月費，才能設預算與對帳
B. 工程主管 — 在架構圖加機器時，需要立刻知道預算影響
C. 雲端架構師 — 產圖後要給一個可對外說明的成本數字
D. 技術決策者 — 只要總額與趨勢，不需要逐項拆解
E. Not yet defined
X. Other (please specify)

[Answer]: C. 雲端架構師 — 產圖後要給一個可對外說明的成本數字

## Q3. 成功長什麼樣子？用什麼衡量？

A. 能從架構圖擷取資源、查出報價、顯示每項資源拆解與總額（圓餅圖），並可用「每日運作時數」重算月費
B. 上述 A，另加「每月預算上限」與超支時雙方都看得到的警告
C. 上述 A，另加定價模型對比（Spot／RI）或 Egress 熱點
D. 只要畫面上有一個總金額就算成功，拆解可之後再做
E. Not yet defined
X. Other (please specify)

[Answer]: B. 上述 A，另加「每月預算上限」與超支時雙方都看得到的警告

## Q4. 為什麼是現在做？觸發原因是什麼？

A. 使用者故事 C1–C3 已寫好，A 柱產圖後需要銜接「查看預估成本」
B. 專案或客戶已有實際超支／報價爭議
C. 要先補上 cost calculator（ADR-0006 點名的核心模組）再擴其他 FinOps
D. None — 沒有特定外部期限，屬機會性補齊產品柱
E. Not applicable
X. Other (please specify)

[Answer]: A. 使用者故事 C1–C3 已寫好，A 柱產圖後需要銜接「查看預估成本」

## Q5. 關鍵 stakeholder 有哪些？各自在意什麼？（select all that apply）

A. FinOps 分析師 — 數字可重算、可拆解、可標記人工覆寫
B. 工程主管 — 改圖時預算變化可見、超支要被通知
C. 雲端架構師 — 成本數字能對到圖上的資源，而不是另一份表
D. 開發／維運 — 實作與維護成本、不要為了估價去碰雲端 production
E. Not identified — 目前只有你一個決策者
X. Other (please specify)

[Answer]: A, B, C, D

## Q6. 誰決定範圍與優先序？誰有影響力但不決策？

A. 你單獨決定（本分支與本 intent 的產品邊界由你拍板）
B. 你決定，但 FinOps 角色對「數字怎麼算」有否決權
C. 需要團隊共識（多人會審）
D. Not identified
X. Other (please specify)

[Answer]: B. 你決定，但 FinOps 角色對「數字怎麼算」有否決權

## Q7. 有溝通或回報節奏的需求嗎？

A. 無 — 做完在 PR 說明即可
B. 需要在 decisions-log 記錄關鍵產品決議（你明確要求時才寫）
C. 需要開 ADR（例如是否呼叫雲端官方報價、憑證怎麼放）
D. Not applicable
X. Other (please specify)

[Answer]: A. 無 — 做完在 PR 說明即可

## Q8. 這個 workflow 以 `mvp` scope 起跑（23/33 stages、Standard 深度、約 20 個 approval gate；略過 Operation 與部分 Ideation）。這符合你心中的產品邊界嗎？

> 本題區分「確認 workflow 選定的 scope」與「定義不同的產品邊界」。

A. 確認 — `mvp` 就是我要的產品邊界（先交核心、略過 Operation）
B. 產品邊界更小 — 只要驗證「圖 → 金額」能跑，希望改用更輕的 scope（如 `poc`）
C. 產品邊界更大 — 這是完整 FinOps 產品線，希望改用 `feature`（含 Operation）
D. Not yet defined — 先跑，之後在 gate 調整
X. Other (please specify)

[Answer]: A. 確認 — `mvp` 就是我要的產品邊界（先交核心、略過 Operation）

## Q9. 這一輪 intent 的產品切片要做到哪裡？

> [desc] 寫了「starting with C1 then C2 and C3」，同時又寫 First-pass MVP 只含擷取資源、查報價、圓餅拆解、每日時數。兩者需要你定錨。

A. 只做 C1 核心：擷取資源、查報價、圓餅拆解、每日運作時數覆寫；C2／C3 不在本輪交付
B. 做完 C1，並為 C2／C3 留可見入口（例如停用的導覽），但不做 Spot／RI 與 Egress 計算
C. 本輪一次做完 C1 + C2 + C3
D. Not yet defined
X. Other (please specify)

[Answer]: A. 只做 C1 核心：擷取資源、查報價、圓餅拆解、每日運作時數覆寫；C2／C3 不在本輪交付

## Q10. 矛盾解消：Q3 的成功條件含「預算上限與超支雙方警告」，Q9 本輪卻只做 C1 核心（擷取／報價／圓餅／時數）

> **偵測到的矛盾**（stage-protocol.md §3 強制檢查）：
>
> | 來源 | 內容 |
> |---|---|
> | Q3=B | 成功包含每月預算上限，以及超支時雙方都看得到的警告 |
> | Q9=A | 本輪只交付擷取資源、查報價、圓餅拆解、每日運作時數覆寫 |
>
> 預算上限與超支警告不是 Q9 列出的 C1 核心四件。若不釐清，intent-statement 會同時寫「本輪必做」與「本輪不做」。

A. 本輪成功仍含預算上限與超支雙方警告（視為 C1 第一輪必做，不是 C2／C3）
B. 本輪成功只做到 Q9 的四件；預算上限／超支警告放到下一輪
C. 本輪只做「可設定預算上限並在畫面上標示是否超支」，不做通知雙方
D. Not yet defined
X. Other (please specify)

[Answer]: A. 本輪成功仍含預算上限與超支雙方警告（視為 C1 第一輪必做，不是 C2／C3）

## Consolidated Summary Confirmation

prompt: Does this all look correct before I generate the artifact?

A. Looks correct — Generate the artifact from these answers
B. Request changes — Revise one or more answers before generation

[Answer]: A. Looks correct

## Assumption Confirmation

下列假設同時出現在 `intent-statement.md` 與 `stakeholder-map.md` 的 `## Assumptions & Open Questions`：

1. Q3／Q10 的「雙方」未點名角色。本文件暫將「超支時要被通知／看得到警告」對應到 Q5 已選的 FinOps 分析師與工程主管，不把雲端架構師或開發／維運列為警告的必達收件人 [Q3] [Q5] [Q10]
2. 「查詢雲端報價」是產品能力，本階段不選定報價來源（公開價目、合約價、或人工覆寫為主）；取得報價時不得引入 production credentials [desc] [Q3] [memory:M2] [memory:M4]
3. 導覽是否新增 C（成本／FinOps）大類、以及「查看預估成本」入口要掛在產圖後 CTA 或獨立看板，本階段未確認；只確認能力本身 [Q4] [memory:M5]
4. （開放問題）FinOps 對「數字怎麼算」的否決權，其行使時機與範圍（例如覆寫單價、否決某個報價來源）尚未界定 [Q6]

A. Accept assumptions
B. Convert to follow-up questions

[Answer]: B. Convert to follow-up questions

## Q11. 「超支時雙方都看得到警告」的雙方是誰？

A. FinOps 分析師與工程主管
B. FinOps 分析師、工程主管與雲端架構師
C. Q5 列出的全部 stakeholder（含開發／維運）
D. Not yet defined
X. Other (please specify)

[Answer]: B. FinOps 分析師、工程主管與雲端架構師

## Q12. 本輪「查詢雲端報價」產品上要以什麼為準？（不含雲端 production 帳務憑證）

A. 公開價目（list price）為準，缺價時允許人工覆寫並標記
B. 以人工覆寫為主，公開價目只當預設參考
C. 必須接雲端官方報價 API（仍不得使用 production credentials）
D. Not yet defined
X. Other (please specify)

[Answer]: C. 必須接雲端官方報價 API（仍不得使用 production credentials）

## Q13. 「查看預估成本」的入口這輪要做到哪裡？

A. 產圖成功後 CTA「查看預估成本」即可，本輪不做獨立 FinOps 導覽大類
B. Sidebar 新增 C（成本／FinOps）入口，並保留產圖後 CTA
C. 只做獨立 FinOps 看板，不做產圖後 CTA
D. Not yet defined
X. Other (please specify)

[Answer]: B. Sidebar 新增 C（成本／FinOps）入口，並保留產圖後 CTA

## Q14. FinOps 對「數字怎麼算」的否決權，本輪要做到什麼程度？

A. 能人工覆寫單價或運作時數並標記 Manual Override，即視為否決權已落地
B. 否決權是核准流（FinOps 核准後數字才對外）；本輪先不做核准流
C. 本輪不實作否決權，只記載給後續 intent
D. Not yet defined
X. Other (please specify)

[Answer]: B. 否決權是核准流（FinOps 核准後數字才對外）；本輪先不做核准流

## Q15. 矛盾解消：FinOps 在意「可標記人工覆寫」（Q5=A），但報價來源選了官方 API（Q12=C、未選缺價覆寫）

> Reviewer Finding 1（Major）：Q5=A 含「可標記人工覆寫」；Q12=C 未選「缺價時允許人工覆寫並標記」。每日運作時數覆寫（Q3）≠ 單價覆寫。

A. 本輪人工覆寫只含每日運作時數；單價以官方 API 為準，不可覆寫
B. 時數可覆寫；官方 API 缺價或失敗時，單價也可覆寫並標記 Manual Override
C. 時數與單價隨時可覆寫並標記；官方 API 只是預設值
D. Not yet defined
X. Other (please specify)

[Answer]: B. 時數可覆寫；官方 API 缺價或失敗時，單價也可覆寫並標記 Manual Override

## Q16. 超支警告要讓三位角色「看得到」，最低可測的形式是什麼？

> Reviewer Finding 2（Major）：未指定送達機制則 QA 無法寫通過／不通過。

A. 成本畫面內的視覺標示（總額變色或橫幅），不另外發通知
B. 成本畫面標示，加上進入產品時可見的站內通知
C. 成本畫面標示，加上電子郵件
D. Not yet defined
X. Other (please specify)

[Answer]: B. 成本畫面標示，加上進入產品時可見的站內通知
