# Code Summary — `U3 rbac-story-ids`（`spec`，S）

<!-- Stage: code-generation（Construction 3.5）· Unit: rbac-story-ids · kind: spec -->
<!-- Testing Contract: methodology=test-after, strategy=standard,
     contract_sha256=sha256:1f0b6822601f52ff3e71a9bd20a949c9e106f87999f78c986398d5e1963f2f77 -->

## 一、交付結果

`role_permissions` 預設矩陣由 **308** 列增為 **352** 列（11 角色 × 32 story id），
新增 `K1`／`K2`／`K3`／`K4` 四個 story id 的 44 列 seed 語意；
`ensure_missing_role_permissions` 的 log 擴充為記錄被插入的 `(role, story_id)` 配對
（`SEC-4`）；兩份 seed 副本的逐列等值由新測試鎖住（`SEC-5`）。

零端點、零畫面、零容器、零環境變數、零新依賴（`backend/requirements.txt` 與
`.github/workflows/ci.yml` 皆未改動，`git diff --numstat` 對兩者為空）。

**十二個步驟全部完成**，其中 Step 6 的「跑綠」因計畫本身的排序缺陷而在 Step 7
之後才成立（見 §五 的 `PD-1`）。

## 二、改動的六支檔

| 檔 | 改動 | 實測 diff |
|---|---|---|
| `backend/services/rbac_seed_data.py` | `DEFAULT_ROLE_PERMISSIONS` 末端插入 44 列（`K1`→`K2`→`K3`→`K4`，角色序沿用 `CANONICAL_ROLES`） | `+44 −0` |
| `backend/services/rbac.py` | `ensure_missing_role_permissions` 的 `inserted` 計數改為 `inserted_pairs: List[str]`，log 擴充為一行彙總含 `role/story_id` 配對；層級維持 `INFO`；docstring 補 `SEC-4` 的理由 | `+15 −5` |
| `backend/services/user_router.py` | `STORY_FEATURE_LABELS` 新增 `K1`–`K4` 四個鍵，附註明其經公開 `/roles/catalog` 揭露的既定後果 | `+9 −0` |
| `schema_rbac.sql` | `INSERT INTO role_permissions` 區塊加同樣 44 列（原最後一列補結尾逗號）；檔頭第 12 行「預設矩陣（308 列）」→ 352 | `+46 −2` |
| `DEPLOY.md` | 五處列數（`:577`、`:591`、`:596` 中文段；`:1259`、`:1270` 英文段）308 → 352 | `+5 −5` |
| `backend/tests/test_rbac_story_ids_seed.py` | **新檔**，7 個測試案例 | 新增 |

**本單元沒有碰計畫六支清單以外的任何檔**。工作樹中另有其他單元的既存改動
（`agent_router.py`／`design_agent.py`／`wa_collab_orchestrator.py`／`test_agent.py`／
`progress_channel.py` 等），與本單元無關，未被動到——上表的 `numstat` 是逐檔驗證的結果。

### 44 列不是手抄的

表格逐列轉錄自 `functional-spec.md §一′`，再由
`scratchpad/gen_rows.py` 以 `v`／`e`／`r` 字元展開成 Python 與 SQL 兩種形式，
**兩份副本出自同一支產生器**（這是它們一開始就等值的原因，不是事後對出來的）。
產生器自己斷言角色序等於 `CANONICAL_ROLES`，並印出各欄實算：

```
K1: view=8 edit=0 allfalse=3
K2: view=11 edit=4 allfalse=0
K3: view=8 edit=4 allfalse=3
K4: view=8 edit=4 allfalse=3
```

四行與 `functional-spec.md §一′` 的腳本輸出**逐字相同**。

### 11 項不變量施工後複算（全部 PASS）

```
len=352  roles=11  sids=32  dupes=[]  missing=[]  complete(11×32)=True
K3.edit 持有者 = ['Platform_Admin','Project_Admin','Project_Architect','Project_Editor']
K2.edit 持有者 = ['Platform_Admin','Project_Admin','Project_Architect','Project_Editor']
BR5.4（K2.edit ⊆ K3.edit）= True
完全不持有 K3 = ['Ops_Lead','Platform_Engineer','SRE']，三者皆持有 A1 view = True
完全不持有 K4 = ['Ops_Lead','Platform_Engineer','SRE']
BR1.3（有 A1 view 無 K1）= ['Ops_Lead','Platform_Engineer','SRE']
不具 K2.edit 的角色數（AC9.2.3 可構造）= 7
K1–K4 的 can_review 全為 false = True
新 id 與既有 28 個無重複 = True（sids 由 28 增為 32）
```

## 三、七個測試與全套前後比對

**單元指令**：`cd backend && python -m unittest tests.test_rbac_story_ids_seed -v` → `Ran 7 tests … OK`
**全套指令**：`cd backend && python -m unittest discover -s tests -v`

| | 測試數 | 結果 |
|---|---|---|
| 施工前（基準） | **432** | `OK`（零失敗） |
| 施工後 | **439** | `OK`（零失敗） |
| 差 | **+7** | 等於本單元新增的 7 個案例，**既有項零失敗** |

`11c` 特別確認的兩支：`python -m unittest tests.test_rbac tests.test_collab`
→ `Ran 26 tests … OK`。

| # | 測試 | 承載 |
|---|---|---|
| 1 | `test_the_matrix_has_exactly_352_rows_and_no_missing_combination` | `U3-V4`、`BR3.4`′ |
| 2 | `test_a_role_with_a1_view_does_not_hold_k3` | `U3-V1`、`BR5.3` |
| 3 | `test_at_least_one_role_does_not_hold_k4` | `U3-V2`、`BR6.5` |
| 4 | `test_every_k2_editor_also_holds_k3_edit` | `U3-V3`、`BR5.4` |
| 5 | `test_the_four_new_story_ids_never_grant_review` | `U3-V5`、`EC-4` |
| 6 | `test_the_seed_write_logs_which_rows_it_inserted` | `SEC-4`、`D-7` |
| 7 | `test_the_sql_seed_block_matches_the_python_default_row_for_row` | `SEC-5`、`BR4.4`′、`D-5` |

七個都在**一支檔**（`D-10`）。另通過的閘門：`dump_openapi.py --check`
（「規格檔與後端程式碼一致」——證明端點集合未變，`SEC-1`／`SEC-3`）、
`validate_repo_contract.py`、`validate_env_contract.py`。

## 四、八項突變驗證（逐項 mutate → grep → run → restore → re-verify）

每一項突變都先 `grep` 確認檔案真的變了才跑測試
（`test-case-authoring.md §5` 記過一次突變沒生效而被誤讀為「測試沒抓到」）。
還原後以 `shasum` 對照施工完成時的快照，`rbac_seed_data.py` 與 `rbac.py`
兩支皆 **IDENTICAL**。

| # | 突變內容 | 計畫指定必須紅的測試 | 結果 |
|---|---|---|---|
| `M1` | 刪掉 `('Platform_Owner','K4',True,False,False)` 一列 | 測試 1（長度） | **紅 ✓**（另 4 個測試一併紅） |
| `M2` | `('Platform_Owner','K4',…)` 的 `story_id` 改成 `'K3'` | 測試 1（**組合**） | **紅 ✓**，長度斷言未觸發 |
| `M3` | `SRE` 的 `K3` 改為 `(True,False,False)` | 測試 2 | **綠 ✗ —— 計畫缺陷，見 `PD-2`** |
| `M3-eff` | **三個**不持有 `K3` 的角色全部改為 `(True,False,False)` | 測試 2 | **紅 ✓** |
| `M4` | `SRE` 的 `K4` 改為 `(True,False,False)` | 測試 3 | **綠 ✗ —— 同 `PD-2`** |
| `M4-eff` | **三個**不持有 `K4` 的角色全部改為 `(True,False,False)` | 測試 3 | **紅 ✓** |
| `M5` | `Project_Architect` 的 `K3` 改為 `(True,False,False)` | 測試 4 | **紅 ✓** |
| `M6` | `('Developer','K3',…)` 的 `can_review` 改為 `True` | 測試 5 | **紅 ✓** |
| `M7` | `rbac.py` 的 log 改回只記列數 | 測試 6 | **紅 ✓**（僅測試 6，隔離乾淨） |
| `M8` | **只**改 Python 的 `('Platform_Admin','K4')` 的 `can_edit` → `False`，不動 SQL | 測試 7（**第三段**） | **紅 ✓** |

### 紅燈訊息逐項

`M1` → 測試 1：
```
預設矩陣應為 352 列（11 角色 × 32 story id），實為 351 列。BR3.4′ 的總數約束被
破壞——少列代表某個 (角色, 能力) 組合在權限頁是破洞，而 user_can 對缺列回
false，現象是「那個角色沒有那個權限」而不是一個可辨識的錯誤。
```

`M2` → 測試 1（**長度斷言通過、組合斷言紅**，這正是 `D-11` 要求兩個突變的理由）：
```
預設矩陣的 (角色, story_id) 組合不完整——BR3.4′ 的組合約束被破壞。
  重複的組合（1）：[('Platform_Owner', 'K3')]
  缺漏的組合（1）：[('Platform_Owner', 'K4')]
  預期外的組合（0）：[]
總數可能仍然正確——這正是本子斷言不能併入長度斷言的理由。
```

`M3-eff` → 測試 2：
```
沒有任何角色同時「持有 A1 view」且「完全不持有 K3」——BR5.3 的可達性保證被破壞。
後果：AC12.5.1（邀請缺權限者被拒且畫面說明他缺少什麼）與 AC12.5.3（拒絕不留
半套狀態）的 Given 不可構造，兩條 AC 成為永遠不會失敗的死碼。
```

`M4-eff` → 測試 3：
```
沒有任何角色完全不持有 K4——BR6.5 的可達性保證被破壞。後果：BR6.4（不持有 K4
者看不到未填欄位計數）成為不可觸發的死碼，而沒有任何測試或畫面會顯示這件事發生了。
```

`M5` → 測試 4：
```
下列角色持有 K2.edit 卻不持有 K3.edit：['Project_Architect']——BR5.4 被破壞。
後果：AC12.1.2 逐字「Given 我剛建立一個專案，When 我嘗試邀請成員，Then 該動作
可用——不需任何額外授權步驟」直接失敗。現象是「我建的專案，我管不動」。
```

`M6` → 測試 5：
```
下列 K1–K4 的列把 can_review 設為 true：[('Developer', 'K3')]——EC-4 被破壞。
```

`M7` → 測試 6（**只有這一個測試紅**）：
```
'K1' not found in 'INFO:cloud360.rbac:ensure_missing_role_permissions: inserted 44 rows'
: seed 寫入的日誌沒有提到 'K1'——SEC-4 被破壞。
```

`M8` → 測試 7，**第三段確實觸發**，且 `(key, python, sql)` 三元組指出是哪一個旗標：
```
SQL 側 352 列（1 個 INSERT 區塊錨點）、Python 側 352 列。
  [只在 SQL] 1 列（Python 那份漏加）：('Platform_Admin','K4',True,True,False)
  [只在 Python] 1 列（SQL 那份漏加）：('Platform_Admin','K4',True,False,False)
  [兩邊都有但旗標不同（(role, story_id), python, sql）] 1 列（值不同——最危險的那一類）：
    (('Platform_Admin','K4'), (True,False,False), (True,True,False))
```

**兩側列數都是 352**——一支只比列數與 story id 集合的測試會在此放行。
這就是 `[Q2]` 選項 C 被否決的實證，也是第三段不可省的證明。

## 五、計畫缺陷（三項，**都沒有以變通繞過**）

### `PD-1`（Step 6e 不可能成立）— 排序缺陷

計畫 Step 6e 要求 `SEC-5` 的等值測試「跑綠」，而 SQL 側的 44 列到 **Step 7a**
才加入。在 Step 6 的時點 Python 側 352、SQL 側 308，該測試**必然紅**。

**處置**：照順序寫出並執行 Step 6 的測試，如實記錄其紅燈（下方逐字），
再執行 Step 7，而後複跑取得綠燈。**沒有放寬測試、沒有調換步驟定義。**
附帶收穫：這次紅燈是第二段（「只在 Python」）的免費突變驗證——

```
SQL 側 308 列（1 個 INSERT 區塊錨點）、Python 側 352 列。
  [只在 SQL] 0 列（Python 那份漏加）：無
  [只在 Python] 44 列（SQL 那份漏加）：
    ('Developer','K1',True,False,False) … 另有 34 列未列出
  [兩邊都有但旗標不同…] 0 列
```

**修法建議**：Step 6 與 Step 7 對調，或把 Step 6e 改寫為「寫出測試並記錄其紅燈；
綠燈於 Step 7 之後複驗」。

### `PD-2`（`M3`／`M4` 如字面執行無法讓目標測試變紅）— 突變設計缺陷

`BR5.3` 的 `logic` 逐字是「**IF 存在 role** 使得 …」，`BR6.5` 同形；
而 `BR5.1`／`BR6.1` 的當前值使 **三個**角色（`SRE`／`Ops_Lead`／`Platform_Engineer`）
同時符合。只改 `SRE` 一個，另兩個仍滿足存在量化 → 測試 2／3 保持綠。

這**不是測試寫錯**：測試實作的正是 `U3-V1`／`U3-V2` 與 `BR5.3`／`BR6.5` 指定的
存在量化斷言。缺陷在突變的粒度——`nfr-design` 的 `D-10` 表格與
`unit-test-instructions.md §三` 都把它寫成單一角色。

**處置**：兩項都先照字面執行並如實記錄其為綠（`M3`／`M4`），再執行最小有效突變
（`M3-eff`／`M4-eff`：三個角色全改）證明斷言非恆真。**沒有為了讓 `M3` 變紅而把
測試改寫成「不持有 `K3` 的角色集合恰為那三個」**——那會把一條可達性保證
過度釘死成預設值快照，日後任何合法調整都會紅燈，等於用一個新缺陷換一個綠勾。

兩條測試的 docstring 已就地註明其為存在量化、單一角色突變不足以讓它紅。

**修法建議**：`D-10` 與測試指示的 `M3`／`M4` 欄改為「把**全部**符合該可達性保證
的角色一併改掉」。

### `PD-3`（`M3`／`M4`／`M5`／`M6` 必然連帶讓測試 7 紅）— 可預期的交互作用，非錯誤

任何只改 Python 一側的突變都會同時破壞 `SEC-5` 的等值性。計畫未提及這點。
不影響任何結論（目標測試仍各自獨立判定），記此以免下一輪把多個紅燈讀成
「突變設計不精準」。`M7` 與 `M8` 無此交互作用。

## 六、ADR-0006 四面向（實作層落點）

| 面向 | 判定 | 本單元的實作落點 |
|---|---|---|
| **IAM** | **適用（核心）** | 44 列預設值（`rbac_seed_data.py` ＋ `schema_rbac.sql`）；最小權限的具體落點是 `K1`／`K3`／`K4` 皆不給三個純唯讀維運角色、`edit` 只給四個建立者角色；三條可達性／蘊含保證由測試 2–4 鎖住並經突變驗證（`M3-eff`／`M4-eff`／`M5`）；完整性由測試 7 鎖住（`M8`） |
| **Encryption** | **不適用** | 不新增欄位、不儲存機密值；44 列僅為布林旗標與角色名 |
| **Network exposure** | **適用（一處）** | `STORY_FEATURE_LABELS` 的四個中文標籤經 `user_router.py` 的**公開** `/roles/catalog`（無 `Depends(get_current_user)`）對未驗證訪客可讀。**照 `BR4.5` 的既定處置發布、不加入 `CATALOG_EXCLUDED_STORIES`**，並在程式註解就地寫明這是已接受的揭露而非缺陷。`RR-1`（該端點的 DoS 面）承接站為 `observability-setup`（`D-16`），本單元不宣稱已處置 |
| **Audit logging** | **適用（部分）** | log 擴充（`rbac.py`）＋ 測試 6 的 `assertLogs` 斷言 ＋ `M7` 突變。log 只寫 `role/story_id`，**不含任何使用者身分**。**仍未處置**：`BR7.1`–`BR7.3` 的拒絕事件稽核由 `H-8` 指派 `U19` |

**PBT hard constraint 判定 N/A（非豁免）**：`rules.md` 修訂 1 實算 `calculation`
類規則為 0；七個案例全部是對固定資料集合的斷言，無值域可探索。`BR7.4` 點名的
挑選純函式（真正的 PBT 標的，性質為排列不變性）是 `U19` 的交付物，
已由 `U3-A3` 具名交接，**不讓它在兩個單元之間掉落**。

## 七、已具名交接、本單元刻意不做的事

| ID | 事項 | 承接 |
|---|---|---|
| `U3-A1` | 邀請一般成員的 allow/deny 雙向（`K3.view`） | `U19` |
| `U3-A2` | 邀請／改為專案管理者的 allow/deny 雙向（`K3.edit`） | `U19` |
| `U3-A3` | 自動改選的候選集合過濾 ＋ 挑選純函式的 PBT（排列不變性） | `U19` |
| `H-8` | `BR7.1`–`BR7.3` 的**拒絕**事件稽核 | `U19` |
| `H-9` | 三個維運角色的 `K2.view` 是否為死資料 | `U7` |
| `H-10` | `unit-of-work-story-map.md` 未把 `US11`／`US12` 指給 `U3` | 本站（`code-generation`）——**見下** |
| `H-11` | `BR7.3` 窄化了 `AC12.4.1`，待收斂 AC 原文 | 本站——**見下** |
| `RR-1` | 公開 `/roles/catalog` 的 DoS 面 | `observability-setup` |
| `RR-3` | 兩份 seed 副本本身不消除（產生腳本不存在） | 未指派，`BR4.1`′ 已記載 |

`H-10` 與 `H-11` 的承接站都是 `code-generation`（本站），而兩者都是**上游文件的
文字缺口**，不是程式缺口：

- `H-10`：`unit-of-work-story-map.md` 只把 `US1.4`／`US9.2` 指給 `U3`，故本檔的
  `traceability.json` 的 `upstream_ids` 只能列那兩群的 7 條 AC。`BR5`–`BR7` 實際
  支撐的 `AC12.*`／`AC11.*` 全部掛在別的單元。**本站不自行改已核可的 story map**，
  在此重申該缺口仍然存在。
- `H-11`：`AC12.4.1` 逐字「被選中者為該專案**最早加入**的成員」無資格限定，
  而 `BR7.3` 窄化為「最早加入**且**持有全域 `K3.edit`」。**窄化本身正確且不改**
  （不窄化會讓被選中者成為管理者後每個動作 403）；要收斂的是 AC 原文，
  而本站不回改 `stories.md`。`Developer`／`FinOps_Analyst`／`Security_Reviewer`／
  `Platform_Owner` 四個角色持有 `K3.view` 而無 `K3.edit`（施工後複算確認仍為這 4 個），
  即該窄化的實際影響範圍。

另外，`schema_rbac.sql` 的驗證註解（施工前第 **761** 行、施工後位移至第 **805** 行）
**全程未被編輯**：它本來就寫 `-- 352`，而該檔區塊實算為 308，屬 `6f9227d` 的既存
漂移（`RR-4`）；本單元加完 44 列後它**碰巧變成正確**。腳本對它只做斷言不做替換，
`git diff` 對該行為空可證。這一行的正確性是本單元的副作用，不是任何人修過它。


## 八、刻意未改動的檔與位置（由 `source-manifest.json` 搬入）

`source-manifest.json` 的 schema 是**嚴格**的（`stage`／`unit`／`version`／`writes`
四個鍵），而實作 agent 另外寫了一個 `unchanged_by_design` 清單——那份資訊有價值，
但放在 manifest 裡會讓它不符 schema。**由 orchestrator 搬到這裡**，manifest 收斂為
嚴格形狀（`creates` 的唯一項已含於 `writes`，`deletes` 為空）。

| 路徑／位置 | 為什麼刻意不動 |
|---|---|
| `backend/requirements.txt` | 零新依賴（SEC-2）；ast／re／unittest／collections 皆標準庫 |
| `.github/workflows/ci.yml` | 新測試檔由既有 python -m unittest discover -s tests 自動撿到，不需 CI 設定變更 |
| `backend/services/rbac_seed_data.py:existing_308_rows` | 不修改既有 308 列中的任何一列 |
| `schema_rbac.sql:verification_comment` | 該行本來就寫 -- 352（6f9227d 的既存漂移 RR-4），本單元加完 44 列後碰巧變成正確；全程未編輯，git diff 對該行為空 |
| `backend/services/user_router.py:CATALOG_EXCLUDED_STORIES` | BR4.5 定案：K1–K4 照 J3a／J3b 的既有先例發布，刻意不加入排除集合 |
| `backend/database.py` | D-9：不收斂呼叫端另外記的那次裸列數——動它超出 [Q2]=A 的範圍 |

## 九、`traceability.json` 的兩處結構修正（orchestrator 施作）

實作 agent 的 `traceability.json` 有兩處不符 `traceability` sensor 的 schema，
已於審查請求**之前**修正，兩項都不改任何覆蓋主張：

| # | 問題 | 修正 |
|---|---|---|
| 1 | **62 個 `OK` 列的 `target` 寫成散文**，而 stage 檔逐字要求「Every `OK` target must be one existing workspace-relative implementation or test file」。sensor 回報 65 項 `invalid_targets`。 | `target` 改為該列的裸路徑（由散文中擷取並逐一驗證檔案存在），**原散文完整保留於新增的 `note` 欄**——覆蓋主張與理由一字未減。 |
| 2 | **`reverse` 寫成 `{artifact, ids}` 的索引形狀**，而 schema 要的是 `{id, status, target}`；另有 `PD-1`／`PD-2`／`PD-3` 三列放在 `coverage` 但不在 `upstream_ids` 內。 | `reverse` 改為 schema 形狀並只留三個計畫缺陷列；原索引保留於非 schema 鍵 `artifact_index`。另有 7 列的 `status` 使用封閉集合之外的值（`Accepted`／`OK（副作用）`／`Unresolved`／`Reported`），已逐列更正並在 `target` 內就地註明原值。 |

修正後 `traceability` sensor：**`pass: true`、0 findings**（修正前 65 項）。
