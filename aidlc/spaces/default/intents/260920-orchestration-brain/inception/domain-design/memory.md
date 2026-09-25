<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-09-25T10:46:59Z — **使用者的重新框定要先查證是否等價，查完常常比表面小**。E2 的回覆（「一個專案，多個需求……需求不用被完整紀錄，摘要即可」）看起來是推翻已核可的三層階層，逐字比對後發現其中「一個系統一份 drawio 架構圖、一份架構圖多個 tab」**已經是 `[RA:FR9.1]` 的原文**（「一個系統對應一份架構圖檔與其中多張圖」），完全不是新東西；真正新的只有「需求」這個成分。而使用者自己那句「不用被完整紀錄」正是在避開建完整實體。若當初直接當成「推翻階層」處理，就會去動 5 份已核可產出而其中大部分根本不需要動。
- 2026-09-25T10:46:59Z — **「不用錢」有時是技術不可行而不是價格問題**。使用者問「openrouter 沒有免費的模型嗎」，查 OpenRouter 的 API reference 與 FAQ 兩處後確認它**沒有 embeddings 端點**（只有 `chat/completions` 與 `generation`，兩頁對 embedding 零提及）。所以那些 `:free` 模型是對話模型，產不出 pgvector 要存的向量。這個區別重要：回答「OpenRouter 的免費模型不夠好」會是錯的，正確答案是「那條路不存在」。

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->
- 2026-09-25T10:46:59Z — **`upstream-coverage` 的 `team-practices` 缺口第二次出現，而第二次又挖出真東西**。refined-mockups 那輪補它時挖出 `react-hooks/set-state-in-effect` 的兩層抓取形狀；這一輪補它時挖出 `team.md` 的**後端分層規則直接約束六個元件的內部形狀**——新模組一律三層（router → service → 純函式）、純運算下沉到不讀 DB 的函式，而我原本的 `components.md` 完全沒提。這條還順勢指出 `IntentRouter` 的門檻判定與 `WorkOrchestrator` 的狀態轉換是純運算，因此正是 property-based 測試的落點。教訓：這個 sensor 的 `team-practices` 項不是形式，它兩次都指向我漏掉的真約束。
- 2026-09-25T11:53:59Z — **我在同一份產出裡寫了互相矛盾的兩句話，而六項自檢全部沒抓到**。`components.md:242` 的 `ProjectHierarchy.behaviour` 寫「讀、建立、修改、刪除一律經 `require_story_action`，**不得有任何繞過該 dependency 的路徑，含同進程直呼 service 層**」，而同一份檔的機讀目錄自己宣告 `SessionContext --sync--> ProjectHierarchy` 與 `WorkOrchestrator --sync--> ProjectHierarchy`——`sync` 就是同進程呼叫。**兩句話直接對撞，而且是我自己在同一份檔裡寫的。** 為什麼六項自檢沒抓到：自檢 2（契約端點三問）檢查的是**欄位與方法有沒有人寫／讀／清**，自檢 5（跨檔傳播）檢查的是**同一事實在各檔是否一致**——兩者都是「有沒有交代」與「跨檔是否一致」，沒有一項檢查「**同一份檔內的 behaviour 敘述與 depends_on 宣告是否自相矛盾**」。可執行補強：對每個元件，把它 `behaviour` 裡的每一條禁令，拿去對照它自己的 `dependents` 清單——若某個禁令的形狀（如「不得同進程呼叫」）與任何一條 `style: sync` 的入邊衝突，那就是矛盾。這條檢查零成本，而它抓到的是一個授權繞過。
- 2026-09-25T11:53:59Z — **`ADR-0006` 在本站兩份產出中出現 0 次，而它是 hard constraint**。`project.md` 逐字要求「對每一項變更檢查 ADR-0006 security baseline 的四個面向」且「涉及 IAM／權限矩陣／網路暴露／稽核記錄的變更，須在該 stage 產出中明列 security 影響與處置，不得僅以『已有 ADR-0006』帶過」。本站動到其中三個面向（`K1`／`K2` 是 IAM、記憶可見範圍與稽核是 audit logging、Redis ＋ Ollama 是 network exposure），卻一張表都沒有。**這與我在 user-stories 自己抓到的 PBT 缺口是同一類**——hard constraint 在某一站沒有落點，而該站的自檢清單裡沒有「逐一對照本專案的 hard constraint」這一項。六項自檢沒有這一條，所以兩次都是靠別人（或事後）發現。

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-09-25T10:46:59Z — **`EmbeddingPort` 存 `embeddingModel` 是為了讓不相容變成結構上不可能，而不是靠紀律**。fastembed 不支援 bge-m3，但支援同為 1024 維的 `multilingual-e5-large`——維度剛好對上，所以 pgvector 欄位可共用。這個「剛好對上」很危險：它讓兩個不同向量空間的向量**寫得進同一個欄位而不報錯**，相似度檢索會回垃圾。處置是每列存 model id、檢索只比對同一 model id。代價是多一個欄位與一道過濾；換到的是這個錯誤無法靜默發生。
- 2026-09-25T10:46:59Z — **三個 Port 實作 ＋ 大聲失敗，而不是自動降級**。使用者要「本機有 Ollama 走 Ollama、沒有走 fastembed 或退回全文，讓使用者自己選」。自動偵測並降級聽起來更方便，但向量與全文的檢索結果差異大，靜默切換會讓「為什麼找不到我的記憶」無法除錯——而本 repo 最貴的既有教訓正是靜默降級（`N8N_USER` 從未寫入導致架構圖 icons 靜默退回灰底佔位圖）。故加上「偵測不到選定提供者時大聲失敗並列出可選值」這條我自己的約束。
- 2026-09-25T11:53:59Z — **技術選型進了本站的 ADR，而 stage 檔明文說技術棧不屬這一站**。ADR-007／008 選了 pgvector、Ollama、bge-m3、fastembed 並改了 DB image，而 stage 檔逐字寫「it does not choose the tech stack or NFR patterns — those belong to the NFR and infrastructure stages」。審查指出的不一致很尖銳：**同一份產出裡，我把 `IntentRouter` 的路由模型正確地延後給 `nfr-requirements`，卻把記憶層的向量技術就地定案了**。兩者都是技術選型，處置卻不同。真正的原因是使用者在 E7 直接選了 pgvector——但那應該被記成「使用者的技術偏好，待 infrastructure-design 落實」，而不是本站的 ADR，且無論如何都該揭露這個越界。教訓：當使用者的答案把一個超出本站 charter 的決定交到手上時，記錄它但要標明它的正確落點，不要用一個 ADR 把它吸收成本站的決定。

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
- 2026-09-25T10:46:59Z — 自檢 2 查出三處缺口，**全部在「誰清」與「誰讀」**，與 requirements-analysis 那輪「寫入端最容易漏」剛好相反：DG-1 稽核事件在其記憶被 90 天清除後的去向（`[RA:FR4.5]` 與 `[RA:FR4.7]` 兩條已核可需求在此交會且互相拉扯）、DG-2 `Project`／`System` 刪除的 cascade（會讓 `[US:AC9.1.4]` 的不變量在**執行期**被打破，而遷移當下是滿足的）、DG-3 `DiagramChangeRecord` 無讀取端（使用者定案此選項的理由逐字就是一個讀取端，而它不存在；本 repo 已有 `estimate_audit_events` 只寫不讀的同型前例）。三項皆不自行定案，指派 `functional-design`（H-7）。
- 2026-09-25T10:46:59Z — **`OQ-1` 被指派給本站但本站未定案**，如實記載為未完成的指派而非已解決。它是「切回共享時獨立那段的處置」——屬對話歷程的保留語意，不是元件邊界問題；`[DD:E6]`=A 的單一 key ＋ TTL 已決定外框（兩段都在同一 key 下、一起到期），剩下的保留／捨棄／可回溯需與 `functional-design` 的歷程 schema 一併決定，故轉移至 `units-generation`（ALWAYS）。
- 2026-09-25T10:46:59Z — Ollama 的 2GB RAM 與 bge-m3 的 1.2GB 取自一般認知，**未在 staging 主機實測**，而 `DEPLOY.md`／`LOCAL-DEV.md` **完全沒有記載該主機的 RAM／CPU**。本 intent 已要往那台機器上加第 5（Redis）與第 6（Ollama）個服務，而沒有任何文件能回答「加得下嗎」。
