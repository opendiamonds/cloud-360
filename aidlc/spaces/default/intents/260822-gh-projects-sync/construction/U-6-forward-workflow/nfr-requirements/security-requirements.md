# Security Requirements — U-6 正向同步 workflow

<!-- Stage: nfr-requirements（Construction，per-unit）· Unit: U-6-forward-workflow · kind: service -->

## ADR-0006 四面向

| 面向 | 判定 | 內容 |
| --- | --- | --- |
| **IAM** | **完全適用** | 本單元是憑證從 workflow secret 進入各 action 的**唯一入口**。見 SEC-1 |
| **Encryption** | 適用（平台承擔） | HTTPS；憑證由 GitHub secret 機制保管，本單元不落地它 |
| **Network exposure** | 不適用 | 只有出站呼叫（[req:NFR-S5]） |
| **Audit logging** | **適用** | 每輪的判定與寫入結果落在 workflow log 與受管區塊（[req:NFR-S6] 的三要素） |

## SEC-1：憑證的分發面在此收斂

本單元把 `GH_TOKEN` 傳給 U-3、U-4、U-5 三支 action。**U-1 與 U-2 不得收到它**——它們是零 I/O 純函式，收到憑證會讓 [US:S-10 AC 1] 的 fixture 驅動前提失效（見 U-1 的 `security-requirements.md`）。

**約束（二元可判）**：`aidlc-sync-forward-impl.yml` 中呼叫 `aidlc-sync-map` 與 `aidlc-sync-block` 的兩個 step **不得有 `env: GH_TOKEN`**。讀 YAML 即可驗。

**權限集合依 ADR-0014 為三項**（組織層 Projects 讀寫 ＋ 用途受限的 repo 內容寫入 ＋ Issues 寫入）。三者分別由 U-3、U-4、U-5 使用，而**本單元把同一份憑證發給三者**——沒有機制讓各自只拿自己那一份。此即 U-3 SEC-2 與 U-4 SEC-1 記載的結構性事實在分發端的樣貌。

> **權限集合現為四項（ADR-0015 §8）**：ADR-0014 補入的是第三項 Issues 寫入，而 §8 進一步指出**開 PR 與推分支在 GitHub 權限模型中是兩個獨立權限**，第四項為 `Pull requests: write`（佐證：`deploy.yml:174-175` 在本 repo 上正在運行的設定即分列兩行）。本檔沿用的是 NFR-S1 當時的三項計數，更正指令與閘門（Bolt 0，須在憑證鑄造前）見 `../../../inception/decisions/0015-functional-design-upstream-amendments.md` §8。指標補於 2026-08-30T01:31:09Z。

## SEC-2：`reverse_pending` 的 fail-closed 是一條安全性質的決定

`business-rules.md` 的 R-2.5 定：查詢開啟中反向 PR 失敗時**整輪中止**，不寫任何 Status。

**這不只是可靠度選擇，也是安全選擇**：`reverse_pending` 的用途是「哪些 intent 的看板值**不該**被機制覆寫」，因為人在那上面表達過判斷。算不出來就覆寫，等於在不知道是否有人的判斷在場的情況下改寫它——[US:S-6] 要防的正是這件事。

**R-2.6 的「不得偽裝成 `suppressed`」同屬此列**：把故障記成正常判斷，會讓受管區塊寫下不存在的反向 PR。**稽核紀錄說謊比沒有紀錄更糟**，因為它讓人以為自己知道發生了什麼。

## SEC-3：兩道自我排除防線的安全意義

防線②（HEAD commit 訊息含 `[aidlc-sync]` 整輪 skip）**可被任何有推送權的人觸發**——U-4 的 SEC-2 已完整記載此事及其低嚴重度判定與「記載它，不修它」的結論。

**本單元補一個分發端的觀察**：防線②在此是**整輪層級**的，所以誤觸的後果是整輪不處理，而非單一 intent。這放大了 U-4 SEC-2 的影響面（從一個 intent 變成全部），但**不改變其嚴重度判定**——防線①（結構性，回寫後無漂移）不依賴任何判斷，正確性仍由它保底。

## 與上游的對應

四面向依據為 `requirements.md` 的 NFR-S1／S4～S6 與 `project.md` 的 ADR-0006 落點，權限集合依 **ADR-0014**；兩道防線與其代價引自 [ad:services.md] 的 S-A；[US:S-6]／[US:S-10 AC 1] 引自 `stories.md`；`reverse_pending` 的 fail-closed 與不得偽裝見本單元的 `business-rules.md` R-2.5／R-2.6，一輪序列見 `business-logic-model.md`，跨單元契約見 `domain-entities.md`；零 I/O 約束引自 U-1 的 `security-requirements.md`，`[aidlc-sync]` 標記的可觸發性引自 U-4 的同名檔；action 的組裝見同輪的 `tech-stack-decisions.md`；單元邊界引自 [ug:unit-of-work.md] 的 U-6。

---

## Review (nfr-requirements — Group A)

**Verdict**: **NOT-READY**（整組）
**Reviewer**: aidlc-architecture-reviewer-agent
**Date**: 2026-08-30T05:28:27Z
**Iteration**: 1
**涵蓋單元**: U-6 / U-7 / U-8 / U-9 / U-11（每單元 5 份，共 25 份產出，全數逐檔實讀）

> 本段落寫在 U-6 的檔內，但**涵蓋整個 Group A**——落點由 dispatch 指定，非表示發現集中於 U-6。

### 逐單元判定

| 單元 | Verdict | Critical | Major | Minor | 主要理由 |
| --- | --- | --- | --- | --- | --- |
| **U-6** forward-workflow | **READY** | 0 | 0 | 1 | 四面向齊備、NFR-P1 拆解具體、排隊殘留誠實記載且不弱化上游準則。僅一處計數錯位 |
| **U-7** reconcile-workflow | **NOT-READY** | 1 | 4 | 1 | 五份產出全數未吸收 functional-design 最後兩組規則（R-6 的 C-4 回寫、R-7 的 `ref: ut`），且重新主張一個已被 ADR 明文撤回的量測 |
| **U-8** reverse-workflow | **NOT-READY** | 1 | 1 | 0 | 以「上游未指派」為由自行裁定 concurrency，而已核可的 `services.md` 其實指派過；gh-aw 前提的更正只傳播到一份檔 |
| **U-9** selftest-workflow | **NOT-READY** | 1 | 0 | 0 | 靜態檢查對象與觸發 allowlist 指向不會存在的檔案形式，使本 intent 唯一的自我測試閘門在兩個方向同時靜默失效 |
| **U-11** readme-pointer | **READY** | 0 | 0 | 0 | 四面向逐項判定齊備且各附理由；四份「不適用」的理由一致且成立 |
| **跨單元** | — | 0 | 1 | 1 | NFR-C1／NFR-C2 零承接；`upstream-coverage` sensor 的引用缺口 |

**合計**：3 Critical、6 Major、3 Minor。

### 發現

| # | 嚴重度 | 檔案:行 | 一句話 | 建議落點 |
| --- | --- | --- | --- | --- |
| **C-1** | **Critical** | `U-7/nfr-requirements/performance-requirements.md:10`、`:12`；`U-7/nfr-requirements/security-requirements.md:37` | 重新主張 `latency_samples` 由本單元承載 NFR-P1 的量測（逐字「`latency_samples` 是 **NFR-P1（U-6 的 5 分鐘延遲）** 的量測落點」「U-6 的效能需求由本單元量測」），與 ADR-0015 §7 及 `U-7/functional-design/domain-entities.md:19`／`:40-46` 逐字相反（「**本單元填不出值**」「**在修正落地前，本單元不填此欄位**，且不得以「本輪執行耗時」冒充」）；`security-requirements.md:37` 更把該欄位標為「同步耗時」——正是 ADR 明文禁止的頂替值 | **Bolt 2 gate**（ADR-0015 §7 的既定確認人）；nfr 層應改記「NFR-P1 目前無量測擁有者」而非宣稱有 |
| **C-2** | **Critical** | `U-8/nfr-requirements/performance-requirements.md:15`、`:19` | 缺口 P-2 的前提「反向（本單元）… **未指派**」對 `requirements.md` NFR-P3 成立，但對已核可的 `services.md:58` **不成立**——該列逐字「concurrency｜與 S-B **同一組**（兩者都是排程、都碰 record，不應並行）」。U-8 據此裁定「**本單元自成第三組**」等於在未標明的情況下推翻已過 gate 的 application-design；而該互斥的必要性在 ADR-0015 §13 讓 U-7 取得 record 寫入能力（補 C-4、每日 commit+push 同一份 `sync-state.json`）之後**上升而非下降** | **Bolt 3 gate ＋ `services.md` S-C 列**；若真要改為第三組，須以「標出缺口、不逕改上游」的形狀重走，並回答 `services.md` 給的「都碰 record，不應並行」理由為何不再成立 |
| **C-3** | **Critical** | `U-9/nfr-requirements/tech-stack-decisions.md:18`、`:32`；`U-9/nfr-requirements/performance-requirements.md:31`、`:33` | 靜態檢查（R-1.2／R-2）的對象逐字為「編譯後的 `.lock.yml`」、觸發 allowlist（R-3）逐字為 `.github/workflows/aidlc-sync-*.md`／`.lock.yml`，但四支 `aidlc-sync-*` 已全數定案為**純 Actions `.yml`**（U-6／U-7／U-8／U-9 各自的 `tech-stack-decisions.md`；[ug:unit-of-work.md]:105／:117／:130／:142 的交付欄）。兩個後果皆靜默：(a)「這條規則**唯一的機械化落點**」目標集合為空、永遠綠燈；(b) 改動 `aidlc-sync-forward.yml` 的 PR **不會觸發 U-9**，而 U-9 是六項繼承斷言的唯一執行點（`U-9/nfr-requirements/reliability-requirements.md:34`） | **Bolt 4 gate**（U-9 交付）＋ `U-9/functional-design/business-rules.md` 的 R-2／R-3；需重新指定檢查對象與 glob |
| **M-1** | Major | `U-7/nfr-requirements/performance-requirements.md:24-35`；`scalability-requirements.md:11`、`:29`；`security-requirements.md:22` | U-7 五份產出對 `R-6`／`R-7`／`commit_and_push`／`write_sync_state`／`ref: ut` **零命中**（逐檔 grep）。呼叫成本表只列四項並算出「6 × 4 ＋ 2 = **26 次**」，漏掉 ADR-0015 §13 補入的 C-4 回寫；依 ADR §13 代價段（「每日多一次 commit+push」）應為 27，依 R-6.6（「每個 intent 至多一次推送」）應為 32——**兩種讀法皆非 26**，而該數字正是 NFR-P4／FR-D3 批次上限對 C-T5 的判斷基礎。同一個舊數字傳播到另外兩份檔 | **code-generation**，並在 **Bolt 2 gate** 前先確認「每日一次」與「每 intent 一次」哪個為準 |
| **M-2** | Major | `U-7/nfr-requirements/tech-stack-decisions.md:24`、`:26` | 缺口 M-1 裁定（報告落 job summary）的兩條理由已被上游推翻：理由 1「**零新增狀態**——…不新增 issue、**不新增檔案**」與理由 3「commit 進 repo 會每天產生一個 commit，**放大 [US:S-1 AC 7] 的 CI 觸發問題**，且需要擴大 U-10a 的 `paths-ignore`」，而 ADR-0015 §13 逐字「**代價**：reconcile 每日多一次 commit+push……**U-10a 已為 `sync-state.json` 設計 `paths-ignore`，沿用即可**」。本單元早已每日 commit+push，被否決選項的邊際成本遠小於所述。**裁定可能仍正確，理由不成立** | **code-generation**（重述理由）；若理由改寫後裁定翻轉，回 **Bolt 2 gate** |
| **M-3** | Major | `U-7/nfr-requirements/reliability-requirements.md:49` vs 同輪 `tech-stack-decisions.md:28` | 同輪兩份產出互斥：reliability 稱一致率「**是本機制唯一可長期追蹤的健康指標**……若未來要定 SLO，它是唯一有量測基礎的候選」，而 tech-stack 的 M-1 裁定明寫「**但趨勢追蹤因此不可得**：job summary 只存在於單次 run」。在該裁定之下一致率不具長期追蹤基礎，「沒有 SLO」一節的收尾論證因此失去支撐 | **code-generation**；二擇一：改寫 reliability 的宣稱，或把「長期追蹤」列為 M-1 裁定的已知限制並指名補救落點 |
| **M-4** | Major | `U-7/nfr-requirements/reliability-requirements.md:37-43`（「唯一的 fail-closed 路徑」全節） | R-7.1 的失效模式完全缺席。`U-7/functional-design/business-rules.md:107` 逐字：`schedule` 只在預設分支觸發、本 repo 預設分支實測為 `main`，不處理則「**對帳拿過期的 record 去比看板，一致率、補平判定、三份清單全部失真**」，且 `:111` 明記「**失真是靜默的**」。這比該檔列為唯一 fail-closed 的 `reverse_pending` 更嚴重（後者紅燈＋通報，前者無任何訊號），卻不在四種中斷表、不在冪等性表、不在 fail-closed 節 | **code-generation**（補入可靠度失敗模式）；`ref: ut` 的實作確認掛 **Bolt 2 gate** |
| **M-5** | Major | `U-8/nfr-requirements/performance-requirements.md:37`；`U-8/nfr-requirements/reliability-requirements.md:38` | gh-aw 前提的更正只傳播到一份檔。`tech-stack-decisions.md:9` 已註明「**此處先前寫成 gh-aw 的 `.md` ＋ 編譯出的 `.lock.yml`，已更正**」、`:13`「**因為不走 gh-aw**……沒有編譯步驟就沒有漂移」，但 perf:37 仍寫「P-2 的三組 concurrency group **全部落在 gh-aw 編譯出的 `.lock.yml` 內**……須以編譯後的 `.lock.yml` 複驗」，reliability:38 仍寫「『PR 建立失敗即刪除已推送分支』這條規則的**可實作性取決於 gh-aw 的 safe-outputs 語意**」。兩處都會讓實作者去查一個不會存在的檔，並把純 Actions 下 `git push --delete` 即可的動作當成受版本限制的未決項 | **code-generation** |
| **M-6** | Major | 全 25 份產出（`NFR-C1`／`NFR-C2` grep 零命中） | 上游兩條共存需求無任何落點。NFR-C2（「新 workflow 的 `name`（＝ body H1）須與現有 **11 支**不同」）是二元可判的建置期檢查，而本組正好新增四支 workflow ＋ 三支 `*-impl.yml`；NFR-C1（既有 CI 四道關卡與 `deploy.yml` 行為不得改變）在 U-7 每日 commit+push、U-8 每日開 PR、U-9 新增 `on: pull_request` 之後，是本組最直接會碰到的共存面。兩者既未被承接、也未被逐條判為不適用 | **code-generation**（NFR-C2 可直接寫成建置期檢查）；NFR-C1 掛各 Bolt gate |
| **m-1** | Minor | `U-6/nfr-requirements/tech-stack-decisions.md:23`、`:25` | 標題「承接 bash 的**四項**既有代價，本單元不新增第五項」，而本文列出**五項**（U-1 `null`、U-2 序列化、U-3 GraphQL 200、U-4 `jq`、U-5 `gh issue list --json`），故「第五項」的序數亦錯位（應為第六項） | code-generation |
| **m-2** | Minor | `U-9` 的 performance／scalability／reliability／tech-stack 四份；`U-6/tech-stack-decisions.md`（5/25 檔） | 本 stage frontmatter 宣告 `upstream-coverage` sensor，判準為「輸出散文須引用 `consumes:` 宣告的每一份 artefact（`business-logic-model`、`business-rules`、`requirements`）」。上述五份對 `requirements.md` 零引用（`grep -c '[^-]requirements\.md'` ＝ 0），會落成 `SENSOR_FAILED` | code-generation（各補一句「與上游的對應」引用） |
| **m-3** | Minor | `U-7/nfr-requirements/security-requirements.md:31-38` | SEC-2 宣稱「**逐項檢視**報告的六份清單與兩個數字」，但該表未含 R-7.3 新增的 `ut HEAD SHA` 欄位。SHA 本身無敏感性，判定不變，但「逐項」的宣稱與實際列舉不符 | code-generation |

### 與 `open-items.md` 的關係

送出前已先讀 `<record>/construction/functional-design/open-items.md`（含 iteration 6／7 的追加登錄）。**上表 12 項均不在該檔已登錄的項目之內**，逐項核對如下：

- 該檔的 U-7 段落登錄 A:M-5／A:M-6／A:m-4／A:m-9，皆為 functional-design 層的指派、編號與序列圖問題，**未觸及 nfr 層是否吸收 R-6／R-7**（M-1〜M-4 為此處的新後果）。
- 該檔完全沒有 U-9 的任何一項（C-3 為新發現）。
- B:M-4 登錄的是 `decided_at` 值域變更推翻 **U-2** 的 audit-logging 判定，與 C-1（U-7 `latency_samples`）、C-2（U-8 concurrency）不同。
- B:M-5 登錄「權限三項的 §8 指標只補了三處，U-1／U-5 另兩處仍無」——**Group A 五個單元皆已補上該指標**（U-6:22、U-7:14、U-8 全檔採四項、U-9:63；U-11 判定不適用故不需），故不重複列。

### 有查證但**未成立**的疑點（記錄以免下一輪重查）

| 疑點 | 結論 |
| --- | --- |
| U-6 承認「第三個以後到達的 run 會取消先前的 pending，即使 `cancel-in-progress: false`」是否違反 NFR-P3 的 AC | **不成立**。AC 逐字「**兩個**事件觸發的執行不會互相取消而是排隊」，兩個 run 的情形確實排隊；U-6 `scalability-requirements.md:15-22` 已如實記載三個以上的殘留且不弱化上游準則 |
| U-6 `performance-requirements.md:25-29`「排隊時間計入 5 分鐘預算故該準則可能不成立」是否為擅自放寬 | **不成立**。該節明寫「本站不改寫該準則」，只記明後果，符合「標出不逕改」的既有紀律 |
| U-11 產出全部五份而其中四份判「不適用」是否為漏做 | **不成立**。`kind` 於 [ug:unit-of-work.md] 刻意留空而觸發全矩陣，四份各自逐條對照 NFR 編號並附理由，符合 `project.md ## Mandated` 的「不適用者一律附理由、不留空白」 |
| U-9 Q-1（組織層授權下 R-1.3 的 403 恆不可達）是否為假警報 | **成立且處置正確**。NFR-S1 的「**組織層** Projects 讀寫」確實涵蓋組織內全部 Project，403 需要真實的範圍外；該檔給了三個候選落點、指派 Bolt 0 gate，並做了指派目標的 EXECUTE／CONDITIONAL 檢查 |
| U-8 缺口 P-1（權限實為四項）是否與 ADR-0015 §8 重複登錄 | **不重複**。§8 已承載，U-8 引用它而非另開，屬正確的沿用 |

### 未查證項（不臆測）

| 項 | 卡在哪 |
| --- | --- |
| U-7 R-7.2「推自 `ut` 分叉的自建分支」之後，該回寫**如何抵達 `ut`** | 需與 U-4 的 `commit_and_push` 及分支保護實況交叉核對；`open-items.md` 的 A:M-2 已登錄 R-3.1 與 R-7.2 的矛盾，本輪不重複判定。**但若該回寫不會被合併，M-1／M-2 與 `U-7/reliability-requirements.md` 全篇「本單元是其他單元的可靠度來源」的論證會一起失效**——建議在 Bolt 2 gate 一併確認 |
| 若 `latency_samples`／一致率改為「commit 進 repo」落點，對 U-10a `paths-ignore` glob 集合與 U-9 allowlist 交集的影響 | 取決於 C-3 與 M-2 的處置方向，兩者未定前無法判定 |
| C-T5（框架單次操作次數上限）實際值 | 上游明列為 PRE-1 第 2 項的實測待辦，本輪不臆測數字；M-1 的重算只指出 26 為錯，不主張正確值 |

### Summary

整組 **NOT-READY**。三個 Critical 的共同形狀是**「宣稱存在的東西實際不存在」**，且三者都靜默：U-7 宣稱它在量測 NFR-P1，而 ADR-0015 §7 已明文禁止它填那個欄位；U-8 宣稱上游沒指派 concurrency，而 `services.md:58` 指派過、且指派的理由（「都碰 record，不應並行」）在 C-4 補入後更成立；U-9 宣稱有一道靜態檢查與一組觸發 allowlist，而兩者指向的 `.md`／`.lock.yml` 在四支 workflow 全數改為純 Actions 之後都不會存在。六個 Major 中有四個屬同一根因——**U-7 的 nfr 層完全沒有吸收 functional-design 最後補上的 R-6（C-4 回寫）與 R-7（`ref: ut`）**，以致成本模型、技術裁定理由與可靠度失敗模式三者都停在補入之前的世界。U-6 與 U-11 品質良好：四面向齊備、「不適用」逐項附理由、對排隊殘留與缺乏 SLO 的處理誠實且不越權發明數字，可放行。
