---
name: tcms-verify
description: >
  驗證測試案例的完整性與正確性，作為同步進 TCMS 之前的關卡。先跑機械檢查
  （必填欄位、空洞預期、追溯目標存在、API/UI 比對實作），全過之後再做語意
  審查（規格是否真的描述了需求、步驟是否可被外人執行、回歸案例是否說得出
  它在防什麼）。未通過不得繼續。
argument-hint: "[--file <manual-test-cases.md>] [--spec <spec.ts>]"
user-invocable: true
---

# 測試案例驗證關卡

`tcms-test-cases` stage 的驗證步驟，也可單獨執行。它存在的理由是：一份填得
不完整或寫錯規格的測試案例，比沒有案例更糟——它讓人以為某個行為被覆蓋了。

驗證分兩層，**順序不可顛倒**：機械層全過之前不做語意審查，因為對著一份欄位
都沒填齊的案例談語意是浪費。

撰寫標準在 `aidlc/spaces/<active-space>/knowledge/aidlc-quality-agent/test-case-authoring.md`，
本 skill 驗的就是它。

## 第 1 層：機械檢查

```bash
python3 scripts/tcms_validate.py --all
```

或指定對象：

```bash
python3 scripts/tcms_validate.py --file <record>/construction/tcms-test-cases/manual-test-cases.md
python3 scripts/tcms_validate.py --spec frontend/tests/e2e/regression.spec.ts
```

工具檢查四類，全部可判定：

| 類別 | 內容 |
|---|---|
| 必填欄位與格式 | 目的／受測介面／前置條件／測試步驟／通過條件／追溯都在；步驟表格每列都有操作與預期結果 |
| 空洞預期結果 | 預期結果不得是「正常」「成功」這類無法判定的詞；且每個案例至少要有一個帶具體證據的預期（數字、引號、backtick、「不得」） |
| 追溯目標存在 | 引用的檔案路徑與測試名稱回 repo 核對 |
| API/UI 比對實作 | API 端點與 method 比對 `openapi.json`，UI 路徑比對 `frontend/src/App.tsx` 的路由表 |

**ERROR 一律阻擋**。WARN 要逐項判讀，不得無視——常見的 WARN 是「OpenAPI 未宣告
此狀態碼」，那多半代表端點缺 `responses=` 宣告，是真實的文件落差。

退出碼非 0 就停在這裡：把問題與修法回報給使用者，不要進第 2 層。

### 一種不算案例缺陷的 ERROR

追溯指向的檔案存在於**另一支尚未合併的分支**時，這裡會紅燈。那是真實的跨分支
依賴，不是案例寫錯——處置是說明依賴關係並確認合併順序，不是把追溯改掉。判斷
依據：`git log --all --oneline -- <path>` 查得到該檔案在別的分支上。

## 第 2 層：語意審查

機械層全過後才做。逐案讀過，對每一點給出「通過／有問題＋具體理由」，**不要**
只回一句「看起來沒問題」。

1. **目的是否指向一個真的會失敗的行為**
   「驗證頁面正常顯示」這種目的對任何實作都成立。目的要指向一個具體的失敗模式。

2. **回歸案例的背景是否說得出它在防什麼**
   必須包含症狀、錯誤訊息逐字、以及**既有自動化層為何沒抓到**。第三項最常被
   漏掉，而它正是這個案例為什麼是手動案例的理由。

3. **步驟能不能被沒參與開發的人執行**
   前置條件是否可複製貼上？改了 `.env` 有沒有提醒重啟後端？步驟裡有沒有出現
   只有作者知道的隱含前提？

4. **受測介面是否涵蓋案例實際會碰到的介面**
   機械層只驗「列出來的存在」，不驗「該列的有沒有漏」。一個會刪除帳號的案例
   只寫了清單 API 而沒寫 DELETE，機械層看不出來。

5. **通過條件是否二元可判**
   兩個人分別執行會不會得到相反結論？

6. **是否與自動化層重複**
   這個行為如果已經有自動化斷言，就不該存在手動案例（`test-case-management-plan.md`
   的單一真實來源）。比對 `automation-test-plan.md` 的覆蓋盤點。

7. **規格是否與需求一致**
   對照該 intent 的 `<record>/inception/user-stories/stories.md`：案例宣稱驗證的
   AC，是不是真的驗到了那條 AC 說的事。AC 說「帶有與資料庫一致的值……而非因
   構造遺漏而缺失或為 null」，案例卻只驗欄位存在，那就沒驗到。

## 第 3 層：報告與關卡

產出報告（在 stage 內執行時寫入 `<record>/construction/tcms-test-cases/`；
單獨執行時直接呈現）：

- 機械檢查：通過數／總數、ERROR 與 WARN 逐項
- 語意審查：逐案逐點的判定與理由
- 未通過項目與具體修法
- 結論：**通過** 或 **不通過**

**不通過就停**。不要「先同步再修」——TCMS 上一份錯的案例會被當成已覆蓋的證據，
而錯誤的覆蓋感比沒有覆蓋更危險。

通過後才執行同步：

```bash
python3 scripts/tcms_sync.py --file <path> --dry-run    # 手動案例
python3 scripts/tcms_sync.py --spec <path> --dry-run    # 自動化案例
```

預覽給使用者看過，核可後才拿掉 `--dry-run`。
