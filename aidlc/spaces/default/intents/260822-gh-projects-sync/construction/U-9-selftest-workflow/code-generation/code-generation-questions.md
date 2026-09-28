# Code Generation Questions — U-9 自我測試 workflow

<!-- Stage: code-generation（Construction，per-unit）· Unit: U-9-selftest-workflow · kind: service -->

> 人工已授權 orchestrator 自行裁決（2026-09-05）。**不在授權範圍**：寫入 #16、commit／push／開 PR、建立憑證型 secret、啟用正式同步、代替 Bolt gate 做 ADR 級裁決。

## Q1（阻塞）— `functional-design` 與 `nfr-requirements` 對檢查對象的說法互相矛盾

**Question**: `open-items.md` 的 **`N:C-3`（Critical，期限「Bolt 1 前更正檔名樣式」）** 逐字指出：本單元的靜態檢查對象與觸發 allowlist 指向 `aidlc-sync-*.md`／`.lock.yml`，而四支 workflow **已全數定案為純 Actions `.yml`** ⇒「唯一的機械化決定性閘門**恆綠**，且改同步 workflow 的 PR **不觸發 U-9**」。

更正**已經做了一半**：

| 檔案 | 說法 | 時間 |
| --- | --- | --- |
| `nfr-requirements/tech-stack-decisions.md:32-34` | **`.yml` 原始檔**（`.github/workflows/aidlc-sync-*.yml`），並逐字記載此更正的由來 | 2026-08-30T06:11:59Z |
| `functional-design/business-rules.md:25`、`:29` | 仍寫「解析編譯後的 **`.lock.yml`**」「allowlist 涵蓋 `aidlc-sync-*.md`／`.lock.yml`」 | **未更正** |
| `functional-design/business-logic-model.md:22`、`:83` | 同上 | **未更正** |

**`functional-design` 才是實作者讀的規則正本**——照它寫，本單元交付的就是一個指向不存在檔案的閘門。

- **A. 依 `nfr-requirements` 的更正版實作（`.yml` 原始檔），把 `functional-design` 的四處矛盾大聲標出、以測試釘住，但不回改上游** — 與 U-8 實作者拒絕照 orchestrator 錯誤計畫行事、選擇已過 gate 之正確版本的處置同型
- B. 照 `functional-design` 的字面實作 — 交付一個恆綠的閘門，等於本單元完全沒做
- C. 先回頭改 `functional-design` — 那是已核可上游 artifact，超出授權範圍

[Answer]: A. 依更正版實作、標出矛盾、以測試釘住 <!-- 2026-09-05T18:54:06Z, orchestrator 裁決 -->

**依據**：①`N:C-3` 本身就是**已登錄的 Critical 且修法明確**（「更正檔名樣式」），不是待裁決的開放問題；②更正已在 `nfr-requirements` 落地並附完整理由，`functional-design` 只是沒跟上——與 C-7.1 完全同型（已決定的修正沒有傳播）；③B 會讓本單元的**唯一機械化閘門**恆綠，而該閘門正是它存在的理由；④C 逾越授權。**四處矛盾登錄為待 gate 追認，落點 Bolt 1（`N:C-3` 的原定期限）。**

## Q2 — 端到端那一段的測試 Project

**Question**: 完成判準含「憑證做範圍外寫入時回 403」與端到端驗證，實作註記逐字要求測試 item 必須是**本次執行專屬**或位於**獨立測試看板**——常駐於 #16 會成為第 72 張卡進入 P3 視野，且並行 CI 寫同一 item 會觸發回讀不符而**自動增生 issue**（ADR-A3）。

- **A. 端到端段以 stub 實作，並把「需要真實看板」的部分明確標為未驗證** — 人工保留事項含「不得寫入 #16」，而 #23 的寫入雖被允許過（U-6 的 live 測試），但本單元的端到端需要**本次執行專屬的 item**，在沒有 commit／push 的前提下無法產生真實觸發
- B. 對 #23 做真實端到端 — 需要真實 PR 觸發才有意義，而開 PR 不在授權內

[Answer]: A. stub 實作，未驗證部分明確標出 <!-- 2026-09-05T18:54:06Z, orchestrator 裁決 -->

**依據**：本單元的驗證方式是「⑥workflow 執行期（CI 紅綠）」，而 CI 紅綠需要真實 PR 觸發——那不在授權內。**如實記載：U-9 的完成判準三條中，靜態檢查那條可在本 stage 驗證，另兩條（改壞映射 ⇒ CI 紅燈、憑證 403）只有 stub 證據。**

## Plan Approval

[Answer]: Approve Plan（orchestrator 自核，依人工授權） <!-- 2026-09-05T18:54:06Z -->
