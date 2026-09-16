# Tech Stack Decisions — U-1 映射與解析 composite action

<!-- Stage: nfr-requirements（Construction，per-unit）· Unit: U-1-map-parse-action -->

## 決定

**`using: composite` ＋ 全部 step 使用 `shell: bash`**（[Q1=A]）。

檔案落點 `.github/actions/aidlc-sync-map/action.yml`。本 repo **無 composite action 先例**——`.github/actions/` 目錄不存在，此為首例。

## 理由

| 面向 | 判定 |
| --- | --- |
| 既有慣例 | repo 的 14 處 `shell:` 宣告**全部是 `bash`**（`.github/workflows/*.yml` 實測計數）。這是 workflow step 的慣例，composite action 沿用它不引入第二種心智模型 |
| 新先例成本 | **零**。不需新 runtime、不需 `node_modules`、不需打包產物進版控 |
| 規則相容性 | **無爭議**。`project.md ## Forbidden` 禁止以 repo 內新增的實作程式承載無人值守的流程自動化，同一條並要求「決定性的映射邏輯應優先放在純 Actions 步驟」；bash step 明確落在後者 |
| fixture 驅動 | `aidlc-sync-selftest.yml`（U-9）以純文字 fixture 驅動時不需額外 runtime，[US:S-10 AC 1] 的前提維持 |

**被否決的兩案與其代價**（記錄以免下次重問）：

- **`shell: python`**：`None` 與 `""` 天生可分，最貼合 `business-rules.md` 的 R-1 群。但它落在 `## Forbidden` 那條規則的模糊交界——composite action 由事件觸發、無人在迴圈內，字面上屬「無人值守」。此爭議未經裁定即採用會是替使用者做一個他不知道自己在做的決定。
- **`using: node20`**：`null`／`""` 可分，`@actions/core` 有設 output 的標準做法，且 repo 既有 ESLint 可涵蓋。但需把 `ncc` 打包產物進版控，而 **frontend 之外本 repo 無任何 Node 建置產物進版控的先例**。

## 這個決定的已知代價（不掩飾）

**bash 沒有原生的 `null`**，而 `business-rules.md` 的 R-1.2（欄位存在但空 → 回空字串）與 R-1.3（欄位完全缺席 → 回 `null`）的區分，是該檔明文標為**安全關鍵**的一條——`domain-entities.md` 記載現況 record 的 `## Runtime State` 只有 `- **Revision Count**: 0`，`Parked` 是**缺席**而非空值，混同會讓 park 特判永不觸發。

**承接方式**：以哨兵字串（例如 `\x00ABSENT\x00`）或分離的 exit code 表達 `null`，並在 `action.yml` 內以註解寫明該哨兵的語意。

**這是一個手工慣例，不是型別系統保證的東西**——未來的編輯者可能靜默弄壞它。因此 `business-rules.md` R-1 群已明文要求：該規則的驗證必須**直接斷言 `get_field` 的回傳值**，不得只斷言最終 `Decision`（因為 R-1.2 與 R-1.3 在第 1 條判定上結論相同，錯誤不會被判定結果暴露）。這條約束由本決定直接產生，落在 U-9 的 fixture 集。

## 對照既有技術棧（[kb:technology-stack.md]）

本站在下決定前查了 codekb 的技術棧盤點，三項與本決定相關：

| 事實 | 出處 | 對本決定的影響 |
| --- | --- | --- |
| repo 同時有 **Python 3.12**（`backend/`、`scripts/`，含 1,595 LOC 驗證／同步腳本）與 **Node.js 22**（frontend build、backend runtime、CI） | [kb:technology-stack.md] | 兩個被否決的方案在**執行環境上都可行**，否決理由不是「跑不起來」，而是規則爭議（python）與版控先例（node） |
| `frontend/scripts/check-api-types.mjs` 是 **CI gate**（`ci.yml:69` 跑 `npm run check:types`） | 實測 `ci.yml` 與 `frontend/package.json:13` | repo **有** Node 腳本作為 CI 閘門的先例。但那是**純 `.mjs` 原始碼**，不是 `ncc` 打包產物——「無 Node 建置產物進版控先例」的判斷因此仍然成立，兩者不可混為一談 |
| GitHub Actions 為 CI/CD 主幹：`ci.yml`(4 job) ＋ `deploy.yml`(3 job) ＋ 11 組 gh-aw | [kb:technology-stack.md] | composite action 落在既有主幹內，不引入新的自動化層 |

**一項對 codekb 的更正（實測不符）**：[kb:technology-stack.md] 記載「action 釘選 **全部 SHA pin**」。實測 `.github/workflows/*.yml` 的 `uses:` 集合，**SHA pin 與版本標籤混用**——`actions/checkout@34e114876b…`、`actions/setup-node@48b55a01…` 是 SHA，但同時存在 `actions/checkout@v4`、`actions/checkout@v6`、`actions/setup-node@v4`。「全部 SHA pin」對 `.github/aw/actions-lock.json`（gh-aw 的鎖檔）成立，對手寫 workflow **不成立**。此更正屬 codekb 的新鮮度問題，不改變本決定。

## 與上游的對應

承載形式引自 [ad:decisions.md] ADR-A1 與 [F1=A]（一律參數化）；`get_field` 的四條行為與其安全關鍵性引自本單元的 `business-rules.md` R-1 群與 `business-logic-model.md` §步驟 1；`requirements.md` 的 FR-J6（`getField()` 語意複製）為該行為的正本；`unit-of-work.md` 的 U-1 條目定義本單元的交付與驗證方式。
