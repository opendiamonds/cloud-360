# Performance Requirements — `U23 project-pages-ui`

> 撰寫時間 2026-10-15T22:52:51Z（`date -u` 取值）。
>
> 單元類型 `ui`（`produces_kinds` 使本站只產出 performance／security／tech-stack／traceability 四份）。
> **識別字**：可繼承 inception NFR 者用 `NFR<父條>.100` 起（`.100` 區段實查為空，見問題檔前言）；
> 無法誠實繼承任何 inception NFR 者以 `PPN-nn` 宣告為孤兒，並在 `traceability.json` 的 `reverse` 段逐條寫明理由
> （比照 `U24` 的 `UIP-*`）。`PPN-nn` 與題號 `[PPN1]` 是兩種東西：前者是需求，後者是問題。
>
> **`[PPN1]`=A 已定案**（2026-10-15T22:59:34Z 經選單作答，`nfr-requirements-questions.md:89`）：`PPN-07` 為定案需求。
> `[PP3]` 選項 A 原文的「零 schema 變更」（`functional-design-questions.md:172`）由 `[PPN1]`=A 取代為「零資料表／欄位變更，新增一個索引」，
> 並觸發 `project.md ## Mandated` 的 `schema_rbac.sql` ＋ `DEPLOY.md` blocking 同步（見 `tech-stack-decisions.md` 的 `PPN-25`）。

## 零、上游來源

| 來源 | 用到什麼 |
|---|---|
| `construction/project-pages-ui/functional-design/functional-spec.md` | W1／W3／W5／W6 的請求序列、§八 `OPEN-PP23-5` |
| `construction/project-pages-ui/functional-design/rules.md` | `BR85.1`（切籤不發請求）、`BR85.2`（未填總和）、`BR87.1`–`BR87.3`（伺服器端查詢形狀）、`BR88.3`（暫定並行上限 4、不截斷） |
| `construction/project-pages-ui/functional-design/frontend-components.md` §六 | 7 個 API 消費點與次數（清單頁 1＋P、詳情頁 2＋2S、儲存 k＋1） |
| `construction/project-pages-ui/carried-review-items.md` | R-04（佇列內優先序與重讀是否進佇列） |
| `inception/requirements-analysis/requirements.md` | `NFR1`–`NFR11`（`:400`–`:585`）逐條判定適用性 |
| `codekb/chiton/technology-stack.md` | 前端只有 Playwright、無 unit 框架；`openapi-typescript` 為唯一精確 pin |
| repo 實測 | `backend/database.py:37`、`backend/Dockerfile:30`、`schema_rbac.sql:353`／`:594-615`、`backend/models.py:380`／`:426`、`hierarchy_router.py:67-88` |

## 一、可繼承 inception NFR 的要求

| ID | 要求 | 目標 | 量測方式 | 父條與繼承理由 |
|---|---|---|---|---|
| `NFR11.100` | 建立系統（W4）完成後**不發生頁面切換** | `pathname` 變更 **0** 次 | Playwright：記錄 `page.url()` 的 pathname 序列，建立系統前後相同 | `NFR11`（跨功能任務的頁面切換次數須嚴格少於基準，`requirements.md:563`）。W4 就地展開輸入、成功後只重讀系統清單 |
| `NFR11.101` | 建立專案成功後**直接落在該專案詳情**，不經清單頁 | 自送出到抵達 `/projects/<新 id>` 的 `pathname` 變更 **恰 1** 次 | 同上；斷言最終 pathname 的 id 等於 `POST` 回應的 `id` | `NFR11`。`BR82.5` 的導向使「建專案 → 填需求」少一次回清單再點入 |
| `NFR11.102` | 切換總覽／需求／記憶摘要三籤**不改 pathname、不新增瀏覽歷史項** | `pathname` 變更 **0** 次；`history.length` 不增加 | Playwright：切籤三次後斷言 pathname 不變、`page.evaluate(() => history.length)` 不變 | `NFR11`。W5 以 `replace` 更新 `?tab=` |

> 三條都是本單元對 `NFR11` 的**正向貢獻**，不在其計分母體內：`NFR11` 的母體是 `user-stories` 產生的**跨功能**任務情境
> （`requirements.md:566-569`），專案頁的建立與填寫目前不在已命名的情境中。把它們加進母體不屬本站職權（同 `U24` 的
> `NFR11.80`／`.81` 處置）。

## 二、本單元自有的效能要求（孤兒，無 inception 父條）

| ID | 要求 | 目標 | 量測方式 |
|---|---|---|---|
| **`PPN-01`** | 扇出請求的**並行上限**：清單頁（端點 2）一個佇列、詳情頁（端點 5 ＋ 端點 7）一個佇列，任一時刻在途請求數上限 | **4**（`OPEN-PP23-5` 定案，確認 `BR88.3` 的暫定值） | Playwright：以 `page.route` 對端點 2 加 1 秒延遲、構造 P＝6 → 以 request／requestfinished 事件計數，在途數最大值**恰為 4**；詳情頁構造 S＝3（端點 5 ＋ 7 共 6 個）同樣恰為 4。**突變**：佇列改成 `Promise.all` 全發 → 最大值 6 → 紅 |
| **`PPN-02`** | 佇列內的**發出順序** | 清單頁：專案 id 遞增。詳情頁：**全部端點 5（需求欄位）先於任何端點 7（變更紀錄）**，兩組內各依系統 id 遞增 | Playwright：記錄攔截到的請求順序，斷言順序序列。**突變**：端點 7 先入佇列 → 紅 |
| **`PPN-03`** | **不截斷、不設總數硬上界**：清單頁發出 P 次端點 2、詳情頁發出 S 次端點 5 與 S 次端點 7，全部渲染 | 請求數 = P／2S；清單列數 = P；佇列中尚未完成的項目顯示既有的載入子狀態（`systems-loading`；總覽未填與待補區在全部完成前顯示載入中） | Playwright：P＝6、並行 4 → 6 列全部出現「N 個系統」；在第 5、6 個請求被延遲期間，該兩列顯示載入子狀態而非「尚無系統」。**突變**：`slice(0, 4)` → 第 5、6 列缺 → 紅 |
| **`PPN-04`** | 頁面卸載後，佇列中**尚未發出**的請求不再發出 | 卸載後新發出的扇出請求數 **0** | Playwright：P＝8、端點 2 延遲 2 秒，進頁後 0.5 秒導航離開 → 3 秒內端點 2 總請求數 ≤ 4 |
| **`PPN-05`** | 切籤**不發請求**（`BR85.1`） | 切籤時對 `/api/**` 的請求數 **0** | Playwright：載入完成後切籤三次，攔截計數不增加 |
| **`PPN-06`** | 兩支列舉端點的**伺服器 SQL 語句數不隨資料量增長**（無 N+1） | 專案清單：P＝1 與 P＝8 的語句數**相等**；系統清單：S＝1 與 S＝8 的語句數**相等** | `TestClient` ＋ SQLAlchemy `event.listen(engine, "before_cursor_execute", …)` 計數（`backend/tests/helpers.py` 的 SQLite 引擎；監聽器於 `tearDown` 以 `event.remove` 卸除，否則會在同一進程的其他測試中繼續計數）。**突變**：`list_visible_projects` 改為對每個 id 呼叫一次 `is_project_visible` → 兩組計數不等 → 紅 |
| **`PPN-07`**（`[PPN1]`=A） | 「以使用者查成員列」有索引支撐 | `schema_rbac.sql` 與 `models.py` **皆有** `ix_project_members_user_id ON project_members (user_id)`；`schema_rbac.sql:608-615` 的註解改寫為「條件 ① 已由 `U23` 成立，故建立」 | `test_membership_data.py` 的 `test_M3`（ORM 與 DDL 索引名稱集合相等，`:139`）維持綠燈，且新增一條斷言兩者皆含此名；`grep -c "ix_project_members_user_id" schema_rbac.sql DEPLOY.md` 各 ≥ 1 |

### 二之一、`PPN-01` 的 4 是怎麼來的（不是憑空）

| 依據 | 實測 | 推論 |
|---|---|---|
| backend 進程數 | `backend/Dockerfile:30` 為單一 `uvicorn main:app`，無 `--workers` | 所有使用者的請求共用一個進程、一個連線池 |
| DB 連線池 | `backend/database.py:37` 為 `create_engine(db_url)`，**未設** `pool_size`／`max_overflow` | 採 SQLAlchemy 預設：常駐 5、溢出 10。兩支列舉 handler 與需求欄位 handler 皆為同步 `def`（`hierarchy_router.py:152`、`:299`；`requirement_field_router.py:146`），各佔一條連線直到回應 |
| 同頁其他請求 | 詳情頁的端點 1、2（進頁各 1 次）、`U24` 掛在 `Layout` 的待確認改選查詢（`membershipApi.ts:282`）都**不進佇列** | 端點 1、2 在扇出**之前**依序完成（W3 第 1–3 步），故扇出期間一位使用者的在途數最多為 4（佇列）＋ 1（`Layout` 的查詢）＝ **5**，恰在常駐池之內；溢出連線只在多位使用者同時進頁時才用到 |
| 上限更大的代價 | 例如 8：一位使用者即可吃掉常駐池全部 5 條並開始用溢出連線 | 兩位使用者同時打開系統數多的專案，就會讓第三位使用者的任何請求排隊等連線 |

**限制（如實記載）**：「瀏覽器對同源 HTTP/1.1 的連線上限」不是本推論的依據——正式環境經 Cloudflare Tunnel，前端到邊緣可能是
HTTP/2，該上限不一定存在；本站未實測。4 的依據只有上表的伺服器側事實。

### 二之二、`PPN-02` 的順序為什麼這樣排（帶入項 R-04）

`BR85.1` 要求總覽與需求籤讀**同一份** `fieldsBySystem`，而總覽的「未填需求欄位 Σ」與「待補的需求」要等**全部**端點 5 完成
才是完整值（`BR88.3`）。若端點 7 與端點 5 交錯排隊，需求籤要等約 2S 個請求才可用；改為端點 5 全部在前，需求籤只等 S 個。
「使用者目前選取的系統優先」不另設：進頁時選取的系統即依 id 遞增的第一個，已是第一個發出的請求；之後的切換選取不改變
已在佇列中的順序（避免佇列重排的狀態複雜度，且只影響第一次載入）。

**不進佇列的請求**（回答 R-04 的第二半）：儲存後的重讀（W6 第 6 步）、`[重新整理]`（`BR85.6`）、`k` 次 `PUT`、
端點 1、詳情頁進頁的那一次端點 2、建立後的系統清單重讀——它們都是**一次使用者動作的直接後果**，排在進頁扇出之後會讓
使用者按了儲存卻要等其他系統的載入完成。它們的數量以使用者動作為上界，不構成扇出。

## 三、`OPEN-PP23-5` 的「上界」定案：不設硬上界（已知代價）

`functional-spec.md` §八 把「請求數上界」指派本站。本站定為**不設硬上界**，理由見問題檔 §一 第 2 點（截斷被 `BR88.3`
排除；拒絕渲染製造斷崖）。由此產生的已知代價：

| 量 | 算式 | 例 |
|---|---|---|
| 清單頁請求數 | 1 ＋ P | P＝20 → 21 |
| 清單頁的扇出批次 | ⌈P ÷ 4⌉ | P＝20 → 5 批 |
| 詳情頁進頁請求數 | 2 ＋ 2S | S＝10 → 22 |
| 詳情頁的扇出批次 | ⌈2S ÷ 4⌉ | S＝10 → 5 批 |
| 儲存一次的請求數 | k ＋ 1 | 改 3 欄 → 4 |

頁面完整載入的時間大約是「批次數 × 單一請求往返時間」，**隨 P、S 線性增加**，而本 repo 沒有任何量測 P、S 實際分佈或延遲的
機制。這是 `[PP1]`／`BR87.4`「路徑與回應形狀不變」的直接後果：要降低請求數只能新增批次端點（例如一次回多個系統的欄位），
那是新的 API 範圍，不在本單元。

## 四、`PPN-07` 的背景（`[PPN1]`）

`BR87.1` 的可見集合由三條子查詢組成，逐條對照既有索引：

| 子查詢 | 條件 | 既有索引 | 覆蓋 |
|---|---|---|---|
| 成員那一半 | `project_members.user_id = ?` | `uq_project_members_project_user (project_id, user_id)`——`user_id` **不是**前導欄 | **否**，全表掃描 |
| 擁有者那一半 | `projects.owner_user_id = ?` | `ix_projects_owner_user_id`（`schema_rbac.sql:353`） | 是 |
| 零成員列 | `NOT EXISTS (… WHERE m.project_id = p.id)` | `uq_project_members_project_user` 以 `project_id` 為前導欄 | 是 |
| 系統清單的可見性（`is_project_visible`） | `project_id = ? AND user_id = ?` | 同上唯一索引 | 是 |

只有第一列缺索引，且只影響**專案清單**這一支端點。依 `[PPN1]`=A，以 `PPN-07` 補上；`U18` 的 `security-design.md` §4.3（`:316-329`）
寫下的觸發條件 ① 由本單元成立，該紀錄因此有了執行者。

## 五、刻意不設的目標

| 不設 | 理由 |
|---|---|
| 端點回應時間的毫秒數（P50／P95） | 本 repo 無延遲量測機制；寫一個量不到的數字是裝飾。N+1 這個真實失敗模式改由 `PPN-06` 的語句數不變性擋 |
| 前端快取專案／系統清單 | 清單是授權結果：被移出後若仍讀快取，畫面會顯示已無權存取的專案（與 `AC12.6.2` 方向相反）。每次進頁重讀 |
| 批次端點（一次回多個系統的欄位或變更紀錄） | `[PP1]` 選項 A 與 `BR87.4` 已定「路徑與回應形狀不變」；新增端點是另一個範圍 |
| 首屏繪製時間、bundle 大小 | 本單元新增三頁沿用既有 Vite 建置與路由，無新依賴（`tech-stack-decisions.md`）；無既有預算可對照 |
