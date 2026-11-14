# Infrastructure Design 問題檔 — `U22` `progress-channel`

> 單元：`U22` `progress-channel`（`library`，M）
> Stage：`infrastructure-design`（3.4）　Depth：`Minimal`　Review class：`advisory`（單輪、兩種結論皆終局）
> 建立時間：2026-10-04T01:56:05Z
> 產出：`cicd-pipeline.md`、`traceability.json`（2 項）

---

## §〇 本 stage 的 CONDITIONAL 適用性判定

`project.md` 要求逐項對照 condition 條款並把判定理由記入 diary，**不得憑 feature
表面大小直覺 skip**。condition 逐字為：

> Infrastructure services need mapping, deployment architecture required, or cloud
> resources needed. **Skip if no infrastructure changes and infrastructure already defined.**

| 條款 | 判定 | 依據 |
|---|---|---|
| Infrastructure services need mapping | **不成立** | `library`，無進程、無 socket、無 port、無容器（`SEC-4`） |
| Deployment architecture required | **不成立** | 零新環境變數；`deploy/docker-compose.deploy.yml` 維持 6 個服務 |
| Cloud resources needed | **不成立** | 無任何雲端資源 |
| **CI pipeline 的內容** | **成立** | 本單元引入**三道 grep 閘門**：`U22-V3`（五個退場符號 ＋ 三個呼叫點）、`U22-V5`（本模組無鑄造函式）、`S-7`（形狀級例外檢查）。這三道目前**都不存在** |

**判定：執行，不 skip。** 理由不是「condition 的前三款成立」——它們都不成立——而是
**kind 過濾本身告訴我們該做什麼**：`produces_kinds` 把 `infrastructure-specification`
與 `monitoring-design`（infra 那兩份）過濾掉，只留 `cicd-pipeline` 與 `traceability`
給 `library`。引擎回的 `produces` 實測為 2 項，與此一致。所以本站的工作範圍就是
CI 那一半。

> **附帶更正**：`nfr-design` 的三處產出逐字宣告本 stage 對 `library`「kind-vacuous」，
> 那是錯的（該輪審查 `R-01`，Critical）——`produces_kinds` 有四條，前兩條是
> `[service, ui, packaging]`，後兩條 `cicd-pipeline` 與 `traceability` **含 `library`**，
> 而 `cicd-pipeline` 正是本 stage 的 `review_artifact`。本站的存在即為該更正的證據。

---

## 前言：不重問的已定案事項

| 已定案 | 出處 |
|---|---|
| 零新依賴、零環境變數、零 compose 變更、compose 維持 6 服務 | `U22-D3`、`SEC-4` |
| 測試框架 `unittest`、落點 `backend/tests/`、`IsolatedAsyncioTestCase` | `U22-D8` |
| 三道 grep 閘門的**內容** | `U22-V3`／`U22-V5`／`S-7` |
| log 分級與不含 `content` | `U22-D6`、`SEC-3` |
| `project.md` 的五項 blocking 觸發皆未命中，`LOCAL-DEV.md` 同步不適用 | `tech-stack-decisions.md §四` |

## 本站開工前的實地查證

`ci.yml` 的 `backend` job 現有步驟（`:235` 起，逐步讀出）：

1. `actions/checkout@v4`
2. `actions/setup-python@v5`
3. `pip install -r requirements.txt`
4. **Import FastAPI app** — `python -c "import main; print('app:', main.app.title)"`
5. **OpenAPI spec drift** — `python scripts/dump_openapi.py --check`
6. **WS contract spec drift** — `python scripts/dump_ws_contract.py --check`
7. **Run unit tests** — `python -m unittest discover -s tests -v`

兩項可用的既有先例：**步 5／6 是「跑一支 Python 腳本、`--check` 失敗即紅燈」的形狀**
（`scripts/dump_openapi.py`、`scripts/dump_ws_contract.py`），而**步 7 會自動撿到
`backend/tests/` 下的任何新檔**。

---

## Q1 — 三道 grep 閘門要以什麼形式進 CI？

三道閘門的內容已定，形式未定。兩個既有先例各有道理，而選錯會留下一道沒人跑的檢查。

- **A（建議）— 寫成 `backend/tests/` 下的測試，由步 7 自動撿到。** 以
  `unittest` 的一支測試檔（例如 `test_progress_channel_contract.py`）讀取
  `design_agent.py`／`agent_router.py`／`wa_collab_orchestrator.py`／`progress_channel.py`
  的原始碼文字並斷言三個條件。好處：**零 CI 設定變更**（步 7 已存在且會自動撿到），
  失敗時的輸出是標準的 unittest 失敗訊息，且**本機與 CI 行為一致**（開發者跑
  `python -m unittest` 就會看到）。代價：以測試讀原始碼文字在感覺上不像單元測試；
  但本 repo 已有同形先例——`test_schema_rbac_sql_matches_migration_ddl`
  （`test_hierarchy_migration.py:454`）正是用測試解析 `schema_rbac.sql` 的文字。
- **B — 寫成 `scripts/check_progress_channel.py --check`，在 `backend` job 加第 8 步。** 好處：
  與步 5／6 的既有先例完全一致，語意上「這是一道契約檢查」而非單元測試。代價：
  要改 `ci.yml`（一個新步驟）、新增一支 `scripts/` 檔；而 `project.md` 的 `## Forbidden`
  有一條關於「不得以 repo 內實作程式承載無人值守流程自動化」——本項由 `on: push`／
  `pull_request` 觸發、無人在迴圈內，**落在該條的禁止範圍內**（該條的既有例外是
  `tcms` plugin 的腳本，它們只被 stage 檔呼叫，`.github/` 下無 workflow 呼叫它們）。
  選 B 需要先裁決那條規則是否適用。
- **C — 寫成 `.github/workflows/` 的純 Actions 步驟（直接在 yaml 裡跑 `grep`）。** 好處：
  避開 B 的規則問題（純 Actions 步驟不是 repo 內的實作程式），且 `project.md` 逐字
  建議「決定性的映射邏輯應優先放在純 Actions 步驟」。代價：三道檢查中有兩道需要
  否定條件與多檔比對（「三個呼叫點**都**要傳入新鍵」），寫成 shell 的可讀性與可維護性
  比 Python 差；且失敗訊息是 `grep` 的 exit code，不會說明哪一個呼叫點漏了。
- **D — 不進 CI，列為 code review 的檢查項。** 代價：本單元的全部價值在於修掉三個
  安靜的失敗模式，而把驗證放在人工 review 等於新增第四個安靜失敗模式。

`[Answer]`: A <!-- 人工作答 2026-10-04T02:27:38Z（`date -u` 實取）。選項文字與選單逐字一致。 -->

---

## Q2 — 突變驗證（確認閘門真的會紅）要不要列為本站的交付條件？

`project.md` 的 `tcms-test-cases` 規則要求自動化腳本必須做**突變驗證**——把修正改回
錯的行為、確認測試紅燈、還原複驗。那條規則的落點是 `tcms-test-cases` stage，但
本單元的三道閘門有一個特殊性質：**它們檢查的是「某個字串不存在」**，而這類檢查
最容易寫成恆真（grep 寫錯 pattern 就永遠找不到，於是永遠綠）。

- **A（建議）— 列為本站的交付條件，且指定突變內容。** 三道閘門各指定一個突變：
  ① 把 `_progress_queue` 一行加回 `design_agent.py` → `U22-V3` 必須紅；
  ② 在 `progress_channel.py` 加一行 `import uuid` → `U22-V5` 必須紅；
  ③ 把 `:216` 的固定字串改回 `f"...{e}"` → `S-7` 的形狀級檢查必須紅。
  好處：把「這道閘門不是恆真」變成一個**做過就有紀錄**的動作，而不是等
  `tcms-test-cases` 去推斷。代價：`code-generation` 要多做三次改回／複驗／還原。
- **B — 交給 `tcms-test-cases` stage 處理，本站只寫閘門內容。** 好處：不重複職責；
  那個 stage 本來就 `execution: ALWAYS` 且有 `/tcms-verify` 關卡。代價：本站知道
  突變該是什麼（我剛列出三個），交出去等於讓下一站重新推導；而 `project.md` 記過
  「指派事項找不到誠實的轉移目標時寧可寫明無承接站」——這裡有承接站，但資訊會流失。
- **C — 只要求第三道（`S-7`）做突變驗證。** 理由：`S-7` 是三道裡唯一**本站新創**的
  形狀級檢查，另兩道是直接的字串存在性。代價：`U22-V3` 的三個呼叫點條件其實是最
  容易寫成恆真的那一個（它要斷言三處**都**傳入新鍵，漏寫一處的 grep 會過）。

`[Answer]`: A <!-- 人工作答 2026-10-04T02:27:38Z（`date -u` 實取）。選項文字與選單逐字一致。 -->

---

## Assumptions & Open Questions

（本站產出時填寫）
