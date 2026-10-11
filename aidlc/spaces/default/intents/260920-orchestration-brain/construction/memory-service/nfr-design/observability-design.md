# 可觀測性設計 — `U8 memory-service`

> 本 repo **有 logs、無 metrics、無 traces**，告警的唯一既有管道是 GitHub Issues
> （`U9` 已逐一查證）。本檔不發明不存在的承載機制。

## 〇、上游依據

| 上游 | 本檔用到它的什麼 |
|---|---|
| `nfr-requirements/observability-requirements.md` | `NFR7.30`–`NFR7.34` 與「無 SLO」的理由 |
| `nfr-requirements/security-requirements.md` | `NFR6.21`（日誌不得含記憶內容） |
| 本站 `security-design.md` | §二之二 的「對外收斂、內部保留」——日誌是枚舉與誤刪的唯一區分手段 |
| `memory-purge/infrastructure-design/monitoring-design.md`（`U9`） | 四支柱現況表 |
| `team.md` `## Code Style` | logger 一律 `cloud360.<module>` |

## 一、結構化日誌設計：欄位白名單

**白名單而非黑名單**，理由見 `security-design.md §四之二`
（`logger.warning(f"...{memory}")` 會把 `content` 帶進日誌，而功能完全正常）。

| 允許的欄位 | 用途 |
|---|---|
| `principal_id` | 誰 |
| `memory_id` | 哪一筆 |
| `kind` | 三種之一 |
| `reason` | `owner`／`scope`（拒絕時） |
| `candidates_after_scope` ／ `candidates_after_model` | 兩道過濾後的筆數（`NFR7.34`） |
| `provider` ／ `available_providers` | 提供者不可用時（`NFR7.32`） |

| **禁止** | `content`、`embedding`、**整個模型物件** |
|---|---|

| logger 名稱 | `logging.getLogger("cloud360.memory_<layer>")`——不用 `__name__`（`NFR7.33`） |

## 二、日誌層級

| 事件 | 層級 | 理由 |
|---|---|---|
| 授權拒絕（`owner`／`scope`） | `WARNING` | 可恢復、預期會發生 |
| 提供者不可用 | `ERROR` | 操作失敗且需要人介入 |
| 成功寫入／讀取 | **不逐筆記錄**（**一個例外，見 §三**） | `BR7.1` 讓每輪對話寫一筆 episodic——逐筆記錄會把日誌變成記憶內容的第二份副本，而那正是 `U5` 刻意不讓稽核表含內容的同一個理由 |

**那個例外與本列不衝突（承審查 `R-03`）**：§三 要求 `search` **回空集合時**
記錄兩道過濾後的**筆數**。區別在對象與內容兩個維度——
本列禁止的是「**每一筆**被讀到的記憶」（會複製內容），
§三 要求的是「**這一次查詢**」的**聚合筆數**（不含內容）。
故 §三 不是對本列的放寬，是一個正交的診斷面。

## 三、`NFR7.34`：空結果的可診斷性（本站最實用的一條）

`search` 回空集合有三種成因，而三者在 `U15` 的畫面上**完全一樣**：

| 情境 | 是否為缺陷 |
|---|---|
| 使用者真的沒有記憶 | 否 |
| `BR2.2` 的可見範圍過濾排除全部 | 否 |
| **`BR3.2` 的模型分群排除全部**（換過提供者而未重新 embed） | **是** |

**設計**：`search` 回空時，記錄兩道過濾各自之後的候選筆數。

| 觀察到 | 可判定為 |
|---|---|
| `candidates_after_scope = 0` | 使用者沒有可見的記憶（前兩種） |
| `candidates_after_scope > 0` 且 `candidates_after_model = 0` | **第三種——缺陷** |

**筆數不是內容**，故不違反 `NFR6.21`。
這是在沒有 metrics 的情況下，讓一個靜默缺陷變成可事後診斷的最低成本做法。

## 四、`[D1]`=A 之後，日誌承擔了新責任

刪除路徑的對外回應收斂為 404 之後，**日誌是區分「使用者誤刪」與
「有人在枚舉」的唯一手段**：

| 情境 | 對外 | 日誌 |
|---|---|---|
| 擁有者誤刪已刪除的記憶 | 404 | **不含** `reason="owner"` |
| 非擁有者探測存在的記憶 | 404 | **含** `reason="owner"` |

**故 `NFR7.30` 在 `[D1]`=A 之後由「稽核義務」升格為「唯一的偵測面」。**
若日誌也收斂，枚舉行為就完全不可見。

**本站不新增告警**（無 metrics 基礎），但記明：
若日後要偵測枚舉，判準是「單一 principal 短時間內大量帶 `reason="owner"`
的 404」——而那需要日誌聚合，屬 `N8-10` 的範圍。

## 五、Metrics／SLI／SLO

| SLI | SLO | 窗口 |
|---|---|---|
| — | — | — |

**無 SLO**，理由三項（承 `nfr-requirements §二`）：無 metrics 承載機制；
`NFR3.20`／`NFR3.23` 是一次性量測的需求而非持續量測的誤差預算；
本單元不是獨立服務。

**候選 SLI（待承載機制）**：`search` 延遲百分位、授權拒絕率、
帶 `reason="owner"` 的 404 率。記為 `N8-10`（承接）。

## 六、Tracing 與 correlation id

| 項目 | 設計 |
|---|---|
| 分散式追蹤 | **無**（repo 無 OpenTelemetry／X-Ray） |
| correlation id | **不新增**。本單元是進程內三層呼叫，唯一外部呼叫是 `U6` 的 embedding，而 `K-06` 不含 tracing 要求 |
| 誠實限定 | `U11` 經同進程 facade 呼叫 `search` 時，該次檢索的日誌與觸發它的對話**無法關聯**。這在診斷「為什麼大腦沒用到某筆記憶」時是真實的不便，但補它需要跨單元的 correlation 機制。記為 `D8-6`（承接見 §六之一） |

### 6.1 `D8-6` 的承接（承審查 `R-02`）

**承接站：`U13 brain-gateway` 的 `nfr-design`。**
理由：correlation id 必須由**擁有對話邊界的那一層**產生並向下傳遞，
而那是 `U13`（`K-12` 的 WebSocket 握手與每輪對話的起點）。
本單元只能消費它，無法產生它——在 `U8` 自行發明一個 id 會得到一個
與對話無關的識別字，比沒有更糟。

**位置已查證在游標之後**：`U13` 在 B6、本單元（`U8`）在 B3，
且 `U13` 的 per-unit stage 尚未執行。
**轉移目標**：`U13` 的 `nfr-design` 為 `CONDITIONAL`；若被 skip 則轉
`U13` 的 `code-generation`（**ALWAYS**）。
