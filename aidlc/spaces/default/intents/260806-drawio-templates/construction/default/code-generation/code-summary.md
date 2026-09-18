# Code Summary

## 建立/修改的檔案
- `backend/prompts/cloud_architecture_system_prompt.md` — 更新了 Azure 幾何範本及 JSON 呼叫範例的座標及架構。

## 關鍵決策
- 依據使用者更新的 `Azure_template.drawio.xml`，將系統提示詞中的 Azure 區域與元件座標進行同步更新：
  - 更新了 Integration & Compute Group、App Group / VNet、Database Group 以及 Monitoring Group 的寬高與絕對座標。
  - 同步更新對應 nodes（如 VPN gateway, Azure Databricks, Azure Spring Apps, AKS, Azure SQL Database, Azure Monitor）的座標點與 edges。

## 測試與驗證
- 執行 `python3 scripts/validate_repo_contract.py` 驗證通過，確保 repository contract 完整合規。
