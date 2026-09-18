# Code Generation Plan — backend-activity-policy（U1）

> Stage: code-generation（Construction 3.5）· Unit: `backend-activity-policy`（C-1、C-2、C-3）
> 上游輸入：本單元的 `../functional-design/{business-logic-model,business-rules,domain-entities}.md`、`../nfr-requirements/*`、`../../../inception/application-design/decisions.md`（AD-1、AD-3、AD-4、AD-6、AD-8）。

## 落點對照

| 元件 | 檔案 | 性質 |
|---|---|---|
| C-1 活動時間政策 | `backend/services/activity.py` | **新檔** |
| C-2 活動時間記錄器 | `backend/services/activity.py`（同檔）＋ `backend/services/auth.py` 的掛載點 | 新函式 ＋ 既有函式加一行 |
| C-3 資料模型 | `backend/models.py` | 既有 model 加一欄 |
| C-3 既有環境補欄 | `backend/database.py` 的 `_ensure_last_activity_schema()` | 新函式，掛進既有的 `init_db()` |
| 部署資產同步（blocking） | `schema_rbac.sql`、`DEPLOY.md` | 既有檔案 |

**C-1 與 C-2 同檔的理由**：兩者一起構成「這次活動要不要記、要記什麼」這一件事，且 C-2 是 C-1 唯一的呼叫端。分兩檔會讓一個 30 行的政策獨自成模組，與本 repo「engine／service 類純函式模組」的既有粒度不符。C-1 的兩個判定仍是**零 I/O 的純函式**，可被單元測試與 property-based 測試直接呼叫 —— 那才是 AD-4 要保住的性質，不是檔案數。

## 順序與理由

1. `models.py` 加欄 → 2. `activity.py`（純函式先於記錄器）→ 3. `auth.py` 掛載 → 4. `database.py` 補欄補丁 → 5. 部署資產同步 → 6. 測試。

第 4 步**不可省**：`create_all` 不會 ALTER 既有表。省掉它的後果是 staging 上每個已認證請求都會失敗，**而 CI 全綠** —— 測試以 in-memory SQLite 直接建表、從不經過 `init_db()`。

## 測試計畫

| 測試 | 涵蓋 | 落點 |
|---|---|---|
| 兩個判定的邊界 | 5 分鐘含等於、90 天不含等於、無紀錄態、未來時間、naive datetime | `tests/test_activity.py` |
| property-based | 兩個判定在整段區間上的單調性（`@given` × 4） | 同上 |
| 記錄器的提交契約 | 寫入後重新讀出確認**真的提交了** | 同上 |
| 節流的可觀測行為 | 視窗內不更新、視窗後更新、只留最後一次 | 同上 |

**已知缺口（沿自設計，未消除）**：C-2 的「失敗先復原」分支與 C-3 的既有環境補欄**無自動化驗證**。前者需要注入資料庫失敗，後者需要真實的 ALTER 路徑；承接方式為部署後重啟 ＋ 人工核對。**本輪已在真實 docker stack 上實際驗證後者**（見 code-summary）。
