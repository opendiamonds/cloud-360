# Code Generation 問題檔 — `U3 rbac-story-ids`

> Stage：`code-generation`（3.5）　Unit：`U3 rbac-story-ids`（`spec`，S）
> 建立時間：2026-10-04
>
> 本站只有一個關卡：**Plan Approval**。它涵蓋三份內容——
> `code-generation-plan.md`、其中逐字貼入的 Testing Contract、
> 以及 `unit-test-instructions.md`。

---

## Plan Approval

**核可範圍**：

| 檔 | 內容 |
|---|---|
| `code-generation-plan.md` | 12 個實作步驟、六個刻意省略的基準步驟及其理由、故事↔步驟追溯、ADR-0006 四面向落點、八項突變 |
| 其中的 Testing Contract | methodology `test-after`、strategy `standard`、`contract_sha256: sha256:1f0b6822601f52ff3e71a9bd20a949c9e106f87999f78c986398d5e1963f2f77` |
| `unit-test-instructions.md` | 一支新測試檔、7 個測試、8 項突變驗證、精確的 unit-scoped 指令 |

**實際會改動的六個檔**（計畫 §〇 與 §一）：

1. `backend/services/rbac_seed_data.py` — 新增 44 列
2. `schema_rbac.sql` — seed 區塊加 44 列 ＋ 檔頭第 12 行的數字
3. `DEPLOY.md` — 五處「308」（後兩處在英文段落內）
4. `backend/services/user_router.py` — `STORY_FEATURE_LABELS` 補四個鍵
5. **`backend/services/rbac.py`** — log 擴充（`SEC-4`，2 行以內）
6. `backend/tests/test_rbac_story_ids_seed.py` — 新檔，7 個測試

**核可時請一併知道這三件事**：

- **第 5 項比上游原始的「只改 seed 資料」寬**。它是 `nfr-requirements` `[Q2]`=A
  的後果：`H-3`（seed 寫入只記列數、不記哪些列）在 `functional-design` 被記為
  「無自然承接站」，而 `nfr-requirements` 判定本站就是 NFR 的落點，故把它收為
  `SEC-4`。改動量在 2 行以內，但它確實碰了既有共用函式。
- **`schema_rbac.sql` 第 761 行是陷阱，不是第二處要改的數字**。它**現在就寫
  `-- 352`** 而該檔區塊實算為 **308**，屬 `6f9227d`（2026-08-23）的既存漂移。
  本單元加完 44 列後它會**碰巧變成正確**——計畫 Step 7c 明文要求不得去找一個
  不存在的「308」。
- **`team.md` 的 A 規則（授權矩陣變更需 allow/deny 雙向測試）本單元只能做一半**。
  本單元**就是** `role_permissions` 的 seed 變更，但 allow/deny 雙向需要端點，
  而本單元零端點。交付的是授權**資料**的結構前提（測試 2–5）；
  allow/deny 雙向已具名交接 `U19`（`U3-A1`–`U3-A3`）。
  **這是真實的覆蓋缺口，不是豁免**，已寫進 `unit-test-instructions.md §四`。

**跨單元的未決項**（不在本計畫範圍，但核可後仍然存在）：
`H-10`（story map 沒把 `US11`／`US12` 任何一則指給 `U3`）、
`H-8`（`BR7.1`–`BR7.3` 的拒絕事件稽核）、
`RR-1`（`/roles/catalog` 的 DoS 面，承接站 `observability-setup`）、
`RR-2`（`project.md`／`CLAUDE.md` 引用不存在的 `deploy/nginx.conf`）。

[Approval Fingerprint]: sha256:v3:95ebef4545630248e65ba979eb4ac50e05b8037308c33508d6928ab9f1bf75ac
[Planned Source]: 8bb243309b8206a78eb65a3802b0a39b9874ba00eb78a6e87b43d36448938397

- "Approve Plan" — proceed to code generation
- "Request Changes" — revise the plan

[Answer]: Approve Plan
