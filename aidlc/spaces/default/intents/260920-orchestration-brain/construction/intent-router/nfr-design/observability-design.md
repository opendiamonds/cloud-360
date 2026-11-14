# Observability Design — `U11 intent-router`

> 承接 `nfr-requirements/observability-requirements.md`。該檔已確立最重要的指標是
> **反問率**，且本 intent **沒有任何告警通道**（`U10` 的 `OPEN-N10-4`）。
> 本檔設計訊號的**形狀**，並如實記載它們目前無處可送。

## 一、一個型別承載全部訊號（與 `SEC-3` 的白名單是同一個決定）

```python
@dataclass(frozen=True)
class RoutingObservation:          # 欄位集合即白名單（SEC-3/SEC-5）
    turn_id: str
    slot_count: int                           # NFR3.73
    capability_ranks: tuple[tuple[str, int], ...]
    scores_available: bool
    can_single_out: bool                      # NFR1.60 的分子
    elapsed_ms: int                           # NFR3.72
    error_kind: str | None                    # NFR3.74（型別名，非訊息）
    memory_degraded: bool                     # D-1 的唯一保險（R-02 補）
```

**一個型別、兩個用途**：它同時是日誌的白名單與指標的來源。分成兩套會讓
「日誌記了但指標沒算」或反之成為可能，而兩者的欄位本來就該一致。

## 二、五個訊號與它們各自要回答的問題

| 訊號 | 計算 | 它回答什麼 | 依據 |
|---|---|---|---|
| **反問率** | `count(can_single_out == False) / count(總輪次)` | 分類器變差了？門檻設錯了？**還是有人在用門檻調準確率？** | `NFR1.60` |
| **classify 耗時 P50／P95** | `elapsed_ms` 的分位數 | `NFR3.60` 的 800 ms 達標了嗎 | `NFR3.72` |
| **槽位數分佈** | `slot_count` 的直方圖 | `FR5.1` 的多意圖能力**在線上真的被觸發過嗎** | `NFR3.73` |
| **失敗率（按型別）** | `error_kind` 分組計數 | 是供應商掛了，還是我們的 prompt／schema 壞了 | `NFR3.74` |
| **`prompt_guard` 命中數** | `error_kind == "prompt_guard_hit"` | 安全事件的量 | `SEC-4` |
| **記憶降級率**（修訂 1，審查 `R-02`） | `count(memory_degraded) / count(總輪次)`；另記**連續降級次數** | `U8` 多久沒取到過了？**這是 `D-1`（降級而非失敗）唯一的保險**——沒有它，「記憶永遠取不到」是無聲的 | `D-1`；`logical-components.md` §三 |

### 反問率為什麼要和準確率一起看——這是本檔的核心

`NFR1` 的連動條款逐字：「調高信心門檻會讓系統多反問、少交辦，準確率的帳面數字
因此上升，**但那不是識別變準了**」。

**設計上的落法**：儀表板上**不得**單獨呈現準確率。兩者必須同一張圖、同一個時間軸。
這不是美觀偏好——單獨呈現準確率會讓一個「把門檻調到 0.99」的改動看起來像改善。

### 槽位數分佈為什麼是必要的

`BR4.1`／`BR4.4`／`BR4.5`（多意圖整組）**在線上永遠是 1 個槽位時就是死碼**，
而沒有這個分佈，沒有人會發現。這與 `NFR7.62` 的可達性檢查是同一種警覺：
**規則存在不等於規則在作用。**

## 三、相關性：`turn_id` 是唯一的串接鍵

本單元不產生自己的 trace id。`turn_id` 來自 `K-02` 的訊息封包（`U2` 已定），
而它貫穿 `U13` → `U11` → `U12` → 能力 agent。

**設計決定：本單元不引入 OpenTelemetry 或任何 tracing 套件。**

| 理由 | 內容 |
|---|---|
| 零前例 | repo 全樹無 tracing 基礎設施（無 X-Ray、無 OTel、無 Jaeger） |
| 引入成本不屬本單元 | 它是跨全平台的工具鏈決策，不由一個 service 單元夾帶（同 `team.md` 拒絕 Vitest 的理由形狀） |
| `turn_id` 已足夠 | 本 intent 的呼叫鏈是同進程的四跳，`turn_id` 加結構化日誌即可重建；分散式 tracing 要解的是跨網路多服務的問題，本鏈不是 |

**記為交接**：若日後鏈路變成跨進程（例如 `TS-3c` 提到的 `OQ-N1` 回覆單元獨立部署），
這個判斷要重審。

## 四、告警：訊號有了，通道沒有（沿用 `OPEN-N10-4`，不開第二個缺口）

| 值得告警的訊號 | 建議條件 | 現況 |
|---|---|---|
| `LlmUnavailable` 失敗率 | 5 分鐘內 > 5% | **無通道** |
| 反問率異常 | 偏離基準 ±50% 持續 15 分鐘 | **無通道** |
| `MalformedRouting` 出現 | 任何一次（它代表 prompt／schema 壞了） | **無通道** |
| `prompt_guard` 命中突增 | 單一 principal 短時間多次 | **無通道** |

**本 repo 無 Prometheus、無 CloudWatch、無任何告警管道**（`U10` 的 `OPEN-N10-4`
已查證並登記）。本站**不自行發明一個**——那會是憑推論加的基礎設施。

**在 `OPEN-N10-4` 關閉之前，上述指標的實際消費方式是人工查詢結構化日誌。**
本檔如實記載這一點：**不把「有指標」寫成「有監控」。**

## 五、先有觀測、再換模型（一個排序建議，有具體理由）

`backend/services/brain_router.py` 的 DEMO `_classify`（關鍵詞計分）**已經**回傳
「依信心值排序的候選清單」，其 docstring 逐字「信心值定義域 0–1（`AC1.2.4`），
容許為 `None`（`BR2.3`）」——**資料形狀與本單元設計的一致**。

**所以上述五個訊號可以在換模型之前就接上 DEMO 的計分器。** 這樣換 Jev 的那一天
**有基準可比**：反問率從多少變多少、耗時從多少變多少。少了這一步，第一次實測
拿到的數字沒有對照組，而 `NFR1` 的校正程序需要的正是對照。

**這是建議的實作順序，不是新需求**；記為 `code-generation` 的交接事項。
