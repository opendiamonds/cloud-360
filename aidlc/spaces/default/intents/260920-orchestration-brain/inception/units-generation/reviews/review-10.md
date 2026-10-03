## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-03T01:37:40Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Critical | `aidlc/spaces/default/intents/260920-orchestration-brain/inception/units-generation/unit-of-work.md` 第 37–53、306–312 行「單元清單」的 Directory 欄；`unit-of-work-story-map.md` 全表的 Directory 欄 | 本站兩份產出對**每一個**單元（U1–U24，無一例外）都把 Directory 寫成 `construction/u<N>-<name>/`（例如 `construction/u1-brain-infra/`、`construction/u4-hierarchy-data/`），但實際磁碟上已交付的四個單元的目錄是 `construction/brain-infra/`、`construction/brain-ws-contract/`、`construction/hierarchy-data/`、`construction/rbac-story-ids/`——**完全沒有 `u<N>-` 數字前綴**（已以 `find construction -maxdepth 1 -type d` 核對，`brain-infra/` 下已有 `code-generation/`、`nfr-design/`、`nfr-requirements/`、`infrastructure-design/` 四個完整產出）。引擎本身的慣例亦證實這一點：`.claude/tools/aidlc-swarm.ts` 的 `construction/${unit}/${stage.slug}/...`（第 622、746、788 行）用的 `unit` 是裸單元名字串，不帶編號前綴。本站自己在修訂 4 開頭明寫「17 個單元全部有效、不改名、不插號、不回改。理由不是文件慣例而是磁碟現況……引擎的 per-unit 收據與 construction 目錄都以單元名為鍵，改名或插號會讓已完成的工作變成找不到歸屬的孤兒」——但緊接著整份文件的 Directory 欄用的正是一個與這個磁碟現況不符的命名法，對已交付的 `U1`／`U2`／`U3`／`U4` 四個單元而言，字面上就是在建議一個與既有 `code-generation` 產出**不同**的新目錄，正好構成文件自己警告要避免的那種孤兒化。本檔沒有任何其他 stage 檔或 engine 文件要求 `u<N>-` 前綴（已查 `units-generation.md` 與 `construction/*.md` 皆無此慣例），純屬本站筆誤且系統性地貫穿全部 24 個單元。 | 把 `unit-of-work.md` 與 `unit-of-work-story-map.md` 內所有 Directory 欄的 `construction/u<N>-<name>/` 改為 `construction/<name>/`（與既有四個已交付目錄及 `aidlc-swarm.ts` 的鍵一致），逐一核對 24 個單元與全部橫跨多單元的 Directory 連結欄位。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 自寫 DAG 解析腳本（解析 `unit-of-work-dependency.md` 的機讀 yaml 邊塊） | 單元 24（唯一）、邊 46、無環、kind 分佈 `{packaging:3, spec:5, library:2, service:9, ui:5}`、可平行根 5（`brain-infra`／`brain-ws-contract`／`rbac-story-ids`／`hierarchy-data`／`progress-channel`）、層數 7（各層數 5/4/4/5/3/1/2）、完全互相獨立對 146 | 與 artifact 聲稱的每一個數字逐一比對，**全部相符，無一處偏差**。拓樸健全性（唯一名稱、無未宣告依賴、無自我依賴、無環、kind 合法）亦全部通過 |
| `bun .claude/tools/aidlc-sensor-traceability.ts` | `{"pass":true,"gaps":[],"orphans":[],"findings_count":0}` | 31 則故事（`stories.md` 以 `^### US\d+\.\d+` 實算確認為 31）全數映射、無孤兒、無缺口 |
| `bun .claude/tools/aidlc-sensor-upstream-coverage.ts` | `{"pass":true,"unreferenced":[],"findings_count":0}` | `components`／`decisions`／`requirements`／`stories` 四項上游在本站四份產出的聯集中皆被引用 |
| 元件→單元邊映射核對（解析 `components.md` Part A ＋ A' ＋ A'' 的全部 `depends_on`/`dependents`，映射到單元後逐條比對 `unit-of-work-dependency.md` 的 yaml） | `BrainGateway`／`IntentRouter`／`SessionContext`／`WorkOrchestrator`／`MemoryStore`／`ProjectHierarchy`／`ProjectMembership`／`RequirementRegistry`／`McpBridge`／`ProgressChannel` 十個元件的每一條依賴邊，映射到對應單元後**全部**在單元 yaml 的 `depends_on` 中找到對應項，無缺邊、無發明邊 | 契約端點的依賴面（attack #2 的主軸）通過；domain-design 審查 R-01/R-02 修過的對稱性問題在本站的映射上沒有復發 |
| 引用核對：`agent_router.py:125`、`wa_collab_orchestrator.py:79`、`design_agent.py:31/32/169/174/198/160/163`、`user_router.py:673`、`openapi.json` 的 operation/status 分佈、`rbac_seed_data.py` 的角色與 story id 數 | 全部逐行以 `grep -n` 或 Python 解析核對，**行號與內容逐一相符**：`openapi.json` 實算 42 paths／55 operations／`{200:53,422:45,201:1,204:1}`；`rbac_seed_data.py` 實算 11 角色、28 現行 story id（11×28=308，與 baseline 相符；11×30=330、11×32=352 的算式亦相符） | 本站對「引用要分開驗事實與驗定位」這條自我施加的規則確實落實，第 5 項攻擊面（repo 事實核對）沒有找到反例 |

### Summary

核心問題只有一個，但它是結構性的：本站兩份機讀＋人讀產出對**全部 24 個單元**使用的 `construction/u<N>-<name>/` 目錄命名法，與引擎實際行為（`aidlc-swarm.ts` 用裸單元名為鍵）及磁碟上已交付四個單元的真實目錄（`construction/brain-infra/` 等，無編號前綴）不符——而本站自己在修訂 4 開頭的理由段落，逐字描述的正是「磁碟現況以單元名為鍵」這件事，卻沒有讓 Directory 欄遵守它自己剛陳述的事實。這會讓下游（`functional-design`／`code-generation`）依本檔的 Directory 欄去找或建目錄時，對已完成的四個單元產生孤兒目錄，恰好是 `project.md` 已記過的失敗模式（`reverse-engineering:260822-re-c3`）在這裡以另一種形狀重演。除此之外，DAG 拓樸的七項聲稱數字（24 單元／46 邊／5 可平行根／7 層／146 獨立對／kind 分佈）經腳本重算全部精確相符；domain-design 的三個 YAML 區塊映射到單元 DAG 後逐邊比對無缺邊無發明邊；traceability 與 upstream-coverage 兩個 sensor 都乾淨通過；本輪新引用的十餘處程式碼行號與內容逐一核對無誤；`[UG:G8]`=C 的 K3/K4 與 352 列算式經 `rbac_seed_data.py` 實測角色數驗證成立；九項指派逐一有處置、交接事項的轉移目標在 stage-graph 中存在且在游標之後。findings 計數：Critical 1、Major 0、Minor 0。建議：僅需修正 Directory 欄這一處系統性筆誤（機械替換即可，不涉及單元切分或依賴圖的重新設計），其餘設計與拓樸內容扎實，不需要另一輪 advisory 審查即可修復。
