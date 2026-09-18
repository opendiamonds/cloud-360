# Integration Test Instructions

前端與整合層的唯一自動化驗證是 Playwright e2e（本專案無 unit／component 框架）。

```bash
docker compose -f deploy/docker-compose.test.yml up -d --build
cd frontend && BASE_URL=http://localhost:8090 npx playwright test
```

**實測結果：14 個 case 全部通過**（本 intent 之前為 6，新增 8 —— 其中 1 個是修復既有的失效 case）。

## 本 intent 新增／修改的 case

| # | Case | 涵蓋的 AC |
|---|---|---|
| 1 | 表格出現最後活動時間欄，且該欄顯示**具體時間值** | AC-1.4 |
| 2 | 分頁控制可見且顯示總筆數與目前頁次 | AC-5.2（UI 面）、AC-5.9（非僅顏色） |
| 3 | 切換到第 2 頁取得不重複的帳號，且**停用後仍停在第 2 頁** | AC-5.3、AC-5.6（停用） |
| 4 | 角色調整仍可用且不影響最後活動時間欄 | NFR-7 回歸、AC-1.5 |
| 5 | **切頁期間分頁控制不消失**，且鍵盤可達可觸發 | AC-5.9、AC-5.10 |
| 6 | **刪除後仍停在原頁次**，且總筆數遞減 | AC-5.6（刪除） |
| 7 | 超出範圍的頁次顯示**空態**並可回到第 1 頁 | AC-5.4（UI 子句） |
| 8 | 小螢幕改為卡片佈局，分頁控制仍可用且可跳頁 | AC-4.1、AC-5.7 |
| 修復 | 「Developer 看不到系統管理區」 | 既有失效 case，非本 feature |

## 兩個關鍵手法

**多頁資料**：seed 只有 `admin` 一個帳號。需要多頁的 case 以**公開註冊端點**（無認證依賴）建立 21 個帳號 —— 既有 e2e 已示範同一手法。實測 bcrypt 約 0.305s／次，21 個約 6.4s，在 30s 逾時內。

**切頁中的瞬間**：AC-5.10 的「控制項不消失」時間窗極短，以 `page.route` **刻意延遲** 1.2 秒清單回應，在回應抵達前斷言 nav 仍可見且 `aria-busy="true"`。沒有這個延遲，這條斷言會退化成恆真。

## 誠實揭露

`ui-regression` gh-aw workflow 在 CI 上對相同的短生命週期 stack 執行同一套 case，是**真閘門**（讀 `pw-report.json` 的 `stats.unexpected`，非 0 即 `exit 1`）。本輪的 14 個 case 是在**本機**的同構 stack 上跑的；CI 上的首次執行仍待 PR 觸發。
