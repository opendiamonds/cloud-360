# Reliability Requirements — legacy-cost-retirement

> Unit: `legacy-cost-retirement`（U3）· kind: **service**（退場）  
> 上游：FD BR9.5、bolt-plan B5、澄清 Q3=A／Q5=A。

## NFR — 與 U8 同批部署（Q3=A）

- **目標**：避免 staging／trunk 出現「舊成本 API 已刪、新估價 UI 未上」的中間態。
- **閘門形式**：**程序閘門**——code-gen 計畫與 PR 檢查清單明列「須含 U8 變更」；合併採同一 squash／同批；**CI 不**機械偵測 U8 路徑。
- **失敗模式**：若僅合 U3 → 視為程序違規，應拒合或立即補 U8。

## NFR — 表生命週期（Q5=A）

- 本 unit：**rename → archive_*** ＋ `DEPLOY.md` 記載保留到期日（≥90 天）。
- **不做**啟動時自動 DROP；到期 DROP 另開 chore／operation，避免誤刪與不可逆。
- 雙軌 DDL 必須一致，避免冷啟動與文件 schema 分歧。

## NFR — 退場後可啟動

- 移除舊 router／Calculator 後，應用仍須完成啟動（含無目錄價金鑰時可啟動——與 U4 FR11.4 精神一致）。
- `warm_aws_pricing_cache.py` 等工具不得因誤 import 已刪模組而在文件／CI 誤導為必跑失敗；須修正或刪除。

## 明確不在本 unit

| 項目 | 歸屬 |
|---|---|
| 新 API 可用性 SLO | U2 |
| 建議產生成功率 | U7 |
| UI 可用性 | U8／U9 |

<!-- confirmed: Looks correct -->
