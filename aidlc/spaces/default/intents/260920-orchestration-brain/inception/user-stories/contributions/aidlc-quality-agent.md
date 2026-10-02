**Collaborator:** aidlc-quality-agent

<!-- 本行由 conductor 於 2026-10-02T05:43:10Z 補上：品質 agent 寫出本檔時漏了引擎要求的
     identity marker 首行，核可關卡因此被擋下（collaborator notes incomplete）。
     本檔的其餘內容未被改動，全部為該 agent 自己寫的。 -->

# user-stories mob 貢獻 — quality agent（第 2 輪：US11／US12／US13）

**貢獻者**：aidlc-quality-agent
**量測基準**：worktree `chiton`，`git rev-parse --short HEAD` = `9130b80`，量測時間 2026-10-02T02:56:10Z
**本輪範圍**：`requirements.md` 修訂 1 新增的 `FR11`／`FR12`／`FR13`，對應待撰寫的 US11／US12／US13
**我的視角**：這三則故事的每一條 AC，**哪一層自動化能驗它**；驗不了的要被指名為驗不了，而不是留給別人在部署後發現

> **立場聲明**：本檔不為任何既有產出背書。下文每一項量測都附指令與輸出；凡我沒跑過的，一律列在最後一節「未檢查範圍」。
> `team.md ## Testing Posture` 與 `codekb/cloud/code-quality-assessment.md` 的數字我**全部重量**，不轉引——結果是前者有四處過時、後者正確。

---

## 第一部分：規則層與 codekb 的實測校正

### Q-01 `team.md ## Testing Posture` 有四處數字過時，其中兩處會讓下游低估既有測試基礎

**檢查內容**：逐項重量 `team.md` 的「既成事實」段。

**指令與輸出**：

```
$ git rev-parse --short HEAD
9130b80

$ ls backend/tests/test_*.py | wc -l
      46
$ ls backend/tests/*.py | wc -l
      48

$ grep -rn "@given" backend/tests/ | wc -l
      48
$ grep -rl "@given" backend/tests/ | wc -l
      16

$ cd frontend && npm run lint
/…/src/pages/AssessmentPage.tsx
  365:6  warning  React Hook useEffect has a missing dependency: 'detectProviderFromXml' …
/…/src/pages/WorkspacePage.tsx
  302:6  warning  React Hook useEffect has a missing dependency: 'fetchDiagrams' …
✖ 2 problems (0 errors, 2 warnings)
```

**逐項對照**：

| `team.md` 的宣稱 | 實測（`9130b80`） | 判定 |
|---|---|---|
| 「`backend/tests/` **21 個**測試檔」 | `test_*.py` **46** 個（目錄內 `.py` 共 48） | **過時 2.2 倍** |
| 「**7 個檔共 13 個** `@given`」 | **16 個檔共 48 個** `@given` | **過時 3.7 倍** |
| 「`0 errors, 3 warnings`（`AssessmentPage.tsx:365`、`LoginPage.tsx:36`、`WorkspacePage.tsx:279`）」 | `0 errors, **2** warnings`（`AssessmentPage.tsx:365`、`WorkspacePage.tsx:**302**`）；`LoginPage.tsx:36` 已消失、`WorkspacePage` 行號由 279 移到 302 | **過時**（三個細節兩錯一對） |
| 「Frontend 完全沒有 unit／component 測試框架」 | **仍然正確**。`frontend/package.json` 的 `devDependencies` 18 項中測試相關只有 `@playwright/test@^1.56.0`；無 vitest／jest／`@testing-library/*`。`scripts` 新增了 `check:types`／`gen:ws-types`／`check:ws-types`，但沒有 `test:unit` | **正確，予以確認** |

**嚴重性自評**：**Minor**（規則層的記載落差，不影響 US11–13 的 AC 正確性，但會讓下游誤判「補測試的起點很低」）

**建議落點**：**DoD**（US11／US12／US13 共用一條）——「本故事的測試落點以本檔 Q-01 的實測基準為準；不得引用 `team.md ## Testing Posture` 的 21 檔／13 個 `@given`／3 warnings 這三個數字」。
規則層是 append-only，本輪不改 `team.md`；依 `refined-mockups:c3` 把校正記在本站。

---

### Q-02 「六道 CI 閘門」已成 13 道，而新增的兩道**正好覆蓋本 intent 的 WebSocket 變更路徑**——這直接推翻下游的既有判定

**檢查內容**：`project.md`／`team.md` 反覆引用「本 intent 的六道現有 CI 閘門」，而 `delivery-planning` 的學習條目逐字寫「既有的兩道閘門對 WebSocket **完全無效**（它不在 `openapi.json` 的 42 個 path 內）」。我重數 `ci.yml` 的實際斷言步驟。

**指令與輸出**：

```
$ python3 -c "import re;src=open('.github/workflows/ci.yml').read();
  [print(' -',m.group(1)) for m in re.finditer(r'^      - name: (.+)$',src,re.M)]"
 - Check out enough history to read the PR head commit
 - Decide whether this run came from a sync write-back
 - Validate repository contract
 - Validate environment configuration contract
 - Validate cost calculator import boundary        <-- 新
 - Validate pricing lookup boundary                <-- 新
 - Lint
 - API type contract drift                         <-- 新
 - WS contract type drift                          <-- 新
 - Typecheck and build
 - Spec must not be served statically              <-- 新
 - Import FastAPI app
 - OpenAPI spec drift
 - WS contract spec drift                          <-- 新
 - Run unit tests
 - Build backend image
 - Build frontend image

$ ls -la ws-contract.json
-rw-r--r--@ 1 … 31012 Sep 29 22:25 ws-contract.json

$ python3 -c "import json;d=json.load(open('ws-contract.json'));
  print(len(d['components']['schemas']), list(d['components']['schemas'])[:6])"
23 ['ClarifyCandidate', 'ClarifyPayload', 'CorrectWorkItemPayload', 'CostCardPayload', 'DonePayload', 'ErrorPayload']
```

`ci.yml` 內的註解逐字說明這一對閘門存在的理由：

```
# WS drift gate 2 of 2 (the spec's gate is in the backend job below).
# WebSocket needs its own pair because FastAPI does not register websocket
# routes: /api/collab/ws/... is absent from openapi.json's 42 paths, so the
# two gates above are structurally blind to it -- not under-covered, but
# with no assertion at all on that change path (ADR-0019 / NFR5.1).
```

**發現**：扣掉 checkout／判流／兩個 docker build，**實際斷言步驟為 13 道**，不是六道。更關鍵的是 `ws-contract.json`（23 個 schema，含 `WorkItem`／`WsServerMessageType`／`CostCardPayload`）與 `services/brain_ws_contract.py` **已經存在**，WS 漂移雙閘門**已經上線**。
`delivery-planning` 當時的判斷（WebSocket 無任何機械閘門）在 `9130b80` 上**已不成立**——那個缺口已被 ADR-0019 補上。

**對 US11／US12 的直接後果**：這兩則故事若經 WebSocket 傳遞任何新訊息型別，**已經有機械閘門**（後端重 dump `ws-contract.json` ＋ 前端重產 `ws-contract.d.ts`，任一未同步即紅燈）。這把「只能靠 e2e」的判定改成「契約層已有閘門、e2e 只需驗呈現」。

**嚴重性自評**：**Major**（不是 AC 錯誤，是**可驗證層的判定基礎變了**；不修正會讓 US11／US12 的 DoD 要求一道已經存在的閘門，或反過來漏掉它）

**建議落點**：**DoD**（US11＋US12）——「若本故事新增或改動 WebSocket 訊息型別，必須在同一個 PR 內重 dump `ws-contract.json`（`python scripts/dump_ws_contract.py`）並重產 `frontend/src/types/ws-contract.d.ts`（`npm run gen:ws-types`）；CI 的 `WS contract spec drift` 與 `WS contract type drift` 兩道閘門即為驗收證據。」

---

### Q-03 `estimate_readers.py` 的 PBT 缺口**確認存在**，codekb 的記載正確；以下是它五個函式真正該有的性質

**檢查內容**：brief 要求我查證三支解析器，不採信 codekb。

**指令與輸出**：

```
$ wc -l backend/cost/estimate_readers.py backend/cost/estimate_parser.py backend/cost/estimate_validator.py
     384 backend/cost/estimate_readers.py
     322 backend/cost/estimate_parser.py
     122 backend/cost/estimate_validator.py

$ ls backend/tests/ | grep -i "estimate"
test_estimate_intake_api.py
test_estimate_parser.py
test_estimate_validator.py          <-- 沒有 test_estimate_readers.py

$ grep -rn "@given" backend/tests/test_estimate_parser.py backend/tests/test_estimate_validator.py
backend/tests/test_estimate_parser.py:404:    @given(st.binary(min_size=0, max_size=64))
backend/tests/test_estimate_parser.py:411:    @given(
backend/tests/test_estimate_validator.py:106:    @given(

$ grep -rn "estimate_readers" backend/ | grep -v "\.pyc"
backend/cost/estimate_parser.py:8:from cost.estimate_readers import (
backend/tests/test_estimate_parser.py:11:from cost.estimate_readers import MAX_PAYLOAD_BYTES
```

**判定：codekb 的三項宣稱全部正確**——384 行、無專屬測試檔、兩支手足各有 `@given`（2 與 1）。測試側唯一的接觸是 `test_estimate_parser.py:11` import 了一個**常數** `MAX_PAYLOAD_BYTES`，不是任何函式。這確實是 `project.md` PBT hard constraint（經 ADR-0017 移錨至估價表解析器）的**實際違反**，不是記載落差。

**brief 點名的五個函式，我實讀後認為該斷言的性質**（全部可用既有 `hypothesis`，零新依賴）：

| 函式 | 該斷言的性質 | 為什麼這條會真的失敗 |
|---|---|---|
| `normalize_header(cell)` | **冪等**：`normalize_header(normalize_header(x)) == normalize_header(x)`；且輸出無首尾空白、無連續空白 | 實作為 `" ".join(cell.strip().lower().split())`。任何人改成 `replace(" ","")` 或加上全角空白處理都可能破壞冪等 |
| `parse_number(raw)` | **全域性**：對任意 `str` 永不拋例外（回 `Decimal` 或 `None`）；**非有限值一律 `None`**（`NaN`／`Infinity`） | `Decimal(cleaned)` 只接 `InvalidOperation, ValueError`；若未來清洗步驟引入 `TypeError`／`ArithmeticError` 就會炸穿 |
| `sniff_format(bytes, name)` | **副檔名優先且輸出封閉**：回傳值 ∈ `{"csv","xlsx",None}`；給定 `.xlsx`／`.csv` 副檔名時**與內容無關**；空 bytes ＋ 無檔名 → `None`（不得 IndexError） | `file_bytes[:2]` 在空 bytes 上安全，但任何改成 `file_bytes[0]` 的重構會立刻 IndexError |
| `read_csv_table(bytes)` | **列寬不變量**：回傳非 `None` 時，`len(row) == len(headers)` 對每一列成立；列數 ≤ `MAX_ROWS`；**永不拋例外**（任意 binary 輸入） | 已有 `@given(st.binary())` 在 `test_estimate_parser.py:404` 測到類似形狀，但那是測 parser 不是測 reader 本身 |
| `read_xlsx_table(bytes)` | **解壓炸彈上界**：`xlsx_uncompressed_bytes` 超過 `MAX_PAYLOAD_BYTES`（32 MiB）時必回 `None` 而非讀入；對非 ZIP 的任意 binary 回 `None` 不拋例外 | 這是**安全性**不變量（zip bomb），而目前它沒有任何測試 |
| （附帶）`best_clouds(scores)` | **同分集合性**：回傳的每個 cloud 分數相同且等於最大值；**排列不變**；結果 ⊆ `scores.keys()`；`minimum` 以下全濾掉時回 `[]` | 見 Q-05——它是本 repo 現成的「可比較確定性」正確範例 |

**我實跑的驗證**（證明這些性質現在就能寫、而且其中兩條現在是綠的）：

```
$ cd backend && python3 -c "… hypothesis @given(st.text()) max_examples=400/600 …"
--- normalize_header idempotence (hypothesis) ---
idempotent over 400 examples: PASS
--- parse_number totality (hypothesis) ---
never raises: PASS
--- best_clouds determinism ---
best_clouds({'aws':5,'gcp':5,'azure':1}) -> ['aws', 'gcp']
best_clouds({'aws':1,'gcp':1,'azure':1}) -> []
best_clouds({})                          -> []
--- sniff_format filename dominance ---
csv bytes named .xlsx -> xlsx
empty bytes, no name  -> None
```

**嚴重性自評**：**Major**（hard constraint 的實際違反。已由人工裁決指派 `tcms-test-cases`，故不是本輪新發現；但 US11–13 的 DoD 需要指名它，否則它會在 construction 被當成「別人的事」）

**建議落點**：**DoD**（掛在哪一則故事由 lead 定，我建議掛 US13——它是本輪唯一的「既有程式修補」型故事，性質最接近）——「`backend/cost/estimate_readers.py` 的 `@given` 覆蓋為本 intent 的 construction 交付項，落點 `tcms-test-cases`；最低要求為上表六條性質中的 `normalize_header` 冪等、`parse_number` 全域性與非有限值、`read_xlsx_table` 解壓上界三條。」

---

### Q-04 `parse_number` 有三個**我實測到的**靜默錯值行為，其中一個是大小寫不對稱——這是估價金額的入口

**檢查內容**：既然 `estimate_readers.py` 無測試，我直接對 `parse_number` 餵邊界值。

**指令與輸出**：

```
$ cd backend && python3 -c "
from cost.estimate_readers import parse_number
for s in ['1,2,3','\$-5','1e5','  1,234.50 ','usd 5','NaN','Infinity','\$\$5','1,,000']:
    print(repr(s),'->',repr(parse_number(s)))"
'1,2,3'       -> Decimal('123')
'$-5'         -> Decimal('-5')
'1e5'         -> Decimal('1E+5')
'  1,234.50 ' -> Decimal('1234.50')
'usd 5'       -> None          <-- 注意
'NaN'         -> None
'Infinity'    -> None
'$$5'         -> Decimal('5')
'1,,000'      -> Decimal('1000')
```

實作（`backend/cost/estimate_readers.py:88-109`）的清洗步驟是
`text.replace(",","").replace("$","").replace("USD","").replace("NT$","").strip()`。

**三個發現**：

1. **大小寫不對稱**：`"USD 5"` 會被清成 `"5"` → `Decimal('5')`，而 `"usd 5"` 清完仍是 `"usd 5"` → `None`。同一份估價表若幣別欄用小寫，整欄變成「未定價」。而 `normalize_header` 全程 `.lower()`，所以**同一個模組內兩種大小寫策略並存**。
2. **畸形千分位靜默接受**：`'1,2,3' -> 123`、`'1,,000' -> 1000`。一個打錯的千分位不會被拒絕，而是變成**另一個數字**。估價金額場景下這是靜默錯值，不是格式錯誤。
3. **負數與科學記號靜默接受**：`'$-5' -> -5`、`'1e5' -> 100000`。`parse_number` 沒有任何非負值域約束。

**為什麼這屬於 US13 的範圍邊緣而仍須指名**：這三項都不是本 intent 引入的，但 Q-03 已把 `estimate_readers.py` 的測試補寫納入本 intent。補測試的人若只寫 happy path，這三項會被測試**固化**為「預期行為」——那比沒有測試更糟（`project.md` 逐字：「錯誤的覆蓋感比沒有覆蓋更危險」）。

**嚴重性自評**：**Major**（既有缺陷，但會被本 intent 的補測試動作固化）

**建議落點**：**DoD**（與 Q-03 同一則故事）——「補寫 `estimate_readers.py` 測試時，`parse_number` 的三項已知行為（`USD`／`usd` 不對稱、畸形千分位靜默接受、負數與科學記號無值域約束）須在測試內**明文標記為待決**，不得直接寫成期望值。是否改行為屬獨立決定，不由補測試動作夾帶。」

---

## 第二部分：逐故事的可驗證層判定

brief 的第 1 問：每則新故事由哪一層驗。下表是我的判定，**「無」一欄是刻意的**。

| FR | 可驗證層 | 理由（實測依據） |
|---|---|---|
| FR11.1 建立專案／系統＋空狀態 | **Playwright e2e**（唯一） | 前端無 unit 框架（Q-01）。`projects`／`systems` 表已存在（`schema_rbac.sql:327`／`349`），但**空狀態是純前端呈現**，後端測不到 |
| FR11.2 按 agent 分組固定欄位＋「未填」文字 | **Playwright e2e**（唯一） | 「不得只靠顏色」是 DOM 文字斷言，只有 e2e 碰得到 |
| FR11.3 總覽籤計數與需求籤讀同一份狀態 | **Playwright e2e**（唯一）；見 Q-14 | 這是**跨元件狀態一致性**，前端 unit 測試才是它的自然落點，而該層不存在 |
| FR11.4 MCP server 獨立進程 | **目前無任何層**；見 Q-12 | repo 內零 MCP 基礎設施 |
| FR11.5 token 不得進工具 schema | **backend `unittest`**（結構斷言），但須先有 schema；見 Q-12 | 不需 `@given`，是對 schema 的靜態斷言 |
| FR11.6 授權入口不變 | **`TestClient`**（allow／deny 雙向） | `require_story_action` 是 FastAPI dependency，可用 `app.dependency_overrides` 覆寫 |
| FR12.1 建立者自動成為 owner | **`TestClient`** ＋ e2e | 需要 `project_members` 表；見 Q-06 |
| FR12.2 角色變更在詳情頁 | **Playwright e2e**（「不在清單就地編輯」是 UI 約束） | — |
| FR12.3 可多位 `project_admin` | **`TestClient`** | — |
| FR12.4 自動改選＋FR12.4a 恆定 | **`TestClient`** ＋（可選）`@given`；見 Q-05 | 「最早加入」需 `joined_at`；見 Q-06 |
| FR12.4b 稽核 | **目前無可斷言的持久層**；見 Q-11 | 既有 `_audit_append` 只寫 logger |
| FR12.4c／c-i 橫幅出現與清除 | **`TestClient`**（持久化端點）＋ e2e（呈現） | — |
| FR12.5／5a 唯一成員擋下 → 409 | **`TestClient`**，但**掛錯端點**；見 Q-10 | **最高價值發現** |
| FR12.6／6a 兩層串聯＋邀請前置 | **`TestClient`** allow／deny 雙向 | `team.md` A＋B 規則交叉要求 |
| FR13.1 per-key 狀態 | **backend `unittest`**（`IsolatedAsyncioTestCase`） | 見 Q-07 |
| FR13.2 兩請求事件互斥 | **可建構，我已實際建出**；見 Q-07 | brief 第 4 問的答案 |
| FR13.3 先結束者不得毀掉另一條通道 | **可建構**，但 FR13.3 的**描述與實際行為不符**；見 Q-08 | — |
| FR13.4 `thread_id` 落回預設 | **backend `unittest`**（靜態呼叫點斷言即足）；我已複驗 | 見 Q-09 |

---

## 第三部分：編號發現（續）

### Q-05 FR12.4a 宣稱的「恆定」**不是一個能失敗的性質**，因此不是真正的 PBT 標的；真正該測的是「排列不變」

**檢查內容**：brief 第 2 問。FR12.4a 逐字為「挑選結果對同一組成員資料**恆定**——同樣的成員集合與加入時間必然選出同一人。此性質使它適用 property-based 測試」。

**發現**：「同一輸入必然產生同一輸出」對任何**純函式**是定義上的真，**不可能失敗**。它正是 `project.md ## Corrections` 記過的恆真 AC 形狀（`user-stories:c4`：「查出恆真（不可能失敗）的驗收標準時改寫而非刪除」）。把它寫成 PBT 的理由不成立——`@given` 產生隨機輸入是為了探索**輸入空間**，而「同輸入同輸出」不需要任何輸入探索就恆真。

**真正會失敗、且正是「最早加入」這條規則的風險所在**：**排列不變性**。
`ORDER BY joined_at` 在時間戳**相同**時，PostgreSQL 不保證穩定順序；同一組成員以不同插入順序或不同實體順序餵進來，可能選出不同人。這條性質**會真的紅燈**，而它抓到的正是「缺少 tiebreak」這個缺陷。

**repo 內已有正確範例**：`backend/cost/estimate_readers.py:247-255` 的 `best_clouds` 用
`key=lambda item: (-item[1], item[0])` ——分數相同時以名稱升冪 tiebreak，使結果對輸入排列不變。我實測確認：

```
$ best_clouds({'aws':5,'gcp':5,'azure':1}) -> ['aws', 'gcp']   # 同分，順序由名稱決定
```

**我建議實際斷言的四條性質**（`@given` 產生成員清單，**刻意包含重複時間戳**）：

1. **排列不變**：`pick(shuffle(members)) == pick(members)` ← 這條會抓到缺 tiebreak
2. **值域封閉**：回傳者必屬輸入成員集合，且**非**被移除的那位 owner
3. **最小性**：被選者的 `joined_at` ≤ 集合內每一位的 `joined_at`
4. **全域性**：成員集合非空（扣掉離開者後）時必回恰好一位，不得回 `None`

**嚴重性自評**：**Major**（AC 寫成恆真，照它寫出的測試不會失敗；且它是 scope 記名的 PBT 候選，誤判會讓一條 hard-constraint 相關的測試變成裝飾）

**建議落點**：**AC**（改寫 FR12.4a 的對應 AC，不刪除——保住它的防禦意圖，改落點）：

> **AC12.4a**（改寫後）
> **Given** 某專案有兩位以上成員，且其中至少兩位的加入時間**完全相同**
> **When** `project_owner` 的帳號被移除而觸發自動改選
> **Then** 挑選結果與成員資料的**輸入順序無關**——以任意排列重算必得同一人；且被選者必為該專案現存成員之一、不得是被移除者、其加入時間不晚於任何其他成員

**配套 DoD**：「自動改選的挑選邏輯須以 `hypothesis` `@given` 斷言上述排列不變性，測試資料必須包含重複時間戳的案例。」

---

### Q-06 FR12.4 的「最早加入的成員」沒有可讀的欄位——`project_members` 表在 repo 內不存在

**檢查內容**：FR12.4 的挑選規則依賴「加入時間」。我查這個欄位在哪。

**指令與輸出**：

```
$ grep -rn "project_members" --include="*.py" --include="*.sql" . | grep -v __pycache__
（零命中）

$ grep -n "CREATE TABLE IF NOT EXISTS \(projects\|systems\)" schema_rbac.sql
327:CREATE TABLE IF NOT EXISTS projects (
349:CREATE TABLE IF NOT EXISTS systems (
```

`projects` 的實際欄位（`schema_rbac.sql:327-333`）：
`id` / `name` / `owner_user_id` / `is_default` / `created_at`。
**沒有成員表，沒有 `joined_at`，沒有 per-project 角色欄。**

**發現**：FR12 的四項行為（FR12.1 建立者自動成為 owner、FR12.2 指定角色、FR12.3 多位 admin、FR12.4 最早加入者接手）**全部**依賴一張不存在的 `project_members` 表，而 `requirements.md` 的 FR12 **沒有任何一條指名要建立它**。FR12.6 只說「既有 308 列全域矩陣不動；`project_admin` 不進 `CANONICAL_ROLES`」——那是在說**不要動什麼**，沒說要**建什麼**。

這正是 `project.md` 記過的那條教訓的同型重演：「契約端點三問必須對**本 intent 新建的資料模型與實體**也跑一次，而**寫入端**是三問中最容易漏的一問」。FR12 的成員表三問全缺：誰建（無）、誰讀（FR12.1–12.4 都讀）、誰清（成員離開時）。

**附帶的 blocking 後果**：新增 `project_members` 表會觸發 `project.md ## Mandated` 的同步規則——`schema_rbac.sql` 與 `DEPLOY.md` 必須在同一個 PR 更新，否則不得標示該 construction stage 完成。FR12 目前沒有任何一條提到這件事。

**嚴重性自評**：**Critical**（US12 的每一條 AC 的 Given 都不可構造——沒有成員表就無法建立「某專案有兩位成員」這個前置狀態）

**建議落點**：**AC**（US12 需要一條前置 AC）＋ **DoD**：

> **AC12.0**（新增）
> **Given** 一個剛建立的專案
> **When** 查詢它的成員清單
> **Then** 回應包含每位成員的使用者識別、per-project 角色、以及**加入時間**；加入時間對同一專案內的任兩位成員構成可比較的全序（含同時間時的 tiebreak 依據）

**DoD**：「`project_members`（含 `joined_at` 與 per-project 角色）的 DDL 須寫入 `schema_rbac.sql` 並同步更新 `DEPLOY.md` 的『這支 SQL 會建立的表／欄位』表——此為 `project.md ## Mandated` 的 blocking 規則，未完成不得標示 construction 完成。」

---

### Q-07 FR13.2 **在這個 harness 裡可以建構，我已實際建出並跑過**——不需要任何新 seam

**檢查內容**：brief 第 4 問——`unittest`、無 pytest、驅動 `run_design_agent` 需要 LLM，FR13.2 是否可構造。

**先確認前提**：

```
$ grep -rn "run_design_agent" backend/tests/
（零命中——現有 48 個測試檔沒有任何一個驅動過它）

$ grep -rln "IsolatedAsyncioTestCase\|asyncio.run" backend/tests/
backend/tests/test_diagram_builder.py
backend/tests/test_diagram_builder_edges.py
backend/tests/test_diagram_icons.py
backend/tests/test_langgraph_migration.py
backend/tests/test_a3_langgraph_migration.py
backend/tests/test_langgraph_runtime.py

$ python3 --version
Python 3.13.7
```

**答案：可構造，零新依賴、零新 seam。** 需要的縫全部是 `services.design_agent` 的**模組層名稱**，`unittest.mock.patch.object` 直接可覆寫：

| 需要覆寫的名稱 | 位置 | 為什麼需要 |
|---|---|---|
| `llm_auth_ready` | `design_agent.py:179` | 不覆寫則第 180 行直接 `yield error` 後 return |
| `build_graph` | `design_agent.py:109`，於 `:189` 被呼叫 | 它內部才建 `ChatAnthropic`（`:121`）——**LLM 在這個函式裡面**，覆寫它即切斷 LLM |
| `build_system_prompt` / `format_user_prompt` | `:186` / `:187` | 避免讀 `prompts/*.md` 檔 |

假圖只需提供 `.compile(checkpointer=…)` → 回傳具 `.astream(state, config=, stream_mode=)` 的 async iterator。
**關鍵**：假節點必須在 put 事件時**重讀模組全域** `da._progress_queue`，因為真正的工具就是這樣做的（`design_agent.py:81`、`:84`、`:96`、`:101` 每一處都重讀全域）。

**我實跑的結果**（`IsolatedAsyncioTestCase` 等價的 `asyncio.gather` 兩請求）：

```
$ JWT_SECRET=probe python3 scratchpad/fr13_probe2.py
Design Agent 執行失敗
Traceback (most recent call last):
  File "…/backend/services/design_agent.py", line 203, in run_design_agent
    async for q_event in _drain_progress(_progress_queue):
  File "…/backend/services/design_agent.py", line 163, in _drain_progress
    event = queue.get_nowait()
AttributeError: 'NoneType' object has no attribute 'get_nowait'
A -> [('xml', '<xml-from-A/>')]
B -> [('error', "發生未預期錯誤：'NoneType' object has no attribute 'get_nowait'")]
A payload set: {'<xml-from-A/>'}
B payload set: {} (EMPTY)
FR13.2 disjoint AND both non-empty ? False
```

**兩項重要的操作性結論**：

1. **不加顯式 barrier 的版本會是綠的（＝假綠）**。我第一版只用 `asyncio.sleep(0.001)` 錯開兩個請求，結果**通過**（A、B 各收到自己的事件、互斥且非空）。必須用 `asyncio.Event` 把交錯**釘死**成「A 進入 → B 覆寫全域 → A 的工具 put → A 收尾」才重現得出來。
   **這直接影響 AC 的可驗證性**：FR13.2 的 AC 若只寫「兩個併發請求」而不要求釘死交錯順序，寫出來的測試會**時好時壞**，而 `ui-regression` 容忍 `stats.flaky`、`playwright.config.ts:17` 也設 `retries: 1`——一個 flaky 的併發測試在 CI 上會被重試掩蓋。
2. 這個測試落在 `backend/tests/`，會被現有 `python -m unittest discover -s tests` 自動撿到；無需改 CI。

**嚴重性自評**：**Major**（這是對 brief 第 4 問的正面回答——不需要新 seam；但「必須釘死交錯順序」這個條件若不寫進 AC／DoD，交付出來的會是一個假綠測試）

**建議落點**：**AC**（FR13.2 的 AC 須含交錯條件）＋ **DoD**：

> **AC13.2**（建議措辭）
> **Given** 兩個對 Design Agent 的請求重疊執行，且第二個請求在第一個請求的事件**尚未取走之前**開始
> **When** 兩個請求各自讀取自己的事件串流
> **Then** 兩個請求收到的 progress／xml 事件集合**互斥**，且**各自非空**

**DoD**：「FR13.2 的測試須以 `asyncio.Event` 顯式釘死交錯順序，不得依賴 `sleep` 錯開——後者實測會通過（假綠）。落點 `backend/tests/`，`unittest.IsolatedAsyncioTestCase`，覆寫 `services.design_agent` 的 `llm_auth_ready`／`build_graph`／`build_system_quote`／`format_user_prompt` 四個模組層名稱。」

---

### Q-08 FR13.3 把失敗模式寫成「**靜默**丟棄」，但實測是一個 `AttributeError` 崩潰——照字面寫的 AC 會**恆真通過**

**檢查內容**：FR13.3 逐字為「現狀 `design_agent.py:218` 把全域設為 `None`，使另一請求其後的 progress／xml／error 事件被**靜默丟棄**；修正後此行為不得存在」。我用 Q-07 的探針實測這條路徑。

**實測結果**（同上輸出）：先結束的請求執行 `finally: _progress_queue = None`（`:218`）後，另一個進行中的請求在 `:203` 以 `None` 呼叫 `_drain_progress`，於 `:163` 觸發
`AttributeError: 'NoneType' object has no attribute 'get_nowait'`。
該例外被 `:213` 的寬 `except Exception` 捕獲，轉成**使用者可見**的事件：

```
B -> [('error', "發生未預期錯誤：'NoneType' object has no attribute 'get_nowait'")]
```

**發現**：實際行為**不是靜默丟棄**，是**另一個請求的產生器被例外中斷**，並對使用者吐出一則內部錯誤訊息。兩者的差別不是用詞精粗，而是**可驗證性**：

- 一條按 FR13.3 字面寫出的 AC（「事件不得被靜默丟棄」）**現在就通不過也抓不到真問題**——因為現狀的失敗**本來就不是靜默的**。測試若斷言「沒有事件被靜默遺失」，在修正前後**都會通過**（修正前 B 收到的是一則 error 事件，不是「靜默無事」）。
- 這正是 brief 第 5 問要的那一類：**AC 通過而它要保護的東西是壞的**。

另外，FR13.2 的「已實測：A 收到 B 產生的架構圖 XML、B 收到空」與我的量測**方向不同**：我的交錯順序下 A 收到自己的 XML、B 收到一則 error（不是「空」）。兩種結果都可達，取決於交錯時點——**這本身就是重點**：失敗是非決定性的，所以描述必須指明交錯條件（見 Q-07）。

**嚴重性自評**：**Major**（AC 的失敗模式描述錯誤，照它寫的測試恆真）

**建議落點**：**AC**（改寫，保留防禦意圖、改落點到真會失敗的面）：

> **AC13.3**（建議措辭）
> **Given** 兩個對 Design Agent 的請求重疊執行
> **When** 其中一個請求**先行結束並完成清理**
> **Then** 另一個仍在進行的請求**不得因此收到任何 `type: "error"` 事件，也不得中斷其事件串流**——它其後產生的 progress／xml 事件須照常送達

**附帶 AC（可選，獨立的防禦面）**：「任何內部例外訊息不得逐字出現在送往使用者的事件內容中」——現狀 `:214` 的 `f"發生未預期錯誤：{e}"` 把 `AttributeError` 的原文送給了使用者，這同時是 ADR-0006 的資訊暴露面。

---

### Q-09 FR13.1 只點名 `_progress_queue`，而 `design_agent.py` 有**三個**模組層可變狀態；另外 FR13.4 我已複驗為真

**檢查內容**：FR13.1 要求把 `_progress_queue` 改為 per-key。我列出該模組所有模組層可變名稱。

**指令與輸出**：

```
$ grep -nE "^[_a-zA-Z][_a-zA-Z0-9]*(:| =)" backend/services/design_agent.py
27:logger = logging.getLogger(__name__)
29:PROMPT_PATH = …
31:_progress_queue: asyncio.Queue[dict[str, str]] | None = None     <-- FR13.1 點名
32:_last_xml: str | None = None                                      <-- 未點名
169:memory = MemorySaver()                                            <-- 未點名

$ grep -n "_last_xml" backend/services/design_agent.py
32:_last_xml: str | None = None
78:    global _last_xml
95:        _last_xml = xml_data
176:    global _progress_queue, _last_xml
184:    _last_xml = None

$ grep -rn "_last_xml" backend/ --include="*.py" | grep -v __pycache__
（只有上列五處，全在 design_agent.py 內）
```

**兩項發現，嚴重性不同，我分開報**：

1. **`_last_xml`（`:32`）形狀與 `_progress_queue` 完全相同**——`:95` 由工具寫入、`:184` 由每個新請求重設。兩個併發請求下，A 寫入的值會被 B 的進入清成 `None`。
   **但我必須誠實說明它目前無害**：全 repo `grep` 顯示 `_last_xml` **沒有任何讀取點**（只有宣告、`global` 宣告、一次寫入、一次重設）。它是**write-only 的死狀態**。
   所以它不是現行缺陷，而是**陷阱**：FR13.1 只修 `_progress_queue`，`_last_xml` 留在原地；下一個為它加上讀取端的人會原封不動地繼承同一個競態，而那時 FR13 已經「完成」。
   **建議處置：FR13.1 應明文說它要被刪除**（既然無人讀），而非默默留著。

2. **`memory = MemorySaver()`（`:169`）是全模組共用的 LangGraph checkpointer**，與 FR13.4 直接相關。

**FR13.4 我已獨立複驗**（FR13.4 自述「本輪未獨立複驗」，現在複驗完成）：

```
$ sed -n '74,84p' backend/services/wa_collab_orchestrator.py
    last_xml: Optional[str] = None
    async for event in run_design_agent(messages, current_xml):

$ sed -n '171,175p' backend/services/design_agent.py
async def run_design_agent(
    messages: list[dict[str, str]],
    current_xml: str | None = None,
    thread_id: str = "default-thread",
) -> AsyncIterator[dict[str, str]]:
```

**確認 FR13.4 的事實為真**：呼叫只傳兩個位置引數，`thread_id` 落回 `"default-thread"`；配合 `:169` 的共用 `memory`，所有 A4 共編路徑共用同一個 checkpointer thread。FR13.4 可由「待查」升為**已查證**。

**嚴重性自評**：`_last_xml` **Minor**（死狀態，非現行缺陷，但是陷阱）；`thread_id`／`memory` **Major**（已複驗為真的跨使用者狀態共用）

**建議落點**：
- **DoD**（US13）——「FR13.1 的範圍須明文涵蓋 `design_agent.py` 的**全部三個**模組層可變狀態並逐一給出處置：`_progress_queue` 改 per-key、`_last_xml` **刪除**（全 repo 無讀取端，已 grep 確認）、`memory` 的 thread 隔離依 FR13.4 處理。只改一個而留兩個，等於把同一個競態留給下一個人。」
- **AC**（FR13.4 升格）——「**Given** 兩位使用者各自在 A4 共編中驅動 Design Agent，**When** 兩者的請求先後送出，**Then** 兩者的對話歷程不得互相出現在對方的後續回應中」（這條碰得到真實失敗面，而「不得傳預設 `thread_id`」是實作細節，屬 DoD）。

---

### Q-10 FR12.5a 把檢查掛在**停用**端點，而 FR12.5c 用來佐證它的資料庫約束**只在刪除時才生效**——AC 會通過而真正的破壞路徑仍是 500

**這是我這輪最高價值的發現**（brief 第 5 問要的那一類）。

**檢查內容**：FR12.5a 逐字「檢查掛在**既有的停用使用者端點**上……命中則回 **409**」；FR12.5c 逐字「`schema_rbac.sql:330` 的 `owner_user_id` 為 `NOT NULL` 且無 `ON DELETE` 子句——**資料庫今天就會擋下該刪除**。FR12.5a **不需放寬任何 schema 約束**」。我查這兩句指的是不是同一個操作。

**指令與輸出**：

```
$ grep -nE "@router\.(get|post|put|patch|delete)" backend/services/user_router.py | sed -n '11,12p'
635:@router.put("/{user_id}/active", response_model=UserSchema)      <-- 停用（deactivate）
679:@router.delete("/{user_id}")                                      <-- 刪除（delete）
```

`PUT /{user_id}/active`（`:635-675`）的全部副作用是 `target_user.is_active = request.is_active` ＋ `db.commit()`。**沒有任何列被刪除。**

`DELETE /{user_id}`（`:679`）第一道門是：

```
:690    if target_user.is_active:
:691        raise HTTPException(400, detail="請先停用帳號後再刪除")
```

即**必須先停用、才能刪除**，兩個操作是前後兩步。

`schema_rbac.sql:330` 的實際內容與 COMMENT：

```
327:CREATE TABLE IF NOT EXISTS projects (
328:  id SERIAL PRIMARY KEY,
329:  name VARCHAR(255) NOT NULL,
330:  owner_user_id INTEGER NOT NULL REFERENCES users (id),
…
COMMENT ON COLUMN projects.owner_user_id IS
  'U4: who owns this project. Deletion behaviour of the referenced user is
   deliberately NOT decided (OQ-H1, landing U7) — no ON DELETE clause, …';
```

**發現（三段）**：

1. **FR12.5c 佐證的是錯誤的操作。** `REFERENCES users (id)` 無 `ON DELETE` 子句 → PostgreSQL 預設 `NO ACTION` → 外鍵**只在 `DELETE FROM users` 時才檢查**。`PUT /{user_id}/active` 不刪任何列，**外鍵永遠不會觸發**。所以 FR12.5a 的落點（停用端點）在資料庫層**完全沒有任何後備保護**，而 FR12.5c 讀起來像是說有。

2. **真正的破壞路徑（DELETE）在 FR12.5a 之後仍然沒有 409。** `_hard_delete_user`（`user_router.py:291-307`）的內容我實讀：它刪 `UserDiagramChat`、`diagram_shares`、`RoleAuthorizationRequest`，對擁有架構圖者回 403（`:299-302`），然後 `db.delete(user)`。**它完全不碰 `projects`**。而 `user_router.py` 全檔只有 3 個 `except`，`_hard_delete_user` 與 `delete_user` 都沒有 try/except。
   所以：一位**擁有專案但不擁有架構圖**的使用者被刪除時 → 通過 403 那道門 → `db.delete(user)` → `projects.owner_user_id` 外鍵違反 → **未捕獲的 `IntegrityError` → HTTP 500**，不是 FR12.5a 要的「409 ＋ 專案清單」。

3. **這個情境在 FR11 落地後才變得可達，而正是本 intent 讓它可達。** 現狀的專案只由遷移建立，而遷移**只為持有架構圖的使用者**建專案：

```
$ sed -n '361,363p' backend/services/hierarchy_migration.py
def _users_holding_diagrams(db: Session) -> list[tuple[int, str]]:
    """`BR2.5`：持有至少一張架構圖的使用者。不持有圖者**不**建立預設專案。
```

  所以今天「有專案、無架構圖」不可達——`:299` 的 403 總是先擋下。**FR11.1 讓使用者能手動建立專案**，於是「有專案、無架構圖」立刻成為可達狀態，而那條路徑的終點是 500。

**為什麼這是「AC 通過而東西是壞的」**：一條照 FR12.5a 寫的 `TestClient` 測試——停用唯一成員的 owner、斷言 409 ＋ 專案清單——**會通過**。而使用者真正用來移除帳號的兩步流程（先停用、再刪除）在第二步會拿到 500 ＋ 資料庫錯誤。測試綠燈，功能壞的。

**嚴重性自評**：**Critical**

**建議落點**：**AC**（US12 需要兩條，不是一條）：

> **AC12.5-1**（停用面，對應 FR12.5a）
> **Given** 某使用者是一個或多個專案的唯一成員
> **When** 管理員對他發出停用請求
> **Then** 停用被拒絕並回 409，回應中列出那些只有他一人的專案

> **AC12.5-2**（刪除面，**本輪新增，FR12.5 未涵蓋**）
> **Given** 某使用者已停用，且仍是某個專案的擁有者（即使他不擁有任何架構圖）
> **When** 管理員對他發出刪除請求
> **Then** 回應為帶說明的 4xx 並列出該專案；**不得**為 500，也不得出現資料庫錯誤原文

**DoD**：「AC12.5-2 的測試須構造『有專案、無架構圖』的使用者——這是 FR11.1 新開的可達狀態，`_hard_delete_user`（`user_router.py:291`）目前對 `projects` 零處理且全函式無 try/except。兩條 AC 各需 allow／deny 雙向 `TestClient`（`team.md` A＋B 規則），並同步重 dump `openapi.json`（CI OpenAPI 漂移閘門）。」

**附帶請 lead 注意**：FR12.5c 的句子「資料庫今天就會擋下該刪除」字面為真但誤導——它擋的方式是未捕獲的 500。建議在 FR12.5c 就地註明，並把「FR12.5a 不需放寬任何 schema 約束」保留（這句是對的）。

---

### Q-11 FR12.4b 要求的稽核，在這個 repo 裡**沒有任何持久層可寫**；而 FR12.4d 承諾它在成員詳情頁看得到——logger 做不到這件事

**檢查內容**：FR12.4b 要求「自動改選須留稽核：誰、何時、對誰、舊角色、新角色」。FR12.4d 說「紀錄存在於 FR12.4b 的稽核與**成員詳情頁的變更紀錄**，但需主動查看」。我查既有稽核機制是什麼。

**指令與輸出**：

```
$ grep -rn "def _audit_append" -A 16 backend/services/user_router.py
213:def _audit_append(title, request_raw, outcome, approver) -> None:
214:    """記錄一筆權限稽核事件到應用程式日誌。
216:    原本寫入某台開發機的絕對路徑（AI-DLC v1 的 `aidlc-docs/audit.md`），被
217:    `os.path.exists` 擋著，實際上在任何環境都不會執行。…此處改走標準 logger，
219:    由既有的日誌收集管線承接。
220:    """
221:    logger.info(
222:        "【權限稽核】%s | 請求: %s | 結果: %s | 核准者: %s", …)

$ grep -niE "CREATE TABLE IF NOT EXISTS.*(audit|change_record|history)" schema_rbac.sql
217:CREATE TABLE IF NOT EXISTS archive_cost_audit_event (
292:CREATE TABLE IF NOT EXISTS estimate_audit_events (
393:CREATE TABLE IF NOT EXISTS diagram_change_records (
```

**發現**：

1. 使用者／權限領域唯一的稽核機制 `_audit_append` 寫的是 **`logger.info`**，不是資料表。它**不可查詢、不可在 UI 呈現、不可被測試斷言內容**（只能用 `assertLogs` 斷言有一行日誌，那驗的是「有沒有記」而不是「記了什麼能不能被讀」）。
2. 存在的三張稽核表沒有一張可用：`archive_cost_audit_event`（`:217`，依本 intent 先前查證，`archive_*` 屬 **RETIRED** 區塊）、`estimate_audit_events`（`:292`，估價領域）、`diagram_change_records`（`:393`，架構圖領域）。**成員角色變更沒有表。**
3. **FR12.4b 與 FR12.4d 合起來自相矛盾**：FR12.4b 可以用 logger 滿足（「留稽核」），但 FR12.4d 承諾同一份紀錄**在成員詳情頁看得到**——UI 不可能讀 logger。兩條並存時，FR12.4b 實際上隱含要求一張**新表**，而它沒有任何一條文字說要建。

這是契約端點三問的「**誰讀**」缺席：FR12.4b 指名了寫入端（系統自動改選時），FR12.4d 指名了讀取端（成員詳情頁），但中間的載體不存在。

**嚴重性自評**：**Critical**（FR12.4d 是已核可決定的呈現承諾，而它目前無法被實作；且 `_audit_append` 的存在會讓實作者誤以為「沿用既有機制」即可——那會讓 FR12.4d 靜默落空）

**建議落點**：**AC**：

> **AC12.4b**（建議措辭）
> **Given** 某專案的 `project_owner` 帳號被移除而觸發自動改選
> **When** 任何具權限者開啟該專案的成員詳情頁
> **Then** 頁面顯示一筆變更紀錄，含**時間、被變更的成員、變更前角色、變更後角色、以及「由系統自動改選」這個發起來源**；該紀錄在重新登入與換裝置後仍然存在

**DoD**：「成員角色變更紀錄須有持久化載體（新表或既有表的延伸），其 DDL 同步進 `schema_rbac.sql` 與 `DEPLOY.md`（`project.md` blocking 規則）。**不得以 `user_router.py:213` 的 `_audit_append` 滿足本項**——它只寫 `logger.info`，UI 無法讀取，FR12.4d 的承諾會落空。」

---

### Q-12 FR11.4／FR11.5 的受測對象**完全不存在**——repo 內零 MCP 基礎設施，FR11.5 的斷言現在無處可掛

**檢查內容**：FR11.4 指定「MCP server，跑在獨立進程」；FR11.5 要求「對 MCP server 宣告的每一個工具 schema 做斷言」。我查 MCP 在 repo 的現況。

**指令與輸出**：

```
$ grep -rniE "^mcp|modelcontextprotocol|fastmcp" backend/requirements.txt
（零命中）

$ grep -rln "mcp" backend/services/ backend/cost/
（零命中）
```

**發現**：後端無任何 MCP 套件、無任何 MCP 模組。FR11.5 是本輪三則故事裡**唯一的安全不變量**，而它的受測對象要到實作階段才存在。這不是缺陷，但有兩個可執行後果必須被指名：

1. **FR11.5 的斷言形狀取決於 schema 怎麼產生**，而那還沒決定。若工具 schema 由 Python 型別標註自動產生（`fastmcp` 等的常見做法），斷言可以是對產生出的 schema dict 做結構掃描；若是手寫 JSON，斷言對象是那份檔案。**兩者的測試寫法不同**，而 FR11.4 只說「獨立進程」，沒說 schema 來源。
2. FR11.5 寫成「properties 不含任何名稱匹配 `token`／`key`／`secret`／`authorization`（不分大小寫）」——這是**黑名單**斷言。黑名單會漏：`bearer`、`cred`、`auth`、`jwt`、`session`、`cookie` 都不在清單內。一個叫 `bearer` 的參數會**通過**這條斷言。

**嚴重性自評**：**Major**（FR11.5 是安全不變量，而它的斷言有可繞過的缺口；FR11.4 的 schema 來源未定使測試落點懸空）

**建議落點**：**AC**（FR11.5 改為白名單，使它不可繞過）：

> **AC11.5**（建議措辭）
> **Given** MCP server 宣告的任一個工具
> **When** 檢視該工具的 JSON schema
> **Then** 其 `properties` **只包含該工具業務所需的、明文列舉過的參數名**；任何未在該列舉清單內的欄位即為不合格（白名單），且 schema 內不得出現任何憑證類欄位

**DoD**：「FR11.5 的斷言須對 MCP server **實際宣告出的** schema 執行（非對原始碼字串 grep），落點 `backend/tests/`；工具參數的白名單須與工具定義放在同一處，使新增參數必須同時更新白名單。FR11.4 須補明工具 schema 的產生方式（型別標註自動產生 vs 手寫），否則本測試的對象不確定。」

---

### Q-13 `project.md` 把 **agent routing** 列為 PBT hard constraint 的落點，而 `requirements.md` 全檔對 routing 沒有任何 PBT 判定

**檢查內容**：`project.md ## Testing Posture` 的 hard constraint 清單，對照 `requirements.md` 的 PBT 判定表。

**指令與輸出**：

```
$ sed -n '/^## Testing Posture/,/^## Deployment/p' aidlc/spaces/default/memory/project.md
**Property-based testing 為 hard constraint**（ADR-0006）。下列核心模組的測試必須包含
property-based 測試，不得只有 example-based：IaC generator、cost calculator、**agent routing**。

$ grep -niE "property-based|PBT|hypothesis|@given" …/requirements-analysis/requirements.md
288: …FR12.4a…適用 property-based 測試…
577: **PBT（ADR-0006 的第二條 hard constraint）逐項判定**：
581: | FR12.4 自動改選的挑選規則 | 適用… |
582: | FR11.5 token 不得進工具參數 | 不適用 PBT… |
583: | FR13.2 併發事件互斥 | 不適用 PBT… |
584: | 既有缺口 | estimate_readers.py… |
724: | M1-5 | estimate_readers.py 的 PBT 缺口 | … |
```

**發現**：`:577` 的判定表標題是「**新增 FR**」，所以它只判了 FR11／FR12／FR13——這在範圍上說得通。但把全檔一起看：**`requirements.md` 對「agent routing」這個 hard-constraint 落點，沒有任何一處 PBT 判定**。而本 intent 的能力 1（意圖識別）與能力 10（路由到既有端點）**就是** agent routing——`project.md` 逐字點名的三個落點之一，在這個 intent 裡由 N/A 轉為實際存在。

這與 `project.md` 已記過兩次的教訓同型：「hard constraint 在某一站沒有落點，而該站的自檢清單裡沒有『逐一對照本專案的 hard constraint』這一項」，以及「我把一條規則寫進 `## Mandated`，然後在下一站立刻違反同一條」。

**我誠實標明範圍**：這不是 US11–13 的義務（routing 屬 US1／US10，上一輪已寫）。但判定表是**修訂 1 新增的**，lead 正在同一輪動它，此刻補最便宜；拖到 construction 才發現，`@given` 要補在一個已經寫完的路由模組上。

**嚴重性自評**：**Major**（hard constraint 無落點記載；非 US11–13 本身的缺陷）

**建議落點**：**DoD**（掛 US1 或 US10，由 lead 定；或在 `requirements.md` 的 PBT 判定表加一列並註明它涵蓋既有 FR）——「意圖識別／路由的純函式核心須含 `@given` 斷言，不得只有 example-based；此為 `project.md ## Testing Posture` 逐字點名的 `agent routing` 落點。建議性質：路由決策對候選集合的**排列不變**、信心值落在宣告值域內、輸入為空時有定義的回退。」

---

### Q-14 FR11.3 的「讀同一份狀態」只有 e2e 碰得到，而 e2e 驗不出「同一份」——它驗的是「兩個數字剛好相等」

**檢查內容**：FR11.3 要求「總覽籤的『未填需求欄位』計數，與需求籤的實際未填數**讀同一份狀態**；在需求籤儲存後，總覽籤的計數須同步變化」。我判斷哪一層能驗它。

**依據**（已於 Q-01 量測）：前端無 unit／component 測試框架；唯一能碰前端的自動化層是 Playwright e2e（`frontend/tests/e2e/` 兩個 spec，共 583 行）。

**發現**：「讀同一份狀態」是**實作結構**的斷言（單一狀態來源），e2e 只能觀察**呈現**。e2e 能寫的最強斷言是「改需求籤 → 切到總覽籤 → 數字變了」。這條斷言在以下實作下**會通過，而需求的意圖是壞的**：總覽籤各自重抓一次 API。兩個數字會相等、會同步變化，但它們是**兩份**狀態——只要兩次抓取之間有第三者修改、或其中一次失敗，兩個數字就會分歧，而 e2e 的 happy path 永遠看不到。

這正是 `project.md` 記過的那條：「查出恆真（不可能失敗）的驗收標準時改寫而非刪除：防禦意圖通常是真的，錯的是落點層次」。FR11.3 的意圖（避免兩份計數漂移）是對的，落點（讀同一份狀態）在可用的驗證層上不可觀察。

**嚴重性自評**：**Major**（AC 的意圖無法由任何現有層驗證；照字面寫的 e2e 會給出假保證）

**建議落點**：**AC**（改寫到可觀察的面——讓**分歧**本身成為可觸發的情境）：

> **AC11.3**（建議措辭）
> **Given** 詳情頁已開啟，總覽籤顯示未填需求欄位數為 N
> **When** 在需求籤填入一個先前未填的欄位並儲存，**且不重新載入頁面**
> **Then** 總覽籤顯示的數字變為 N−1；**且在此期間未對後端發出第二次需求欄位查詢**

最後那個子句把「同一份狀態」轉成**可觀察**的事實——Playwright 的 `page.route`／`waitForRequest` 可以數請求次數。沒有它，這條 AC 無法分辨單一狀態來源與兩次抓取。

**DoD**：「AC11.3 的 e2e 須以 Playwright 的請求攔截斷言儲存後的請求次數，不得只斷言兩個數字相等。」

---

### Q-15 `requirements.md` 的「308 列全域矩陣」是**對的**，`project.md` 某條學習條目的「330 列」是錯的——請勿把對的改成錯的

**檢查內容**：FR12.6 寫「既有 308 列全域矩陣不動」，而 `project.md ## Mandated` 有一條學習條目寫「11 個角色與 330 列矩陣都已被下游引用」。兩個數字不一致，我實算。

**指令與輸出**：

```
$ cd backend && python3 -c "
from services.rbac import CANONICAL_ROLES, STORY_IDS, DEFAULT_ROLE_PERMISSIONS
print('CANONICAL_ROLES:', len(CANONICAL_ROLES))
print('STORY_IDS:', len(STORY_IDS))
print('DEFAULT_ROLE_PERMISSIONS rows:', len(DEFAULT_ROLE_PERMISSIONS))
print('roles x stories =', len(CANONICAL_ROLES)*len(STORY_IDS))"
CANONICAL_ROLES: 11
STORY_IDS: 28
DEFAULT_ROLE_PERMISSIONS rows: 308
roles x stories = 308
```

**判定**：**308 = 11 × 28，`requirements.md` 正確。** `project.md` 那條學習條目的 330 是錯的（28 vs 30 個 story id 的差）。
同時確認 FR12.6 的另一句也對：`Project_Admin`（底線、首字大寫）**確實在** `CANONICAL_ROLES` 內，所以 FR12.6 說「`project_admin` 不進 `CANONICAL_ROLES`」是必要的——否則就是 `project.md` 警告過的同名不同義碰撞。

**嚴重性自評**：**Minor**（`requirements.md` 無誤；報告它是為了**防止 lead 依記憶層去「修正」一個正確的數字**。規則層 append-only，本輪不改 `project.md`）

**建議落點**：無需 AC／DoD。請 lead 在整合時把 308 原樣保留。

---

### Q-16 `backend/test_agent.py` 在 `tests/` 之外，`unittest discover` 永遠不會執行它

**指令與輸出**：

```
$ ls backend/
__pycache__  cost  database.py  Dockerfile  env_bootstrap.py  lenses  main.py
models.py  prompts  requirements.txt  scripts  services  test_agent.py  tests
                                                          ^^^^^^^^^^^^^
```

CI 的指令是 `python -m unittest discover -s tests -v`（`ci.yml`「Run unit tests」步驟），起點為 `backend/tests`。`backend/test_agent.py` 在其上一層，**不會被收集**。

**嚴重性自評**：**Minor**（與 US11–13 無直接關係；一個名字看起來像測試、實際從未執行的檔案，會讓人誤判既有覆蓋）

**建議落點**：無需 AC。建議 lead 不要把它計入既有測試基礎（Q-01 的 46 個 `test_*.py` 計數已排除它，因為它不在 `tests/` 下）。

---

## 第四部分：突變清單（brief 第 6 問）

對每則新故事的關鍵 AC，我會改壞什麼來證明測試真的會紅。**指不出突變的 AC 我也標出來了。**

| AC | 突變（改壞什麼） | 預期紅燈訊號 |
|---|---|---|
| AC11.1 空狀態 | 把空狀態分支改成直接渲染空的 `<table>` | e2e 找不到說明文字與建立按鈕 |
| AC11.2 「未填」文字 | 把「未填」文字移除、只留底色 class | e2e 的文字斷言失敗 |
| AC11.3（改寫後） | 讓總覽籤在切籤時重抓一次 API | 請求次數斷言由 0 變 1 → 紅 |
| AC11.5（改寫為白名單後） | 在任一工具 schema 加一個名為 `bearer` 的參數 | 白名單斷言紅燈（**原黑名單版本會綠**——這就是 Q-12 的理由） |
| AC11.6 授權入口 | 移除該端點的 `require_story_action` dependency | deny 案例由 403 變 2xx → 紅 |
| AC12.0 成員清單含 `joined_at` | 從回應模型移除 `joined_at` | 欄位集合斷言紅燈 |
| AC12.1 建立者自動成為 owner | 建立專案時不寫成員列 | 成員清單長度 1 → 0 → 紅 |
| AC12.4a（改寫為排列不變後） | 把挑選改成 `ORDER BY joined_at`（去掉 tiebreak） | `@given` 在重複時間戳的案例上紅燈（**原「恆定」版本會綠**） |
| AC12.4b 稽核可讀 | 把寫入改回 `_audit_append`（logger） | 成員詳情頁讀不到紀錄 → 紅（**若 AC 只寫「留稽核」則會綠**） |
| AC12.5-1 停用擋下 | 移除停用端點的唯一成員檢查 | 409 變 200 → 紅 |
| AC12.5-2 刪除面 | **不需突變——現狀就是紅的**（500），這條 AC 一寫出來就是失敗的，修完才轉綠 | 這是它價值最高的地方 |
| AC13.2 事件互斥 | **不需突變——現狀就是紅的**，我已實跑確認（Q-07） | `FR13.2 disjoint AND both non-empty ? False` |
| AC13.3（改寫後） | **不需突變——現狀紅的**（B 收到 error 事件）。注意**原措辭版本現狀是綠的**（因為失敗不是靜默的）——Q-08 的全部理由 | — |
| AC13.4 thread 隔離 | 把 `thread_id` 傳遞改回不傳 | 兩使用者對話互相汙染 → 紅 |
| **FR12.2「不在清單就地編輯」** | **我指不出能讓它變紅的突變**。「角色變更在詳情頁進行」是**沒有某個東西**（清單頁沒有下拉）。e2e 可斷言「清單頁無角色下拉」，但那在清單頁改版後會以無關理由紅燈，而真正該防的（有人**加回**就地編輯）要靠同一條斷言——它是弱斷言但不是恆真，**可接受**，我把它標為最弱的一條 | — |
| **FR12.3「可同時有多位 admin」** | 突變＝加一條「至多一位」的限制。但若實作從未加過這種限制，這條 AC 驗的是「沒有某個不存在的限制」——**接近恆真**。建議改寫為可觸發的形式：「指定第二位 admin 後，**兩位都能執行** admin 動作」，突變＝讓第二位的指定靜默覆寫第一位 | — |

---

## 第五部分：我**沒有**檢查的範圍（請勿把沉默讀成已覆蓋）

1. **未執行完整後端測試套件**。我沒跑 `python -m unittest discover -s tests -v`，所以不知道 46 個測試檔現在是否全綠。Q-01 的計數是靜態的（`ls`／`grep`），不是執行結果。
2. **未執行 Playwright e2e**。`ui-regression` 需要 `docker-compose.test.yml` 的短生命週期 stack，我沒起。e2e 可驗性的判斷來自讀 `regression.spec.ts`（490 行，含 `login()`／`registerUser()` 兩個可重用 helper，以及既有的 `@api`／`@ui` 規格註解）與 `playwright.config.ts`，**不是來自實跑**。
3. **未驗證 `ui-regression` 在本 PR 上的實際行為**。我只讀了 `.github/workflows/ui-regression.md:277-289` 確認 `stats.unexpected != 0 → exit 1`、`stats.flaky` 被容忍。沒有觸發過一次 run。
4. **未檢查 US1–US10 的既有 20 則故事**。我只看了 US9 的格式，沒有逐條複驗既有 AC。所以我**不能**保證 US11–13 的新 AC 與既有 AC 無重複或無矛盾——那需要逐條對照，我沒做。
5. **未檢查 `brain_router.py`（455 行）與 `brain_ws_contract.py` 的內容**。我只數了它的端點（唯一一個 `@router.websocket("/ws")`，`:238`）與 `ws-contract.json` 的 schema 名稱。**本 intent 可能已有相當部分落地**，而我沒評估這對 US11／US12 的「新建 vs 修改」判定有什麼影響——這是我這份貢獻最大的未檢查缺口，建議 lead 指派給 developer agent 或自行確認。
6. **未檢查 `test_hierarchy_migration.py`（41581 bytes、15 個 `@given`）的內容**。它是全 repo `@given` 最密集的檔案，可能已覆蓋 FR11 的部分專案／系統不變量。我**沒有**確認 FR11.1 是否已被它部分覆蓋。
7. **未驗證 `_hard_delete_user` 的 500 路徑為實際執行結果**。Q-10 第 2 段的「未捕獲 `IntegrityError` → 500」是從實讀程式（`:291-307` 無 try/except、不碰 `projects`；`:299` 的 403 只看架構圖）**推導**的，不是跑出來的——它需要真實 PostgreSQL（SQLite 的外鍵預設不強制，`tests/helpers.py` 走 in-memory SQLite，所以用現有測試基座**驗不出來**）。這一點本身也是一個發現：**FR12.5 的刪除面在現有測試基座上無法被驗證**，因為它依賴 PostgreSQL 的外鍵行為，而測試用的 SQLite 預設不強制外鍵。建議 lead 把這一句加進 AC12.5-2 的 DoD。
8. **未檢查 `validate_cost_calculator_boundary.py` 與 `validate_pricing_lookup_boundary.py` 的內容**。我只在 `ci.yml` 看到這兩個步驟存在，沒讀它們，所以不知道 Q-03 的 `estimate_readers.py` 是否已被其中之一納入邊界檢查。
9. **未檢查 FR12.6 兩層串聯的既有授權測試是否可擴充**。`test_rbac.py`／`test_j5_authz.py`／`test_review_authz.py` 我沒開——`team.md` 說它們都在 service 層而非 HTTP 層，我**沒有複驗這一點**。
10. **未對 `estimate_readers.py` 的 `column_map`（`:266-354`，近 90 行，最長的函式）做任何性質分析**。Q-03 的表只覆蓋 brief 點名的五個函式加 `best_clouds`。
