# NFR Requirements — U-1 映射與解析 composite action

<!-- Stage: nfr-requirements（Construction，per-unit）· Unit: U-1-map-parse-action
     來源標籤：[ad:*] application-design；[req:*]／[US:*] requirements／stories；
     [ug:*] units-generation；[fd:*] 本單元的 functional-design。 -->

## CONDITIONAL 適用性判定

condition：「Performance requirements, security considerations, scalability concerns, or tech stack selection needed. Skip if no NFR requirements and tech stack already determined.」逐項對照 U-1：

| 條款 | U-1 判定 | 依據 |
| --- | --- | --- |
| Performance | ❌ 不適用 | `produces_kinds` 已把 `performance-requirements` 限於 `[service, ui]`，U-1 是 `library`。NFR-P1 的 5 分鐘延遲上限落在 workflow 層（U-6），非本單元 |
| Security | ✅ 適用 | U-1 讀取 record **全文**並把片段寫進 output。它自己不持有憑證，但這正是需要寫下來的事——否則下一個人會想當然地給它憑證 |
| Scalability | ❌ 不適用 | 同 `produces_kinds`，限 `[service]` |
| Tech stack selection | ✅ 適用 | **本 repo 無 composite action 先例**（`.github/actions/` 不存在），`using:` 與實作語言完全未定 |
| Skip if 兩者皆無 | ❌ 不適用 | 上述兩項皆有 |

**判定：EXECUTE**，產出兩份（`security-requirements.md`、`tech-stack-decisions.md`）。與 directive 解析出的 `produces` 一致。

## 上游已定案、本站不重問

| 事項 | 出處 |
| --- | --- |
| NFR-S1～S6 的**機制層**內容（IAM 範圍、獨立 secret、不留存憑證字串、加密由平台承擔、network exposure 不適用、稽核三要素） | `requirements.md` NFR-S1～S6 |
| 承載形式為 composite action，且四項設定一律為 input 不得寫死 | [ad:decisions.md] ADR-A1、[F1=A] |
| action 的 input／output 清單與集合型 input 的換行分隔序列化 | [fd:business-logic-model.md] §介面（[Q1=A]／[Q2=A] 的連帶裁定） |
| C-1／C-2 零 I/O | [ad:components.md] |

## 待決問題

### Q1. composite action 的 `using:` 與實作語言選什麼？

本 repo 的 14 處 `shell:` 宣告**全部是 `bash`**，但那是 workflow step 的既有慣例，不是 composite action 的先例——`.github/actions/` 目錄不存在。U-1 要做的事包含逐行解析、行錨定比對、有序判定與字串截斷。

A. **`using: composite` ＋ `shell: bash`**：與 repo 既有的 14 處 `shell: bash` 一致。看得到的效果：零新工具鏈；`aidlc-sync-selftest.yml` 用 fixture 驅動時不需額外 runtime。代價：`get_field` 的四條行為（尤其 R-1.2「存在但空回空字串」與 R-1.3「缺席回 null」的區分）在 bash 中沒有原生的 `null`，要用 exit code 或哨兵字串模擬，而**那個區分正是 `business-rules.md` 標為安全關鍵的那一條**。

B. **`using: composite` ＋ `shell: python`**：runner 預裝 Python。看得到的效果：`None` 與 `""` 天生可分，R-1 群直接對應；有序判定與截斷邏輯可讀性高。代價：`project.md ## Forbidden` 禁止以 repo 內新增的實作程式承載**無人值守**的流程自動化——本機制正屬此類。該條的邊界以觸發來源判定，而 composite action 由 workflow 事件觸發、無人在迴圈內，**看起來正落在禁止範圍**；但它承載的是決定性映射而非「同步」本身，且該條同時明文要求「決定性的映射邏輯應優先放在純 Actions 步驟」。這個交界需要裁定，不是我可以自行判斷的。

C. **`using: node20` ＋ JavaScript**：GitHub Actions 的原生 action runtime。看得到的效果：`null`／`""` 可分；`@actions/core` 提供 output 設定的標準做法，不必手寫 `$GITHUB_OUTPUT` 跳脫；且 repo 已有 ESLint 設定可涵蓋它。代價：需要 `node_modules` 或打包成單檔（`ncc`），而**本 repo 的 frontend 之外沒有任何 Node 建置產物進版控的先例**；打包產物進版控會與「不得留存建置產物」的一般直覺衝突（此點本 repo 無明文規則，需確認）。

X. Other（請說明）

[Answer]: A  <!-- 2026-08-29T06:08:46Z（讀自 date -u）· composite ＋ shell: bash -->

### Q2. U-1 讀 record 全文並把片段寫進 output——這條路徑要不要防機敏外洩？

U-1 本身不持有任何憑證（它的 input 全是文字與設定），但它**讀 `aidlc-state.md` 全文**，並把 `current_stage`、`intent_id` 等片段寫進 action output。GitHub Actions 的 output 會出現在 workflow log 中，而本 repo 為 **public**，Actions log 公開可讀（此事實已記入 `project.md ## Mandated` 的憑證查證規則）。

A. **不設額外防線，明記理由**：`aidlc-state.md` 的內容本來就在公開版控中，它進 log 不構成新的暴露面；且 U-1 的 output 是四個具名欄位而非全文回顯。看得到的效果：不引入沒有真實威脅模型的機制。代價：若未來有人把機敏內容寫進 record（例如 `Parked` 理由含 token），本單元會原樣搬進 log——而它是**離 log 最近的一層**。

B. **對 output 做遮罩**：在寫 output 前對已知的憑證樣式（`ghp_`、`github_pat_`、PEM 標頭等）做比對並替換為 `[REDACTED]`。看得到的效果：多一道與 `validate_repo_contract.py` 同族的防線。代價：樣式清單是寫死的，而 `project.md` 已記載「本 repo 唯一的 secret 掃描器結構上看不到應用程式碼」——在這裡補一個作用域極窄的掃描器，可能製造「已經有防線了」的錯覺。

C. **不在 U-1 處理，但把它列為 U-9 自我測試的一條斷言**：斷言 U-1 的 output 不含憑證樣式。看得到的效果：防線落在**會持續執行**的層，而不是一段沒人會再看的程式碼。代價：U-9 在 Bolt 4，而 U-1 在 Bolt 1——中間有三個 Bolt 的時間差。

X. Other（請說明）

[Answer]: C  <!-- 原記 2026-08-29T06:08:46Z；字母於 2026-08-30T05:48:54Z 由 A 更正為 C -->

> **字母更正（2026-08-30T05:48:54Z，reviewer 本輪 Critical）。** 原記 `[Answer]: A`，但同行註解「列為 U-9 的斷言，不在 U-1 處理」與 artifact 的處置**逐字都是選項 C 的原文**，而選項 A 的原文是「不設額外防線」。三者中兩者指向 C、一者指向 A，且 **U-9 因此背了一條跨三個 Bolt 的交付約束**——壓在一個沒被記為選中的選項上。
>
> **已重新取得人工裁決：C**（使用者於 2026-08-30T05:48:54Z 明確選擇「列為 U-9 的斷言」）。依 `project.md` 的 `user-stories:260822-us-L3`——當人工輸入的底層事實為真、但因紀錄疏失而無法被證實時，正確處置是重新取得一次可驗證的裁決，而不是替它主張原意。artifact 的處置不變（本來就是 C），U-9 的斷言約束因此有了合法來源。
