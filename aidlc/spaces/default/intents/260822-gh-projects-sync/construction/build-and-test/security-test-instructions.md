# Security Test Instructions — AI-DLC ↔ GitHub Projects 同步機制

<!-- Stage: build-and-test（Construction）· 上游：12 個單元的 security-requirements.md · ADR-0006 為 hard constraint -->

## 本系統的威脅模型是「一支高權限機器人在一個公開 repo 裡自動改東西」

不是 web 應用，沒有使用者輸入、沒有 SQL、沒有 XSS。OWASP Top 10 之中真正適用的只有三條：
**Broken Access Control**（誰能觸發它、它能寫什麼）、**Security Misconfiguration**
（憑證放哪、分支保護擋不擋）、**Logging Failures**（公開 log 洩漏什麼）。其餘七條在
`.claude/knowledge/aidlc-devsecops-agent/security-guide.md` 的意義下不適用——**逐條寫下
不適用比只列適用的那幾條有用**，因為它讓「是不是漏看了」變成可核對的事實。

## ADR-0006 四面向：本階段的實地查證結果

`project.md ## Mandated` 要求對每一項變更檢查四面向。各單元的
`security-requirements.md` 都有自己的判定表，本階段**不重抄，只做一件上游做不到的
事——把宣稱拿去對真實 GitHub 查證**。以下四項為本階段以 `gh api` 實跑的結果
（2026-09-06，帳號 `opendiamonds`）：

| 面向 | 查證指令 | 實測結果 |
| --- | --- | --- |
| IAM | `gh api repos/opendiamonds/cloud-360/actions/secrets --jq '.secrets[].name'` | 11 個 secret，**`AIDLC_SYNC_TOKEN` 不在其中** |
| IAM | `gh api repos/opendiamonds/cloud-360/actions/variables --jq '.variables[].name'` | 2 個 variable（`APP_ID`、`GH_AW_DEFAULT_MODEL_COPILOT`），**同步憑證不在其中** |
| network exposure | `gh api repos/opendiamonds/cloud-360 --jq '.visibility'` | **`public`** |
| audit logging | `gh api repos/opendiamonds/cloud-360/branches/{ut,main}/protection` | `ut`：`required_status_checks: null`、`enforce_admins: false`；`main`：唯一 check 為 `Repository contract`、`enforce_admins: true` |

encryption 一項對本 intent **不適用**：沒有自建的傳輸或儲存通道，全部經 GitHub API
（TLS）與 GitHub 自身的儲存。**不適用要寫理由，不留空白**。

## 現在就能跑的安全檢查

### S-T1：新增檔案不得含硬編碼憑證

```bash
git status --porcelain | grep -v '^??' | awk '{print $2}' > /tmp/f
find .github/actions .github/workflows/aidlc-sync-*.yml -type f ! -path '*__pycache__*' >> /tmp/f
sort -u /tmp/f | grep -v '^aidlc/spaces/default/intents/' | xargs grep -nEi \
  'gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----'
```

**本輪實測：97 個檔案，2 處命中，兩處都是刻意的合成假 token**
（`run-stub-tests.py:891`、`:921`，用來測遮罩邏輯本身）。判準是**每一處命中都要能指出
它為什麼是假的**，不是「零命中」——遮罩測試需要一個看起來像 token 的字串。

> 附帶記錄（Minor）：這兩個字面值落在一個 **public** repo 裡，naive 的第三方掃描器會
> 命中它們。GitHub 自身的 secret scanning 會驗證 token 有效性所以不會告警，但外部工具
> 不一定。已知並接受，不是待辦。

### S-T2：憑證不得成為 composite action 的 input

```bash
grep -n "^  *[a-z_]*token[a-z_]*:" .github/actions/*/action.yml
```

判準：**零命中**。四支 action.yml 的註解逐字寫明理由（「把憑證放進介面等於邀請每一個
呼叫端傳一個你手上有的 token」），且 `run-stub-tests.py` 有機械斷言鎖住它。憑證一律經
`env:` 由配置好的 workflow 傳入。

### S-T3：同步判定不得落在 LLM 步驟內

```bash
python3 .github/actions/aidlc-sync-selftest/check-agentic-steps.py
```

這是本 repo 三塊結構性盲區之一（所有 LLM 路徑）的守衛。**它的掃描面以「執行可達性」
界定而非「檔案位置」**——遞迴解析 `python3 X`／`bash X`／`source X`／`./X`，解不開者
fail-closed。這一點是它前兩版被打穿兩次之後換的原則：位置型邊界每一輪都有下一格，
總數不收斂。改動它之前先讀 U-9 `code-summary.md` 的 C-1 節。

### S-T4：`ci.yml` 的四個 job 未被靜默改動

```bash
python3 .github/actions/aidlc-sync-ci-guard/check-ci-yml.py     # 19 項，含 SEC-1a〜1d
python3 .github/actions/aidlc-sync-ci-guard/run-probe-tests.py  # 13 項行為測試
```

**兩支都尚未接進任何 workflow**，目前要靠人記得手動跑（U-10a 的 Plan Approval 裁決項 2：
接進 `repo-contract` 會變成 `ci.yml` 檢查自己）。**「19 項全綠」不等於「這些設定受保護」。**

## 三項必須在 gate 上被看到的風險（本階段查證，不自行處置）

### K-1：`[aidlc-sync]` 標記可被任何有推送權的人使用，而沒有任何東西擋那次合併

U-10a 的 `gate` job 讓帶 `[aidlc-sync]` 的 commit 跳過 `ci.yml` 全部四個 job。標記是
**commit 訊息裡的一段文字**，任何有推送權的人都放得進去。

本階段以 `gh api` 複驗了它的第二半，結果比 U-4 `security-requirements.md` 的 SEC-2 記載
的更嚴重：

- `ut` 的 `required_status_checks` 為 **`null`**（整個 key 不存在）、`enforce_admins: false`
  ⇒ **`ut` 上沒有任何 required check，跳過四個 job 之後合併不會被擋**；
- `main` 唯一的 check 是 `Repository contract`，而 GitHub 官方文件逐字
  「Successful check statuses are success, **skipped**, and neutral」⇒ 被 skip 時視同通過。

**而 `ut` 正是每個 Bolt 的合併目標，且 deploy-on-merge 掛在它上面**（ADR-0007）。
指派 Bolt 1 gate。

### K-2：公開面比一般直覺大

repo 為 `public`，因此下列全部是匿名可讀：

| 內容 | 落點 | 上游登錄處 |
| --- | --- | --- |
| record 全文 | Actions log | U-1 SEC-1 |
| 受管區塊 | issue body | U-2 SEC-2 |
| 失敗通報內容 | 公開 issue | U-5 SEC-2 |
| 對帳報告與一致率 | 公開的 job summary | U-7 SEC-2／SEC-3 |

遮罩是**部分**有效的：`notify.sh` 的清洗能擋 `Authorization:` 那一類，但 token 被空白或
換行任意切割時仍會逃逸。**三條殘留形狀寫在程式碼註解、以註解而非斷言記載於測試**——
把弱點斷言成「預期行為」會讓日後真要補強它的人看到紅燈。遮罩防的是不小心貼上，不是
刻意規避。

**另一項**：README 的看板連結**匿名存取回 404**（Project #16 為 `public: false` 而 repo
為 public）。ADR-0016 §9 只授權修 URL 形狀，「public repo 的 README 宣告需求正本在一個
外部讀者打不開的看板」是產品決定，未逕自處置。

### K-3：權限大於需要，且沒有更細的收斂手段

- U-3 `security-requirements.md` SEC-2 逐字：「本單元拿到的權限**大於**它需要的」。
- ADR-0016 把寫入身分由 GitHub App 改為擁有者 token 之後，**`repo` scope 整包涵蓋
  contents／issues／PR 寫入，沒有 App 那種細緻權限可收斂**。`requirements.md` 的 OQ-1
  （把 repo 內容寫入權收斂到最小）候選手段幾乎耗盡。
- 測試看板 #23 與正式看板 #16 的**隔離只靠 `AIDLC_PROJECT_NUMBER` 這個設定值，不靠
  權限**——同一份憑證同時寫得了 #16。live runner 的 `exit 4` 防呆是唯一防線。

這三項在 ADR-0016 已正面寫出，本階段只補上「已用 `gh api` 複驗」這一層。

## 已知的機制落差（不是本 intent 造成的，但會影響對本 intent 的信心）

`validate_no_obvious_secrets()`（`scripts/validate_repo_contract.py`）只讀
`contract_files()`——**`backend/`、`frontend/`、`deploy/`、`.github/` 都不在其中**。
本 repo 唯一的 secret 掃描器結構上看不到本 intent 交付的任何一支程式。這是 `team.md`
已登錄的既有落差，S-T1 是本階段對它的手動補償，**不是替代品**。

## 本階段沒有做的（誠實列出）

| 項目 | 為什麼 |
| --- | --- |
| SAST（Bandit／Semgrep） | 本 repo backend 完全沒有 linter／formatter／type checker（`team.md` 既成事實）；為本 intent 單獨引入一套掃描器是獨立的工具鏈決策，不由本階段夾帶 |
| 依賴 CVE 掃描 | 本 intent 的交付物**零第三方依賴**（除 PyYAML 外全是標準庫）；沒有可掃的依賴清單 |
| DAST | 沒有 running application |
| U-9 第二段的 403 斷言 | 該狀態在組織層授權下**不可達**——見 `integration-test-instructions.md` |

## 與上游的對應

四面向的判定表引自 12 個單元的 `security-requirements.md`；`[aidlc-sync]` 標記的可觸發性
引自 U-4 SEC-2 與 U-10a SEC-1，分支保護的實測為本階段以 `gh api` 取得；公開面清單引自
U-1 SEC-1／U-2 SEC-2／U-5 SEC-2／U-7 SEC-2；遮罩的三條殘留形狀引自 U-5 的
`code-summary.md`；權限收斂手段耗盡引自 ADR-0016 §4 與 `requirements.md` OQ-1；
兩支守衛未接進 workflow 的理由（接進 `repo-contract` 會變成 `ci.yml` 檢查自己）引自
U-10a `code-generation-plan.md` 的 Plan Approval 裁決項 2；
secret 掃描器作用域的落差引自 `team.md ## Deployment` 的「已知的規則宣稱與機制落差」。
