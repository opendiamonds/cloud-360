# 安全需求 — `U5 memory-data`

> 本站承接 `functional-design` 的 13 條規則（`BR1.1`–`BR4.3`）與 7 項開放缺口。
> **本站不複寫那 13 條**——`team.md` 的「單一真實來源」規則禁止在無鎖住一致性
> 的測試時新增副本。本檔只處理**本站新定案**的三件事。

## 〇、上游依據（逐一指名，含檔名）

| 上游產出 | 本站用到它的什麼 |
|---|---|
| `rules.md`（本單元 `functional-design`） | 13 條規則，特別是 `BR3.3`（`fulltext` 模式下 `embedding` 為 NULL——這是否決欄位層加密的關鍵）、`BR2.2`（稽核不含記憶內容——這是保存期討論的前提）、`BR4.2`（清除不得由 `backend/` 排程程式承載） |
| `functional-spec.md`（本單元） | §一 的 `DG-1` 處置與其兩項代價；`OPEN-M2`（稽核保存期未定）與 `OPEN-M4`（`OQ-3` 的風險鏈）——本站關閉這兩項 |
| `requirements.md` | `FR4.5`／`FR4.5a`／`FR4.7`（保存期與稽核）、`NFR6`（schema 隔離與驗證）、`NFR7`、`OQ-3`（加密手段，本站關閉） |
| `contract-summary.md` | 契約 `K-05` 的 `verification.why_not_existing_tests`（既有測試對本契約零驗證能力）與 `retry_and_idempotency`（無資料遷移，故不需遷移工具）；契約 `K-01` 對 `OLLAMA_EMBED_MODEL` 的 validation（1024 維的來源） |
| `unit-of-work.md` | `:248` 把 `OQ-3` 指派給 `nfr-design` 並點名其風險鏈——**這是本站必須就地定案的理由** |
| `technology-stack` | 本 repo 為 brownfield，既有技術棧記載於 `project.md` 的 `## Tech Stack`（PostgreSQL）與 `team.md` 的 `## Testing Posture`（`unittest`、未使用 pytest、`tests/helpers.py` 改走 in-memory SQLite）。本單元**不變更**其中任何一項，唯一新增的技術層是 pgvector（見 `tech-stack-decisions.md` §一） |

## 一、本站定案了什麼（而非承接）

| id | 需求 | 二元判準 | 來源 |
|---|---|---|---|
| **`NFR6.1`** | episodic memory 的**靜態加密**由**主機層**承載（磁碟／LUKS），不在應用層或資料庫欄位層 | 部署文件載明該主機的磁碟加密狀態；**本 repo 無法驗證它**（見 §三） | 使用者裁決 `[M2]`=A（2026-10-06），關閉 `OQ-3` 的靜態面 |
| **`NFR6.2`** | 記憶層的**傳輸**為 compose 內部流量，不跨主機邊界；**不要求 `sslmode`** | `DATABASE_URL` 的主機名為 compose 內部服務名（`db`），非 `localhost`、非對外 IP。`validate_env_contract.py` 已擋 localhost 來源滲透 | 使用者裁決 `[M2]`=A，關閉 `OQ-3` 的傳輸面 |
| **`NFR7.2`** | `memory_audit_events` 的保存期為 **90 天，以其自身 `occurredAt` 為鍵**（**不隨記憶消失**） | 清除查詢的 WHERE 條件為 `occurredAt < now() - 90 days`，**不是** join 到 `memory_records` 的時間 | 使用者裁決 `[M4]`=A（2026-10-06），關閉 `OPEN-M2` |

## 二、`OQ-3` 為什麼在本站定案而不是往下推

`unit-of-work.md:248` 把 `OQ-3` 指派給 `nfr-design`，而**那一站是 CONDITIONAL
且其條件依賴本站是否執行**（與 `OQ-4`／`OQ-10` 同一條風險鏈）。
本站是 **ALWAYS**，故**是攔截它的唯一機會**；若推給 `nfr-design` 而該站 skip，
沒有任何機制會提醒（這正是 `OPEN-M4` 記載的風險）。

### 查證過的部署現況（結論建立在這些事實上，非推測）

| 查證項 | 結果 |
|---|---|
| PG 的資料落點 | compose 具名 volume `db_pg18:/var/lib/postgresql/data`，**未加密** |
| 連線字串 | `postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}`，**無 `sslmode`** |
| `db` 是什麼 | compose **內部服務名**——流量不離開 docker 網路 |
| 全樹加密設定 | **零命中**（無 `pgcrypto`、無 `sslmode`、無 `encrypt`） |

### 為什麼不選欄位層加密

對 `content` 做 `pgcrypto` 或應用層加密會**破壞已核可的 `fulltext` 模式**：

- `BR3.3`（＋ `ADR-008`）定下 `fulltext` 模式為支援的降級路徑，該模式下
  `embedding` 為 NULL、**以全文檢索承載**；
- **密文無法全文檢索**，且 embedding 的產生本身需要明文。

故欄位層加密不是「更安全的同一個設計」，而是**取消一個已核可的能力**。
`[M2]`=A 是三個加密選項中**唯一不破壞既有能力**的，且應用層變更為零。

## 三、`NFR6.1` 的誠實缺口：本 repo 無法驗證它

把靜態加密交給主機層的代價必須寫明：**本 repo 沒有任何機制能確認
`192.168.10.10` 的磁碟真的加密了**。

- 它不是 CI 可檢查的事實（CI 跑在 GitHub runner 與自架 runner，不是資料庫主機）；
- 它不是應用層可檢查的事實（PG 看不到底層區塊裝置的加密狀態）；
- 故它是一個**運維承諾**，不是一道閘門。

記為 `OPEN-N5-1`，承接站 `infrastructure-design`（本單元的下一站，
但**該站為 CONDITIONAL**，故轉移目標為 `code-generation`，ALWAYS）。

**不把它寫成「已滿足」**：ADR-0006 的 encryption 面對本單元是**適用**的
（`unit-of-work.md:248` 逐字），而本站的處置是「指定承載層並揭露其不可驗證性」，
不是「已解決」。

## 四、`NFR7.2` 的兩個衍生決定（本站一併定案，避免下游懸空）

使用者的裁決是「稽核以自身 `occurredAt` ＋ 90 天為獨立時鐘」。這逼出兩個
下游必須知道的子決定，本站就地定案：

1. **「清除稽核事件」這個動作本身不留稽核紀錄。**
   理由是**無終止遞迴**：若清除稽核要留稽核，那筆新紀錄 90 天後又要被清除、
   又要留一筆……永不收斂。`FR4.7` 的文字是「**記憶的**刪除動作應留下稽核紀錄」
   ——它約束的對象是記憶，不是稽核本身。故本決定不違反 `FR4.7`。
2. **清除稽核的機制同受 `BR4.2` 約束**：不得由 `backend/` 內的排程程式承載，
   須走 gh-aw 或 GitHub Actions workflow，且決定性的映射邏輯放在純 Actions 步驟。
   這意味著 `N-6` 實際上要清**兩種**資料（逾期記憶 ＋ 逾期稽核事件），
   而上游只寫了前者——記為 `OPEN-N5-2`。

**`FR4.7` 的實際滿足窗口因此是明確的**：記憶在建立後 90 天被清除，
該清除事件再活 90 天。即「刪除留稽核」在刪除後**有 90 天**是真的成立的，
而非上一輪選項 ① 之下的**零秒**。

## 五、ADR-0006 四面向：本站的增量

| 面向 | 本站的增量 |
|---|---|
| **IAM** | 無增量。grant 邊界已由 `BR1.2` 承載（`functional-design`） |
| **Encryption** | **本站定案**：`NFR6.1`（靜態→主機層）、`NFR6.2`（傳輸→compose 內部）。關閉 `OQ-3`，並揭露 `NFR6.1` 不可由本 repo 驗證（`OPEN-N5-1`） |
| **Network exposure** | 無增量。本單元零端點、零進程、零監聽埠 |
| **Audit logging** | **本站定案**：`NFR7.2`（稽核保存期 90 天，以自身 `occurredAt` 為鍵）＋ 兩個衍生決定（清除稽核不留稽核、清除機制同受 `BR4.2`） |

**PBT 判定：N/A（非豁免）**，同 `functional-design` 的判定——本單元是 DDL 與
grant，沒有任何函式可施加 property。
