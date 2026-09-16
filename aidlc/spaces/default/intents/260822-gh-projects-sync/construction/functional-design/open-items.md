# Functional Design — 未關閉項登錄（open items）

<!-- Stage: functional-design（Construction，per-unit）· 全 stage 範圍 -->

**建立時間**：2026-08-30T09:55:00Z
**來源**：reviewer iteration 5（兩組，共 38 項發現）
**狀態**：本 stage 在 iteration 5 後**停止送審迴圈**（見下方「為什麼停在這裡」），4 個 Critical 已修，其餘於此登錄並帶進閘門。

---

## 為什麼停在這裡

五輪對抗式審查的 Critical 數為 **4 → 6 → 8 → 4**，但「由前一輪修正動作造成」的佔比從未下降。iteration 5 要求 reviewer 對每項發現分類，結果是決定性的：

| 類別 | Group A | Group B | 合計 | 佔比 |
| --- | --- | --- | --- | --- |
| **新引入**（本輪修正動作造成） | 17 | 9 | **26** | **68%** |
| 既存漏審 | 2 | 5 | 7 | 18% |
| 新設計問題 | 3 | 2 | 5 | 13% |

兩位 reviewer 各自獨立給出同一個診斷：**「修法的覆蓋面比它宣告的損害面窄」**（Group A）、**「缺陷從『規則缺席』移到了『規則寫了但兩端接不上』」**（Group B）。

**這不是 reviewer 品質問題，是補丁式修正在此規模的交叉契約上不可靠**：每次只修 reviewer 點名的落點，漏掉同一個事實的其他表達面。再跑一輪的期望值是「修好 N 項、新增 0.7N 項」，不收斂。

**停止決定由使用者在 iteration 5 前預先設定**（「若發現再度以『修正自己造成』為主，就不再迴圈」），本輪達成該條件。

---

## 已修的 4 個 Critical（不列入 open items）

| # | 內容 | 修法 |
| --- | --- | --- |
| A:C-1 | U-7 的 R-6.5 只補三欄，`managed_block_hash` 在 U-6 的 ②③ 失敗場景下**永久錯誤**，而 R-6.2 明文禁止修復 ⇒ ADR-A6 的「無人為變更卻每天開反向 PR」重新可達 | 新增 **U-7 R-6.8**（修復路徑一併回寫該欄，取值路徑同 U-6 的 R-5.4）；R-6.2 限定為補平路徑 |
| A:C-2 | R-5.10 (b) 的「不首建」寫在寫入鏈裡，而首建分岔發生在算出 `Decision` **之前**、R-3.1 一字未動 ⇒ [req:FR-J3] 在 `260802-default` 上仍不可滿足 | 新增 **U-6 R-3.0**（`Decision` 計算上提到分流之前，`unparseable`／`whitelisted` 在此擋下）；R-5.10 (b) 降為深度防禦 |
| A:C-3 | 序列圖第三度未跟上規則；且圖上「失敗不連坐」與 R-5.12 字面相反 | 序列圖與 fallback 第三次重畫；**R-5.12 由「任一步失敗即完全不回寫」改為「逐欄記錄實際寫成功的部分」**——原寫法會自己製造 A:C-1 剛堵住的卡死 |
| B:C-1 | `write_body` 要靠受管標記決定附加或替換，而**標記語法全 stage 未定義**、C-6 三方法也不回傳跨度 ⇒ 實作者只能在 U-3 自建一份落在 R-4 群互鎖之外的格式副本 | U-2 新增 **`MANAGED_BLOCK_BEGIN`／`MANAGED_BLOCK_END`** 兩個具名常數（受 R-4 群互鎖約束）；U-3 的 R-6 群改為引用、新增 R-6.6 處理標記損壞 |

**附帶關閉**：A:M-1（R-6.3 與 R-6.5 字面互斥）、B:M-2（`write_body` 要求呼叫端先跑 `parse` 而無人跑——已由 B:C-1 的自行定位修法消解）、兩組的 m-8（ADR-0015 §13 未代入的 `%s` 佔位符）。

---

## Open items（依落點分組）

**閱讀方式**：每一項都是**已知且已定位**的缺口，不是「可能有問題」。`類別` 沿用 reviewer 的分類。**這些項目未經任何獨立視角驗證其修法**——它們的處置留給 code-generation 或指定的 gate。

### U-6 forward-workflow

| # | 嚴重度 | 類別 | 內容 | 落點／閘門 |
| --- | --- | --- | --- | --- |
| A:M-3 | Major | 既存漏審 | 已撤回的「`managed_block_hash` 由 U-2 `content_hash` 產生」殘留在 U-4 的 schema 表與 U-6 的方法表，與 R-5.4 的回讀取值相反 | code-generation |
| A:M-4 | Major | 新引入 | R-5.10 (b) 的「僅回寫 `SyncState`」語意未定義；且 `unparseable ∩ reverse_rejected` 時 [US:S-6 AC 5] 的告示永久靜默 | code-generation |
| A:M-7 | Major | 新引入 | `resolve_if_open` 的失敗值域寫五個（含 `Failed`）而依據段列四個；`Failed` 在 U-6 錯誤表中不存在 | code-generation |
| A:M-8 | Major | 新引入 | R-6.1b 的「本輪處理成功」全單元僅此一處、無定義，被 R-3.0／R-5.10 兩條無寫入路徑弄成歧義 | code-generation |
| A:M-10 | Major | 新引入 | 插入的 `Context` 表把 R-7 方法表切斷，三列成孤兒且 `render` 列重複兩次 | code-generation（純結構） |
| A:m-3 | Minor | 新設計問題 | `suppressed → frozen: ` 的前綴指派無上游來源卻寫在「依據」欄，與拒絕為 `undecidable` 指派的理由自相矛盾 | **ADR-0015 §14**／Bolt 1 gate |
| A:m-7 | Minor | 新設計問題 | R-5.11 稱假 `Aborted` 通報「是正確的」，未寫下其時間界（到次日對帳為止每次 push 一則） | Bolt 1 gate |
| A:m-8 | Minor | 新引入 | 表內序數倒置（R-5.12 排在 R-5.11 之前） | code-generation |

### U-7 reconcile-workflow

| # | 嚴重度 | 類別 | 內容 | 落點／閘門 |
| --- | --- | --- | --- | --- |
| A:M-5 | Major | 新引入 | R-7.4 指派 U-8 套用同一組分支落點規則，但 U-8 已定稿、且 gate 掛在 Bolt 2 而 U-8 屬 Bolt 3 ⇒ 無收件人 | **需新 ADR 節或改掛 Bolt 3 gate** |
| A:M-6 | Major | 新設計問題 | R-7.3 為上游型別 `ReconcileReport` 新增 `ut HEAD SHA` 欄位，ADR 未列節、上游零指標 | **ADR-0015 需新增一節** |
| A:m-4 | Minor | 新引入 | iteration 4 C-4 點名三處只修兩處，「與上游的對應」仍寫「一字未改」 | code-generation |
| A:m-9 | Minor | 新引入 | 序列圖把 `SyncState` 寫成「三欄 ＋ binding」，與 U-4 的七欄 schema 不符 | code-generation |

### U-4 binding-store

| # | 嚴重度 | 類別 | 內容 | 落點／閘門 |
| --- | --- | --- | --- | --- |
| A:M-2 | Major | 新引入 | R-3.1 仍要 U-7「推其排程觸發分支」（＝`main`），與 U-7 新增的 R-7.2（推自 `ut` 分叉的自建分支）直接矛盾；`:47` 仍稱 ADR「不裁定」 | code-generation |
| A:m-5 | Minor | 既存漏審 | 兩處表格斷裂不在先前「四處」盤點內 | code-generation（純結構） |

### U-1 map-parse-action

| # | 嚴重度 | 類別 | 內容 | 落點／閘門 |
| --- | --- | --- | --- | --- |
| B:M-1 | Major | 新引入 | 同檔兩個 `## R-6`（新 `scope_note` 群 vs 既有「總函式性」），交叉引用因此指向兩處 | code-generation（比照 U-6／U-7 的 renumber 前例） |
| B:m-3 | Minor | 既存漏審 | `parse` 演算法與主流程圖仍無產出 `scope_note` 的步驟 | code-generation |
| B:m-4 | Minor | 新引入 | 新增型別段後「本檔新增……有兩項」成為過期計數 | code-generation |
| B:m-5 | Minor | 新設計問題 | `Unparseable` 路徑無 `stages`，`scope_note` 的值未定義而 R-6.5 又禁止空字串 | **需設計判斷**；Bolt 1 gate |
| B:m-6 | Minor | 既存漏審 | `scope_note` 進雜湊卻不在漂移三欄 ⇒ 非當前 stage 的 scope 變動不觸發重寫 | Bolt 1 gate |

### U-2 managed-block

| # | 嚴重度 | 類別 | 內容 | 落點／閘門 |
| --- | --- | --- | --- | --- |
| B:M-4 | Major | 新引入 | `decided_at | null` 讓受管區塊在「有寫 Status」那一支不含時間戳，推翻了 `security-requirements.md` 的 ADR-0006 audit-logging 判定而未重判 | **nfr-requirements gate** |
| B:m-1 | Minor | 新引入 | churn／雜湊敘述未隨 `decided_at` 的分支限定更新（三處） | code-generation |
| B:m-2 | Minor | 既存漏審 | R-1.2 的可判定方式仍寫「兩個只在此處不同的 `Decision`」，而 `scope_note` 不在 `Decision` | code-generation |

### U-5 notifier ／ 跨檔

| # | 嚴重度 | 類別 | 內容 | 落點／閘門 |
| --- | --- | --- | --- | --- |
| B:M-3 | Major | 新引入 | 把 U-8 寫進「`resolve_if_open` 的呼叫者」表，而 ADR-0015 §5 補的是**通報鏈**、U-8 三份產出對 `resolve_if_open` 零命中 | code-generation |
| B:M-5 | Major | 既存漏審 | 「權限三項」的 §8 指標只補了三處，U-1／U-5 另兩處仍無 | **nfr-requirements gate** |
| A:M-9 | Major | 新引入 | ADR-0015 §14 是 Bolt 1 的 blocking gate，卻未登錄 Bolt 1 DoD（同輪 Bolt 2 補了三條） | **Bolt 1 gate**（登錄遺漏） |
| A:m-2／B:m-7 | Minor | 新引入 | ADR-0015 的 `Amends:` 行「以下原文」是截斷片段，無法履行比對用途 | code-generation |
| A:m-6 | Minor | 新引入 | `bolt-plan.md` 的 §13 條目吞掉 Bolt 2 原有的基線 DoD 本文 | **Bolt 2 gate** |
| B:m-9 | Minor | 既存漏審 | `ReconcileReport` 仍無 `undecidable` 欄位、該句仍與 §7 共用同一個閘門 | **ADR-0015**／Bolt 2 gate |

---

## 需要在 Bolt 開工前處理的項目（不可留給 code-generation）

以下五項涉及**已核可上游的修訂**或**尚未有承載形式的設計判斷**，不是實作細節：

1. **A:M-5** — R-7.4 對 U-8 的指派無收件人（U-8 已定稿、gate 掛錯 Bolt）。
2. **A:M-6** — `ReconcileReport` 新增欄位無 ADR 節、上游零指標。
3. **A:M-9** — ADR-0015 §14 未登錄 Bolt 1 DoD，而它是該 gate 的 blocking 項。
4. **B:M-4** — `decided_at` 值域變更推翻 ADR-0006 的 audit-logging 判定，需重判。
5. **B:m-5** — `Unparseable` 路徑的 `scope_note` 值未定義且與 R-6.5 的非空要求衝突。

**其餘 20 項的共同性質**：規則已寫對、但引用它的圖／表／鄰檔沒跟上，或計數過期。這一類在 code-generation 寫出真實程式碼時會被編譯器、型別檢查與測試自然逼出來——把它們留在設計層再繞一輪的邊際效益，已由五輪實測證明為負。


---

## 追加登錄：iteration 6／7（2026-08-30T03:52:29Z）

閘門受阻後追加兩輪審查。經過見下方「為什麼多跑了兩輪」。**這兩輪的全部發現一律登錄、不再修**——iteration 7 的 reviewer 自己的結論逐字是「**不建議再開修正迴圈**——五項落點與修法均已逐字定位，直接登錄帶進閘門即可」。

### 為什麼多跑了兩輪

`aidlc-state.ts` 拒絕核可：**「A later declared-artifact write clears the matching receipt」**——iteration 5 之後我又編輯了產出（修四個 Critical），收據全部失效。引擎不接受「口頭聲明修正未經驗證然後照樣過關」。

iteration 6 因此上場，抓到**兩個新 Critical**（皆出自修正 3）；我修掉後收據再次失效，iteration 7 上場，又抓到**兩個新 Critical**（皆出自那次修正的傳播面未走完）。**這正是本檔開頭那張表描述的形狀在閘門前又重演兩次**，故停止。

**關鍵認知**：引擎要求的是**新鮮的終局收據**，不是 `READY`——`NOT-READY` 同樣算數。所以「帶著 open items 進閘門」這條路存在，只是收據必須是**最後一個動作**。前六輪每次都在記完收據後又去修，才把收據洗掉。

### iteration 7 的發現（5 項，全部「新引入」）

| # | 嚴重度 | 內容 | 落點／閘門 |
| --- | --- | --- | --- |
| **C-7.1** | **Critical** | U-7 的 **R-6.1（補平路徑）推進 `last_synced_at` 卻不重寫受管區塊**，與新增的 R-5.13（該欄語意＝受管區塊上一次成功寫入的時刻）直接矛盾。時序：反向 PR 被拒 → U-7 每日排程先跑（PR 關閉不觸發事件驅動的 U-6）→ 補平並推進時刻＋補齊三欄 → 次輪 U-6 三欄無漂移、R-5.6 第二來源亦不成立 ⇒ **[US:S-6 AC 5] 的告示永久靜默且無紅燈**。**`last_synced_at` 現有三個寫者（R-5.4／R-6.1／R-6.8），本輪只對兩個做了語意對齊。** 修法：R-6.2 的禁動欄位由一欄擴為兩欄 | **Bolt 1 開工前**（靜默失效） |
| **C-7.2** | **Critical** | `write_body` 失敗的處置在**四處**逐字保留修正前的行為（「對應的那一欄維持原值」／「其餘欄位照常回寫」＝`last_synced_at` 前進＝C-6.2 原樣）：`U-6/business-logic-model.md:53`、`:66`、`U-3/business-rules.md:104`、`U-3/domain-entities.md:50`。其中序列圖那兩處是 iteration 6 建議欄**逐字點名**的落點而未執行 | **Bolt 1 開工前**（靜默失效） |
| M-7.1 | Major | `U-6/business-logic-model.md:54` 的 `read_item` 仍無錯誤出口，R-5.12 第四種分支不在序列圖上（例外自然傳播使行為恰好正確，故非 Critical） | code-generation |
| M-7.2 | Major | R-5.12 第二種與第三種對 `last_synced_at` 的處置在「**同輪兩步皆失敗**」時字面互斥（單一步驟失敗時不矛盾）。統括句＋R-5.13 可推導正確解 | code-generation |
| m-7.1 | Minor | `U-4/domain-entities.md:19` 的 `last_synced_at` 欄位定義未隨 R-5.13 收斂 | code-generation |

### iteration 6 的殘留發現（2 個 Critical 已修，其餘登錄）

| # | 嚴重度 | 內容 | 落點／閘門 |
| --- | --- | --- | --- |
| — | Major ×4 | 含 `parse` 對「BEGIN 有 END 無」無規則、`MANAGED_BLOCK_BEGIN` 內嵌版本使跨版本比對未定義、`U-4/domain-entities.md:39` 的「誰寫」未隨 R-6.8 更新（**此項已於 iteration 7 前修正**）等 | code-generation；標記語法兩項掛 **Bolt 1 gate** |
| — | Minor ×4 | 含四項修正的時間戳原填 `09:55:00Z` 為未經 `date -u` 的編造值（**已更正為依 mtime 重建的 `02:47:00Z` 並註明**） | 已處理 |

### 「Bolt 1 開工前處理」清單（更新）

原有 5 項，加上 **C-7.1**、**C-7.2** 共 **7 項**。兩個新增項的共同性質是**靜默失效**——不紅燈、不通報、不進任何清單，只有 [US:S-6 AC 5] 的告示在使用者看不到的地方永久消失。


---

## nfr-requirements 的發現登錄（2026-08-30T05:48:54Z）

**單輪封頂**（停止判準於該輪**開始前**與使用者商定，依 `project.md` 剛升進的規則）。兩組審查合計 **5 Critical、9 Major、6 Minor**，全部登錄、不修產出。**唯一例外**是 U-1 的 Q2 人工裁決紀錄矛盾，已重新取得裁決並更正（見下）。

**逐單元 verdict**：READY = U-2／U-3／U-4／U-5／U-6／U-10b／U-11（7 個）；NOT-READY = U-1／U-7／U-8／U-9／U-10a（5 個）。

### Bolt 1 開工前必處理（機制不生效，且失效是靜默的）

| # | 嚴重度 | 內容 | 落點 |
| --- | --- | --- | --- |
| **N:C-1** | **Critical** | **`U-10a` 選的 `paths-ignore` 在它自己指認的失敗路徑上無效。** `pull_request` 事件的 `paths-ignore` 比對的是**整個 PR diff**（base↔head），不是本次 push；同步回寫進到一個已有 PR 的分支時，該 PR 的 diff 必然同時含開發者的 record 變更 ⇒ 過濾永不成立 ⇒ 新 run 照建、`cancel-in-progress: true` 照取消既有 run。**[US:S-1 AC 7] 兩半皆不可滿足**，而 `U-10a/tech-stack-decisions.md:29` 自己就寫「真正會發動的是 `pull_request`」 | **Bolt 1 前重選機制**（候選：`if:` 條件擋 job、或改用 commit message 標記；`[aidlc-sync]` 前綴已是既有契約） |
| **N:C-3** | **Critical** | **`U-9` 的靜態檢查對象與觸發 allowlist 指向 `aidlc-sync-*.md`／`.lock.yml`**，而四支 workflow 已全數定案為純 Actions `.yml` ⇒ 唯一的機械化決定性閘門**恆綠**，且改同步 workflow 的 PR **不觸發 U-9** | **Bolt 1 前更正檔名樣式**（U-9 於 Bolt 4，但 allowlist 影響的是每個 PR） |
| **N:M-5／N:M-4(B)** | Major | `U-10b` 的交付物只寫改四支 gh-aw 的 `.md`，**缺 `gh aw compile` ＋ commit `.lock.yml`** 這一步（GitHub 執行的是 lock）；漏了則排除完全不生效且無紅燈。`U-8` 亦有兩處仍要求以不存在的 `.lock.yml` 複驗 | Bolt 1（U-10b）／Bolt 3（U-8） |

### 設計衝突（推翻已核可上游，需裁決）

| # | 嚴重度 | 內容 | 落點 |
| --- | --- | --- | --- |
| **N:C-2** | **Critical** | **`U-8` 逕自裁定反向同步「自成第三組 concurrency」，推翻已過 gate 的 `services.md:58`**（「與 S-B 同一組……都碰 record，不應並行」）。該互斥在 ADR-0015 §13 給 U-7 補上 C-4 之後**更必要**，因為兩者都會寫 record | **需 ADR 或回退**；Bolt 2／3 gate |
| **N:C-1(A)** | **Critical** | **`U-7` 重新主張 `latency_samples` 由自己承載 NFR-P1 量測**，違反 ADR-0015 §7 與其 functional-design 的「本單元填不出值／不得以本輪執行耗時冒充」；`security-requirements.md:37` 正把它標為被禁止的頂替值「同步耗時」 | Bolt 2 gate |

### 其餘（code-generation 承接）

- **N:M-1** `U-7` 的「6 × 4 ＋ 2 = 26 次」漏算 C-4 的兩個呼叫（應為 27 或 32，兩讀法皆非 26）——而該數字是批次上限對 C-T5 的判斷基礎。
- **N:M-2** `U-7` 報告落點的兩條理由被 ADR-0015 §13 代價段推翻（它早已每日 commit+push、也已沿用 `paths-ignore`）。
- **N:M-3** `U-7` 同輪互斥：「一致率是唯一可長期追蹤的健康指標」vs「趨勢追蹤因此不可得」。
- **N:M-4** `U-7` 的 R-7.1 靜默失真（checkout 落在 `main`）完全缺席於 reliability 檔。
- **N:M-6** **全 25 份產出對 NFR-C1／NFR-C2 零命中**——既未承接也未判為不適用，而本 intent 正好新增四支 workflow ＋ 三支 `*-impl.yml`（NFR-C2 要求 `name` 與現有 11 支不同）。
- **N:M-1(B)** `U-3` 的 audit-logging 列仍寫「記錄落在受管區塊與 workflow log」，與 U-2 本輪 SEC-5 的重判（`mapped` 支不含時間戳）相反——B:M-4 的重判沒傳到實際寫入點。
- **N:M-2(B)** `U-10b` 的補償控制「合併後 push 仍會跑 `ci.yml`」與 U-10a 的同一條 glob 加在兩個觸發器上直接矛盾。
- **Minor ×6**：`U-1` 四面向表被插入引文從中截斷；`U-3` 四項集合下的散文未隨 §8 重算；`U-2` 的「兩處獨立佐證」實為同一個 commit；`U-6` 標題「四項」而本文五項；5/25 檔對 `requirements.md` 零引用（`upstream-coverage` sensor）；`U-7` SEC-2 揭露表未含 R-7.3 的 `ut HEAD SHA`。

### 已於本輪關閉（不列為 open item）

- **U-1 Q2 的人工裁決紀錄矛盾**（reviewer 判 Critical）：`[Answer]` 記 A（「不設額外防線」）而註解與 artifact 逐字都是 C（「列為 U-9 斷言」），使 U-9 的跨 Bolt 約束壓在未被記為選中的選項上。**已重新取得人工裁決 C 並更正字母**，artifact 不變。
- `open-items.md` 指名由本閘門承接的 **B:M-4**（`decided_at` 值域推翻 U-2 的 audit-logging 判定）與 **B:M-5**（權限四項指標）皆已處理；reviewer 複查確認 B:M-5「五處齊備、可判定關閉」。
- 送審前自檢抓到的兩個真缺口（U-2 SEC-2 白名單會擋掉 R-1.5 的告示、U-1 的 output 數）已修。
- reviewer 另複查四項**未成立**：U-1／U-2 的零 I/O 成立；U-2 SEC-1 對 sha256 的定位正確；U-3 的 `write_body` IAM 已反映；U-10a 對 `actions-lock.json` 的供應鏈發現成立且處置正確。


### B:M-1 — 已關閉（code-generation，2026-08-30T06:40:39Z）

`U-1/functional-design/business-rules.md` 的總函式性群已由 `R-6` 改編為 **`R-7`**，`business-logic-model.md:95` 的交叉引用同步更新，新編號處留對照註。`## Review` 段內的歷史引用**刻意未改寫**（改寫會讓那幾輪 iteration 的紀錄與當時實況不符），對照註已說明歷史 `R-6` 一律指總函式性。

> **記一筆流程錯誤**：本次 code-generation 一度另開 `CG:MIN-1` 重複登錄同一件事，並把指派寫成「下次觸及該檔時」——而 B:M-1 早已登錄且落點就是 code-generation（即當下）。錯在新增登錄前沒有先 grep 既有登錄。由實作 agent 的回報反向抓出。此為本 intent 第五次「新增前未查既有集合」的同型失誤。

### CG:OPEN-1 — `ParsedRecord.binding` 未實作，上游對其來源有兩處互相衝突的敘述（2026-08-30T06:40:39Z）

**嚴重度**：需閘門裁決（非缺陷，是上游矛盾）

U-1 的實作未產生 `binding`，`intents_json` input 保留在介面上但目前無消費者。實作者的理由經複核成立：

1. 本 action 的五個 output **沒有一個承載 `binding`**，`business-rules.md` 的 R-1～R-7 沒有一條讀它；
2. 綁定編號在 `intents.json` 中的**鍵名上游從未指定**，現行 `intents.json` 的條目也沒有該欄位；
3. **兩處上游互相衝突**——`component-methods.md` 把 `read_binding(record_path)` 定為 **C-4（U-4）** 的方法、`requirements.md` FR-A2 說它在「record 內」，而 `business-logic-model.md` §步驟 1 第 3 點寫「從 `intents_json` 取」；
4. 已核可的 11 步計畫**沒有任何一步**涵蓋 binding。

**處置**：不猜。在鍵名未定且讀者不存在的情況下實作一個解析器，只會產生看起來權威、實際是猜測的值。`map.sh:270-283` 有完整註解。**指派 Bolt 1 gate 裁決**：(a) 確認 `binding` 歸 U-4 且本 action 的 `intents_json` input 應移除，或 (b) 指定 `intents.json` 的鍵名並補 U-1 的第六個 output。

### CG:OPEN-2 — README 的 Project #16 連結無回歸保護（U-11，2026-08-30T07:39:15Z）

**嚴重度**：Minor（已知缺口，計畫層已裁決不補）

`validate_repo_contract.py` 的 `REQUIRED_TEXT` 對 `README.md` 鎖的是既有關鍵字（`Cloud-360`／`AWS`／`GCP`／`Azure`／`draw.io`／`Mobile Web`／`Cloud Security Posture`／`human approval gate`／`MCP & Skill Management`），**不含 U-11 新增的 `projects/16` 連結**。刪掉整個 `## Requirements Source` 段，contract 仍綠燈，無任何自動化層察覺。

**已裁決不補**（Plan Approval 選 Approve Plan，替代選項「把連結加進 REQUIRED_TEXT」明列在題目中未被選）。記在此處是為了避免下游把「validate 通過」誤讀成「這段受保護」。若日後要補，一行的改動。
