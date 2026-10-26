# 邏輯元件 — `U19 membership-service`

> 本站設計上游 `nfr-requirements` 的 **29 條 `NFR12.x`** 的承載形式。
> 本站**不複寫** `functional-design` 的 29 條 `BR` 規則（`team.md` 的單一真實來源）。
>
> `U19` 是 `service`，故六份設計產出全部適用（`U5`／`U18` 只有 `security-design`）。


## 〇、本檔的用途

把本單元的 NFR 設計落成**元件層檢視**：邊界、失效域、blast radius、共用資源。
它是 `nfr-design` 與 `infrastructure-design` 之間的橋，而本單元**零新基礎設施**，
故本檔的實質內容是**行程內的邏輯邊界**與**它們各自的失效後果**。

## 一、邏輯元件清單

| 元件 | 形式 | 位置 | 失效後果 |
|---|---|---|---|
| `MembershipFacade` | Python 類別，同進程 | `backend/services/`（新） | 全部 per-project 授權判定停止 → 所有消費端拒絕存取專案資料 |
| `membership_router` | FastAPI router，同進程 | `backend/services/`（新） | `U24` 的成員頁無法讀寫；授權判定仍可用（同進程呼叫端不受影響） |
| `select_successor` | **純函式**，無狀態 | 同上 | 自動改選無法挑選；**不受資料庫或鎖影響**（`BR4.1` 的附帶好處） |
| 既有停用端點的前置檢查 | 既有 router 內的一次呼叫 | `backend/services/user_router.py`（**改既有**） | 檢查失效 → `AC12.3.3` 的保護消失，而**停用仍會成功**（靜默） |
| `create_project_with_owner` | `U19` facade 的新方法 | 同 `MembershipFacade` | 新建專案回到零成員狀態（`[ND1]` 要修的那個） |
| 回填腳本 | 手動 CLI | `backend/scripts/`（新） | 既有專案維持零成員 |

## 二、失效域與 blast radius

### 2.1 本單元是一個**單點**，而這是刻意的

`BR1.1` 要求 `MembershipFacade` 是 per-project 授權判定的**唯一**提供者。
設計後果：**它是一個單點**——它不可用時，`U20`／`U13`／`U21`／`U24` 全部無法判定授權。

| 這是缺陷嗎 | 不是 |
|---|---|
| 理由 | 授權的單一來源是 `ADR-012` 的決定，而多個來源的後果（判定不一致）比單點不可用嚴重得多 |
| 它與既有系統的關係 | 它在**同一個 FastAPI process** 內，故「它不可用」等於「backend 不可用」——沒有獨立的失效模式 |

### 2.2 blast radius 表

| 失效 | 範圍 | 是否靜默 |
|---|---|---|
| `MembershipFacade` 拋例外 | 該請求失敗；其他請求不受影響 | 否（有例外） |
| 鎖等待過長 | 同一專案的其他成員變更排隊；**不同專案不受影響**（`NFR12.13`） | **是**（請求會成功，只是慢）→ `NFR12.27` 的 log 是唯一痕跡 |
| 死鎖 | 一個停用請求被資料庫中止 | 半靜默（有錯誤，但間歇且在容忍 flaky 的 CI 中像雜訊）→ `security-design.md §一之二` 的排序預防它 |
| 既有停用端點的前置檢查未被呼叫 | `AC12.3.3` 的保護消失 | **是**——停用照常成功。這是本單元最危險的失效模式 |
| 回填未執行 | 既有專案的擁有者被拒絕存取自己的專案 | 否（使用者會立刻發現） |

**`2.2` 的第四列是本單元最危險的一項**，而它的對策不在本站：
`BR6.3` 要求既有兩道保護不得被削弱，`FR12.5b` 要求 `TestClient` 測試
斷言 409 的狀態碼與欄位集合。**沒有那個測試，拿掉這道檢查不會有任何東西變紅。**

## 三、共用資源

| 資源 | 共用者 | 本單元的影響 |
|---|---|---|
| `SessionLocal`（全域 session factory） | 全部既有 router 與 service | **不改它**（`NFR12.5`）——這是 `[N1]`=A 勝過 `SERIALIZABLE` 的理由之一 |
| PostgreSQL 連線 | 同上 | 本單元不新增連線池設定 |
| `projects` 表（`U7`／`K-07` 擁有） | `U7`、本單元（**取鎖**） | **本單元對它取 `FOR UPDATE` 鎖，而 `U7` 的既有程式不知道這件事。** 見 §三之一 |
| `project_members`／`reselection_events`（`U18`／`K-15`） | 本單元（唯一寫入端）、`U20`／`U24`（經 facade 讀） | — |
| `logging` 管線 | 全部模組 | 新增 logger `cloud360.membership` |

### 3.1 本站查出的一項跨單元影響：`U7` 不知道有人在鎖它的表

`NFR12.1` 讓本單元對 `projects` 列取 `FOR UPDATE`。而 `U7` 的既有操作
（`create_project`／`delete_project`／`list_projects`）**完全不知道**這件事。

| `U7` 的操作 | 與本單元的鎖的互動 |
|---|---|
| `list_projects`（唯讀） | 不受影響——`FOR UPDATE` 不阻塞普通 `SELECT` |
| `create_project` | 不受影響——新列還不存在 |
| **`delete_project`** | **會阻塞**：它 `db.delete(project)` 需要該列的鎖，而本單元可能正持有它 |

**`delete_project` 被阻塞是正確行為**（不該在成員變更進行中刪掉專案），
但**`U7` 沒有任何文件提到它可能等鎖**。寫下來是因為下一個人看到
`delete_project` 偶發變慢會從錯的方向找原因。記為 `OPEN-ND19-9`。

## 四、本單元不新增的基礎設施（給 `infrastructure-design` 的交接）

| 項目 | 狀態 |
|---|---|
| 新進程／容器 | **無**（`embedded`） |
| 新監聽埠 | **無** |
| 新環境變數 | **無**（`NFR12.27` 的門檻刻意設為常數而非 env，見 `observability-design.md §一之二`） |
| 新外部服務 | **無** |
| 新資料庫物件 | **無**（兩張表由 `U18` 交付；`[FD3]`=A 的 `cause` 欄是對 `U18` 的回補指派） |
| 新 CI job | **本站不預選**——併發測試需要真實 PostgreSQL（`OPEN-N19-5`），而 `U5` 已建立該載體 |

**故 `infrastructure-design` 對本單元預期為薄**：唯一的實質項目是
**併發測試的 CI 載體**（擴充 `memory-schema` job 或新增一個），加上兩支待執行腳本的
部署步驟（`U18` 的 DDL 腳本 ＋ 本單元的回填腳本）。
