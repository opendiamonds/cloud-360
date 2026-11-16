## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-03T11:30:42Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-54 | Critical | `construction/brain-infra/nfr-requirements/tech-stack-decisions.md` §一「既有堆疊裡與本單元相關的事實」表 ＋ `security-requirements.md` `NFR6.1` 落點表 ＋ `tech-stack-decisions.md` §四（九處同步清單） | 這兩份產出把 `brain-infra` 描述成**尚未實作、待交付**的工作（「現值」`postgres:16-alpine`、「staging 服務數 4」、「Redis 在本 repo 的現況：零基礎設施用途」、`:13`／`:19–20`／`:96` 等行號引用）。但 `git log` 顯示該單元的整條 construction 管線**已於 Inception 重跑前完整跑完並合併**：`fd0d2bf` 完成 `nfr-requirements`、`5c13c11` 完成 `nfr-design`、`b07e20e` 完成 `infrastructure-design`、`7ce1bee`（2026-09-27）完成 `code-generation`（提交訊息逐字「Redis 與 Ollama 兩個服務、PG 18＋pgvector、部署期資料面與 ACL 探測」），其後才以 `aaf2000`「於 Inception／Construction 邊界 park 工作流程」暫停、接著重跑 Inception 產出能力 11／12／13。**實測 repo HEAD**：`deploy/docker-compose.deploy.yml` 已有 6 個服務（`db`／`backend`／`redis`／`ollama`／`frontend`／`cloudflared`，以 `grep` 逐行確認），db image 已是 `pgvector/pgvector:pg18`（實際在 :40，非文件稱的 :13）、具名 volume 已改名為 `db_pg18`（:52／:382，非 :19–20／:96）、`redis:8-alpine` 已在 :160；`docker-compose.yml`（本機 dev）與 `docker-compose.test.yml` 的 db image 也已是 `pgvector/pgvector:pg18`；`schema_rbac.sql` 的 `CREATE EXTENSION IF NOT EXISTS vector;` 已置於 `BEGIN;`（現為 :37，非文件稱的 :24）之後第一條敘述（:45），全檔現為 779 行、`COMMIT;` 在 :757（非文件稱的 644 行／:633）——與 `security-requirements.md` `NFR6.2`／`NFR6.2a` 要求的落點與順序完全一致。換言之：這兩份文件要求的東西幾乎全部已經照著做出來並上線了，但文件本身的敘事與逐一行號引用卻仍停在實作之前的舊狀態，對現在要做 Keep／Redo 判斷的人是誤導性的——它們讀起來像一份還沒開工的規格，而不是一份已出貨基礎設施的記錄 | 在核可 Keep 之前，必須讓人工決策者知道這個事實：該單元的 construction 四個 stage 皆已完成且已合併。對它重跑 `nfr-requirements`（乃至下游 `nfr-design`／`infrastructure-design`／`code-generation`）如果只是重新核可既有決定，等同重做已完成的工作；如果因新能力（見 R-55）而產生新要求，代表要改動的是**已上線的 compose／SQL／workflow**，而不是一份尚未落地的計畫文件——這是遠比「更新文件」更大的工作量，須明確呈交使用者裁決是否真有新要求、以及改動已出貨基礎設施的範圍與風險。文件本身所有 `<file>:<line>` 引用與「現值」表格，若要繼續作為文件使用，也需要重新核對現行行號 | New |
| R-55 | Major | `security-requirements.md` §五「本站刻意不決定的事」與 `traceability.json` 的 `reverse` 清單 ＋ `tech-stack-decisions.md`（全檔） | 上游單元依賴文件的修訂 4 Assumptions 明文寫著一個**仍然開放、且直接落在本單元職責內**的問題：新增單元之一的部署模型是本 intent 第二個 `standalone`（獨立進程、跑在**同一台 staging 主機**上），而「`brain-infra` **是否需要為它新增第七個 compose 服務**，屬 `infrastructure-design` 的範圍，本站不定」。`NFR8`（新增元件的部署設定完整性）正是本單元自己的核心職責，而三份產出對 `MCP`／`mcp_server`／`mcp-bridge`／該新單元編號／`progress-channel` 等關鍵詞的命中數實測為 **0**——不是「判定不適用」，是完全沒有提及這個仍然開放、且已被上游明確點名可能落在本單元身上的問題。依 R-54 的事實，`brain-infra` 不是一個尚未定稿的計畫，而是**已經照 6 服務、兩段式內部網路拓樸建好並上線的基礎設施**——若上游日後判定需要第七個服務，那是對**已上線拓樸**的擴充，而不是對一份草稿的補充。本站現有的推導邏輯不成立並不代表這個問題不存在，只是上游尚未定案，不等於本單元可以對它保持沉默 | 在「本站刻意不決定的事」與 `traceability.json` 補一筆明確的交叉引用，指出：(a) 本單元尚未涵蓋這個問題；(b) 承接站是 `infrastructure-design`（3.4）；(c) 若判定需要第七個服務，影響的是**已合併**的 compose 拓樸，不是尚未動工的草稿，以便承接站迭代與任何重新核可本單元的人都能看到這個落差 | New |
| R-50 | Minor | `security-requirements.md` §〇 `S-5` 列（約 :79）與 `NFR4.1(c)` 承載者表下方「適用範圍」表（約 :94–95） | 沿用先前審查記錄的量詞殘留：`S-5` 欄（「一份掛載的 Redis 設定資產……必須掛進兩份 compose」）與其下 15 行處已更正為「必須有，但不會是同一份檔」的敘述不一致。本輪重新核對兩處位置仍存在（內容未變），屬刻意保留、未處置的既有殘留，非本輪新引入 | 下次觸及本節時，依既有審查記錄的建議統一量詞用語；本輪不阻擋 | Unresolved |
| R-52 | Minor | `security-requirements.md` §六「修復後的狀態（可複驗）」項（約 :787–789） | 沿用先前審查記錄：引用 `aidlc-state.md:89`／`:31` 的具體行號在該檔每次 stage 推進時會被引擎重寫，行號本身不穩定（R-51 的成因即為同類行號漂移）。緩解因素是同一句已把目標行的全文逐字寫出，可供字串複驗。本輪重新核對內容與位置仍一致，未變化 | 下次觸及此節時，考慮把行號降格為輔助定位（保留逐字字串為主索引）或改引不可變的 audit shard 事件 | New |
| R-53 | Minor | `security-requirements.md` §六「修復的代價，已承擔完畢」項（約 :790–796） | 沿用先前審查記錄：「`Invalidated Downstream Artifacts` 與 `Invalidated Downstream Reviews` 兩欄逐字列出本單元三份產出」的量詞對第二欄不成立（實查 audit shard，後者僅一筆）。本輪重新核對內容與位置仍一致，未變化 | 下次觸及此節時改為「`Invalidated Downstream Artifacts` 逐字列出本單元三份產出，`Invalidated Downstream Reviews` 列出其審查收據一筆」 | New |

### 本輪查證過但未發現缺陷的項目（供完整性記載）

- **ADR-0006 四面向判定方向**：本單元 `security-requirements.md` §一的四面向判定（IAM／Encryption／Network exposure／Audit logging 皆「適用」）與現行 `requirements.md`（原表 ＋ 修訂 1 的新增能力補判定表）、上游單元依賴文件修訂 4 的 ADR-0006 表逐項核對，**沒有查到方向相反的矛盾**（R-54／R-55 是遺漏與時效問題，不是判定方向錯誤）。
- **CI 閘門作用域聲稱**：`security-requirements.md` §四對 `scripts/validate_env_contract.py` 的函式名與行號（`compose_variables` :101、`validate_deploy_stack_is_fully_supplied` :168、`validate_deploy_template_is_complete` :184、`validate_scopes_are_separated` :212、`validate_local_dev_template_is_complete` :242、`DEPLOY_COMPOSE` :40）與其作用域（只讀 `deploy/docker-compose.deploy.yml`，不含 test compose）經開檔逐一核對，**與現行腳本完全一致**；`.github/workflows/deploy.yml` 的「Require the secrets that must not default」步驟只在 `deploy` job（非 `rollback` job）的聲稱亦與現行 workflow 相符。CI 的真實 PostgreSQL job（文件稱「尚未存在」）確認**仍不存在**於 `.github/workflows/ci.yml`，與文件聲稱一致。
- **加密手段延後的連言條件**：重新核對上游單元依賴文件修訂 4 現行的下游設計 stage condition（連言 ＋ 逐單元執行），本單元「跑過本站不保證其他記憶相關單元會跑」的推導邏輯在重跑後的 Inception 下**仍然成立**，非缺陷。

### Validation Tool Results

本次未執行 `traceability`／`upstream-coverage` 等 sensor 工具（受限於跨單元讀取邊界與時間預算，改以手動逐條核對 `traceability.json` 的 `upstream_ids`／`coverage`/`reverse` 三區對照 `security-requirements.md` 的章節標題，確認全部可解析且無缺漏）。核對結果：`traceability.json` 列出的 11 個上游 NFR 全部在 `requirements.md` 現行版本中存在（標題逐字核對），`coverage`／`reverse` 兩區指到的章節在 `security-requirements.md` 中皆存在，未發現斷鏈。

### Summary

本輪最重要的發現不是文件內部的邏輯缺陷——三份產出在 2026-09-26／09-27 當時的自我審查相當紮實（十輪審查、R-50 之前的所有發現皆已處置）。問題是世界已經變了兩次，而文件只跟上了一次：Inception 重跑（新增三項能力）發生在本單元的整條 construction 管線**已經完整跑完並合併**之後。這代表 (1) 文件裡幾乎每一條 `<file>:<line>` 引用與「現值」基準，在對照現行 repo HEAD 時都已失真（R-54，Critical）；(2) 上游已經點名一個直接落在本單元職責內、至今仍開放的問題（新單元是否需要本單元新增第七個 compose 服務），而三份產出對它完全沉默（R-55，Major）。在核可 Keep 之前，人工決策者需要知道：這不是「要不要相信一份尚未過時的規格」的問題，而是「一段已經上線的基礎設施，在新增三項能力之後是否需要被重新打開」的問題——兩者的風險與工作量完全不同。
