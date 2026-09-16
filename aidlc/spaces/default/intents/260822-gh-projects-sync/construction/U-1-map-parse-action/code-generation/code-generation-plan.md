# Code Generation Plan — U-1 映射與解析 composite action

<!-- Stage: code-generation（Construction，per-unit）· Unit: U-1-map-parse-action
     Generated: 2026-08-30T06:18:47Z（讀自 date -u） -->

## 這個單元要交付什麼

`unit-of-work.md` 的 U-1 條目：**交付 = `.github/actions/aidlc-sync-map/action.yml` ＋ 其 fixture 集**；`kind: library`；驗證方式限**純文字 fixture 斷言**，不得出現任何網路或檔案系統 I/O（那會摧毀 [US:S-10 AC 1] 的 fixture 驅動前提）。

本 repo **無 composite action 先例**（`.github/actions/` 目錄不存在），此為首例。

## 兩項計畫層決定（送審時請一併裁決）

### 決定 1：邏輯放 `map.sh`，`action.yml` 只做介面轉接

`action.yml` 的 `using: composite` ＋ `shell: bash` 已由 [Q1=A] 定案。但**把全部解析與判定邏輯內嵌進 YAML 的 `run:` 區塊，會讓 U-1 的完成判準無法在本單元內達成**——fixture 斷言就得先跑起一個 workflow（或 `act`），而那正是「純文字 fixture 斷言」要避開的。

因此計畫為：`.github/actions/aidlc-sync-map/map.sh` 承載全部邏輯，**只從環境變數讀輸入、只往 `$GITHUB_OUTPUT`（或 stdout）寫輸出**，自身不開任何檔案；`action.yml` 負責把 7 個 `inputs` 轉成環境變數、呼叫 `map.sh`、宣告 5 個 `outputs`。

- **這讓「零 I/O」成為可測的事實而非宣稱**：測試以 `env` 餵字串直接呼叫 `map.sh`，讀 fixture 檔的是測試框架，不是受測邏輯。
- **代價（誠實記載）**：交付物比 `unit-of-work.md` 字面的「`action.yml` ＋ fixture 集」多一個檔。這是**擴充交付清單**，需要人工同意，不由我自行認定。

### 決定 2：fixture runner 用 `python3`，落點 `.github/actions/aidlc-sync-map/run-fixtures.py`

U-1 的完成判準要求「`get_field` 的四條行為各有反例通過」與「對照表為總函式」，都需要一個能實際跑起來的斷言器。**U-9 擁有 selftest workflow，U-1 擁有 fixture 集**——但兩者之間的「斷言器」在上游沒有指定擁有者，這是一個**真實的契約缺口**（送審前自檢第 2 項的形狀：有讀者、有寫者，但中間那一段沒人具名）。

計畫定為由 U-1 交付，理由：完成判準寫在 U-1 而不在 U-9；且 U-9 的 `tech-stack-decisions.md` 已定案靜態檢查工具為 `python3`，沿用同一個工具不引入第二種心智模型。**U-9 的 workflow 只負責呼叫它。**

若你認為斷言器應歸 U-9，請選 Request Changes——這會把 U-1 的完成判準改為「fixture 集齊備」而把「跑綠」推遲到 U-9，是一個真實的替代方案，不是錯的。

## 實作步驟

### Step 1 — 目錄與骨架
- [x] 建 `.github/actions/aidlc-sync-map/`（repo 首個 composite action）
- [x] `action.yml` 骨架：`name` / `description` / 7 個 `inputs`（含 `default`）/ 5 個 `outputs` / `runs.using: composite`
- [x] `map.sh` 骨架 ＋ `set -euo pipefail`，宣告哨兵常數
- **追溯**：[US:S-2]、[ad:ADR-A1]

### Step 2 — `get_field`（R-1 群，安全關鍵）
- [x] R-1.1 回第一個 match／R-1.2 存在但空回空字串／R-1.3 缺席回 `null`／R-1.4 縮排不算 match
- [x] **`null` 以哨兵字串表達**（`tech-stack-decisions.md` 指定的承接方式），在 `map.sh` 內以註解寫明語意與為何 bash 需要它
- **追溯**：[US:S-2 AC 7–10]、[req:FR-J6]

### Step 3 — `list_stages`（R-2 群）
- [x] R-2.1 行樣式 `- [<c>] <slug> — <EXECUTE|SKIP>`；R-2.2 `in_scope` 由尾綴定
- [x] R-2.3 區塊內不 match 的行靜默略過；R-2.4 零行 match ⇒ `Unparseable{missing:["stage-lines"]}`；R-2.5 無區塊 ⇒ `{missing:["stage-progress-section"]}`
- **追溯**：[US:S-2 AC 1–2]、[req:FR-J4]

### Step 4 — `scope_note` 推導（`business-rules.md` 的 `scope_note` 群，R-6.1–6.5）
- [x] 兩類蒐集、固定格式、空類寫 `none`、**依出現順序不排序不去重**（順序進 `content_hash`，一變雜湊就變）
- **追溯**：[req:FR-F3]、U-2 的 R-1.2

### Step 5 — `map` 判定順序（R-3 群 ＋ R-4 群）
- [x] R-3.1～R-3.7 七條依序；**R-3.6 的「動過」＝ in-scope checkbox 全落在 `{" ", "S"}`，`"S"` 不算動過**
- [x] R-4.1／4.2 白名單分流；R-4.3 白名單只對 `Unparseable` 生效
- **追溯**：[US:S-2 AC 3、5]、[US:S-3 AC 5–6]、[req:FR-B3]、[req:FR-G3]、[req:FR-J5]

### Step 6 — `field_value_for`（R-5 群）
- [x] 四種前綴；R-5.1 只截 slug 尾端；R-5.2 前綴與編號永不截；R-5.3 slug 可截到零長；**R-5.4 前綴＋編號已超限時照寫並允許超限**
- **追溯**：[US:S-5]、[ad:ADR-A4]

### Step 7 — `action.yml` 介面組裝
- [x] 7 個 input 轉環境變數、呼叫 `map.sh`、5 個 output 經 `$GITHUB_OUTPUT` 導出
- [x] `whitelist`／`reverse_pending` 以**換行分隔字串**承載，空字串為空集合
- **追溯**：[Q1=A]、[Q2=A]、`domain-entities.md` §`Config` 的承載形式

### Step 8 — fixture 集（測試資料）
- [x] `fixtures/` 下的純文字案例，逐條規則各一：R-1 四條各含**反例**、R-2.4／2.5、R-3 七條、R-4 三條、R-5 四條、`scope_note` 五條
- [x] **[req:FR-B3] 的孿生 fixture**：兩個只在 `[S]`／`— SKIP` 上不同的 record，斷言 **Status 相同**且 `scope_note` 不同
- **追溯**：[US:S-10 AC 1]、U-1 完成判準

### Step 9 — fixture runner ＋ 斷言（Standard 測試強度）
- [x] `run-fixtures.py`：讀 fixture、以 `env` 呼叫 `map.sh`、比對期望值、非零 exit 表失敗
- [x] **直接斷言 `get_field` 的回傳值**，不得只斷言最終 `Decision`（R-1.2 與 R-1.3 在第 1 條判定上結論相同，錯誤不會被判定結果暴露）
- **追溯**：`business-rules.md` R-1 群的明文驗證約束

### Step 10 — 總函式性檢查（[US:S-2 AC 15]）
- [x] 對 `(checkbox 組合 × runtime_status × parked × in_scope 組合)` 的窮舉／隨機組合斷言：不拋例外、`reason_code` 在值域內且非空、`status != null` **恰好蘊含** `reason_code == "mapped"`
- **追溯**：[US:S-2 AC 15]、`org.md` 的 property-based 落點慣例

### Step 11 — 註解與文件
- [x] `map.sh` 內對哨兵語意、R-5.4 的刻意超限、R-3.6 的「`S` 不算動過」各寫一段**為什麼**（這三處都是後人最容易「順手修掉」的地方）
- [x] `action.yml` 的 `description` 指向本 record 的設計檔

## 不在本單元範圍（避免越界）
- 寫入 Projects #16、開 issue、寫 `sync-state.json`、渲染受管區塊 — 分屬 U-3／U-5／U-4／U-2
- selftest workflow 本身（`.github/workflows/aidlc-sync-selftest.yml`）— U-9

## 本計畫發現的上游瑕疵（登錄，不自行改上游）
- **`business-rules.md` 有兩個 `R-6` 群**：一是 `scope_note` 推導（R-6.1–6.5），一是總函式性。同一識別字指向兩件事，會讓 fixture 與註解的追溯產生歧義。**不使任何 AC 不可滿足**，但屬追溯風險。本計畫一律以「`scope_note` 群」與「總函式性」稱之，不用 `R-6`。指派：下次觸及該檔時把總函式性改編為 `R-7`。
