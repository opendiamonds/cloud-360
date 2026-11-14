# 單元測試指示 — `U6 embedding-port`（`library`）

<!-- Stage: code-generation（Construction 3.5）· Unit: embedding-port · kind: library -->

> Methodology **`test-after`**、Test strategy **`standard`**（每元件 5–8 測試
> ＋ 關鍵邊界的整合測試），兩者皆由 `aidlc-testing-posture.ts render` 的
> Testing Contract 決定，完整 JSON 逐字貼於 `code-generation-plan.md §一`。

## 一 Runner 就緒（第一個可執行測試步驟之前必須完成）

**本單元是 brownfield，runner 已存在，故本節是「驗證」而非「建置」。**

**精確的 unit-scoped 指令**（Testing Contract 要求寫進本檔）：

```bash
cd backend && python -m unittest tests.test_embedding_port -v
```

**全套指令**（CI 跑的那個，`ci.yml` 的 `backend` job）：

```bash
cd backend && python -m unittest discover -s tests -v
```

**驗證要點**：

1. `backend/tests/` 下的新檔會被 `discover` 自動撿到——**無需任何 CI 設定變更**。
2. 框架是 Python 內建 **`unittest`**，**不是 pytest**（`team.md ## Testing Posture` 的既成事實）。
3. property-based 用既有 **`hypothesis`** 的 `@given`（已在 `requirements.txt`）。
4. 新測試檔第一行 import 必須是：
   ```python
   import tests.helpers  # noqa: F401  -- installs the psycopg2 stub before services import
   ```
   理由：本單元**自己**不讀 DB，但啟動整合測試會 import `backend.main`，
   而它的 import 鏈會碰到 DB 模組。
5. **零新依賴**：`hashlib`／`os`／`logging`／`unittest`／`unittest.mock` 皆標準庫；
   `httpx` 與 `hypothesis` 已在 `requirements.txt`。**`backend/requirements.txt` 不變。**

## 二 測試檔與測試清單

**一支新檔**：`backend/tests/test_embedding_port.py`

| # | 測試 | 斷言 | 承載 |
|---|---|---|---|
| 1 | `test_embed_returns_one_vector_per_input` | `len(result) == len(texts)`，順序一一對應 | `P1`、`BR2.1` |
| 2 | `test_every_vector_is_exactly_1024_dimensions` | 每個向量長度**恰為** 1024 | `P2`、`BR2.2` |
| 3 | `test_embedding_is_deterministic_for_the_same_input` | 同輸入兩次呼叫結果完全相等 | `P3`、`BR2.3` |
| 4 | `test_batching_does_not_change_the_vector` | `embed(texts)[i] == embed([texts[i]])[0]` | `P4`、`BR2.1` |
| 5 | `test_different_inputs_get_different_vectors` | 兩個相異輸入的向量**不相等** | **`D-3`**（見下方說明） |
| 6 | `test_empty_input_returns_empty_and_touches_nothing` | `embed([]) == []` 且不發出任何外部呼叫 | `P6`、`BR2.4` |
| 7 | `test_model_id_set_matches_the_allowed_value_set_both_ways` | `I == S`（**雙向**集合相等） | `P5`、`BR3.3` |
| 8 | `test_startup_validation_rejects_missing_and_illegal_provider` | 缺值／不在四值內 → 拋，訊息含四個可選值 | `BR1.1`、`BR1.6` |
| 9 | `test_startup_validation_rejects_non_internal_ollama_host` | `localhost`／`127.0.0.1`／公開 IP 各自被拒 | **`NFR7.1`** |
| 10 | `test_fulltext_yields_no_port` | `EMBEDDING_PROVIDER=fulltext` 時選擇器回 `None`；其餘三者回非 `None` | `BR1.4`、`D-10` |
| 11 | `test_timeout_raises_provider_unavailable` | 以不可達位址或 mock transport 構造 → 拋 `EmbeddingProviderUnavailable` | `NFR3.2`、`D-6` |
| 12 | `test_exception_message_strips_userinfo` | 以含 `user:pass@` 的 `OLLAMA_BASE_URL` 構造，訊息**不含**密碼 | `SEC-2`、`D-7` |
| 13 | `test_oversized_input_is_truncated_with_a_warning` | 超長輸入**不拋例外**、回正常向量，且 `assertLogs` 捕捉到含字元數的 WARN | `D-4` |
| 14 | `test_missing_fastembed_names_the_install_command` | monkeypatch 讓 import 失敗 → 例外訊息含安裝指令 | `BR4.3` |
| 15 | `test_each_embed_logs_provider_model_and_duration` | `assertLogs` 捕捉到含 provider、model_id、批次大小、**耗時毫秒**的 INFO | `D-5` 第 2 條、`NFR3.1` |
| 16 | `test_port_imports_no_db_session_no_rbac_no_router` | 讀模組原始碼，斷言三者 `grep` 皆零命中 | **`SEC-1`**、`D-9`、`BR2.7` |

數量 **16**，高於 `standard` 的「每元件 5–8」區間。
**這是刻意的，且 Testing Contract 允許**（`combination_rule` 逐字：
「a targeted scope regression may add the narrowest necessary test type beyond
the strategy default」）。理由：本單元是 ADR-0006 的 **PBT hard constraint 落點**，
六個性質（`P1`–`P6`）是已核可的設計產出而非本站選的測試量；
其餘十項是 `SEC-*`／`NFR7.1`／`D-4`／`D-7` 各自明文要求的可驗證方式。
把它壓到 8 個就得砍掉已核可的驗證要求——**那是放寬門檻，`construction.md` 禁止**。

### 測試 5 為什麼必須存在

`D-3` 的全部理由：若 `stub` 對所有輸入回同一個向量，測試 1–3、6 **全部會過**，
而 `U8` 日後用 `stub` 寫的任何相似度測試都會變成恆真——每一列的距離都相同。
突變 `M1` 正是為此而設。

### 測試 7 為什麼必須雙向

只驗 `I ⊆ S` 會讓 `S` 裡多出一個沒有實作產生的值而不被發現，
而那個值在資料層看起來像一個合法的向量空間。`BR3.3` 逐字要求雙向。

### 測試 16 的形狀

讀模組原始碼做字串斷言，不是執行期檢查。這與 `project.md` 對 cost 純函式層的
可執行檢查同形，也是 `SEC-1` 唯一能被機械驗證的方式。

## 三 覆蓋範圍的誠實說明

| 實作 | 本檔的測試是否執行到它 |
|---|---|
| `stub` | **是**——測試 1–7 全部對它執行 |
| `ollama` | **部分**：測試 9、11、12 以 mock／不可達位址覆蓋其**失敗路徑**；**其成功路徑（真實回傳 1024 維向量）在 CI 零覆蓋** |
| `fastembed` | **部分**：測試 14 覆蓋未安裝路徑；**其成功路徑在 CI 零覆蓋** |

**真正測不到的只有一件事**：`ollama` 與 `fastembed` 實際回傳的向量是否真為 1024 維。
它在首次真實呼叫時由測試 2 所驗的同一條執行期斷言攔下——**大聲失敗，不是靜默**。
缺口由 `functional-design/functional-spec.md` 的 `OQ-E2` 與
`infrastructure-design/cicd-pipeline.md §三` 具名持有，**不在本站關閉**。

## 四 既有測試必須保持綠燈

Testing Contract 的 `scope_floor` 逐字：「Keep the existing test suite green.」

本單元改動 `backend/main.py` 一處，故全套必須在改動**前後各跑一次並比對**：

- **新增數** == 本單元新增的測試數
- **既有項零失敗**
- **特別注意**：`backend/tests/` 的既有測試**完全不設定 embedding 環境變數**。
  `D-1` 把驗證掛在 startup hook 上而非 import 時，正是為了讓它們不受影響
  ——**既有測試全綠本身就是 `D-1` 這個選擇的驗證**。

### 覆蓋率

`org.md` 宣告「最低 80% line coverage」，而 `team.md` 如實記載本 repo
**完全沒有覆蓋率量測機制**；且本 scope 的 `scope_floor` 逐字為
「This scope adds no extra new-test floor beyond the selected test strategy」。
**本計畫不宣稱達成 80%，亦不以「已達成」記錄。**

## 五 PBT 判定

**適用，且本單元即 ADR-0006 的落點**（K-06 `pbt_note` 逐字
「ADR-0006 的 property-based hard constraint 落點之一」）。

六個性質 `P1`–`P6` 由 `functional-design/functional-spec.md §五` 定義，
本站**不重新定義**，只負責以 `hypothesis` 的 `@given` 實作它們（測試 1–7）。
值域：`st.lists(st.text(), max_size=8)` 之類的文字序列；
`P5` 為純設定推導，不需 `@given`。

## 六 交付後更正（append-only，不改上方已核可內容）

上方內容為 Plan Approval 當時的版本，**保留原樣**。以下三項是實作與審查之後的
事實更正；衝突時以本節為準。

### 1. 本機的執行指令是 `python3`，不是 `python`

`§一` 的兩條指令寫 `python`，而**本 worktree 沒有 `python`**（`command not found`）。
CI 不受影響（`actions/setup-python` 提供 `python`）。本機請用：

```bash
cd backend && python3 -m unittest tests.test_embedding_port -v     # 本單元
cd backend && python3 -m unittest discover -s tests -v              # 全套
```

**這一項對 `build-and-test`（3.6）是硬的**：該站會實際執行此檔的指令，照原文跑會
直接 `command not found` 而非測試失敗，兩者的除錯方向完全不同。

### 2. 測試數為 **30**，不是 16

`§二` 的 16 個案例全部存在且全綠。審查 iteration 1 判定 NOT-READY 並要求補齊
**14** 個（含 `code-generation` 自查補的 2 個），逐一對應見
`code-summary.md §九` 與 `reviews/review-01-unreceipted.md`：

| 新增 | 承載 | 由哪個突變證明它承重 |
|---|---|---|
| `test_model_id_must_be_in_the_declared_set` | `BR3.3` 缺口（自查） | 檢查改 `if False` → RED |
| `test_default_timeout_is_a_named_constant` | `D-6`（自查） | — |
| `test_exception_constructor_strips_userinfo_from_target_and_detail` | `SEC-2` 外層（`M7`） | `MUT-E` |
| `test_configure_embedding_env_*`（4 個） | `R-01`、`BR1.6`、`BR7.1`、`NFR8.2` | `MUT-G` |
| `test_verify_shape_rejects_wrong_dimension` / `_wrong_vector_count` | `R-02`、`BR2.1`／`BR2.2` | `MUT-B`／`MUT-C1` |
| `test_host_and_port_strips_userinfo` | `R-04`、`SEC-2` 內層 | `MUT-F` |
| `test_real_provider_cannot_claim_the_stub_identity` | `R-05`、`BR3.6` | 檢查改 `if False` → RED |
| `test_provider_model_map_matches_the_declared_set` | `R-05` 的連帶一致性 | `M9` |
| `test_timeout_from_env_handles_every_input_shape` | `R-06`、`NFR3.2` | — |
| `test_effective_timeout_is_a_positive_finite_number` | `R-06` | `MUT-A` |

`§二` 結尾對「為何高於 `standard` 的 5–8 區間」的理由原樣成立，只是數字更大：
超出的部分全部是 ADR-0006 的 PBT 落點與 `SEC-*`／`NFR*` 各自明文要求的驗證方式，
以及審查指名的缺口。**沒有一項是為了湊數。**

### 3. 突變驗證需要 `AIDLC_MUTATION_RUN=1`

測試檔有一個只在該環境變數為 `1` 時生效的 hypothesis profile（關閉 shrink）。
理由是實測的：`M4` 讓多個 property 同時失敗時，hypothesis 縮小反例在刻意壞掉的
實作上跑到病態——單一突變燒掉 **10 分 51 秒**的 100% CPU 仍未結束。正常執行與 CI
完全不受影響（兩種模式皆已分別驗過全綠）。做突變驗證時：

```bash
cd backend && AIDLC_MUTATION_RUN=1 python3 -m unittest tests.test_embedding_port
```

### 4. `§三` 的覆蓋範圍說明仍然成立

`ollama` 與 `fastembed` 的**成功路徑**在 CI 依然零覆蓋（`OPEN-1`）。審查 `R-02`
之後的差別是：**「它們回錯維度會被攔下」現在是被測行為**（`_verify_shape` 有了直接
覆蓋），所以 `OPEN-1` 剩下的缺口收窄為純粹的「真實服務未在 CI 執行」。
