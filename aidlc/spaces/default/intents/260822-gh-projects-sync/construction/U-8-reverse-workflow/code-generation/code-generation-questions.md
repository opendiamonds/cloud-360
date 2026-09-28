# Code Generation Questions — U-8 反向同步 workflow

<!-- Stage: code-generation（Construction，per-unit）· Unit: U-8-reverse-workflow · kind: service -->

> **本單元起，人工已授權 orchestrator 自行裁決**（使用者於 2026-09-05 明示「剩下階段可以你自己跑完，中間都不用我進行任何決策」）。以下裁決由 orchestrator 依 memory 規則層與已核可上游設計做出，逐項記錄依據供事後複驗。**不在授權範圍**且維持人工保留的事項：寫入 #16、commit／push／開 PR、建立憑證型 secret、啟用正式同步、代替 Bolt gate 做 ADR 級裁決。

## Q1 — `REVERSE_PR_LABEL` 的單一真實來源

**Question**: **U-8 是反向 PR 的產生者**（D-1 明訂它必須同時設定分支名前綴與 label），但 label 字面目前**硬編碼在 U-6 的 impl**（`aidlc-sync-forward-impl.yml:157`），而 U-7 從 U-6 推導（`reconcile-impl:222`）。若 U-8 也自抄一份，三個單元各有一份副本——與 `SYNC_MARKER` 完全同型的漂移風險（U-10a 的 `MARKER-1` 正是為此而生）。

- **A. U-8 也從 U-6 的 impl 推導** — 全 repo 維持**恰好一份字面**（`forward-impl:157`）＋ 三個推導者。沿用 U-7 已建立的既有形狀，零新模式
- B. U-8 自己硬編（產生者應擁有它） — 語意上較正確，但會製造第二份字面，且要改 U-6／U-7 的推導方向（跨兩個已交付單元）
- C. 抽出共用常數檔 — 最乾淨，但新增一個所有 workflow 都要 checkout 的檔案，形狀改變超出本單元

[Answer]: A. U-8 也從 U-6 的 impl 推導 <!-- 2026-09-05T17:42:42Z, orchestrator 裁決 -->

**依據**：①B 需修改兩個已通過 reviewer 的單元，屬跨單元修改；②`project.md` 的「單一真實來源」規則要求「新增第二份物化前先確認是否有既有常數可用」——U-6 的字面就是既有常數；③A 讓字面數維持 1，是三個選項中唯一不增加漂移面的。**代價如實記載**：真實來源落在**消費者**（U-6）而非**產生者**（U-8），語意上倒置。**登錄為待 gate 追認項**：日後若要正名，正確方向是把字面移到 U-8 並讓 U-6／U-7 改推導——那是一次跨三單元的變更，不由本站夾帶。

## Q2 — `notify`／C-5 的承接

**Question**: R-4c 逐字記載：`components.md` 給 `aidlc-sync-reverse.yml` 的元件鏈**原本不含 C-5**，ADR-0015 §5 已為此開出修訂，但本單元三份設計產出當時對 `notify`／C-5／通報**零次**提及。後果是反向同步的外部失敗只紅燈、**不產生通報 issue**，[req:FR-E1]／[US:S-8 AC 1] 在這條路徑上不成立——與 U-6 iteration 1 被抓到的同一個缺陷。

- **A. 實作 `notify`，比照 U-6／U-7 的形狀** — ADR-0015 §5 已核可 C-5 進入元件鏈，R-4c 也已把 `notify` 列進「本單元呼叫的六個上游方法」，實作它是執行已核可的設計而非擴大範圍
- B. 不實作，標為缺口交給 gate — 會讓一條已被上游指出、且修法明確的缺陷再延一個 gate

[Answer]: A. 實作 notify，比照 U-6／U-7 的形狀 <!-- 2026-09-05T17:42:42Z, orchestrator 裁決 -->

**依據**：ADR-0015 §5 已核可、R-4c 已列入方法表——這是**執行已核可設計**，不是本站自行擴大範圍。U-7 的 C-7.1 教訓正是「已有明確修法的既有項目不該再往後推」。

## Q3 — over-suppression 的「未實測」如何處置

**Question**: R-4 逐字把 over-suppression 標為「本路徑的真正風險，**未實測**」，並說 E-2（一 intent 一 PR）**改變了失敗模式但沒有消除「未實測」**；[US:S-6 AC 3] 的反例在 E-2 下「應**平凡成立**」，但「平凡成立」與「實際成立」是兩件事，**仍需 Bolt 3 實測**。

- **A. stub 行為測試寫出該反例，並明記它不能取代 Bolt 3 的實測** — 在本 stage 能做到的最強驗證：斷言「PR 含 X 不含 Y ⇒ U-6 對 X 暫停、對 Y 照常寫」在編排層成立
- B. 只記載、不寫測試 — 上游已說「平凡成立」，但那正是「看起來成立、實際沒驗」的形狀
- C. 動用真實 API 實測 — 會在 public repo 留下永久 PR 編號，且 Bolt 3 才是它的落點

[Answer]: A. stub 行為測試寫出該反例，並明記不能取代 Bolt 3 實測 <!-- 2026-09-05T17:42:42Z, orchestrator 裁決 -->

**依據**：本 intent 反覆出現的失效形狀就是「結構上成立所以不寫斷言」——R-2.1 自己就寫著「**結構上不可能發生的事，仍要有測試證明它沒發生**，否則未來有人擴大寫入範圍時沒有東西會失敗」。同一條紀律適用於 R-4。C 被排除：`stories.md` 已記載開 PR 會在 public repo 留下永久編號，且人工保留事項含「不得開 PR」。

## Plan Approval

[Answer]: Approve Plan（orchestrator 自核，依人工授權） <!-- 2026-09-05T17:42:42Z -->
