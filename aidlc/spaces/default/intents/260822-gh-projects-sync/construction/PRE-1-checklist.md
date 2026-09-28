# PRE-1 執行清單 — 憑證與框架上限的實測

<!-- 產生於 code-generation stage（2026-08-30T12:43:29Z，讀自 date -u），因 U-3 的完成判準需要它。
     正式定義在 `<record>/inception/user-stories/stories.md` §PRE-1（CAP-9；FR-I3、FR-I4）。
     本檔是那份定義的可執行化，不新增任何要求。 -->

## 為什麼現在要做

`stories.md:323` 把 PRE-1 列為**技術依賴**並寫明：**「憑證確實帶組織層看板寫入權未經實測前，任何寫入路徑都無法完成」**，橫跨 S-1～S-10。

U-3（看板客戶端）是全部寫入路徑的載體，完成判準為「**真實** Projects v2 API 讀寫，對**獨立測試 Project**」（ADR-A3）。而本 repo **無 Projects v2 先例**——實測 `.github/workflows/*.yml`，`graphql` **零命中**，查詢字串、錯誤碼對應、分頁游標全部新寫。未經真實呼叫的這類程式碼，信心很低。

## 你要做的事

### 步驟 1 — 鑄憑證

需要**組織層**（`opendiamonds`）的權限，可能需要組織管理員核准。

ADR-0014 對本項有擴充要求：**須涵蓋三項權限各至少一次真實呼叫，其中必須包含一次開 issue**。

> **只驗 Projects 寫入不構成通過**——缺 Issues 寫入權的憑證會讓本項看起來通過，而在 Bolt 1 才失敗。

需要的權限（依 ADR-0015 §8，**四項**）：

| 權限 | 用途 |
| --- | --- |
| Projects: read & write（**組織層**） | 讀寫 Project #16 的 item 與欄位 |
| Issues: write | 開 issue、寫 issue body 的受管區塊 |
| Contents: write | record 回寫（`sync-state.json`、綁定編號） |
| Pull requests: write | 反向同步開 PR |

### 步驟 2 — 存進 secrets，**然後實地查證**

```bash
# 存
gh secret set AIDLC_SYNC_TOKEN --repo opendiamonds/cloud-360

# 查證它真的在 secrets 而不是 variables（兩邊各查一次，比對名稱）
gh api repos/opendiamonds/cloud-360/actions/secrets   --jq '.secrets[].name'
gh api repos/opendiamonds/cloud-360/actions/variables --jq '.variables[].name'
```

> **這一步不可略過**（`project.md ## Mandated` 明文）。Actions variables 為**明文、UI 可回讀、workflow log 中不遮罩**，而本 repo 是 **public**、Actions log 公開可讀——一次意外 `echo` 即等同公開發布。
>
> **若憑證曾誤存為 variable，僅搬到 secret 不足以結案，必須重新產生金鑰**：「應該沒人看過」是沒有證據的假設。

### 步驟 3 — 開一個獨立測試 Project

ADR-A3 要求驗證**不得**打到正式的 Project #16。開一個組織層的空 Project，記下它的編號。

### 步驟 4 — 四項實測

| # | 要確認的事 | 為什麼 | 來源 |
| --- | --- | --- | --- |
| 1 | 憑證確實帶組織層看板寫入權，**三項權限各至少一次真實呼叫、必含一次開 issue** | 不得以文件敘述代替驗證 | FR-I3、ADR-0014 |
| 2 | 框架單次操作次數上限（C-T5）的**實際值**，以及超限時的行為（截斷／報錯／**靜默略過**） | 「靜默略過」是最壞情形，它不會紅燈 | FR-I4 |
| 3 | `createProjectV2Field` **是否可用** | 它決定 [US:S-5 AC 2] 走哪一支 | FR-I4 |
| 4 | 順帶回答 A-1（組織政策是否阻擋 App 安裝）、A-2（變數名與文件描述不一致）、A-3（看板更新行為是否如文件所述）、A-8（同步身分對 feature 分支的寫入權是否受分支保護阻擋） | 四個未驗證假設 | stories.md §PRE-1 |

> **第 3 項的措辭更正已在上游記載**：`requirements.md` 的 A-5 原寫「平台未支援」是錯的——ADR-0012 `:23-24` 的實測結論是「**gh-aw 的 safe-outputs** 沒有 Projects 操作，必須提權讓 workflow 直接呼叫 `gh` CLI／GraphQL」。**「未支援」的主體是 gh-aw，不是 GitHub 平台。**

### 步驟 5 — 另一項待實測（U-10a 的殘留缺口）

**PRE-1-a**：Repository Rulesets 的 **file-path restriction** 是否可行。

這一項的後果比它看起來大：**若不可行，[US:S-10 AC 5] 的第二個例子（「改 record 目錄以外的檔案應回 403」）在現行設計下無機制可產生**，那條 AC 必須回 user-stories 改寫。

同時，U-10a 的 `pull_request` 側 `if:` 判準需要 bot 身分的**實際值**——那要等憑證鑄出來才確定（已登錄，指派 code-generation 實作 `ci.yml` 時定案）。

## 回來之後

把四項（＋PRE-1-a）的**實際結果**告訴我，我會：

1. 依實測值寫 U-3（例如上限值進 `Config`、`createProjectV2Field` 的可用性決定 S-5 AC 2 走哪一支）
2. 對測試 Project 真跑一次，驗完成判準（回讀不符時回 `Aborted` 且**不送出寫入**；重複執行首建不產生第二則 issue）
3. 接著跑 U-4～U-10b

**不需要你整理成文件**——直接講結果就行，包括失敗的那些（尤其第 2 項若是「靜默略過」，那會改變 U-3 的錯誤處理設計）。
