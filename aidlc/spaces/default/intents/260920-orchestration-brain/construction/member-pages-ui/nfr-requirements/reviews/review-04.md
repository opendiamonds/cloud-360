## Review

**Verdict:** READY

**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-11T00:47:05Z
**Iteration:** 2

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Critical | `construction/member-pages-ui/nfr-requirements/tech-stack-decisions.md` > §一 `TS-U24-6`、§四 `HO-U24-1`–`-3`；`traceability.json` > `reverse` 的 `TS-U24-6` | 已修，且修法本身複驗成立。排序事實重新實測：`bolt-plan.md:494` 逐字 `B1 → B10 → B2 → B11 → B3 → B12 → B13 → B4 → …`、`:480` `U24`→**B12**、`:479` `U23`→**B13**、`unit-of-work.md:426` 的 `U24` 依賴逐字只有 `U19`／`U3`——四項引用的**事實與定位皆正確**。決定改由 `[N4]`=A 交人工裁決（`U24` 自建、`U23` 之後沿用），`TS-U24-6` 與 `traceability.json` note 兩處同步改寫，`[F3]`=A 的原作答與選項本文未被回改（僅加 supersession 敘述），符合 `refined-mockups:c3`。結果是本單元在 B12 自給自足、不需改動任何已核可的 Bolt 順序，原先那條不可滿足的完成條件消失。另兩個被指名複驗的點：`HO-U24-2` 的目標**有效**——`construction/project-pages-ui/` 在磁碟上**不存在**（`U23` 一站未跑），`stage-graph.json` 的 `nfr-requirements` 為 `CONDITIONAL`、`code-generation` 為 `ALWAYS`，兩層轉移目標都寫對；`HO-U24-1`**足夠**——它把「做成可共用形狀」指派給本單元 `code-generation`，而 `U23` 在 B13 之後才動工，屆時元件已存在於原始碼，複用不需要額外契約 | 無 | Resolved |
| R-02 | Major | `construction/member-pages-ui/nfr-requirements/security-requirements.md` > §三之一 `SEC-U24-6`；`traceability.json` > `reverse` 的 `SEC-U24-6` | 已修。新增的 `SEC-U24-6` 是真正的**肯定**義務，且與 `SEC-U24-1` 的禁令不再無法區分——「完全不輸出」現在會讓它紅燈。不變量**可失敗**：`page.on('console')` 對三條路徑各斷言「至少一筆相符訊號」，缺一即紅。三條路徑逐一複驗為真實可構造：① 成員清單抓取失敗可由 Playwright abort route 構造；② 橫幅 403——`membership_router.py:311` 逐字 `Depends(require_story_action("K3", "view"))`，而前端以 `can('K3','view')` 為前置（`frontend-components.md:157`），故真實使用者不會自然拿到 403，但 `UIP-2` 本身就以攔截該端點為量測手段，以 stub 回 403 構造是同一個已採用的機制，非不可達；③ 列舉外角色值送出會由 Pydantic 回 `detail` 為錯誤物件陣列的 422，真實可得。選項代價（「生產環境沒有人在看 console」）已逐字寫進產出並明寫「不把『有 console 訊號』寫成『有監控』」 | 無（三條路徑之外的殘留另記為 `R-07`） | Resolved |
| R-03 | Major | `construction/member-pages-ui/nfr-requirements/performance-requirements.md` > §一 註記段；`traceability.json` > `coverage` 的 `NFR11` note | 已修，兩處同步。引用逐字複驗：`requirements.md:568-571` 確為「情境集合由 `user-stories`（2.4）與該站的故事同源產生；`user-stories` 為 `CONDITIONAL`，skip 時義務轉移至 `build-and-test`（3.6，`ALWAYS`）」，`:577-579` 確為「量測機制……落點 `build-and-test`」，`stories.md:533` 確為 `M-3`「跨功能任務情境集合 ＋ 現行 UI 的切換次數基準」，`:535-537` 確為「若本站被判定不適用而 skip……自動轉移」——定位比上一輪我自己寫的 `:536-538` 更精確。全站再掃 `build-and-test` 與「母體」兩個詞，無任何殘留把母體歸給 `build-and-test`。「把成員管理類情境加進母體」依 `project.md` 判為**無自然承接站**並送核可關卡，未填假目標 | 無 | Resolved |
| R-04 | Major | `construction/member-pages-ui/nfr-requirements/security-requirements.md` > §一 Audit logging 列（facade 方法數）、§五 自檢第 5 項（security 的「100」出現次數） | **只修了一半，兩處殘留。**（a）`security-requirements.md:26` 仍逐字寫「六個路由、**13 個** facade 方法逐一核對」——而 `R-04` 的 Location 欄明確指名「§一 Audit logging 列**與** `performance-requirements.md` §五之一」兩個落點；`performance-requirements.md:139` 已改為 17，`:26` 沒改。這不是計數瑕疵而是**覆蓋宣稱**：實測 `grep -c '^    def ' backend/services/membership_facade.py` = **17**，故該句仍少交代 4 個方法，正是原發現的實質內容。（b）自檢第 5 項事實 B 宣稱數字「由指令輸出」，但 security 的「100」**出現次數**寫 **3**，實測 `grep -o '100' security-requirements.md \| wc -l` = **6**（行數 3 是對的；questions 3/5、performance 12/17、tech-stack 3/3 皆相符，`200 列` 合計 4 相符）——八個數字裡一個仍與其宣告的指令不符。**我上一輪的一個子項，本輪判定作者的拒絕是對的**：`grep -c 'the row is never deleted' schema_rbac.sql` = **1**（只有 `:679`），我回報的 2 是較寬片語 `never deleted` 的結果（實測亦為 2），作者維持 1 並寫明兩者差別，正確；其採納的附帶發現也複驗為真（`:663` 逐字含「There is deliberately NO retention period here (unlike memory.memory_audit_events, NFR7.2)」與「Do NOT add a 90-day purge」，比 `:679` 更直接）。其餘數字全部複算相符：頂層 `def` 1、公開方法 12、舊 regex 13、路由 6、h2 performance 6／security 6／tech-stack 5 | 把 `security-requirements.md:26` 的「13 個 facade 方法」改為 17（或改寫成「公開 12 ＋ 模組層 1」並說明私有方法為何不需核對），並把自檢第 5 項 security 的出現次數改為 6；兩者皆由產生它的指令直接輸出 | Unresolved |
| R-05 | Minor | `construction/member-pages-ui/nfr-requirements/tech-stack-decisions.md` > §一 `TS-U24-5` | 已修。實測 `AdminPage.tsx:197` = `if (!res.ok) throw new Error(...)`、`:198-199` 為該註解、被引用的「不重抓的話，下一頁會靜默略過一個帳號」在 `:199`；同列 `:153`／`:179`／`:200`（`filter`）／`:201`（`setTotal`）／`:203`（背景重抓）全部複驗正確 | 無 | Resolved |
| R-06 | Minor | `construction/member-pages-ui/nfr-requirements/security-requirements.md` > §四 STRIDE 的 Denial of service 列 | 已修。該列現在寫出判定依據（零新端點、六個消費點皆要求已驗證身分——實測 `membership_router.py` 六個 `@router.*` 裝飾點、`require_story_action` 命中 9 次），並逐字寫出 `UIP-2` 的已揭露代價（「換頁密集時的固定請求開銷，且該端點對多數使用者永遠回空陣列」）與「本站未為它設界」。判定維持「否」的理由現在涵蓋請求量本身而非只涵蓋渲染成本 | 無 | New |
| R-07 | Minor | `construction/member-pages-ui/nfr-requirements/security-requirements.md` > §三之一 `SEC-U24-6` 的路徑列舉 | **`R-02` 的修法留下一條仍然靜默的失敗路徑。** `BR21.3` 的 statement 逐字是「橫幅抓取失敗**不對使用者顯示錯誤**；且權限不足屬永久失敗，不重試」——即**任何**橫幅抓取失敗都對使用者無聲。而 `SEC-U24-6` 只為「② 橫幅查詢收到 403」訂了 console 義務，橫幅查詢的**網路錯誤或 5xx** 既不對使用者說話、也無任何輸出義務，於是它同時滿足 `SEC-U24-1`（禁令）與現行 `SEC-U24-6`（三條路徑之外），構成 `construction.md` phase guardrail 逐字禁止的「silent failure」。這是列舉型要求的典型殘留：三條被點名的路徑之外沒有兜底句，而本站是 `[N3]` 的唯一落點 | 把 ② 擴為「橫幅查詢的任何非 2xx 與網路失敗」，或在 `SEC-U24-6` 補一句兜底（本單元每一條對使用者無聲的失敗路徑皆須輸出一筆受 `SEC-U24-1` 限制的 console 訊號） | New |
| R-08 | Minor | `construction/member-pages-ui/nfr-requirements/security-requirements.md` > `:46` 與 `:53` 兩個 `### 三之一` | **`R-02` 的修法把節號撞號。** `grep -nE '^#{2,3} '` 顯示 `:46`（`SEC-U24-5`）與 `:53`（`SEC-U24-6`）兩節都編為「三之一」，同一份檔內同一個節號指向兩段不同內容。目前尚無任何檔以「§三之一」交叉引用它（全站 grep 僅命中這兩個標題本身），故後果限於可讀性與日後引用歧義，但它是本輪新增動作直接造成的 | 把後加的那節改為「三之二」 | New |
| R-09 | Minor | `construction/member-pages-ui/nfr-requirements/tech-stack-decisions.md` > §四 `HO-U24-3` 的 `frontend-components.md:54-55` | `HO-U24-3` 寫「上游 `functional-spec.md:42` 與 `frontend-components.md:54-55` 的字面仍寫『沿用 `U23` 的』」。`functional-spec.md:42` 複驗正確；`frontend-components.md` 的那句話實際起於 **`:53`**（逐字「`<LiveRegion />` 不在本單元的新建清單裡——`[F3]`=A 定它由 `U23` 建、`U24` 沿用」），`:54-55` 只含其後的「完成條件因此含一條對 `U23` 的跨單元依賴」。事實成立、定位少一行。**來源是我自己**：上一輪 `R-01` 的 Location 欄即寫 `:54-55`，本站原樣沿用——與 `refined-mockups:b6cf84a4` 記載的「把審查員給的行號當成已驗證事實直接複製」同形 | 行號更正為 `:53-55` | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| `grep -c '^    def ' backend/services/membership_facade.py` | 17（公開 12、頂層 `def` 1、舊 regex `^[[:space:]]{0,4}def [a-z]` 13） | 證實 `performance-requirements.md:139` 已更正為 17，而 `security-requirements.md:26` 仍為 13 → `R-04` Unresolved |
| `grep -cE '^@router\.(get\|post\|patch\|delete\|put)' backend/services/membership_router.py` ／ `grep -c require_story_action` | 6 ／ 9 | 支撐 `R-06` 的 DoS 判定依據（六個端點皆要求已驗證身分） |
| `grep -c 'the row is never deleted' schema_rbac.sql` ／ `grep -c 'never deleted'` | 1 ／ 2 | 作者對我上一輪該子項的拒絕成立；`:663` 的附帶依據亦逐字複驗 |
| `grep -c '^## '` ×4、`grep -c '100'` ／ `grep -o '100' \| wc -l` ×4、`grep -c '200 列'` ×4 | h2 = 6／6／5（performance／security／tech-stack），行數 3／12／3／3，出現次數 5／17／**6**／3，`200 列` 合計 4 | 七項自檢的數字除 security 出現次數（寫 3、實為 6）外全部相符 → `R-04` 的第二處殘留 |
| `python3 -c "json.load(...)"` on `traceability.json` | `coverage` 11（`OK` 3／`N/A` 8）、`upstream_ids` 11、`reverse` 17（含 `SEC-U24-6`） | 與自檢第 6 項完全相符；`NFR8` 以 `OK → NFR8.80` 在 `coverage`，故 `TS-U24-7` 不入 `reverse` 的理由仍然成立 |
| `sed -n` on `bolt-plan.md:479/480/494`、`unit-of-work.md:426`、`requirements.md:568-571/577-579`、`stories.md:533/535-537`、`AdminPage.tsx:195-204`、`membership_facade.py` ×6、`membership_service.py:472/486`、`functional-spec.md:42/291`、`frontend-components.md:53-55/157/176` | 全部命中所宣稱內容，唯一偏差為 `frontend-components.md:54-55`（應為 `:53-55`） | 本輪引用的事實與定位除 `R-09` 一處外全部正確 |
| `ls construction/`、`stage-graph.json` 的 `execution` | 無 `project-pages-ui` 目錄；`nfr-requirements` = `CONDITIONAL`、`code-generation` = `ALWAYS` | `HO-U24-2` 是有效的下游指派（目標在游標之後且未執行），兩層轉移目標寫法正確 |
| `linter` ／ `type-check` sensor | 未重跑（本輪限唯讀，且該兩支已如實記為 `no-eslint-config`／`no-tsconfig-found`） | 產出零個 `.ts`／`.tsx`／`.py`，tool-unavailable 的記載方式正確，未寫成 pass |

### Summary

**Critical 0、Major 1、Minor 5**，共 9 項（`R-01`–`R-06` 承接，`R-07`–`R-09` 新增）。狀態分佈：**Resolved 4**（`R-01`／`R-02`／`R-03`／`R-05`）、**Unresolved 1**（`R-04`）、**New 4**（`R-06` 已修但本輪首次登記為 `New`，依引擎字彙；`R-07`／`R-08`／`R-09` 為新發現）。依裁定規則（零 Critical、Major ≤ 2）→ **READY**。

四項新發現的分類：`R-07` **new-introduced**（`R-02` 的修法以列舉三條路徑收尾、未留兜底，於是橫幅的非 403 失敗仍然靜默，而這正是該修法要消除的那一類）；`R-08` **new-introduced**（新節與既有節撞成同一個「三之一」）；`R-09` **pre-existing-unreviewed**（錯誤行號的源頭是我上一輪 Location 欄的措辭，本站原樣沿用，事實對、定位偏一行）；`R-04` 的殘留則是 **new-introduced** 的反面——修正動作只覆蓋了發現所點名的兩個落點之一，`project.md` 的 `refined-mockups:a33fc270` 逐字記過這個形狀。

最要緊的結論是 **`R-01` 真的解掉了**，而且不是靠改文字：排序事實已獨立複算（`U24`@B12 早於 `U23`@B13），決定交人工以 `[N4]`=A 裁決，改由 `U24` 自建後本單元的完成條件在它被施工的那一刻可滿足，且不需要動任何已核可的 Bolt 順序；兩個被要求複驗的點（`HO-U24-2` 的目標有效性、`HO-U24-1` 的充分性）都站得住。`R-04` 維持 Unresolved 但**不阻塞實作**：殘留的是一處覆蓋宣稱的數字（13 應為 17）與一個自檢欄位的計數，開發者不會因此做錯任何事；它進入閘門讓人裁決，而非擋住本站。真正值得在下一輪動手的是 `R-07`——它是本輪唯一一項「沒寫下來」而非「寫錯」的缺口，正是七項自檢在結構上照不到、而上一輪 `R-02` 也屬同一類的那個盲區。

VERDICT: READY
