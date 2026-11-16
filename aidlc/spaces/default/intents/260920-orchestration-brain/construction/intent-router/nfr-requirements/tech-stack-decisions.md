# Tech Stack Decisions — `U11 intent-router`

> ID 帶 `.60+`。本檔承載 `OQ-4` 的定案與其整合後果。

## TS-1 — 路由層模型：`typesafe/jev-1.13`

| 項目 | 內容 |
|---|---|
| **決定** | 路由層（意圖識別）使用 **`typesafe/jev-1.13`**，經 OpenRouter |
| **誰決定、何時** | **使用者**，`2026-10-03T11:48:31Z`（`construction/brain-infra/nfr-requirements/nfr-requirements-questions.md` 的 `N12`=B；其前身 `N11`=`B＋X`，原話逐字「B+jev模型使用」）。本站 `[N1]`=C **再確認**，不是新決定 |
| **對應開放問題** | `OQ-4`（`requirements.md:785`）——**本站結案** |
| **`NFR10` 的合規狀態** | `NFR10` 逐字要求「在有**實測準確率與延遲基準**後決定」。**那個基準至今不存在**，故本項嚴格說是**先決定、後驗證**。如實記載，不粉飾：使用者在知情下（`N12` 的選項文字已揭露此落差）做了這個裁決 |
| **替代方案** | `google/gemini-3.7-flash`（現行 `langgraph_runtime.py:17` 的預設，`OQ-4` 的另一個候選）。未被選中，但**仍是 `NFR10` 可替換性的實際對照組**——見 `TS-2` |

### 已實測的中繼資料（公開端點，`HTTP 200`，免金鑰）

| 欄位 | 值 | 來源 |
|---|---|---|
| `architecture.modality` | `text->decisions` | `ideation/rough-mockups/memory.md:47`；`brain-infra` 的 `N13` 複驗 |
| `output_modalities` | `["decisions"]` | 同上 |
| `supported_parameters` | **空陣列** | 同上 |
| `supports_tool_choice` | `none`／`auto`／`required`／`function` **四者皆 `true`** | `N13`（該輪自行查到，上游未記載） |
| context／max completion | 32000／28800 | 同上 |
| 計價 | prompt `$0.042/MTok`、completion **0** | 同上 |
| 公開 `description` | **完全沒有提到信心分數** | `N13`。`rough-mockups/memory.md:47` 寫的「型別化決策＋信心分數」在可取得的公開中繼資料裡**找不到依據** |

## TS-2 — `NFR10`（可替換性）的具體落法 — `NFR10.60`／`NFR10.61`

`NFR10` 要的是**可替換**，不是自動切換（理由見 `reliability-requirements.md`
「不設 fallback 模型」）。落法：

- 路由層模型名為**獨立的環境變數**（`TS-4` 的 `BRAIN_ROUTER_MODEL`），
  **不得**沿用 `LLM_MODEL`——後者是 A1／A3 功能 agent 在用的，共用會讓
  `[F1]`／`NFR10` 逐字允許的「編排層與功能 agent 得使用不同模型」在設定層消失。
- 換模型**不需要改程式**：改環境變數＋重啟即生效。
- 換模型**必須重跑 `NFR1` 的標註集**——準確率數字不可跨模型沿用。
  這一條寫進 `build-and-test` 的交接。

| ID | 需求 | 驗證方式 |
|---|---|---|
| **`NFR10.60`** | 路由層模型由**獨立環境變數** `BRAIN_ROUTER_MODEL` 決定，**不得**與功能 agent 共用 `LLM_MODEL`；換模型不需改程式 | 設定值改動後實際送出的 `model` 隨之改變的測試；且 `grep` 斷言本單元不讀 `LLM_MODEL` |
| **`NFR10.61`** | 換模型後**必須重跑 `NFR1` 的 ≥50 筆標註集**，準確率數字不得跨模型沿用 | 流程義務，落 `build-and-test` 的核可關卡 |

## TS-3 — 三項整合後果（`[N1]`=C 帶進來的，實作者必讀）

| # | 事實 | 後果 | 處置 |
|---|---|---|---|
| **TS-3a** | `supported_parameters` 為**空陣列** | 現行 `openrouter_chat_model` **固定傳 `temperature=0.0`**（`langgraph_runtime.py:95`）。對 Jev 這個參數可能被拒或被忽略 | 路由層**不得**無條件沿用 `openrouter_chat_model` 的現行簽章。`code-generation` 須讓 `temperature` 對本路徑可省略，並**實測**帶與不帶的差異。**這是本站查出的、上游未記載的整合風險** |
| **TS-3b** | 型別化輸出走 **tool/function calling**（`supports_tool_choice` 四項皆 `true`） | 呼叫形狀與既有 OpenRouter chat 不同；repo 內 `with_structured_output`／`response_format`／`JsonOutputParser` **0 命中**（本站 `grep` 實測），本單元會是**第一個** | `code-generation` 須建立這個形狀並以替身測試覆蓋四種畸形回應（`NFR3.70`） |
| **TS-3c** | `output_modalities` 為 `["decisions"]`，**不產生文字** | `initiative-brief.md:313` 逐字：**不適用能力 8**（大腦自身回覆的串流）。亦即 Jev 只能用在本單元，不能兼任「產生自然語言回覆」的那個角色 | 記為對 `OQ-N1`（產生回覆的單元尚未指派）的約束：**那個單元不能用 Jev** |

## TS-4 — 本單元新增的環境變數（`NFR8` 的部署設定完整性）

`project.md` 的 blocking 規則逐字：「**新增 compose 消費的變數時**，同一個 PR
必須讓 `render-env.sh` 寫它、`deploy/.env.example` 列它」，理由是**失敗模式無聲**
（既有實例：`N8N_USER`／`N8N_PASSWORD` 從未被寫入，導致每次部署的架構圖 icons
都靜默退回灰底佔位圖）。

| 變數 | 用途 | 預設 | 缺值行為 |
|---|---|---|---|
| `BRAIN_ROUTER_MODEL` | 路由層模型（`TS-2` 的可替換性落點） | `typesafe/jev-1.13` | 取預設並記一行 INFO。**不致命**——它有一個正確的預設 |
| `BRAIN_ROUTER_TIMEOUT_SEC` | 硬逾時（`NFR3.61`） | `5` | 取預設並記 WARN |
| `BRAIN_ROUTER_MAX_CALLS_PER_TURN` | 每輪呼叫上限（`NFR3.62`） | `1` | 取預設並記 WARN |
| `BRAIN_ROUTER_MAX_RETRIES` | 重試次數（`NFR3.63`） | `0` | 取預設並記 WARN |
| `BRAIN_ROUTER_CONFIDENCE_THRESHOLD` | 門檻（`FR1.7` 的 0.7，`BR3.4` 要求它是設定值不是常數） | **無預設** | **啟動失敗並列出需要的設定**。理由見下 |

**為什麼只有門檻無預設**：`BR3.4` 逐字「缺值不得以預設值靜默啟動」。其餘四個
缺值時系統行為正確、只是沒照設定跑；門檻缺值則**反問路徑的判定基準不存在**，
而那是 `FR1.3` 這條 Must 的觸發條件。既有前例是 `EMBEDDING_PROVIDER` 與
`BRAIN_SESSION_HISTORY_MAX`（`backend/.env.example:111-153`）——兩者都 required
且無預設，缺值即大聲失敗。

**三處同步義務**（**`NFR8.61`**）：`backend/.env.example`、`deploy/.env.example`、
`deploy/render-env.sh`。`python3 scripts/validate_env_contract.py` 會擋下漏接。

## TS-6 — **blocking 前置條件：`OPENROUTER_API_KEY` 必須在 `build-and-test` 之前配置**（修訂 1，審查 `R-06`，Major）

`[N3]`=A 把 `OQ-10`（Jev 的回傳是否帶可比較的信心值）指定給 `build-and-test`
（3.6，`ALWAYS`）。審查正確指出：**「保證會被嘗試」不等於「保證會產出」**。

### 查證過的事實

| # | 事實 | 來源 |
|---|---|---|
| 1 | `build-and-test` 的 `execution` 確實是 `ALWAYS`，且會讀 `nfr-requirements/` 的全部產出建立 Target Verification Matrix | `.claude/aidlc-common/stages/construction/build-and-test.md` |
| 2 | 但該站 Step 9 逐字：「A deferred target remains **`Unverified`** and cannot contribute to a successful stage result. If no later owning stage is scheduled, the target is **`Unverified`, not deferred successfully**」 | 同上，`:144-146` |
| 3 | 以真實 Jev 回應填 `Actual` 欄的前提是 `OPENROUTER_API_KEY` 已配置 | — |
| 4 | **`backend/.env` 仍不存在、shell 的 `OPENROUTER_API_KEY` 未設**（本站 `V4g` 已查，審查複驗一致） | `[跑]` `[ -f backend/.env ]` |
| 5 | 取得金鑰的那一題（`brain-infra` 的 `N14`「金鑰就緒確認」）**`[Answer]:` 欄自 2026-10-03 至今仍為空** | `[讀]` 該問題檔 |

### 所以本站撤回「已解掉」這個措辭

**原措辭**：「本站解掉了上游標的『無自然承接站』」。
**修訂後**：`build-and-test` 提供了一條**真實的執行路徑**（它不會被 skip，且它本來
就會產生 `NFR10` 要求的準確率與延遲基準）——**但它的成功仍依賴一個本單元與
`build-and-test` 都無法控制的外部前置條件：人工把金鑰寫進 `backend/.env`。**

**這與 `project.md` 的 `approval-handoff:5d0af04b` 反面教材同形但不同程度**：
那一條說的是「填一個看起來合理的轉移目標但其實是死指派」。本項的轉移目標是真的
（`ALWAYS` ＋ 本來就會做那件事），差別在於**前置條件沒有被任何機制追蹤**——它只
存在於一份**別的單元**的問題檔裡，而那正是本站 `[N1]` 出題時漏讀的那一份。

### blocking 宣告

| 項目 | 內容 |
|---|---|
| **前置條件** | `OPENROUTER_API_KEY` 配置於 `backend/.env`（該檔由 `.gitignore:19` 忽略，不進版控） |
| **誰能滿足它** | **只有使用者**。本單元、`build-and-test` 都不能 |
| **未滿足的後果** | `NFR1`／`NFR10`／`OQ-10` 在 `build-and-test` 被標 **`Unverified`**（非 deferred 成功），觸發該站的失敗升級梯 |
| **追蹤落點** | 本表 ＋ `traceability.json` 的 `reverse` 的 `OQ-10` 列。**不再只存在於 `brain-infra` 的 `N14`** |
| **最晚期限** | `build-and-test`（3.6）開始之前 |

## TS-5 — 不新增任何套件

| 需要的能力 | 既有套件 | 來源 |
|---|---|---|
| OpenRouter 呼叫 | `langchain-openai` 的 `ChatOpenAI`，經 `langgraph_runtime.openrouter_chat_model` | `technology-stack.md` Backend 套件表 |
| 圖執行 | `langgraph` | 同上 |
| property-based 測試 | `hypothesis` | 同上 |
| 替身 | `unittest.mock`（標準庫） | `team.md` Testing Posture |

**零新依賴。** 這與 `TS-3b`（tool calling 是 repo 內的第一次）不衝突：
新的是**用法**，不是套件。
