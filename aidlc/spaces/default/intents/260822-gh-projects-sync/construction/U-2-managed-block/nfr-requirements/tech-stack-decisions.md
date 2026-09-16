# Tech Stack Decisions — U-2 受管區塊渲染與雜湊

<!-- Stage: nfr-requirements（Construction，per-unit）· Unit: U-2-managed-block · kind: library -->

## 決定

**`.github/actions/aidlc-sync-block/action.yml`，`using: composite`、`shell: bash`、以 `operation: render|parse|hash` 分派**（[Q1=A]）。

執行環境沿用 U-1 的定案（composite ＋ `shell: bash`，見 U-1 的 `tech-stack-decisions.md`）——理由相同：repo 的 14 處 `shell:` 全部是 bash，零新先例、零規則爭議。

## `operation` 分派與既有設計的對應

`business-logic-model.md` 的資料流圖已把三個操作畫成**互不共享狀態的獨立呼叫**（`render` 吃 `Decision`＋`Context` 吐字串；`parse` 吃 issue body 吐 `Block` 或 `null`；`content_hash` 吃 `Block` 吐 sha256）。`operation` 輸入正是把那三條路徑在 YAML 層具名化——分派不是新結構，是既有資料流的直接映射。

同檔的 `parse` 版本分派流程（讀版本標記 → 三種回 `null` 的情形 → 套用對應解析器）**只落在 `operation: parse` 這一支**，另兩支不需要它。這也是「單一 action 但輸入為聯集」的具體長相。

## 為什麼是單一 action 而非三支

三個操作共用**同一份格式知識**：`FORMAT_VERSION`、版本分派的解析器集合、四項必載內容的欄位順序。拆成三支就得把這份知識複製三份，而 `team.md ## Code Style` 的「單一真實來源」明文要求「當同一份事實已存在於程式中，新增第二份物化前必須先確認是否有既有常數或 API 可直接使用」，並要求無法避免的副本必須有鎖住一致性的測試。

composite action 沒有乾淨的共用機制（只能靠相對路徑 source 一個共用腳本），所以「三支 ＋ 共用檔」的形狀並不比「一支 ＋ 分派」單純。

**代價（[Q1=A] 選項本文即已載明）**：`inputs`／`outputs` 成為三種操作的聯集，YAML 層看不出哪些組合合法。承接方式：在 `action.yml` 的 `description` 逐操作列出必要 input 與有效 output，並讓 `operation` 值不合法時**立即失敗**（非零 exit），而非靜默回空值。

## 本單元對 U-1 決定的一項具體代價

U-1 選了 `shell: bash`（[Q1=A]），該檔已記載其已知代價是 bash 沒有原生 `null`。**本單元揭露第二項代價，上一站看不到**：

`content_hash` 的簽章是 `(Block) -> sha256`——雜湊算在**結構**上，因此需要一份**正規化序列化**（固定欄位順序、固定分隔符、固定跳脫規則）。在 bash 中這要手工實作：`printf` 逐欄輸出 ＋ 明確分隔符 ＋ `sha256sum`（或 macOS 的 `shasum -a 256`）。

三個具體風險，全部是 bash 特有的：

| 風險 | 為什麼在 bash 特別容易發生 |
| --- | --- |
| 欄位值含分隔符 | 沒有型別系統把值與分隔符分開；`traceable_row` 或 `scope_note` 若含該字元即產生歧義 |
| 尾端換行 | `$(...)` 會吃掉尾端換行，`printf` 與 `echo` 的行為不同；兩個實作寫法產生不同雜湊 |
| locale 影響排序 | 若序列化涉及任何排序，`LC_ALL` 未固定時同一輸入在不同 runner 上可得不同結果 |

**承接方式（本站定案，非建議）**：序列化函式必須有自己的 fixture——**同一個 `Block` 在兩次獨立執行中必得逐位元相同的序列化字串**，且該 fixture 涵蓋上述三種情形各一例。這條落在 U-9 的 fixture 集，本站標出落點但不指派其擁有權（那是 units-generation 的產出）。

> **這不是回頭質疑 U-1 的決定。** bash 仍是唯一零新先例、零規則爭議的選項，[Q1=A] 成立。但它的代價比 U-1 那一站看得到的更大，如實記載以免下游把「已決定用 bash」讀成「沒有額外成本」。

## 沿用的既有技術事實

| 事實 | 出處 | 意義 |
| --- | --- | --- |
| repo 的 `uses:` 為 SHA pin 與版本標籤**混用**（非 codekb 所稱的全部 SHA pin） | 實測 `.github/workflows/*.yml`（更正見 U-1 的 `tech-stack-decisions.md`） | 本地 action 無論如何沒有 SHA 可釘，見 U-1 的 SEC-3 |
| GitHub Actions 為 CI/CD 主幹 | [kb:technology-stack.md] | 本單元不引入新的自動化層 |

## 與上游的對應

C-6 的公開介面引自 [ad:component-methods.md] §C-6 與 [ad:components.md] 的 C-6 條目（後者**沒有**「承載形式」列，是本站 Q1 的由來）；`Block` 結構、版本分派與序列化需求引自本單元的 `domain-entities.md` 與 `business-rules.md`（[Q1=C]／[Q2=A] 的落地）；格式契約引自 [ad:decisions.md] ADR-A6；單元邊界與完成判準引自 [ug:unit-of-work.md] 的 U-2；`requirements.md` 的 FR-G4 為雜湊比對的正本；既有技術事實引自 [kb:technology-stack.md]。
