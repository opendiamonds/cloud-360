# External Dependency Map — 外部依賴盤點

> Stage: delivery-planning（Inception 2.8）· Intent: 260802-last-login-column
> 上游來源：`../requirements-analysis/requirements.md`（下稱 requirements）、`../user-stories/stories.md`（下稱 stories）、`../refined-mockups/mockups.md`（下稱 mockups）、`../application-design/components.md`（下稱 components）、`../units-generation/unit-of-work.md`、`unit-of-work-dependency.md`、`unit-of-work-story-map.md`、`../practices-discovery/team-practices.md`（下稱 team-practices）。

## 結論：無外部門控項目

逐項盤點 stage 檔列舉的四類外部依賴，**四類皆無**：

| 類別 | 本 intent 的情況 | 判定 |
|---|---|---|
| **外部 API** | 本 intent 的全部行為落在自有 backend、frontend 與 PostgreSQL。application-design 的 AD-5 已定案不引入外部服務；唯一的新增依賴（AD-9 的型別產生工具）是**建置期的 devDependency**，非執行期的外部服務呼叫 | 無 |
| **資料可得性窗口** | 新欄位的資料由系統自己產生（認證請求觸發寫入），無需等待外部資料源。requirements C-1 已記載「系統無任何既有活動紀錄且無可回填來源」—— 這是**已接受的空窗**，非待等待的外部依賴 | 無 |
| **審批前置期** | 本 intent 不觸及 production（requirements C-8：雲端供應商 production 不在本 repository 範圍），無 IaC apply、無 IAM 變更需要跨組織審批。權限矩陣的變更是本專案自有資料，由本 workflow 的 gate 承擔 | 無 |
| **外部團隊交接** | 單一決策者專案，無跨團隊交接（見 `team-allocation.md`） | 無 |

## 為何本檔近乎空白，而這是正確的

stage 檔明示此產出「**Lightweight or empty when fully AI-contained**」。本 intent 正是完全自我涵蓋的情況：

- 部署目標是**自有 staging**（`192.168.10.10`，經 Cloudflare Tunnel 對外），非雲端供應商環境
- CI 全部跑在既有的 GitHub Actions 與自架 runner 上
- 資料庫、後端、前端、對外通道四個服務全部在自有編排內

**不為了填滿版面而虛構條目** —— 捏造「等待某某 API」這類假依賴會讓真正有外部依賴的下一個 intent 讀到這份文件時失去判斷基準。

## 唯一接近「外部」的一項：新的 devDependency

| 項目 | 性質 | 對哪個 Bolt 有影響 | 緩解 |
|---|---|---|---|
| 型別產生工具（AD-9／C-8） | **建置期的套件依賴**，非執行期外部服務 | B3 | 套件解析失敗只會讓 CI 紅燈，不影響已部署的服務；且該工具只在開發與 CI 執行，不進生產環境的執行路徑 |

嚴格說它不是 stage 檔所指的「外部依賴」（無擁有者、無前置期、無需協調），但它是本 intent 唯一**來自 repo 外部**的新東西，故在此登記以免被完全忽略。

## 內部的門控項目（不屬本檔範圍，但指出落點）

下列事項會擋住 Bolt 完成，但它們是**內部**的，記於其他文件：

| 門控 | 記於 |
|---|---|
| requirements C-4 的部署資產同步（blocking） | `bolt-plan.md` 各 Bolt 的 Definition of Done |
| 部署後必須重啟才生效（B1、B2） | `bolt-plan.md`「Bolt 間的交付約束」 |
| 人工核對事項（三類） | `team-allocation.md`「人工必須介入的三類事」 |

---

## Revision 1（2026-08-11）— PU-6 使用者清單分頁

**外部依賴無變化。** C-9 不新增任何外部服務、外部 API 或第三方帳號需求（AD-5 維持成立，`services.md` Revision 1 已複驗）。

唯一相關的既有外部依賴是 **npm registry**（U5 的型別產生器 devDependency，Revision 1 之前已記載）—— C-9 使規格檔多出一個 schema 與兩個查詢參數約束，但不新增任何套件。
