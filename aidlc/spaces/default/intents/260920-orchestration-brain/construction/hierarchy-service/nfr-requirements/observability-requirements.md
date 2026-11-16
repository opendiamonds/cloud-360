# 可觀測性需求 — `U7 hierarchy-service`

## 一、判定：不適用（無新增監控目標），但有一項沿用義務

**逐項對照 condition 後判為不適用**，理由如下，不留空白。

本單元不新增監控目標、不新增告警、不新增健康檢查端點。整體觀測設計屬
`U1 brain-infra` 的 `infrastructure-design`（`monitoring-design.md` 已交付）。
intent 級的 `NFR11`（跨功能任務的頁面切換次數）是**畫面層指標**，
只能在 `U23`／`U16` 量測（`requirements.md:470` 逐字「NFR11 不受此限：
它的判定是『每個情境的切換次數都嚴格少於基準』」）。

**一項沿用義務（不是新需求，但漏了會製造已知的不一致）**：
logger 命名一律 `logging.getLogger("cloud360.<module>")`。
`team.md ## Code Style` 已如實記載現況為 11 支模組用該形式、
**5 支用 `__name__` 屬已知不一致**（`collab_router`、`design_agent`、
`agent_router`、`diagram_builder`），並明訂新模組一律用前者。
本單元是新模組，故須用 `"cloud360.hierarchy_service"` 等形式，不得沿用 `__name__`。

## 二、稽核記錄不等於可觀測性（刻意分開）

本單元確有稽核面，但它**不在本檔**：變更紀錄的稽核屬 ADR-0006 的
audit logging 面，已於 `functional-spec.md` §七之三 逐項判定，
並查出三項減損（級聯刪除、90 天保存期且清除機制不在本 repo、
來源欄位只容納大腦編排一條路徑故經既有 A1 頁面的異動不留紀錄）。
把它寫進「可觀測性」會混淆兩件事：稽核是**對使用者行為的記錄**，
可觀測性是**對系統健康的量測**。本單元有前者、無後者。

## 二、為什麼本單元沒有這一類需求

本單元的形態決定了這一點，不是省略：`unit-of-work.md:43` 逐字把它列為
**`embedded`（同一 FastAPI process 的新 router）**——不新增進程、不新增監聽埠、
不新增部署單位、不呼叫任何外部服務（無 LLM、無 webhook、無檔案 I/O）。
`functional-spec.md` §七之三 的 Network exposure 列逐字「不新增任何對外進程邊界、
不新增任何監聽埠」，而 `unit-of-work.md:249` 逐字把 `U13 brain-gateway` 的新
WebSocket 稱為「本 intent **唯一**新增的對外網路面」。

## 三、若日後本判定失效的觸發條件

本判定綁在「embedded 且無外部依賴」這個前提上。下列任一成立時須重開本站：
把本單元拆成獨立進程、引入任何外部呼叫（計價、LLM、webhook）、
或列舉端點的資料規模由「使用者自有的專案數」變成「全體使用者的專案數」
（後者會讓 `BR6.1` 的列過濾從常數成本變成需要索引設計的成本）。
