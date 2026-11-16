# User Stories Assessment — 統一入口大腦

<!-- Stage: user-stories（Inception 2.4）· Record: 260920-orchestration-brain
     本檔記錄「本 intent 是否需要使用者故事」的判定與理由。
     stage 的 execution 為 CONDITIONAL，故此判定為必做步驟。 -->

## 決定

**Execute**（執行，不跳過）。

## 判定依據（逐項對照 stage 的 condition 條款）

stage 檔的 condition 逐字為：「Execute when user-facing features, multiple
personas, complex business logic, or cross-team work is involved. Skip for pure
refactoring, isolated bug fixes, infrastructure-only changes, or developer
tooling.」四項執行條件逐一判定：

| 條件 | 判定 | 依據 |
|---|---|---|
| **user-facing features** | **成立** | 本 intent 新增一個統一入口頁（能力 1 的唯一載體）、脈絡列、子頁面的「另開新對話」入口、成本答案的結構化卡片。rough-mockups 已產出線框 ＋ 5 條使用者流程並通過核可（原寫「13 格」，修訂 2／3 為能力 11／12 補到第 27 節，實算 **27 格**；此判定不因格數改變） |
| **multiple personas** | **成立** | `stakeholder-map.md` 確認 **4 類**關係人，其中 3 類為直接服務對象（架構設計者、評估／稽核者、成本／FinOps 關注者）、1 類為間接（管理者／平台維運者）[Q2][Q10][Q12][Q14] |
| **complex business logic** | **成立** | 意圖識別與信心門檻判定（FR1.3／FR1.6／FR1.7）、多意圖拆解為 N 個工作項（FR5.1）、多輪對話的指涉詞解析（FR6.1）、三種記憶的授權模型（FR4.3／FR4.3a／FR4.3b）、成本 job 五種狀態事件的轉譯（FR10.4）。不是 CRUD |
| **cross-team work** | **不成立** | `[Q8]` 確認單一決策者、無其他關係人、不需對外回報節奏（`C-O3`） |

四項排除條件（pure refactoring／isolated bug fixes／infrastructure-only／
developer tooling）**皆不成立**：本 intent 建立新的核心資料模型（`projects`／
`systems`）、新的使用者入口與新的互動模型，不是任何一種維護性變更。

**四項執行條件中三項成立，四項排除條件皆不成立 → Execute。**

## 故事最能發揮價值的地方

判定為 Execute 後，本站的故事在下列三處最有作用（其餘能力多半是既有形狀的延伸）：

1. **能力 1（意圖識別與工作交辦）的失敗面。** FR1.3／FR1.6／FR1.7 定義了
   「信心不足時不交辦、改反問」這條路徑，而「意圖識別準確率」是三個成功指標
   之一——一個**會失敗且被量測**的能力。故事與 AC 是把那條失敗路徑寫成可驗收
   行為的地方；線框第 12、13 節已有畫面，但畫面不說明「什麼情況下該走這條」。
2. **能力 3（另開新對話）的邊界。** `[RA:R4]` 定案「對話歷程獨立、作業對象沿用」，
   這個組合只有寫成故事與 AC 才看得出它與能力 2（共享脈絡）的分界在哪。
3. **四個 persona 的實際差異。** 三個直接服務對象在需求層共用同一組 FR，但他們
   進入系統的路徑不同（架構設計者從產圖、評估者從檢視結果、成本關注者從提問）。
   故事是唯一會逼出「這三條路徑是否真的都成立」的產出。

## 本站承接的三項指派（來自 requirements-analysis）

這三項**不是故事**，是量測用的資料交付物，但 requirements-analysis 把它們指派
給本站，且都附了轉移目標（本站為 `CONDITIONAL`，skip 時轉 `build-and-test` 3.6）：

| 指派 | 內容 | 綁定 |
|---|---|---|
| NFR1 | ≥ 50 筆人工標註的意圖測試集（「一句輸入 → 應交辦給哪個能力」的配對） | 準確率 ≥ 80% |
| NFR2 | N 個具名的跨頁面切換情境清單 | 保留率 ≥ 95% |
| NFR11 | 跨功能任務情境集合 ＋ 現行 UI 的切換次數基準（人工清點） | 切換次數嚴格少於基準 |

它們與故事的關係見本站問題檔的 U3。

## 修訂 1：三個新群組的條款重判（2026-10-02T03:25:44Z）

`scope-document.md` 修訂 3／4 新增能力 11（專案系統資訊需求頁）與能力 12（專案成員
管理），`feasibility` 的回跳另把併發隔離定為能力 1／8 的實作前置（`[F17]`＝A）。
三者在本檔原判定之後才出現，故逐一重判 condition——**不是沿用「本站已判 Execute」
就把它們默認納入**：

| 新群組 | 命中的執行條件 | 判定 |
|---|---|---|
| **US11**（能力 11） | user-facing features（`wireframes.md` §15–§18、§22 新增線框）、complex business logic（兩處未填計數的一致性、MCP 通道的身分不被冒用） | **Execute** |
| **US12**（能力 12） | user-facing features（§23–§26）、complex business logic（`project_owner` 帳號被移除時的自動改選、兩層授權串聯、唯一成員的守門） | **Execute** |
| **US13**（能力 1／8 的前置） | **這一項需要說明**：它看起來像 `infrastructure-only changes`，那是排除條件 | **Execute**，理由見下 |

**US13 為什麼不是 infrastructure-only。** 它的失敗是**使用者可見**且有真實受害者——
實測顯示一個使用者會收到**另一個使用者**產生的架構圖 XML。那是跨帳號的內容外洩，
屬 ADR-0006 的 IAM 面，不是效能或整潔問題。若照「模組層全域變數改成 per-key dict」
這個**實作形狀**判，它確實像基礎設施變更；照**可觀察後果**判，它是最該寫成故事的
一則。判準取後者：寫成故事才會讓 `delivery-planning` 以它的真實性質排序，寫成技術債
會被排到後面（`[D-14]`）。

**persona 集合不變，但 `P-4` 多了第二面。** 修訂 1 沒有新增第五個 persona
（`[Q2]` 鎖定四類，新增會構成本站擅自擴大已核可範圍），但 `FR12.5a`／`AC12.3.3`
的 actor 是**系統管理者停用帳號**——原四個 persona 沒有任何一個能合法承載它。
處置是擴充 `personas.md` 的 `P-4` 邊界欄，見該檔。這項由本站 mob 的設計 agent
查出（`[D-01]`），不是我自己發現的。

**三項 NFR 指派（NFR1／NFR2／NFR11）不受修訂 1 影響**：它們綁的是能力 1 與跨頁面
切換的量測，與能力 11／12 無關；其轉移目標不變。

## Assumptions & Open Questions

- 本判定只涵蓋「是否需要故事」，不涵蓋故事的切分與數量——那由本站的問答決定 [assumption]
- 管理者／平台維運者為**間接**服務對象（`[Q10]`＝C），其需求由長期記憶或既有
  稽核紀錄承載、不經由共享工作階段。他是否在本 intent 取得故事，是本站的待決
  問題（見問題檔 U1），不由本判定預設 [assumption]
- **修訂 1 的三個新群組未重跑「故事最能發揮價值的地方」那一節**（2026-10-02T03:25:44Z）：
  該節的三項判斷針對能力 1／3 與四個 persona 的路徑差異，修訂 1 不推翻它們，
  但也沒有為能力 11／12 另做同等分析。若 `delivery-planning` 需要那個輸入，
  它在 `stories.md` 的優先度總覽與各群 DoD 裡有等價資訊 [assumption]

<!-- 修訂 1 定稿：彙整確認於 2026-10-02T03:34:04Z 取得（Looks correct），
     Summary Authorization Id d7207b11010b9e92cabc0694a8dc782f4de30f91e152c4d30b15b5ef1e5e68cc。 -->
