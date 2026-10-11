# Code Summary — `U6 embedding-port`（`library`）

## 〇、一句話

本單元交付 `EmbeddingPort` 契約（`K-06`）與三個實作（`ollama`／`fastembed`／`stub`）
加一個停用狀態（`fulltext`），設定錯誤一律在啟動大聲失敗、不靜默降級為全文檢索
（ADR-008），並把它的四個設定變數同步到三個環境與一道新的 CI 閘門。

**`backend/requirements.txt` 淨變更為零**——`httpx` 與 `hypothesis` 皆為既有依賴，
`fastembed` 刻意不列入（選用依賴，lazy import）。

## 一、改了什麼（10 個檔）

| 檔 | 改動 |
|---|---|
| `backend/services/embedding_port.py` | **新**。Port 介面 ＋ `resolve_provider_selection` ＋ `resolve_embedding_port` ＋ `configure_embedding_env` ＋ 三個 Adapter ＋ `EmbeddingProviderUnavailable`。模組層只 import 標準庫 |
| `backend/tests/test_embedding_port.py` | **新**。19 個測試（7 個 `@given` property） |
| `backend/main.py` | `:15` import `configure_embedding_env`；`:53-57` 於 `on_startup()` 內、`configure_provider_env()` 與 `init_db()` 之間呼叫（`D-1`） |
| `backend/.env.example` | 新增 `EMBEDDING_TIMEOUT_SEC`；`OLLAMA_BASE_URL` 由 `localhost` 改為服務名並寫明本機不可用 |
| `deploy/.env.example` | 新增 `EMBEDDING_TIMEOUT_SEC` |
| `deploy/render-env.sh` | heredoc 加寫 `EMBEDDING_TIMEOUT_SEC=10` |
| `deploy/docker-compose.deploy.yml` | `backend.environment:` 以**無 fallback** 形式傳入 `EMBEDDING_TIMEOUT_SEC` |
| `scripts/validate_embedding_provider_value.py` | **新**。`H-I3`：**import** 本單元的允許值集合與驗證函式，不自行列舉 |
| `.github/workflows/ci.yml` | `repo-contract` job 新增一個 step 跑上述驗證器 |
| `LOCAL-DEV.md` | 硬依賴表、第 1 節前置檢查、第 3 節 `.env`、常見卡關 ＋2 列 |

**與 `U1 brain-infra` 的檔案重疊**：`backend/.env.example`、`deploy/.env.example`、
`deploy/render-env.sh`、`deploy/docker-compose.deploy.yml`、`.github/workflows/ci.yml`、
`LOCAL-DEV.md` 六個檔同時出現在兩個單元的 `source-manifest.json`。這是真實重疊
而非誤列：`brain-infra` 建立了 embedding 的四個變數在三個環境的承載，本單元加上
第五個變數與值的合法性檢查。

## 二、驗證結果（全部由 conductor 實跑，非自報轉引）

| 命令 | 結果 |
|---|---|
| `python3 -m unittest tests.test_embedding_port` | **30 tests OK**（審查 iteration 1 後由 19 增為 30） |
| `python3 -m unittest discover -s tests`（全套） | **469 tests OK**（基線 **439** ＋ 本單元 **30**） |
| `python3 scripts/validate_repo_contract.py` | passed |
| `python3 scripts/validate_env_contract.py` | passed |
| `python3 scripts/validate_embedding_provider_value.py` | passed（3 份設定來源） |
| `python3 scripts/validate_cost_calculator_boundary.py` | passed |
| `python3 scripts/validate_pricing_lookup_boundary.py` | passed |
| `bash -n deploy/render-env.sh` | ok |
| `ci.yml`／兩份 compose 的 YAML 解析 | 三者皆 ok |

**基線的交叉驗證**：439 這個數字由兩個獨立量測取得——派工 agent 在改動前跑出
439 OK，conductor 在本輪開始時獨立重跑也是 439 OK。

## 三、九項突變驗證（交付條件）

全部走 `改錯 → 跑測試 → 確認紅燈 → 還原 → 複驗綠燈`，且**每一項都在改檔後
以行為探測確認輸出真的變了**，不只確認檔案變了。

| # | 突變 | 結果 | 抓到它的測試 |
|---|---|---|---|
| `M1` | `StubAdapter` 對所有輸入回同一向量 | **RED** | `test_different_inputs_get_different_vectors` |
| `M2` | `_stub_vector` 回傳 1023 維 | **RED** | 7 個測試，含 `test_every_vector_is_exactly_1024_dimensions` |
| `M3` | `embed` 回傳的 list 少一個元素 | **RED** | 7 個測試，含 `test_embed_returns_one_vector_per_input` |
| `M4` | 分批與單筆走不同路徑 | **RED** | `test_batching_does_not_change_the_vector`、`test_embed_returns_one_vector_per_input` |
| `M5` | 移除 `localhost` 主機名檢查 | **RED** | `test_startup_validation_rejects_non_internal_ollama_host` |
| `M6` | timeout 改為無限 | **RED**，但**只由原始碼文字斷言攔下** | `test_default_timeout_is_a_named_constant`（見下方更正） |
| `M7` | 例外不剝除 `userinfo` | **RED**（第二輪） | `test_exception_constructor_strips_userinfo_from_target_and_detail` |
| `M8` | 截斷改為拋例外 | **RED** | `test_oversized_input_is_truncated_with_a_warning` |
| `M9` | `stub` 的 `model_id` 改回 `bge-m3` | **RED** | `test_model_id_set_matches_the_allowed_value_set_both_ways` |

### 第一輪有兩項存活，兩者原因不同——如實記載

**`M2` 第一輪存活，是突變本身無效，不是測試不足。** 第一版把
`while len(values) < EMBEDDING_DIMENSIONS:` 改為 `- 1`，但 `_stub_vector` 的
**內層 `for` 有自己的 `if len(values) >= EMBEDDING_DIMENSIONS: break`**，所以最後
一個區塊照樣把長度填到 1024——檔案變了，行為沒變。改為 `return values[:-1]` 後
行為探測回 `dims 1023`，7 個測試隨即轉紅。**教訓**：突變驗證的前置確認必須做到
行為層，只 `grep` 檔案內容會把無效突變誤讀成「測試沒抓到」。本輪已把行為探測
加進突變腳本。

**`M7` 第一輪存活，是真實的測試缺口。** 原測試
（`test_exception_message_strips_userinfo`）走 `OllamaAdapter._target()`，而它用
`urlsplit().hostname` 取主機名——**那條路徑自己就會丟掉 userinfo**，與
`_without_userinfo` 無關。所以把 `_without_userinfo` 從例外建構子整個拿掉，
原測試仍然全綠。

連帶發現：模組原 docstring 逐字宣稱 `_without_userinfo` 是「**唯一的剝除點**……
它失效就是 `SEC-2` 整條失效」，**此宣稱為誤**。已就地更正並新增第 19 個測試直接打
`_without_userinfo`，`M7` 隨即轉紅。

**但那次更正本身也錯了，由審查 `R-04` 推翻（見 §九）。** 我第一次改成「兩個**各自
獨立**的剝除點」——錯的方式更隱蔽：兩者其實是在 `target` 這一個欄位上**串聯**。
`detail` 只經過一層（`_without_userinfo`）；`target` 經過兩層（`_host_and_port`
先縮到 `scheme://host:port`，例外建構子再呼叫 `_without_userinfo` 當後備）。審查讓
`_host_and_port` 改用 `netloc` 保留 userinfo，19 個測試**全綠**（`MUT-F`），正因為
外層默默補上了。同一段敘述連錯兩次，所以第三版在 docstring 裡逐字寫出兩層的次序與
各自的測試，並新增 `test_host_and_port_strips_userinfo` 補上內層的覆蓋。

## 四、偏離計畫之處（逐項附理由）

1. **測試數由 16 增為 19。** 第 17 個是下述 Major 缺陷的回歸測試；第 18 個
   （`test_default_timeout_is_a_named_constant`）承載 `D-6` 的「模組內不得出現裸數字
   timeout」，它同時是 `M6` 唯一的攔截點；第 19 個是 `M7` 的真正標的（見 §三）。
   `standard` 策略的 5–8 區間本已被計畫以 `combination_rule` 的明文允許超出。
2. **模組新增一段啟動驗證，超出原計畫的十項交付。** 見 §五的 Major 缺陷。
3. **`backend/.env.example` 的 `OLLAMA_BASE_URL` 由 `http://localhost:11434` 改為
   `http://ollama:11434`。** 這是使用者裁決的 `NFR7.1` 處置（改文件、不改約束），
   同步落在 `LOCAL-DEV.md`。原值會讓照範本設定的開發者在選 `ollama` 時啟動失敗。
4. **測試檔新增一個只在 `AIDLC_MUTATION_RUN=1` 生效的 hypothesis profile**
   （關閉 shrink）。理由是實測的：`M4` 讓多個 property 同時失敗，hypothesis 縮小
   反例在刻意壞掉的實作上跑到病態——**單一突變燒掉 10 分 51 秒的 100% CPU 仍未
   結束**。正常執行與 CI 完全不受影響（已分別驗證兩種模式皆 19 tests OK）。

## 五、本輪查出並修掉的缺陷（conductor 稽核 landed 模組，非派工方自報）

**Major — `MEMORY_RECORD_EMBEDDING_MODELS` 是個從未被讀取的常數，而它代表的
不變量可被設定繞過。** `:87` 宣告記憶列合法的 `embeddingModel` 集合為三個字面值，
但 `OLLAMA_EMBED_MODEL`／`FASTEMBED_MODEL` 可被設成任意非空字串、`model_id()`
原樣回傳，且 `configure_embedding_env` 只驗提供者與 endpoint、**不驗 model_id**；
全模組對該常數的引用只有 `__all__` 一處。後果：在 `deploy/.env` 設
`OLLAMA_EMBED_MODEL=bge-large`，記憶列就會被蓋上宣告集合外的 `embeddingModel`，
而「只比對同一 `embeddingModel` 的列」那道過濾會把兩個不同向量空間判定為可比較
——正是 ADR-008 要防的污染，最早只會在 `U8` 寫入時才（或根本不會）被發現。
原計畫的測試 7 也抓不到：`I == S` 是在預設值下求值的。

**處置**：`resolve_provider_selection` 新增一條檢查，resolved `model_id` 不在
`MEMORY_RECORD_EMBEDDING_MODELS` 內即拋 `ValueError`（設定錯誤走啟動失敗，與
`BR1.6` 同類），並新增 `test_model_id_must_be_in_the_declared_set` 回歸測試。
**刻意不共用常數推導宣告集合**：`BR3.3` 的雙向測試需要 I 側與 S 側能各自漂移，
共用來源會讓 `M9` 照樣綠。新的驗證器 `scripts/validate_embedding_provider_value.py`
同時把三份設定來源的值餵進這條路徑，所以這個缺口在 CI 也有閘門。

## 六、本單元**沒有**做到的事（不美化）

1. **`ollama` 與 `fastembed` 的成功路徑在 CI 零覆蓋。** `docker-compose.test.yml:18`
   逐字「NO ollama」，`fastembed` 不在 `requirements.txt`。測不到的具體是
   「它們實際回傳的向量是否真為 1024 維」；它由 `_verify_shape` 在首次真實呼叫時
   攔下——大聲失敗，不是靜默。具名缺口 `OQ-E2`、`cicd-pipeline.md §三`，**不在本站關閉**。
2. **`EMBEDDING_TIMEOUT_SEC` 在 import 時求值**（`:240` 的模組層 `_timeout_from_env()`），
   所以壞值會在 import 期間記一條 WARN。對既有測試無影響（它不拋），但與 `D-1`
   「把 env 讀取留在 startup hook」的理由不完全一致。**未修**：改成 lazy 會動到
   一個已被 `__all__` 導出的模組層常數的語意，屬獨立決定。記為 open item。
3. **`PROVIDER_CONTEXT_LIMIT_CHARS` 的單位是字元不是 token**（`H-N3`）。零新依賴
   即無 tokenizer，取保守的 1 token ≈ 1 字元。若有人為 `ollama` 設一個 context
   更小的 1024 維模型，這個值會偏大——該情形由提供者回錯而成為
   `EmbeddingProviderUnavailable`，不靜默。
4. **覆蓋率未量測。** `team.md` 如實記載本 repo 無覆蓋率機制；本 scope 的
   `scope_floor` 逐字「adds no extra new-test floor」。**不宣稱達成 80%。**
5. **`H-N1`（`embed` 延遲的自動化斷言）未提供。** `D-5` 的 INFO log 讓延遲可由
   日誌事後統計，但**沒有任何 CI 檢查會因為 embed 變慢而紅燈**（`RR-4`）。

## 七、跨單元交接

- **`U8 memory-service`**：`embed` 不重試（`BR2.6`），重試上限由呼叫端決定；
  `fulltext` 時 `resolve_embedding_port` 回 `None`，呼叫端以「有沒有拿到 Port」
  分流而非以例外分流（`D-10`）。寫入記憶列時 `embeddingModel` 必須取
  `model_id()`，且該值現在保證落在 `MEMORY_RECORD_EMBEDDING_MODELS` 內。
- **`U5 memory-data`**：`NULL` 的唯一意義是「該列在 `fulltext` 模式下建立」，
  其向量欄位必須同時為 `NULL`。該不變量的執行落點在 `U5`／`U8`，不在本模組（`H-E1`）。
- **`U1 brain-infra`**：六個檔重疊（見 §一）。本單元新增的 `EMBEDDING_TIMEOUT_SEC`
  已依 `project.md` 的 blocking 規則在 `render-env.sh`、`deploy/.env.example`、
  `docker-compose.deploy.yml` 三處同步。

## 八、引擎層的收據狀態（如實記載）

本站的審查收據預期無法登記，原因與先前數站相同且已查明為結構性：
`workspace_requires: true` 的站，其 `REVIEW_COMPLETED` 綁定 workspace source
fingerprint，而該 fingerprint 把 git-ignored 的 `.hypothesis`／`__pycache__` 也算進去
——審查員必須跑測試，跑測試必然改動那些快取，於是 fingerprint 必然改變。
真的發生時留 `review-NN-unreceipted.md`，不假裝記進去了。

本單元另有一段非常規的歷程，一併記載以免日後誤讀 audit：`UNIT_STARTED` 於
`2026-10-05T01:51:06Z` 記下後，引擎路由前移到 `brain-infra`，使
`plan-approval-guard` 的核可目標變成一個尚未重新核可的單元，進而拒絕**全部**
工作區改動與指令執行（派工 agent 命中 8 次）。該狀態下 `park` 被自主模式拒絕、
autonomy 欄位無 CLI、改該欄位的 `Edit` 也被拒，形成無 agent 側出口的死結。
解法是重新取得 `brain-infra` 的 Plan Approval（內容位元組未變，失效的是引擎綁定），
守衛隨即釋放。本單元隨後 `UNIT_PAUSED`（`04:50:31Z`）→ `UNIT_RESUMED`（`04:51:17Z`）
並在同一個 session 內完成。

## 九、對抗式審查 iteration 1 的六項發現與處置

判定 **NOT-READY**（Critical 1／Major 4／Minor 1）。**六項全部處置完成**，並以突變
複驗每一項修法是否承重。審查收據無法登記，原因與處置見
`reviews/review-01-unreceipted.md`（結構性缺陷 `OPEN-6`，非順序錯誤）。

### 審查找到的那個模式，比任何單一發現都重要

**本單元的風險登錄表自己指名為「緩解措施」的三段程式，正是三段零行為覆蓋的程式**
——而三者在 `traceability.json` 都標 `OK`，其依據都能在該程式被改成 no-op 之後存活：

| 被指名的緩解措施 | 它負責緩解什麼 | 審查的突變 | 結果 |
|---|---|---|---|
| `configure_embedding_env()` | ADR-008 的「偵測不到時大聲失敗」 | 掏空成靜默 fulltext no-op | **458 OK**（`MUT-G`） |
| `_verify_shape()` | `OPEN-1` 的「首次真實呼叫時攔下」 | 兩個分支皆改 `if False` | **19 OK**（`MUT-C`） |
| `_host_and_port()` | `SEC-2` 在 `target` 的剝除 | 改用 `netloc` 保留 userinfo | **19 OK**（`MUT-F`） |

我的九個突變沒有一個碰到這三處——**失敗在突變集合的選擇，不在突變的執行**。
九個都是繞著 business rules 設計的，而這三處是繞著「別的東西的風險」設計的，
所以整批漏掉。這是比 `M2`／`M7` 那兩個更深一層的教訓：**突變集合要涵蓋
「我在文件裡宣稱它會保護某件事」的每一段程式**，而不只是涵蓋每一條規則。

### 逐項

| ID | 嚴重度 | 發現 | 處置 |
|---|---|---|---|
| **R-01** | **Critical** | `configure_embedding_env()` 零測試覆蓋（`grep` 回 0）。掏空成「驗證什麼都不做、永不拋錯、靜默選 fulltext」仍 458 全綠——那正是 ADR-008 逐字禁止的靜默降級。而 `NFR8.2` 原本以「458 tests OK」當驗證：**458-green 證明的是 hook 不弄壞既有測試，不是它會動**。此測試義務原就寫在已核可的 `nfr-design/security-design.md:47`（`D-1`）逐字「驗證本身以直接呼叫該函式的單元測試覆蓋」，本輪才補齊 | 新增四測試（缺值／不合法提供者拋錯、ollama 壞主機拋錯、成功時回 `port_present=True` 並記含四項的 INFO、fulltext 分支記「無 Port」）；更正 `NFR8.2`／`BR1.6`／`BR7.1` 的驗證方式註記。`MUT-G` 現由三個測試攔下 |
| **R-02** | Major | `OPEN-1` 把風險整個託付給 `_verify_shape`，而它可被刪除而全綠：套件裡每條維度斷言都跑在 `StubAdapter` 上（本來就回 1024），guard 從不開火 | 以刻意 misbehaving 的 `EmbeddingPort` 子類新增兩測試（回 1023 維、少回一筆）；重述 `OPEN-1`——其 `named-gap` 嚴重度自此才成立 |
| **R-03** | Major | 我改寫的本機指引在**五處**宣稱實作沒做的事（「本機設不出合法值」／`:485` 的「**拒絕啟動**」）。實測：範本的 `http://ollama:11434` **啟動會過**（`NFR7.1` 驗主機名形式、不驗可解析性；`BR1.5` 禁止啟動探測），失敗發生在第一次 `embed()`，是 `ConnectError`。**而 `:485` 是個判斷依據**——照它操作的人會去找一個永遠不會出現的啟動錯誤 | 六處改寫為真實行為；`:485` 拆成兩列（保留服務名 → 執行期 `ConnectError`；改成 localhost／IP／網域 → 啟動失敗），remedy 不變。已實測確認：`startup: PASSED` → `embed: ConnectError` |
| **R-04** | Major | 我的 docstring 更正**過度更正**：兩個剝除點不是各自獨立，而是在 `target` 上**串聯**（建構子 `:172` 也對 `target` 呼叫 `_without_userinfo`，這正是 `MUT-F` 全綠的原因）。且「兩者都已覆蓋」兩半皆假——`target` 路徑的內層零覆蓋 | docstring 第三版逐字寫出兩層的次序與各自的測試；新增 `test_host_and_port_strips_userinfo`；更正 `BR4.4`／`NFR7.3` 註記與 §三 |
| **R-05** | Major | 我的新檢查關掉了「逸出宣告集合」，卻留著**集合內的碰撞**：`ollama` ＋ `OLLAMA_EMBED_MODEL=stub-v1` **被接受**，把真實 ollama 向量蓋上 stub 身分——正是 `BR3.6` 註解逐字描述的後果。檢查驗的是**成員資格**而非**對應關係** | 改為 provider-scoped：新增 `PROVIDER_LEGAL_MODEL_IDS`（provider → 合法身分），蘊含集合檢查；兩份字面值的一致性由 `test_provider_model_map_matches_the_declared_set` 鎖住；回歸案例 `test_real_provider_cannot_claim_the_stub_identity` |
| **R-06** | Minor | `M6` 由**原始碼正則**攔下而非行為：把模組層 `EMBEDDING_TIMEOUT_SEC` 設為 `None`（無限逾時，正是 `M6` 聲稱已駁倒的事），常數與 `httpx` 行不動 → 19 全綠（`MUT-A`）。`_timeout_from_env()` 零直接覆蓋，其刻意偏離 `BR1.6` 的設計也因此無測試支撐 | 新增五種輸入的行為測試（缺值／合法／非數字／0／負數，含 WARN 斷言）＋ `test_effective_timeout_is_a_positive_finite_number`（攔下 `MUT-A`）；更正 `M6` 列與 `NFR3.2` 註記 |

### 複驗：審查原本存活的四個突變現在全部轉紅

| 突變 | 審查時 | 現在 | 攔下它的測試 |
|---|---|---|---|
| `MUT-A` `EMBEDDING_TIMEOUT_SEC = None` | 19 OK 存活 | **RED** | `test_effective_timeout_is_a_positive_finite_number` |
| `MUT-B` 維度檢查 → `if False` | 19 OK 存活 | **RED** | `test_verify_shape_rejects_wrong_dimension` |
| `MUT-C1` 筆數分支 → `if False` | 19 OK 存活 | **RED** | `test_verify_shape_rejects_wrong_vector_count` |
| `MUT-F` `_host_and_port` 保留 userinfo | 19 OK 存活 | **RED** | `test_host_and_port_strips_userinfo` |
| `MUT-G` 掏空啟動 hook | 458 OK 存活 | **RED**（469 tests） | 三個 `configure_embedding_env` 測試 |
| `M9` stub 身分改 `bge-m3`（複驗） | RED | **RED** | `test_provider_model_map_matches_the_declared_set` 等 |
| 新的提供者對應檢查 → `if False` | — | **RED** | `test_real_provider_cannot_claim_the_stub_identity` 等 |

**零存活。** 每一項突變都先經行為探測確認輸出真的改變，再跑測試。

### 審查另外確認、且我接受的判斷

- `US4.1`／`AC4.1.1`–`AC4.1.3`／`BR3.4` 標 `Deferred`：審查回已核可上游逐字核對
  （`rules.md:441-442`、`functional-spec.md:62`、`unit-of-work.md:99-104`），判定
  **邊界先於本站存在，不是為了卸責而發明的**。`AC4.1.2` 尤其是 `SEC-1` **禁止**本單元
  做的授權判定，且該禁令是機器強制的。
- `BR5.1` 標 `N/A`：審查讀了規則本文，其 `violation_behaviour` 逐字「不適用——本條是
  誠實宣告而非禁令」，判定 `N/A` 正確。附帶指出 `R-05` 未修前，該宣告的
  「`model_id()` 隨向量空間改變而改變」那一半是可被設定擊敗的——`R-05` 修完後成立。
- 審查自承**淺掃**之處（未全讀 `code-generation-plan.md` 與 `unit-test-instructions.md`、
  未逐行審 `render-env.sh`／`docker-compose.deploy.yml` 的非 embedding 部分、未看
  `DEPLOY.md` diff、未重新推導 `P1`–`P6` 是否為對的六個性質）如實記載於審查檔，
  **不視為已驗證**。
