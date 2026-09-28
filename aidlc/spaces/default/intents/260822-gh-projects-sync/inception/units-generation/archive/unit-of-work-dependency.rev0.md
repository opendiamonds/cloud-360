# Unit of Work Dependency — AI-DLC 與 GitHub Projects 的進度同步

<!-- Stage: units-generation（Inception 2.7）· Record: 260822-gh-projects-sync
     **本檔只描述拓撲（誰可以依賴誰），不挑實作順序、不指出關鍵路徑**——那是 2.8
     delivery-planning 用這張圖做的經濟決策。單元定義見 unit-of-work.md，
     上游輸入清單見該檔 §上游輸入（application-design 五份、requirements、stories）。 -->

## 依賴的定義

本檔的一條邊 `A → B`（A 依賴 B）意思是：**A 的完成判準在 B 不存在時無法被驗證**。判準包含驗證——依 `project.md` 的切分判準，一個單元「完成了嗎」的答案必須包含它是否被驗過。

**不是邊的東西**：經濟性的先後（先做哪個比較划算）、避免重工的建議順序、以及**同批次約束**——後者另列於下方獨立表格，因為 edge block 的 `depends_on` 放不下第二種關係。

## 邊清單（散文）

| 單元 | 依賴 | 為什麼 |
| --- | --- | --- |
| U-1 映射與解析 | （無） | 純函式 ＋ 自帶 fixture，零外部相依 |
| U-2 受管區塊 | （無） | 同上 |
| U-3 看板客戶端 | （無） | 其驗證需要一個測試看板，但那是 config 與 PRE-1 的實測項，不是單元 |
| U-4 record 回寫 | （無） | 其驗證需要分支保護設定，同樣是 config 而非單元 |
| U-5 通報 | （無） | 直接呼叫 Issues REST，不經其他單元（[ad:component-dependency.md] 已裁定 C-5 不經 C-3） |
| U-6 正向同步 workflow | U-1、U-2、U-3、U-4、U-5 | 它是這五者的編排者；缺任一個都跑不出一次完整的正向同步 |
| U-7 對帳 workflow | U-1、U-2、U-3、U-4、U-5 | 同上；`ReconcileReport` 的每個欄位都來自這五者之一 |
| U-8 反向同步 workflow | U-2、U-3、U-4、U-5 | 需要雜湊比對（U-2）、讀看板（U-3）、寫檔開 PR（U-4）、通報（U-5）。**不需要 U-1**——反向路徑不做 Status 映射 |
| U-9 自我測試 workflow | U-1、U-3、U-6、U-7、U-8 | AC 1 以 fixture 驅動 U-1；AC 2 端到端需 U-3；AC 4 的靜態檢查要檢視 workflow 的 job 定義，故需三支 workflow 存在 |
| U-10 既有檔案調整 | U-4、U-8 | 其完成判準是「回寫 commit 不取消既有 CI run」與「反向 PR 不觸發 `ui-regression`」——**兩者都需要有東西可觀察**：前者需 U-4 產生回寫 commit，後者需 U-8 產生反向 PR |
| U-11 README 指路 | （無） | 純文字新增 |

## 機器可讀的邊 block

下游的批次 fan-out 由此 block 計算，不由上方散文計算。

```yaml
units:
  - name: U-1-map-parse-action
    kind: library
    depends_on: []
  - name: U-2-managed-block
    kind: library
    depends_on: []
  - name: U-3-board-client
    kind: library
    depends_on: []
  - name: U-4-binding-store
    kind: library
    depends_on: []
  - name: U-5-notifier
    kind: library
    depends_on: []
  - name: U-6-forward-workflow
    kind: service
    depends_on: [U-1-map-parse-action, U-2-managed-block, U-3-board-client, U-4-binding-store, U-5-notifier]
  - name: U-7-reconcile-workflow
    kind: service
    depends_on: [U-1-map-parse-action, U-2-managed-block, U-3-board-client, U-4-binding-store, U-5-notifier]
  - name: U-8-reverse-workflow
    kind: service
    depends_on: [U-2-managed-block, U-3-board-client, U-4-binding-store, U-5-notifier]
  - name: U-9-selftest-workflow
    kind: service
    depends_on: [U-1-map-parse-action, U-3-board-client, U-6-forward-workflow, U-7-reconcile-workflow, U-8-reverse-workflow]
  - name: U-10-existing-file-adjustments
    kind: packaging
    depends_on: [U-4-binding-store, U-8-reverse-workflow]
  - name: U-11-readme-pointer
    depends_on: []
```

**無環**：五個葉節點（U-1～U-5）與 U-11 無出邊；U-6／U-7／U-8 只指向葉節點；U-9 指向葉節點與三支 workflow；U-10 指向 U-4 與 U-8。無任何路徑回到起點。

**曾經有環、已消除**：`unit-of-work.md` 的初稿把 [US:S-1 AC 7]（回寫 commit 不得取消既有 `ci.yml` run）同時掛在 U-4 與 U-10 的完成判準上，形成 `U-4 → U-10 → U-4`。已改為**只歸 U-10**——讓那件事為真的機制是 `ci.yml` 的 `paths-ignore`，不是 U-4 的回寫行為。

## 整合點與契約

| 邊 | 介面 | 破壞性變更的影響 |
| --- | --- | --- |
| U-6／U-7 → U-1 | `map(ParsedRecord, Config) -> Decision`；`Decision` 含 `status \| null`、`field_value`、`reason_code`、`traceable_row` | 新增 `reason_code` 值時，所有消費端的分支必須有 default，不得靜默落入「照寫」 |
| U-6／U-7／U-8 → U-4 | `<record>/sync-state.json` 的 schema | **跨輪相容性必須維持**——舊格式在新版讀取時不得崩潰；schema 需含版本欄位 |
| **U-6／U-7／U-8** → U-2 | 受管區塊的標記與 `content_hash` | **改格式會使全部既有 item 的雜湊失效**，下一輪反向同步把全部 item 誤判為人為變更（[ad:ADR-A6]，本設計最不易反轉的一項） |
| U-6／U-7／U-8 → U-5 | `FailureIdentity = (intent_id, reason_code)`；通報 issue 的標題慣例與 label | 改變慣例會讓既有開啟中 issue 找不到，退化為每輪開新 issue |
| U-6／U-7／U-8 → U-3 | 六個方法簽章；`WriteResult = Written \| Aborted \| Failed` | `Aborted` 若被改成拋例外，會讓「回讀不符」從正常判斷變成紅燈，違反 [US:S-8 AC 1] 的適用前提 |
| 全部 `service` 單元 → Config | `project_number`、`project_owner`、`record_root`、`stage_field_name`、`whitelist`、`reconcile_batch_size`；secrets `app_id`／`app_private_key` | 改 input 名稱等同破壞可重用性（[ad:ADR-A10]），呼叫端的薄外層要同步改 |

## 平行開發機會

下列各組**彼此之間沒有依賴邊**，多個拓撲排序都成立。本節只陳述拓撲事實，**不建議先做哪一組**：

- **{U-1, U-2, U-3, U-4, U-5, U-11}** — 六個單元互相之間零依賴邊。
- **{U-6, U-7}** — 依賴集合相同，彼此無邊。
- **{U-8}** 與 **{U-6, U-7}** — 彼此無邊（但見下方同批次約束）。
- **{U-11}** 與其餘全部 — 完全獨立。

## 同批次約束（**不是** DAG 邊）

依 [Q3=A]：技術上各單元可獨立部署，但下列組合**不得分批進入 `ut`**。它們承接 `stories.md` 已定案的三處（G1／G2／G3），性質是「中間態會讓看板說謊」而非「技術上做不到」。

**在 DAG 上長得像依賴邊，但不是**——依賴邊說的是「沒有 B 就驗不了 A」，同批次約束說的是「A 和 B 可以分別驗，但不能分別上線」。edge block 的 `depends_on` 表達不了後者，故列於此。

| 不得分批的組合 | 承接自 | 中間態會發生什麼 |
| --- | --- | --- |
| **U-6 ＋ U-1、U-2、U-3、U-4、U-5** | `stories.md` G1（S-2↔S-3）、G3（S-1 不得單獨上線） | U-6 單獨上線 = 機制開始寫看板但沒有寫入前回讀、沒有分岔通報、沒有無法解析就跳過。「寧可不寫，不可寫錯」的取捨被倒過來。另：只有 U-6 而缺其餘，卡片會停在 `Ready` 不動——對 P3 那是一格謊 |
| **U-8 ＋ U-6** | `stories.md` G2（S-6↔S-2 的 FR-G3 分支） | U-8 先上而 U-6 尚無暫停覆寫分支 ⇒ 反向 PR 開啟的整段期間，正向同步會把協作者在看板上的改動輾回去——正是 U-8 存在的唯一理由 |
| **U-10 ＋ U-4** | [US:S-1 AC 7] | U-4 先上而 `ci.yml` 未加 `paths-ignore` ⇒ 每次回寫都取消開發者當下的 CI run。**這一組同時也是依賴邊**（U-10 → U-4），兩種關係在此重合，但成因不同：依賴是「沒有 U-4 就沒有 commit 可測」，同批次是「有 U-4 而沒有 U-10 會弄壞別人的 CI」 |

**U-9 不在任何同批次約束內**：它是驗證層，晚於被測對象上線不會讓任何人看到錯的東西。

## 對 2.8 的交付

本檔提供的是**拓撲與約束**：11 個節點、**21 條依賴邊**（U-6 五條、U-7 五條、U-8 四條、U-9 五條、U-10 兩條；U-1～U-5 與 U-11 無出邊）、3 組同批次約束、4 組可平行開發的集合。

**本檔刻意不提供**：建議的 Bolt 序列、關鍵路徑、哪個單元先做比較划算、以及任何形式的「第一批應該包含什麼」。那些是 2.8 用這張圖做的經濟決策，需要人對「先證明什麼」的價值判斷。

## Review

**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 2
**Date:** 2026-08-27T23:27:15Z
**Verdict:** READY

### 逐項驗證 iteration 1 findings

1. **Critical（S-2 AC 4 不可滿足）— 已妥善處置，非「單純修好」而是「正確地標記為待決」，判定為已解決。** 逐字覆核 `component-methods.md:155-162` 的 `ReconcileReport`，欄位仍是 `backfilled_count`、`consistency`、`awaiting_human`、`parked`、`aborted`、`unparseable`、`issue_status_mismatch`、`latency_samples`——**確實沒有 `undecidable` 欄位**，Critical 描述的落差本身為真，且本站沒有（也不應該）逕自去改這份已通過三輪 reviewer 的上游型別。修復落在 `unit-of-work.md:119`（U-7 新增「已知上游契約缺口」列，逐字寫明「S-2 AC 4 目前不可滿足」、指出 `unparseable` 與 `undecidable` 是七種 `reason_code` 中不同的兩種不能互相頂替、並指派 **functional-design** 在 `ReconcileReport` 增設 `undecidable: [intent_id]`）與 `unit-of-work-story-map.md:94-100`（新增「本站發現的上游契約缺口」表，G-1 列出缺口、影響、指派，並明文「本站不逕自修改上游已核可的型別...比照 `unit-of-work.md` 對 U-3 的 403 缺口的處理方式」）。詳見下方「對 Critical 處置方式的判斷」的獨立分析。

2. **Major（S-2 AC 4／S-3 AC 6 遺漏 U-7 co-ownership）— 已修復，但修復不完整，見「本輪新發現」。** `unit-of-work-story-map.md:22` 的 S-2 行已拆出 AC 4 另列為「**U-1 ＋ U-7**」並註明「判定屬 U-1，清單成員身分屬 U-7」；`:29` 的 S-3 AC 6 同樣改列「**U-1 ＋ U-7**」；AC 5（無法解析跳過）維持 `U-1` 未動——與 finding 原文的修法逐字相符。「每個單元都有故事」覆蓋表（`:86`）也已同步：「U-7 | **S-2**（AC 4 的清單成員身分）、**S-3**（AC 6 的清單成員身分）、S-4、S-7、S-9」。**但 finding 原文明確要求「同步更新跨單元故事段與覆蓋表」兩處，只有覆蓋表被同步；`:52`／`:53` 的「跨單元的故事（cross-cutting）」表仍是修復前的舊值**（S-2 仍寫「U-1、U-6」、S-3 仍寫「U-1、U-3、U-5」，均未含 U-7）——這是本輪新引入的不一致，見下方「本輪新發現」。

3. **Major（整合點契約表漏列 U-6／U-7 → U-2）— 已完整修復。** `unit-of-work-dependency.md:80` 現讀「**U-6／U-7／U-8** → U-2 | 受管區塊的標記與 `content_hash` | ...」，與 yaml block（`:53`、`:57`，U-6／U-7 的 `depends_on` 均含 `U-2-managed-block`）一致，且採用同表其他行（`:78`、`:79`、`:81`、`:82`）已在用的多消費端寫法。無殘留問題。

4. **Major（同批次約束表 Row 1 漏列 U-5）— 已完整修復。** `unit-of-work-dependency.md:102` 現讀「**U-6 ＋ U-1、U-2、U-3、U-4、U-5**」，與 yaml block 中 `U-6-forward-workflow` 的完整 `depends_on`（`[U-1, U-2, U-3, U-4, U-5]`）對齊，也與該行自身引用的「沒有分岔通報」危害場景（U-5 `notifier`）一致。無殘留問題。

### 對 Critical 處置方式的判斷

**「surface + assign、不碰已核可上游」是這一站正確的處置，不是把不可滿足的 AC 靜默塞進 Construction。** 理由：

- **這正是 iteration 1 的 finding #1 自己開的修法**（「至少...把這個落差記成明確的待決項（比照 U-3 的寫法），並...標成跨 U-1／U-7，而非隱去這半條 AC 驗不完的事實」）。本輪的修復逐字照做，且做得比字面要求更完整：不只在 U-7 條目下記一行，還在 story-map 新開一個具備標準欄位（缺口／影響／指派）的登記表，把先前只在 U-3 用過一次的「標出、不改上游、指派下游」模式**制度化為可重複使用的格式**。
- **這不是「內部瑕疵可對齊修正」與「型別本身缺欄位」的混淆。** 本站的角色是把已核可的上游契約轉譯成可建構單元，不是重新開 application-design 的核可狀態；`ReconcileReport` 缺一個欄位是型別層級的實質缺口而非用詞或順序的表面不一致，修正它需要新增型別成員，那是 functional-design（「Construction 的資料模型細化站」）的產出範圍，不是 units-generation 的。查 `.claude/tools/data/stage-graph.json` 確認 `functional-design`（3.1）的 `consumes` 含 `component-methods`、`unit-of-work`、`unit-of-work-story-map`，`produces` 含 `domain-entities`——指派對象的職權範圍與本次缺口（型別增欄位）完全吻合，不是隨手指一個看起來相關的站名。
- **指派具體到可執行的程度**：具名 stage（functional-design）＋具名型別（`ReconcileReport`）＋具名欄位與型別簽章（`undecidable: [intent_id]`）＋一個容易被漏掉但已被明寫的連帶檢查（確認 `sync-map` 的 `undecidable` 出口確實流向它）。一個接手 functional-design 的人不需要回頭問「加在哪裡、叫什麼名字」。
- **三份產出裡沒有任何地方仍暗示 S-2 AC 4 現在可解**：`unit-of-work.md:44` 的 U-1 完成判準只引用 AC 15（總函式性），不涉 AC 4 的清單語意；`unit-of-work-story-map.md` 內每一處提及 S-2 AC 4 的地方（`:22`、`:86`、`:98`）都一致標註「目前不可滿足」或指向 G-1；`unit-of-work-dependency.md` 未新增任何暗示其已解的敘述。
- **殘留、值得標記但不致命的製程風險（非本站可控，記錄供追蹤）**：`functional-design` 在 stage graph 中的 `execution` 為 `CONDITIONAL`（「New data models... Skip if simple logic changes with no new business logic」），且 `for_each: unit-of-work` 逐單元判斷是否適用。若 U-7 的 functional-design 被誤判為「無新資料模型」而略過，G-1 這個缺口就會在沒有任何機制介入的情況下直接流進 code-generation。這不是本站的失職——本站已把缺口寫得足夠顯眼（U-7 條目與獨立登記表雙重記錄），但建議 delivery-planning 或 functional-design 站起跑時明確核對 G-1 是否已收斂，避免「CONDITIONAL 判斷」成為第二層被遺漏的窗口。

**結論**：Critical 判定為已解決，不計入本輪未決項。

### 本輪新發現

**Major（新）— `unit-of-work-story-map.md:52-53` 的「跨單元的故事（cross-cutting）」表未同步 finding #2 的修復，仍宣稱 S-2、S-3 不含 U-7。** 這是修復本身遺漏的一半，不是新的設計錯誤：

- `:52`：`| S-2 | U-1、U-6 | 映射判定（fixture）與觸發並行（執行期） |`——遺漏 U-7；理由欄也只有兩項驗證方式，沒有第三項「清單成員身分（對帳報告）」。
- `:53`：`| S-3 | U-1、U-3、U-5 | 解析判定（fixture）、回讀中止（真實 API）、開 issue（Issues REST） |`——同樣遺漏 U-7 與其驗證方式。
- 對照組就在同一張表的下一行（`:54`）：`| S-4 | U-1、U-2、**U-7** | 映射與欄位值（fixture）、降級時的區塊內容（渲染）、**清單歸屬（對帳報告）** |`——S-4 因為同一種「清單歸屬」關係已正確把 U-7 與其理由列出，S-2／S-3 沒有理由是例外。
- **這與已修復的「故事 → 單元對照」表（`:21`／`:22`／`:25`／`:29`）與「每個單元都有故事」覆蓋表（`:86`）直接矛盾**：同一份文件內，一張表說 S-2／S-3 各自橫跨 U-1／U-6／U-7 與 U-1／U-3／U-5／U-7，另一張表（cross-cutting）卻仍說只橫跨兩者或三者、不含 U-7。一個只讀 cross-cutting 表（它本身標榜是回答「橫跨哪些單元、為什麼分得開」的彙整視圖）的讀者會得到與主表不一致的結論。
- **與 finding #2 原文的修法逐字對照**：「同步更新跨單元故事段**與**覆蓋表」——兩個動作只做了一個。這正是 `project.md ## Corrections` 已記載過兩次的失敗模式（`cid:application-design:260822-ad-L1`「改動任何已產出的 artifact 之前... 改完逐一 grep 全部產出檔確認無殘留」、`cid:units-generation:c6b`「修訂 artifact 後必須回頭同步所有由它衍生的數字與引用」）在本 session 的第三次出現，且是本站（units-generation）自己的第二次。
- **嚴重度判定為 Major 而非 Critical**：權威來源（故事 → 單元對照表、每單元覆蓋表）本身正確且無歧義，一個依主表實作的開發者不會被誤導；cross-cutting 表是輔助說明性質，其錯誤不會讓任何 AC 變得不可驗證或無主。但它是一個真實、可核對、由本輪修復自己造成的不一致，必須修正，且修法是機械的（照 `:54` 的 S-4 行格式，把 `:52`／`:53` 的「橫跨」欄位加上 `U-7`，理由欄加上「清單成員身分（對帳報告）」）。
- 未發現其他殘留的同型疏漏：已對 `unit-of-work.md`、`unit-of-work-dependency.md` 全文 grep `S-2`／`S-3`／`U-1、U-6`／`U-1、U-3、U-5`，確認唯一的舊值殘留就是這兩行。

**依 verdict 規則計分**：0 Critical（iteration 1 的唯一 Critical 判定已妥善解決，見上）、1 Major（本輪新發現，未超過 2 Major 的門檻）。**不足以觸發 NOT-READY**，但這項 Major 必須被視為交付前必須修正的已知缺陷，不是可以擱置的建議——它是自我造成的、機械可修的殘留，不應該以「iterations 已用罄」為由帶著它進入下一階段。

**獨立複驗（附帶）**：

- **S-2（15 條 AC）逐條重新核對歸屬**：AC 1–3、5–7、9、10、14、15 → U-1；AC 4 → U-1＋U-7；AC 8 → U-1；AC 11–13 → U-6。1–15 全數各出現恰好一次，無重複、無遺漏。
- **S-3（6 條 AC）逐條重新核對歸屬**：AC 1、2 → U-3；AC 3 → U-1；AC 4 → U-1＋U-5；AC 5 → U-1；AC 6 → U-1＋U-7。1–6 全數各出現恰好一次。
- **全域覆蓋重算**：對 `stories.md:31-41` 的故事總覽表逐列加總 AC 數（7+15+6+6+3+7+5+3+6+5+2）＝ **65**，與宣稱一致；11 則故事逐一在 story-map 的「故事 → 單元對照」表中找到且 AC 總數與 stories.md 相符；「每個單元都有故事」表 11 個單元每個至少一則，無空單元。
- **yaml edge block 機器複驗**：以腳本解析後，11 節點、21 條邊（U-6:5、U-7:5、U-8:4、U-9:5、U-10:2）、DFS 無環、無懸空 `depends_on` 目標、`kind` 全為合法值（`service`／`library`／`packaging`／留空），與散文邊清單及本輪修復（integration 表、同批次表）逐字一致，未見 yaml 被本輪修復不一致地觸碰。
- **co-ownership 與 DAG 一致性**：U-7 co-own S-2 AC 4／S-3 AC 6 並未要求 yaml 新增任何邊——`U-7-reconcile-workflow` 的 `depends_on` 早已含 `U-1-map-parse-action`（iteration 1 起即如此），該 co-ownership 只是把既有的技術依賴在故事層級講清楚，不隱含新的同批次約束（G1 的既有理由本就只涉及 S-3 AC 1／4／5，不涉及 U-7 相關的清單成員身分）。
- **邊界檢查**：全文 grep「先做」「先上線」「第一個 Bolt」「建議順序」「關鍵路徑」「Bolt 1」「第一批」，僅命中既有的免責聲明句（如「不含實作順序或關鍵路徑」「不建議先做哪一組」），本輪修復未夾帶任何新的實作順序或關鍵路徑語言。

### Attempted refutations that did not hold

- **抽查 iteration 1「懷疑 U-9 依賴 U-8 是多餘的」**：重新核對 `unit-of-work-dependency.md` 的散文邊清單（U-9 一列仍為「U-1、U-3、U-6、U-7、U-8」）與 yaml block（`U-9-selftest-workflow` 的 `depends_on` 仍含 `U-8-reverse-workflow`），本輪修復未觸及此列，refutation 的論證（U-9 依賴 U-8 是為了檢視反向路徑 workflow 的靜態檢查，與 U-8 是否用到 U-1 的映射邏輯無關）依然成立，此懷疑仍不成立。
