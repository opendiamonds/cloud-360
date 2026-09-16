# Tech Stack Decisions — U-3 看板客戶端

<!-- Stage: nfr-requirements（Construction，per-unit）· Unit: U-3-board-client · kind: library -->

## 決定

**獨立的 composite action `.github/actions/aidlc-sync-board/`，`shell: bash`，以 `gh api graphql` 呼叫 Projects v2，憑證經 `env: GH_TOKEN` 傳入。**

## 為什麼是獨立 action（不與 U-1／U-2 共用）

這不是偏好，是約束：**U-1 與 U-2 的 action 必須維持零 I/O**，那是 [US:S-10 AC 1] 的 fixture 驅動測試的前提（[ad:components.md] 明列 C-1／C-2／C-6 為純函式層）。本單元做真實網路 I/O 並持有憑證，放進同一支 action 會讓那個前提消失——**一支既能被 fixture 純文字驅動、又會呼叫外部 API 的 action，無法被誠實地稱為純函式**。

`components.md` 的 C-3 條目與 C-6 一樣**沒有「承載形式」列**（只有 C-1／C-2 有）。但與 C-6 不同的是，這裡沒有真正的選擇空間——上述約束逼出唯一解，因此本站直接裁定而不出成題目（依 `project.md` 的 `requirements-analysis:260822-ra-c5`：單一可行解不做成假選擇）。

## 呼叫方式與既有先例

| 決定 | 依據 |
| --- | --- |
| `gh api graphql` 而非手寫 curl | `gh` 預裝於 GitHub-hosted runner；它處理認證標頭、重試與 JSON 編碼。手寫 curl 等於重寫這些 |
| 憑證經 **`env: GH_TOKEN`** | **repo 既有形狀**——`agentics-maintenance.yml` 等多支 workflow 皆以 `GH_TOKEN: ${{ secrets.* }}` 傳遞（實測 `.github/workflows/`）。且 `gh` 原生讀取 `GH_TOKEN`，改走 input 再 export 只是多一跳 |
| **不以 action `input` 承載憑證** | 見 `security-requirements.md` SEC-1 |
| 分頁用 `gh api graphql --paginate` | 僅欄位 id 解析需要（[Q1=A] 已消掉 `read_item` 的分頁，見 `domain-entities.md`） |

**本 repo 無 GraphQL 先例**：實測 `.github/workflows/*.yml`，`graphql` 零命中；`GH_TOKEN` 有多處但都是 REST 或 `gh` 子命令。[kb:technology-stack.md] 記載的 11 支 workflow 也沒有一支碰過 Projects v2。查詢字串、錯誤碼對應、分頁游標全部新寫。

## 沿用 U-1 的 bash 決定，並記下本單元的額外代價

執行環境沿用 U-1 的 [Q1=A]（composite ＋ `shell: bash`）。U-1 記載的代價是「bash 沒有原生 `null`」，U-2 補記了「正規化序列化難做」。**本單元的額外代價是錯誤分類**：

`domain-entities.md` 定義了四個錯誤型別（`ExternalError`／`Aborted`／`Failed`／`CannotCreate`），其中只有 `ExternalError` 紅燈。要正確分類，必須從 `gh api graphql` 的輸出中區分「HTTP 層失敗」與「GraphQL 層 `errors` 陣列」——**GraphQL 在錯誤時仍回 HTTP 200 並把錯誤放在 body 的 `errors` 欄位**。在 bash 中這代表：不能只看 exit code，必須解析 JSON body。

**承接方式（本站定案）**：每一次 `gh api graphql` 呼叫後都必須檢查兩層——exit code **與** 回應 body 的 `.errors`；只檢查其中一層即為缺陷。`ensure_field` 的三種可達失敗前提（[ad:component-methods.md] 列出的憑證缺權限／同名欄位型別不同／組織政策阻擋）**全部出現在 GraphQL 的 `errors` 層而非 HTTP 層**，只看 exit code 會把三者都誤判為成功。

## 與上游的對應

C-3 的**七個**方法（含 ADR-0015 §11 增設的 `write_body`，2026-08-30T01:31:09Z 更正）與錯誤型別引自 [ad:component-methods.md] §C-3；純函式層與本單元的分層差異引自 [ad:components.md]；`read_item` 的查找路徑與剩餘的分頁需求引自本單元的 `domain-entities.md`（[Q1=A]）；錯誤處理與紅燈規則引自 `business-rules.md` 與 [ad:services.md]；「無 Projects v2 先例」引自 [ug:unit-of-work.md] 的 U-3 與 [kb:technology-stack.md]；`business-logic-model.md` 的資料流圖說明了四個錯誤型別各自的產生點。
