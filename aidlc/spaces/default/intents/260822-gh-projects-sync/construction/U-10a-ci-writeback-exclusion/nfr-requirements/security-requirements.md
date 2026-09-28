# Security Requirements — U-10a `ci.yml` 的回寫排除

<!-- Stage: nfr-requirements（Construction，per-unit）· Unit: U-10a-ci-writeback-exclusion · kind: packaging -->

## SEC-1（本單元的核心安全考量）：`paths-ignore` 是一條繞過 CI 的路

本單元讓某些變更**完全不觸發 `ci.yml`**。而 `ci.yml` 的四個 job 中，`repo-contract` 執行的是 `python3 scripts/validate_repo_contract.py` 與 `validate_env_contract.py`——**本 repo 唯一的禁止路徑掃描與 secret 掃描**。

**具體後果**：一個**只**觸及被忽略路徑的 PR，四道閘門一道都不會跑。

**嚴重度判定：低，但需要精確的緩解，而緩解就是本單元的實作方式本身。**

逐項拆解：

| 面向 | 判定 |
| --- | --- |
| 是否引入新的權限或存取 | **否**。本單元只改 YAML 的觸發條件 |
| 是否讓機敏資料可被寫入而不被掃描 | **範圍極窄**。被排除的只有 `sync-state.json`（[Q1=A] 後為唯一路徑），其內容是機器產生的同步狀態 |
| 禁止路徑檢查是否失效 | **不失效，但執行窗口變窄**。`validate_no_production_config_added()` 對 `git ls-files` 做**全域**掃描（issue #509 後的行為），所以違規路徑會在**下一次任何 CI 執行時**被抓到——不是永久漏掉，是延後 |
| 是否有人能刻意利用 | 需要推送權，且需要一個**只**改該路徑的 PR。而該路徑下能放的東西是一個 JSON 檔的內容，不是新增任意路徑 |

**緩解就是路徑要窄**（`tech-stack-decisions.md` 的約束）：

- ✅ `aidlc/spaces/*/intents/*/sync-state.json`
- ❌ `aidlc/**` —— 會讓所有 AIDLC 產出的變更繞過 CI
- ❌ `**/*.json` —— 會讓 `package-lock.json`、`.github/aw/actions-lock.json` 等**安全相關**的檔案繞過 CI

**第三項尤其要緊**：`.github/aw/actions-lock.json` 是 [kb:technology-stack.md] 記載的 action SHA 釘選檔。一個把它排除在 CI 之外的 glob，會讓供應鏈釘選的變更不經任何檢查。

## SEC-1b：被排除的內容範圍由 U-4 界定，不由本單元界定

本單元排除的是「U-4 寫了什麼」，而那定義在 U-4 的 `business-logic-model.md`（`commit_and_push` 的 `paths` 參數）與 `business-rules.md` R-3.2。

**這是一條跨單元的安全依賴**：若 U-4 未來擴大它寫入的路徑集合，而本單元的 `paths-ignore` 沒有同步擴大，多出來的路徑仍會觸發 CI（**安全方向正確**，只是 [US:S-1 AC 7] 會退化）。反過來若本單元的 glob 先擴大而 U-4 沒有寫那些路徑，就會出現一段**沒有對應寫入行為的 CI 豁免**——那才是危險的方向。

**約束**：`paths-ignore` 的 glob **不得寬於** U-4 的 `paths` 白名單。兩者的比對是二元可判的（讀兩份 YAML／規則即可）。這與同批次約束（U-4 ＋ U-10a 為真捆綁）是同一件事的兩面——它們必須一起改。

## SEC-2：ADR-0006 四面向

| 面向 | 判定 | 理由 |
| --- | --- | --- |
| **IAM** | **不適用** | 本單元不涉及任何憑證或權限。它改的是 workflow 的觸發條件，不是誰能做什麼 |
| **Encryption** | **不適用** | 無資料傳輸或儲存 |
| **Network exposure** | **不適用** | 無新增端點 |
| **Audit logging** | **間接適用** | 被忽略路徑的變更不會有 CI run 紀錄。但 **git 歷史仍完整**——回寫 commit 帶 `[aidlc-sync]` 標記，`git log --grep` 即可稽核（見 U-4 的 SEC-3） |

## SEC-3：與 NFR-C1 的關係要說清楚

`requirements.md` 的 NFR-C1 要求「既有 CI 四道關卡與 `deploy.yml` **不得因本變更而破壞**」。

**本單元改變的是閘門的觸發覆蓋範圍，不是閘門本身。** 四個 job 的內容、順序、失敗條件一字未動；`deploy.yml` 完全不受影響（它的觸發是 PR closed 到 `ut`，與 `ci.yml` 的 `paths-ignore` 無關）。

**但「不得破壞」的判定應該包含覆蓋範圍**，而上游的驗收準則（`requirements.md` NFR-C1 的「本變更後 `ci.yml` 的…」）本站讀到的是行為層面的比對。**本站的立場**：把「`paths-ignore` 的 glob 不得超出 `sync-state.json`」列為 NFR-C1 在本單元的具體判準，二元可判（讀 YAML 即可驗）。

## 與上游的對應

NFR-C1 與禁止路徑／secret 掃描的作用域引自 `requirements.md` 與 `project.md`（含 issue #509 後 `git ls-files` 全域掃描的行為）；ADR-0006 四面向的落點引自 `project.md`；[US:S-1 AC 7] 引自 `stories.md`；`paths-ignore` 的設計落點引自 [ad:component-methods.md] §C-4 的註；單元邊界與完成判準引自 [ug:unit-of-work.md] 的 U-10a；同批次約束引自 `unit-of-work-dependency.md`；`[aidlc-sync]` 的稽核用途見 U-4 的 `security-requirements.md` SEC-3，其回寫規則見 U-4 的 `business-rules.md`；路徑集合與實測的觸發設定見同輪的 `tech-stack-decisions.md`；`.github/aw/actions-lock.json` 的釘選角色引自 [kb:technology-stack.md]。
