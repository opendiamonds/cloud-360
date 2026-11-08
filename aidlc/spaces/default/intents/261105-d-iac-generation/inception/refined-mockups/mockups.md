# Refined Mockups — Story D IaC 工作區

<!-- Stage: refined-mockups · 中高保真。線框 rough-mockups；行為契約 stories.md。
     Q1–Q6=A。ASCII 外框示意；數字／finding 為假資料。 -->

## 上游輸入

- **wireframes**／**user-flow**（`../../ideation/rough-mockups/`）
- **stories**／**personas**（`../user-stories/`）
- **requirements**（`../requirements-analysis/requirements.md`）
- **Q1–Q6=A**：aside 選圖；自由步驟；aside Agent 進行中；下載 modal；固定三欄殼；沿用 Tailwind＋WCAG AA

## 本站鎖定（相對線框的增量）

| 項目 | 線框 | 本檔 |
|---|---|---|
| 選圖 | aside「脈絡」未釘控件 | aside：圖名＋`<select>`＋上傳；無圖阻擋（Q1） |
| 步驟 | 左列＋footer 下一步語意不清 | 步驟可隨時點；footer 只導覽；執行＝各步主鈕（Q2） |
| 進度 | Agent 狀態示意 | aside 階段文字＋主區骨架；鈕 busy（Q3） |
| 下載閘 | 未畫 | HIGH／CRITICAL → 居中 modal（Q4） |
| Secrets | 主區全寬清單 | 仍固定殼；改寫清單在右欄（Q5） |
| 視覺 | A／C 語彙 | 既有 `brand-*`／`rounded-xl`／`text-red-*`；窄窗堆疊（Q6） |

**殼層**：仍在 Workspace 內（不另開 `/iac` 為主路徑）。建議穩定 test 錨點（Construction 可改實作，勿只改文案）：

| test-id | 用途 |
|---|---|
| `iac-entry` | Workspace「生成 IaC」入口 |
| `iac-step-generate`／`iac-step-scan`／`iac-step-secrets` | 左側步驟鈕 |
| `iac-diagram-select` | aside 圖下拉 |
| `iac-diagram-upload` | 上傳控制 |
| `iac-file-tree` | 草稿檔案樹 |
| `iac-hcl-preview` | 目前檔 HCL 預覽 |
| `iac-agent-status` | aside Agent／進度文案（`aria-live=polite`） |
| `iac-run-d1`／`iac-run-d2`／`iac-run-d3` | 各步執行主鈕 |
| `iac-findings` | 掃描 findings 列表 |
| `iac-rewrite-list` | Secrets 改寫清單 |
| `iac-download`／`iac-copy` | 下載 zip／複製 |
| `iac-download-confirm` | HIGH／CRITICAL 摘要 modal |

---

## M1 — Workspace 入口

對齊 US1.1。有 D1 `view`：入口可點。無 D1 `view`：**disabled**＋可見說明（非隱藏）。

```
+----------------------------------------------------------------------+
| header: Workspace / 專案名                                           |
+----------+-----------------------------------------------------------+
| nav      | main: 架構圖畫布                                          |
| 圖面     |                                                           |
| 設計 A   |                                                           |
| 評估     |                                                           |
| 成本 C   |                                                           |
| 生成 IaC |  <-- test-id=iac-entry；無權時 disabled＋說明             |
+----------+-----------------------------------------------------------+
```

<!-- Text fallback: Workspace 側欄「生成 IaC」可進入 IaC 工作區；無權限時按鈕 disabled 並附缺少權限說明。 -->

---

## M2 — 固定殼（三步驟共用）

對齊 Q5=A／線框 Screen 2–4。

```
+----------------------------------------------------------------------+
| header: IaC 生成（同 Workspace chrome）              [返回 Workspace] |
+--------+------------------------------+------------------------------+
| steps  | main: 草稿（primary）        | aside: 依步驟切換            |
| 1 生成*| 檔案樹 | HCL 預覽            | （見 M2a／M2b／M2c）         |
| 2 掃描 |  main.tf                     |                              |
| 3 Sec. |  variables.tf                |                              |
|        |  outputs.tf                  |                              |
+--------+------------------------------+------------------------------+
| footer: [上一步]  [下一步：…]   ※僅導覽，不觸發執行                  |
| 當步主執行鈕亦可放 footer 右側或 aside 底：見各步                    |
+----------------------------------------------------------------------+
```

<!-- Text fallback: 左步驟、中草稿檔案樹＋預覽、右欄依步驟顯示脈絡／findings／改寫；footer 下一步只換步驟。 -->

**掃描／Secrets 步**：中欄草稿改為唯讀預覽（仍可見），避免兩套佈局。

---

## M2a — 生成步 aside（選圖＋Agent＋下載）

對齊 US1.2／US1.4／US2／US5。

```
+------------------------------+
| 脈絡（h2）                   |
| 圖: [ web-tier-aws     v ]   |  <-- iac-diagram-select
| [上傳 .drawio／.xml]         |  <-- iac-diagram-upload
|                              |
| Agent 狀態（h2）             |
| 待命／正在產生模組…          |  <-- iac-agent-status · aria-live
|                              |
| [執行生成]                   |  <-- iac-run-d1（需 D1 edit）
| [下載 zip] [複製目前檔]      |  <-- 無草稿時 disabled＋說明
+------------------------------+
```

**無圖**：主區＋aside 顯示阻擋文案＋「回 Workspace」CTA；`iac-run-d1` 不可成功送出。  
**上傳失敗**：aside 內錯誤文字（`text-red-700`）；脈絡圖名不變。  
**切圖成功**：`aria-live` 宣告「已清空先前 IaC 產物」；下載／D2／D3 回 disabled。

---

## M2b — 掃描步 aside（findings）

對齊 US3.1／US3.2。

```
+------------------------------+
| 靜態掃描（h2）               |
| [執行掃描]                   |  <-- 無 D1 草稿：disabled＋說明
|                              |
| findings（h3）               |
| HIGH     IAM * …             |  <-- 嚴重度文字標籤，非僅色票
| CRITICAL secret in tf …      |
| MEDIUM   sg open …           |
| （或）「無 finding」         |
| [重新掃描]                   |
+------------------------------+
```

**無草稿空狀態**：右欄可見說明「請先完成生成」；步驟仍可進入（Q2）。  
**進行中**：Agent 狀態「正在掃描…」；`iac-run-d2` busy。  
**失敗**：錯誤＋重試；中欄草稿仍可預覽。

---

## M2c — Secrets 步 aside（改寫）

對齊 US4.1／US4.2／US5.2。Advisory：有 HIGH 仍可進此步。

```
+------------------------------+
| Secrets（h2）                |
| ! 建議改為 SM 參考（無明文） |  <-- role=status／alert
|                              |
| [執行改寫]                   |  <-- 無 D2 成功報告：disabled
|                              |
| 已改寫項目                   |
|  variables.tf › db_password  |
|  （或）「無可改寫項」        |
|                              |
| [下載 zip] [複製]            |
+------------------------------+
```

**不出現**「套用到雲端／apply／destroy」。

---

## M3 — 下載確認 modal（HIGH／CRITICAL）

對齊 US5.1 AC5.1.5–5.1.7／Q4=A。

```
+------------------------------------------+
| 下載前風險摘要                    [x]    |  <-- iac-download-confirm
|                                          |
| 目前掃描含 HIGH: 1、CRITICAL: 1          |
| · CRITICAL secret in tf …                |
| · HIGH IAM * …                           |
|                                          |
| [取消]              [仍要下載]           |
+------------------------------------------+
```

<!-- Text fallback: 居中 dialog 列出 HIGH／CRITICAL 計數或短清單；取消／Esc 不下載；確認後才觸發 zip。無 HIGH／CRITICAL 時不出現此 dialog。 -->

焦點落入 dialog；陷阱至關閉；關閉後焦點回 `iac-download`。

---

## 狀態矩陣（摘要）

| 狀態 | UI |
|---|---|
| 無權入口 | M1 入口 disabled＋說明 |
| 無圖 | 阻擋＋回 Workspace |
| 無草稿開掃描／Secrets | 步驟可開；執行 disabled；右欄空狀態 |
| D1／D2／D3 進行中 | aside 文案＋主區骨架；執行 busy |
| D* 失敗 | 步驟內錯誤＋重試；不整場清空 |
| 切圖 | 清空產物＋live 提示 |
| 有 HIGH 進 Secrets | 允許；findings 文字醒目 |
| 下載＋HIGH | M3 modal；取消不下載 |
| 下載無 HIGH | 直接下載，無 modal |

## Non-goals（UI）

- 代 apply／雲端帳號綁定
- 獨立深色「IaC 品牌」殼（Q6≠B／C）
- 硬精靈鎖死後步不可檢視（Q2≠B）
