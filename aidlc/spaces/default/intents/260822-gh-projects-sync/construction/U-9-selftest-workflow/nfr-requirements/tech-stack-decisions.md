# 技術選型 — U-9 自我測試 workflow

<!-- Stage: nfr-requirements（Construction，per-unit）· Unit: U-9-selftest-workflow · kind: service -->

## 決定：純 Actions 單檔，不走 gh-aw、不拆 `*-impl.yml`

**`.github/workflows/aidlc-sync-selftest.yml`（`pull_request` ＋ `workflow_dispatch`）**，純 Actions、`shell: bash`，加上 fixture 集的驅動端。

**與 U-6／U-7／U-8 的差異有二，兩者都有理由：**

| 面向 | U-6／U-7／U-8 | U-9 | 為什麼 |
| --- | --- | --- | --- |
| 承載 | 純 Actions | **相同** | 決定性邏輯放純 Actions 步驟（`project.md ## Forbidden` 收窄後的規則、ADR-0013） |
| 兩檔拆分（`*-impl.yml`，`on: workflow_call`） | 有（ADR-A10） | **無** | 拆分的理由是**多個觸發器共用同一段實作**並讓它可被參數化呼叫。本單元只有一個觸發器、不被任何人呼叫，拆成兩檔只增加一層間接 |

**不走 gh-aw 對本單元特別重要**：本單元的全部工作是斷言，**沒有任何一項是判斷性的**。把斷言交給 LLM 路徑，等於讓要被驗證的那類不確定性進入驗證層本身——而 `project.md` 記載本 repo 的三塊結構性盲區，第一塊就是「所有 LLM 路徑」。

**直接後果**：`timeout-minutes` 正常生效（見 `performance-requirements.md` 對 gh-aw v0.81.6 靜默丟棄該 key 的記載），且 `business-rules.md` R-1.2 的靜態檢查有明確對象——它檢的是 `aidlc-sync-*` 系列的決定性 job 不含代理式引擎步驟，而本單元自己是那條規則的示範。

## fixture 的存放與格式

| 項 | 決定 |
| --- | --- |
| 位置 | `<record>/.test-fixtures/`（[ad:component-methods.md] 已定案的落點，見 `../functional-design/domain-entities.md`） |
| 格式 | **純文字**，不引入任何序列化框架。[US:S-10 AC 1] 的前提是 U-1 可被純文字驅動 |
| 版控 | **進版控**。`.test-fixtures` 不以 `.aidlc-` 開頭，不落入 `.gitignore:52` 的排除 |

**不引入 fixture 框架（如 snapshot 測試工具）的理由**：本 repo 的前端**完全沒有 unit／component 測試框架**（`team.md` 記載 `devDependencies` 只有 `@playwright/test`），後端用 Python 內建 `unittest`。引入一個新框架只為本單元使用，會是這個 repo 裡唯一的一份，維護成本落在沒人熟悉的地方。**純文字比對加 `diff` 已足以表達本單元的全部斷言。**

## 靜態檢查（R-1.2）的工具

檢查對象是四支 workflow 的 **`.yml` 原始檔**（`.github/workflows/aidlc-sync-*.yml`）。**工具用 `python3`**，理由是：

> **檢查對象於 2026-08-30T06:11:59Z 由「編譯後的 `.lock.yml`」更正為 `.yml` 原始檔（reviewer 判 Critical）。** 四支 workflow 已全數定案為**純 Actions**（見本檔上方「不走 gh-aw 對本單元特別重要」），根本不存在 `.lock.yml`——**指向不存在的檔案使這個唯一的機械化決定性閘門恆綠**，而它正是本單元存在的理由。同一個錯誤也出現在 `performance-requirements.md` 的觸發 allowlist，一併更正。
>
> **為什麼會錯**：本單元的設計早期假設走 gh-aw（那時 `.lock.yml` 是對的），後來改為純 Actions 時只更正了「不走 gh-aw」的論述，沒有回頭改依賴該假設的檢查對象與 allowlist。這是 `project.md` 的 `application-design:260822-ad-L1`（改動一個事實要列出它的全部表達形式）在本 stage 的又一次實例。

- 本 repo 的 `scripts/` 下既有工具全部是 Python（`validate_repo_contract.py`、`validate_env_contract.py`、`tcms_validate.py`、`tcms_sync.py`），CI 以 `python3` 直接呼叫；
- YAML 解析在 Python 標準生態中是既有能力，不需新增依賴到 `backend/requirements.txt`（該檔的依賴**100% 未 pin、無 lockfile**，`team.md` 已記載，新增依賴會落進那個已知問題裡）。

> **這支檢查腳本放哪裡，要注意一條規則。** `project.md ## Forbidden` 禁止「以 repo 內新增的實作程式承載**無人值守的**流程自動化與外部系統同步」，邊界以觸發來源判定——由事件或排程觸發、無人在迴圈內的屬禁止範圍。
>
> **本檢查由 `pull_request` 觸發，形式上落在該範圍內。** 但它**不是流程自動化，也不與任何外部系統同步**——它是一支對 repo 內檔案做靜態比對的驗證腳本，與既有的 `validate_repo_contract.py`（同樣由 CI 事件觸發、同樣是 repo 內 Python）完全同類，而該檔是本 repo 的 contract 正式來源之一、CI 明文執行。**故本站判定不適用該禁令**，理由是規則的標的是「承載同步機制」而非「驗證機制」。
>
> **這個判定須在 Bolt 4 的 gate 被確認**，不由本站單方面定案——它涉及一條使用者本 session 才收窄過的規則的邊界。

## 既有技術堆疊的承接

[ck:technology-stack.md] 記載 CI 的 Python 執行環境為 `python:3.12-slim`（Dockerfile 與 CI 一致）、GitHub Actions 的 action 版本鎖在 `.github/aw/actions-lock.json`，且本 repo 的測試工具為 Python 內建 `unittest`。**本單元的全部選型都落在這些既有能力內，不新增任何一項。**

## 與上游的對應

ADR-A10 的兩檔拆分引自 [ad:decisions.md]；承載形式的規則引自 `project.md ## Forbidden`（2026-08-23 收窄版）與 ADR-0013；三塊結構性盲區與 `scripts/` 既有工具引自 `project.md`；前端無 unit 測試框架、backend 依賴未 pin 引自 `team.md`；[US:S-10 AC 1] 引自 `stories.md`；fixture 落點與 registry 選取邊界引自 [ad:component-methods.md]；U-9 的交付引自 [ug:unit-of-work.md]；R-1.2／R-2／R-3 見本單元的 `business-rules.md`，兩段流程見 `../functional-design/business-logic-model.md`，fixture 集見 `domain-entities.md`；`timeout-minutes` 的 gh-aw 行為見本單元的 `performance-requirements.md`；CI 執行環境與 action 鎖定引自 [ck:technology-stack.md]（`aidlc/spaces/default/codekb/cloud-360/technology-stack.md`）。
