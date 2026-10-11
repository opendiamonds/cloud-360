# 安全設計 — `U5 memory-data`

> 本站設計上游 `nfr-requirements` 定案的三項 NFR 的**承載形式**：
> `NFR6.1`（靜態加密）、`NFR6.2`（傳輸）、`NFR7.2`（稽核保存期）。
> 本站**不複寫** `functional-design` 的 13 條規則（`team.md` 的單一真實來源）。

## 一、上游依據

| 上游產出 | 本站用到它的什麼 |
|---|---|
| `security-requirements.md`（本單元） | `NFR6.1`／`NFR6.2`／`NFR7.2` 三項定案 ＋ 兩個衍生子決定（清除稽核不留稽核、清除機制同受 `BR4.2`）＋ 三項開放缺口 |
| `tech-stack-decisions.md`（本單元） | pgvector 為唯一新技術層；`N-2` 是交付物而非既有能力；`OPEN-N5-3`（image 是否含 pgvector 未查證） |
| `rules.md`（本單元 `functional-design`） | `BR2.1`（稽核不設外鍵——這是本站索引設計的前提）、`BR2.2`（稽核不含內容）、`BR4.2`（清除的承載形式） |
| `entities.md`（本單元 `functional-design`） | `memory_audit_events` 的欄位集合——**本站查出它沒有 `occurredAt` 索引**，見 §四 |
| `contract-summary.md` | 契約 `K-05` 的 `invariants` 與 `verification` |

## 一之二、四個判為不適用的面向：本站同樣無 pattern，理由承接上游

上游 `nfr-requirements` 把四個面向判為不適用，本站逐一確認**無 pattern 可設計**，
並指名承接的檔名以免被讀成漏做：

| 上游產出 | 其判定 | 本站 |
|---|---|---|
| `performance-requirements.md` | 不適用（無新延遲預算或吞吐目標） | 無 pattern。**唯一與效能相關的設計在 §四之二**——`occurredAt` 索引，但它是清除作業的前提而非使用者可見的效能目標 |
| `scalability-requirements.md` | 不適用（非獨立擴展單位） | 無 pattern。schema 不是擴展單位 |
| `reliability-requirements.md` | 不適用（無外部依賴邊界；DDL 可重跑由 `BR1.3` 承載） | 無 pattern |
| `observability-requirements.md` | 不適用（不新增監控目標） | 無 pattern。**附帶**：稽核屬 audit logging 面而非觀測面，設計在 §四 |

`functional-spec.md`（本單元）的 §四「本單元**不**負責的事」是上述判定的依據——
本單元零端點、零進程、零監聽埠，故效能／擴展／可靠性／觀測四面皆無承載對象。

## 二、`NFR6.1`（靜態加密）：沒有應用層 pattern，而這件事本身要設計

上游把靜態加密定在**主機層**（`[M2]`=A），故本站**沒有**加密 pattern 可設計
——沒有金鑰管理、沒有輪替、沒有 envelope encryption、沒有 `pgcrypto` 呼叫點。

**但「沒有 pattern」不等於「沒有設計責任」。** 本站的設計產出是
**讓這個決定不會被誤讀成已滿足**的三項：

1. **DDL 層不得出現任何加密痕跡**。若日後有人在 `memory_records.content` 加上
   `pgcrypto` 呼叫，那會**破壞已核可的 `fulltext` 模式**（`BR3.3`）而不是強化安全。
   故這是一條**禁止**，不是留白。
2. **`DEPLOY.md` 必須載明該主機的磁碟加密狀態**（`code-generation` 的 blocking
   同步項之一）。這是唯一能讓運維承諾被看見的地方。
3. **不得在任何產出宣稱「episodic memory 已加密」**。正確的說法是
   「靜態加密由主機層承載，本 repo 無法驗證」（`OPEN-N5-1`）。

## 三、`NFR6.2`（傳輸）：設計成一個可被現有檢查部分守住的不變量

上游定案「compose 內部流量、不要求 `sslmode`」。這個結論**成立的條件**是
一個不變量，而不是一個事實：

> **`DATABASE_URL` 的主機名必須是 compose 內部服務名。**

若它變成對外 IP 或跨主機位址，`NFR6.2` 的前提立刻不成立而**連線照樣會成功**
——這是本項的靜默失敗模式。

**部分守得住，誠實說明覆蓋範圍**：`validate_env_contract.py` 已檢查
「dev 與部署設定不得互相滲透（localhost 來源、`POSTGRES_*` 等）」，
故它**擋得住 `localhost` 滲進部署設定**；但它**不是**一條「主機名必須是
compose 服務名」的通用規則。

| 情境 | 現有檢查 |
|---|---|
| `localhost` 寫進 `deploy/.env.example` | **擋得住** |
| 主機名改成對外 IP（如 `10.0.0.5`） | **擋不住** |

故本站把後者記為 `NFR6.2` 的殘餘缺口，**不宣稱已完整守住**。

## 四、`NFR7.2`（稽核保存期）：本站唯一的實質設計產出

### 4.1 清除查詢的形狀

```sql
DELETE FROM memory.memory_audit_events
WHERE occurred_at < now() - INTERVAL '90 days';
```

**關鍵是它不 join `memory_records`。** 這直接來自 `BR2.1`（不設外鍵）與
使用者裁決 `[M4]`=A（以自身時鐘為鍵）：

- join 的版本會讓 `purged_by_retention` 事件**出生即逾期**
  （它在記憶建立後 90 天才產生）；
- 不 join 的版本讓它在清除後再活 90 天，`FR4.7` 因此有一個**真實的**滿足窗口。

### 4.2 **本站查出的缺口：`occurredAt` 沒有索引**

`entities.md` 定義了 `occurredAt` 欄位，但**沒有為它建索引**。
上述清除查詢以該欄為截止條件，**沒有索引就是全表掃描**。

**這個缺口有先例可循**：`U4` 的 DDL 對自己的變更紀錄表就為此建了索引，
並逐字寫下理由——「90 天保存期的清除查詢以 `created_at` 為截止欄位，
沒有這個索引它是全表掃描，而這張表**沒有任何讀取端**會順手建索引」。

`memory_audit_events` 的處境**完全相同**：本輪它的讀取面是回補項 `N-8`
（屬 `U8`），所以**不會有任何讀取端順手建這個索引**。

**本站的設計決定**：`memory.memory_audit_events` 必須有
`occurredAt` 的索引，落點 `code-generation` 的 DDL。
以 `IF NOT EXISTS` 形狀撰寫（`BR1.3`）。

### 4.3 清除機制的兩個目標與其約束

`N-6` 現在要清**兩種**資料（`OPEN-N5-2`）：

| 目標 | 截止鍵 | 落點 |
|---|---|---|
| 逾期的 episodic 記憶 | `memory_records.expiresAt` | `U9` ＋ `N-6` |
| 逾期的稽核事件 | `memory_audit_events.occurredAt` | 同上 |

兩者同受 `BR4.2`：不得由 `backend/` 內的排程程式承載，
且決定性的映射邏輯須在**純 Actions 步驟**而非 gh-aw 的 LLM 路徑。

**順序有關係**：清除記憶會**產生**稽核事件（`BR4.3`），所以同一次執行中
應先清記憶、再清稽核——反序會讓剛產生的事件在同一輪就被誤判（它的
`occurredAt` 是現在，不會被選中，故實際上無害，但順序寫明可避免下一個人困惑）。

**清除稽核本身不留稽核**（上游子決定），理由是無終止遞迴。

## 五、ADR-0006 四面向：本站的增量

| 面向 | 本站的增量 |
|---|---|
| **IAM** | 無增量（`BR1.2` 的 grant 邊界已足） |
| **Encryption** | 三項「讓決定不被誤讀」的設計（§二）：DDL 不得出現加密痕跡（且說明為何那是禁止而非留白）、`DEPLOY.md` 須載明主機加密狀態、不得宣稱已加密 |
| **Network exposure** | `NFR6.2` 的不變量化（§三）＋ 誠實的覆蓋範圍表（擋得住 `localhost`、擋不住對外 IP） |
| **Audit logging** | **本站的實質產出**：清除查詢形狀（不 join）、**`occurredAt` 索引**（否則全表掃描，有 `U4` 的同形先例）、兩個清除目標與其順序 |

**PBT 判定：N/A（非豁免）**，同上游兩站——本單元是 DDL 與 grant，無函式。

## 六、殘餘風險

1. **`NFR6.1` 不可由本 repo 驗證**（`OPEN-N5-1`，承接自上游）。
2. **`NFR6.2` 只被部分守住**（§三）：對外 IP 的情境無檢查。
3. **`occurredAt` 索引若漏做，失敗模式是效能而非正確性**——清除照樣正確，
   只是全表掃描。故它**不會被任何測試抓到**，只會在資料量成長後表現為慢查詢。
   這使它容易在 `code-generation` 被省略，故本站把它寫成明確的 DDL 要求而非建議。
