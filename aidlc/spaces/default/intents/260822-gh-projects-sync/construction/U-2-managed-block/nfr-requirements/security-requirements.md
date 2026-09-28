# Security Requirements — U-2 受管區塊渲染與雜湊

<!-- Stage: nfr-requirements（Construction，per-unit）· Unit: U-2-managed-block · kind: library -->

## ADR-0006 security baseline 的四面向逐項判定

`project.md ## Mandated` 要求對每一項變更逐項判定，不適用者附理由。

| 面向 | 判定 | 理由 |
| --- | --- | --- |
| **IAM** | **不適用** | 本單元不持有憑證、不呼叫 API。與 U-1 同，`action.yml` **不得宣告任何 secret 型 input** |
| **Encryption** | **見 SEC-1** | 本單元使用 sha256——這是四個面向中唯一需要實質討論的，但結論是它**不是**加密也不是安全控制 |
| **Network exposure** | **不適用** | 零 I/O，連出站呼叫都沒有。NFR-S5 已判定整個機制此面向不適用 |
| **Audit logging** | **部分適用，但比先前記載的弱** | 受管區塊是稽核紀錄的一部分，**但它在「有 Status 變更」時不含時間戳**——`Block.decided_at` 的值域已改為 `ISO 8601 \| null`，非空僅限「機制決定不寫」那一支。見 **SEC-5**（本輪重判） |

## SEC-1：sha256 在此**不是**安全控制

`content_hash` 產生 sha256，但它的用途是 [req:FR-G4] 的**防迴圈第一道**——判斷「這個區塊還是不是我們上次寫的」。

**它不提供任何防竄改保證。** 任何能編輯 issue body 的人都能改內容並讓機制在下一輪重算出新雜湊；沒有金鑰、沒有簽章、沒有任何一方持有秘密。把它當成完整性保護會是誤解。

**這必須被寫下來的理由**：`sha256` 這個詞在安全語境中通常暗示防竄改，下一個讀 `content_hash` 的人很可能這樣預期。若有人據此推論「受管區塊受保護，不必再管誰能編輯 issue」，那是一個由誤解產生的真實缺口。

**正確的定位**：這是一個**變更偵測**裝置，與 ETag 或 checksum 同類。真正限制誰能改 issue 的是 GitHub 的權限模型，不是這個雜湊。

**連帶約束**：不得把 `content_hash` 的比對結果當作授權判斷（例如「雜湊相符所以這是可信的內容」）。它只回答「變了沒有」。

## SEC-2：受管區塊是公開可讀的

本 repo 為 public，Project #16 的 issue 內容依其設定可能公開可讀。受管區塊必載四項內容，逐項檢查其揭露面：

| 內容 | 揭露什麼 | 判定 |
| --- | --- | --- |
| Status 與 `traceable_row` | 對照表的哪一列命中 | 無敏感性——對照表本身在 repo 內公開 |
| 原因類別與 `decided_at` | 機制何時決定不寫、為何 | 無敏感性 |
| `[S]`／`— SKIP` 差別 | 哪些 stage 在 scope 內 | 無敏感性——`aidlc-state.md` 已公開 |
| 兩段固定說明 | 逐字固定文字 | 無敏感性 |
| **`rejection_notice`**（[US:S-6 AC 5] 的告示） | 某次反向 PR 被關閉而未合併，及其 `closed_at` | 無敏感性——該 PR 本身在 public repo 內可見，關閉時刻是公開事實 |

**判定：不構成暴露。** **五項**全部是 record 內或 public repo 內已公開的事實的重述。

> **`rejection_notice` 這一列是送審前自檢補上的（2026-08-30T05:10:02Z，檢查 2「契約端點三問」）。** functional-design 的 iteration 3／4 為 `Context` 與 `Block` 增設該欄位（ADR-0015 §12）以承載 [US:S-6 AC 5]，而本節的白名單約束（見下）**逐字禁止 `render` 輸出任何未在上表列出的欄位**——上表當時只有四列，於是這條安全約束會**禁止 U-2 的 R-1.5 渲染告示**，兩者直接衝突。補列後衝突消解，且判定不變（該 PR 在 public repo 內本就可見）。
>
> **這正是白名單型約束的固有維護成本**：`Block` 每增一個欄位，本表就必須同步，否則不是安全洞就是功能被自己的安全規則擋掉。已在下方約束句補上這個提醒。

**約束（給實作，二元可判）**：`render` 的輸出**不得**包含 `Decision`／`Context` 中任何未在上表列出的欄位。**`Block` 或 `Context` 每新增一個欄位，上表必須同步新增一列並給出揭露判定**——否則新欄位要嘛被這條約束擋掉（功能失效），要嘛繞過本節上線（安全判定缺漏）。這條的作用是防止未來有人為了除錯而把整個 `Context` 傾印進區塊——那會把尚未被審視過的內容送上公開頁面。PR 上比對 `render` 的欄位清單即可驗。

## SEC-5：`decided_at` 值域變更後的 audit logging 重判（2026-08-30T05:10:02Z）

**觸發**：functional-design 的 iteration 4 Group B C-3 把 `Block.decided_at` 由非空 ISO 8601 改為 **`ISO 8601 | null`**，非空僅限 `status` 為 `null`（機制決定不寫）那一支——理由是 [US-OQ-3] 的必載內容原文用「**或**」，時間戳字面上只屬後半支。`open-items.md` 的 **B:M-4** 指出這**推翻了本檔原先的 audit-logging 判定而未重判**，並指名由本 stage 的閘門承接。

**原判定的錯處**：原文寫「受管區塊必載 `decided_at` 與 Status／原因類別，正好對應 NFR-S6 三要素中的兩項」。現況是——

| 分支 | 區塊含 Status？ | 區塊含時間戳？ |
| --- | --- | --- |
| `mapped`（**有** Status 變更） | 是 | **否** |
| `status = null`（**無** Status 變更） | 否（含原因類別） | 是 |

**兩者恰好互斥**，而 NFR-S6 管的是「**每次 Status 變更**皆可回答哪個 intent、哪個 stage、什麼時間」——也就是說，受管區塊在 NFR-S6 真正涵蓋的那一支上**不提供時間戳**。原判定的「三要素中的兩項」在該支只剩一項。

**重判：NFR-S6 仍然成立，但載體不是本單元。** 逐字核對 `requirements.md` 的 NFR-S6 驗收欄——「見 FR-E3；且成功的寫入亦在 **workflow log** 中留下同樣三項資訊」——**正本一直是 workflow log，受管區塊只是附帶的第二份**。另有兩處獨立佐證同一次 Status 變更的時刻：`sync-state.json` 的 `last_synced_at`（U-6 的 R-5.4 回寫、隨 commit 進版控），以及該 commit 本身的時間戳。**因此沒有稽核缺口，只有本檔的宣稱過強。**

**本單元的 audit logging 判定改為**：受管區塊承載「哪個 intent」（issue 綁定）與「哪個 stage」（`traceable_row`／`scope_note`），**不承載「什麼時間」**；後者由 workflow log、`last_synced_at`、commit 時間戳三者承擔。

> **附帶收益，一併記載**：`decided_at` 退出 `mapped` 支使該支的 `Block` 不再含隨輪變動的時間戳，**語意相同的兩輪必得相同雜湊**——這讓同單元 `business-rules.md` 的 R-2.3 churn 隱憂只作用在「決定不寫」那一支，`content_hash` 的穩定性比先前更強。這是安全面之外的正面連帶，不影響本節判定。

## SEC-4：`parse` 對未知版本回 `null` 的安全面

`business-logic-model.md` 的 `parse` 版本分派把「版本高於當前渲染器」判為回 `null`，其效果是**該 item 被當作不受管、機制不覆寫它**。

從安全角度這是正確的**故障保守**（fail-safe）方向：不確定時不動，而不是用舊規則猜著改。若反過來設計（猜著解析並覆寫），一個由更新版本機制維護的 item 會被舊版本機制無聲改寫——那才是真正的破壞。

**但它的代價在安全面也要記明**：這條路徑**無告警**（`business-logic-model.md` 的邊界情形表已如實載明）。一個持續回 `null` 的 item 會**永久**停留在不受管狀態而無人察覺。這不是機密性或完整性問題，但它讓「機制以為自己在管、實際沒在管」這件事無法被發現。告警落點未指派，本站不擅自指派給 U-5。

## SEC-3：格式契約的失效是可用性風險，不是安全風險

ADR-A6 的失效模式（改格式不重新基準化 ⇒ 全部 item 誤判為人為變更 ⇒ 巨大反向 PR ＋ 全面 `suppressed`）**看起來**像安全事件，但它不是——沒有未授權存取、沒有資料外洩、沒有權限提升。它是**可用性與正確性**事件。

分類正確很重要：把它歸為安全問題會讓它排進錯誤的處置流程（例如要求安全審查），而它真正需要的是 [Q1=C] 的三道 CI 互鎖（見 `business-rules.md` R-4 群）。

## 與上游的對應

四面向依據為 `requirements.md` 的 NFR-S1～S6 與 `project.md` 的 ADR-0006 落點；FR-G4（防迴圈三道防線）為 `content_hash` 用途的正本；必載四項內容引自 [ad:component-methods.md] §C-6（[US-OQ-3] 定案）；格式契約與其失效模式引自 [ad:decisions.md] ADR-A6；`Block` 結構與雜湊涵蓋範圍引自本單元的 `domain-entities.md` 與 `business-rules.md`；單元邊界引自 [ug:unit-of-work.md] 的 U-2；repo 為 public 的事實引自 `project.md`；承載形式的決定見同輪的 `tech-stack-decisions.md`（並引 [kb:technology-stack.md]）。
