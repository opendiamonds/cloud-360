# User Stories 適用性判定 — AI-DLC 與 GitHub Projects 的進度同步

<!-- Stage: user-stories（Inception 2.4）· Record: 260822-gh-projects-sync
     本檔為 stage 檔 Step 2 要求的 CONDITIONAL 適用性判定紀錄。 -->

## 判定

**Execute。**

依 `project.md ## Corrections` 的既有教訓——CONDITIONAL stage 的適用性必須**逐項對照該 stage 的 condition 條款**並把理由記入 diary，不得憑 feature 表面大小直覺 skip——下方逐條列出判定，包含**不成立**的那一條與**看似支持 skip** 的那一條。

## 逐項對照

| condition 條款 | 判定 | 依據（可逐字複驗） |
| --- | --- | --- |
| user-facing features | **命中** | 看板即可見交付面。FR-A1（item 首次出現）、FR-B1（Status 四格）、FR-F1（自訂欄位 `requirements-analysis (2.3)`）、FR-F4（`parked @ <stage>`）、FR-H1（README 指路段落）、FR-G1（待人審的反向 PR）、FR-E1／E3（通報 issue 的內容）、NFR-O2（「等待人工裁決」與「已暫停」兩份獨立清單）——全部是人會看到並據以行動的東西 |
| multiple personas | **命中** | `intent-statement` 明列四類受益者，且各自的**可觀察結果不同**：開發者（FR-B 自動更新）、協作者（FR-G3 手動操作不被彈回）、只看看板的觀看者（FR-A1 第一次看得到 intent 存在）、未來的自己（FR-E1 留痕 ＋ FR-F1 stage 欄位） |
| complex business logic | **命中** | FR-B 對照表為 5 條判定規則 ＋ 1 條優先覆寫（`Parked`）＋ 2 格永不寫入；同一組排除集合同時出現在 FR-B6／FR-D2／NFR-O2 三處；另有寫入前回讀（FR-C）、每日對帳（FR-D）、三道防迴圈（FR-G4）、`getField()` 解析語意複製（FR-J6） |
| cross-team coordination | **未命中** | 單一決策者（`scope-document` 的排序即以「單一決策者、全 Must、依賴序已定」為由不做 WSJF／RICE 評分） |

## skip 條款的逐條檢視

skip 條款為「pure refactoring／isolated bug fixes／infrastructure-only／developer tooling」。前三項顯然不成立（本 intent 新增行為、非修 bug、含可見面）。**第四項需要正面回答，因為 codekb 的 `business-overview.md` 明白寫著「本機制的使用者是開發流程本身而非產品終端使用者」**——那句話單看確實指向 skip。

不採為 skip 理由，原因有二，兩者都可從已核可產出複驗：

1. **skip 條款針對的是「無可見面、無 persona 分化」的工具**，不是「使用者恰好是開發團隊」。本機制的可見面是一塊多人共讀的看板，且四類受益者在其上的**行動不同**（開發者不再手動改、協作者拖卡片、觀看者只讀、維運者處理通報與審 PR）。
2. **本 intent 的核心價值是可信度，而可信度是 perception 層的性質。** `intent-statement` 記載的既成事實是「看板上有 item 標記為 In review、對應 issue 其實已關閉」——**故障不是機制沒跑，是人不再相信它**。需求層（requirements.md 的 40 FR）表達的是機制做什麼；「誰看到什麼、什麼情況下他會停止相信這塊板子」只有故事層驗得到。這正是本 stage 能加最多價值的地方。

## 執行時故事最能加值的區域

1. **可信度的失效面**：FR-C1 中止寫入、FR-J2 分岔通報、FR-J3 跳過不寫、FR-G3 暫停覆寫——這四條的共同意圖是「寧可不寫，不可寫錯」，但**它們各自在看板上留下的痕跡不同**，觀看者能否分辨「機制刻意沒寫」與「機制壞了」是故事層的問題。
2. **`Parked`／`[S]`／`— SKIP` 三種「沒在動但原因不同」的呈現**（FR-B3、FR-B6、FR-F3、FR-F4）：需求已規定差別不得抹平，但「差別要讓誰看出來、看出來要能做什麼」未定。
3. **反向同步的人審環節**（FR-G1、FR-G3）：唯一一個人與機制互相等待的環節。
4. **通報 issue 的可行動性**（FR-E3）：三項資訊是否足以讓收到的人知道下一步。

## 本判定引用的 brownfield 掃描產出

- **`component-inventory.md`**：其「11 組 gh-aw agentic workflows」表（`:208-249`）證明本 repo 的流程層已有 11 支 workflow 各自有觸發、排程、timeout 與 safe-outputs——本 intent 是**在一個已成熟的流程層上再加一支**，不是打通新架構。這支持「complex business logic」命中（新機制要與既有 11 支共存、不搶 concurrency、不重複 `name`），也支持本判定不把它當成 bootstrap 型工作。
- **`business-overview.md`**：其「本機制的使用者是開發流程本身而非產品終端使用者」一句是本判定必須正面回答的反證，處置見上一節。

## 替代覆蓋（若未來重估為 skip 時的對照）

無。requirements.md 不涵蓋上述四區——它的 AC 全是機制行為的二元判準，沒有任何一條表達「某個角色看到之後能做什麼」。
