# Tech Stack Decisions — U-4 record 回寫與同步狀態

<!-- Stage: nfr-requirements（Construction，per-unit）· Unit: U-4-binding-store · kind: library -->

## 決定

**獨立的 composite action `.github/actions/aidlc-sync-record/`，`shell: bash`，直接使用 `git` 與檔案系統操作。**

## 為什麼是獨立 action

與 U-3 同一條理由（U-1／U-2 必須維持零 I/O 以支撐 fixture 驅動），但**理由的第二半不同**：U-3 是網路 I/O ＋ 憑證，本單元是 **git 與檔案系統 I/O**。兩者的驗證方式也不同——[ug:unit-of-work.md] 記載 U-3 是「③真實 Projects v2 API」、U-4 是「**④git 與 repo 行為**」。

把兩者併成一支會讓「這個單元完成了嗎」同時指涉兩種不可互相替代的驗證方式，正是 units-generation 切分判準要避免的形狀。

`components.md` 的 C-4 條目與 C-3／C-6 一樣**沒有「承載形式」列**。與 C-6 不同、與 C-3 相同的是：這裡沒有真正的選擇空間，故直接裁定不出題（`project.md` 的 `requirements-analysis:260822-ra-c5`）。

## 工具選擇

| 決定 | 理由 |
| --- | --- |
| 用 `git` 而非 `gh` | 本單元做的是 commit 與 push，不是 API 呼叫。`gh` 在這裡沒有加值 |
| 用 `git push` 的 stderr 分辨失敗成因 | `business-rules.md` R-3.5 的要求。**兩種失敗都是非零 exit code**，只看 exit code 無法區分 |
| JSON 處理需保留未知欄位 | `business-rules.md` R-2.3。見下方「bash 的第三項代價」 |

## 承接 U-1 的 bash 決定：本單元的第三項代價

U-1 記載「bash 沒有原生 `null`」，U-2 補記「正規化序列化難做」，U-3 補記「GraphQL 錯誤在 HTTP 200 的 body 裡」。**本單元的代價是 JSON 的未知欄位保留。**

`business-rules.md` R-2.3 要求 read-modify-write 時把不認得的欄位**原樣寫回**。在 bash 中處理 JSON 的常見做法是 `jq`，而 `jq` 恰好**能**做到這件事——但只有在寫法正確時：

| 寫法 | 是否保留未知欄位 |
| --- | --- |
| `jq '.last_status = $v'`（就地更新） | **是**——其餘鍵原樣保留 |
| `jq -n '{last_status: …, schema_version: …}'`（重新建構） | **否**——未列出的鍵全部消失 |

**兩種寫法在正常情境下產出相同的檔案**，差別只在有未知欄位時才顯現。這正是 R-2.3 必須被 fixture 鎖住的理由——它是一個**只在跨版本情境下才會暴露**的實作選擇。

`jq` 預裝於 GitHub-hosted runner，不需新依賴。

## commit 身分

commit 的作者身分由憑證決定（GitHub App 產生自己的身分）。這一點**不是本站可自由選擇的**，但它與兩件事相關：

1. **[US:S-1 AC 5]** 定義自我排除為「由**同步身分**推送、訊息含 `[aidlc-sync]`」——身分是其中一半。
2. 該 AC 的適用前提（`stories.md` 的註）指出：若最終選用 repo 預設 `GITHUB_TOKEN`，平台本身即不會為其 push 觸發新 run，該條在該身分下**恆真**。**[Q2=A] 於 application-design 選的是 GitHub App**，故防線②確實會被執行。

**本單元須明確設定 `git config user.name` / `user.email` 為同步身分**，不得沿用 runner 的預設值——否則 commit 作者會是 `github-actions[bot]` 或空值，[US:S-1 AC 5] 的「同步身分」那一半就無從判定。

## 與上游的對應

C-4 的方法契約引自 [ad:component-methods.md] §C-4；驗證方式與單元邊界引自 [ug:unit-of-work.md] 的 U-4；R-2.3／R-3.5 的要求見本單元的 `business-rules.md`，schema 見 `domain-entities.md`，資料流與內部重試見 `business-logic-model.md`；[US:S-1 AC 5] 的適用前提引自 `stories.md`；憑證身分的定案引自 [ad:decisions.md]；元件分層引自 [ad:components.md]；`jq` 的可用性與 runner 環境引自 [kb:technology-stack.md]（GitHub Actions 為 CI/CD 主幹）。
