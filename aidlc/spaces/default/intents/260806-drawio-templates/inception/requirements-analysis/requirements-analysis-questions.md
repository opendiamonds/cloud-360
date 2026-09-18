# Requirements Analysis Questions

請協助確認 Azure 與 GCP draw.io 模板的修改需求：

### [Q1] 針對 Azure 模板 (Azure_template.drawio.xml) 的修改方向是什麼？
- A. 調整現有元件的佈局與座標 (例如 App Service Plan, Database Group 等)
- B. 新增或替換核心的 Azure 雲端服務元件 (例如新增 Azure Key Vault, Azure Monitor 等)
- C. 修改最外層的訂用帳戶邊界 (Azure Subscription) 或 Resource Group 大小
- D. 其他 (請說明)

[Answer]: D. 使用者已直接在對話外手動更新好 Azure 模板，包含新的元件與佈局。

---

### [Q2] 針對 GCP 模板 (GCP_template.drawio.xml) 的修改方向是什麼？
- A. 調整現有 Subnet (Ingest, Processing, Storage, Analytics) 的區劃與大小
- B. 新增或替換核心的 GCP 服務元件 (例如新增 Cloud Run, Secret Manager, Cloud SQL 等)
- C. 調整連線與資料流向 (edges) 的連接點與路徑
- D. 其他 (請說明)

[Answer]: D. GCP 模板無須修改，維持原樣。

---

### [Q3] 修改後的模板是否需要同步更新系統提示詞 (cloud_architecture_system_prompt.md) 中的 JSON 範例座標？
- A. 是，修改後必須同步更新 `cloud_architecture_system_prompt.md` 中的幾何範本與呼叫範例
- B. 否，僅修改 XML 模板，提示詞維持原樣即可
- C. 其他 (請說明)

[Answer]: A. 是，已更新 cloud_architecture_system_prompt.md 中的 Azure 幾何範本與呼叫範例。
