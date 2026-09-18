# Requirements

## 專案背景與目標
- 本次開發意圖 (Intent: `260806-drawio-templates`) 旨在修改 Azure 與 GCP 的 draw.io XML 模板，以符合最新的架構圖規範。
- 將依據與使用者的需求確認結果（確認 `requirements-analysis-questions.md`）來更新模板及相關的提示詞。

## 需求確認結果
- **Azure 模板**：已由使用者手動更新 [Azure_template.drawio.xml](file:///Users/houguanyu/Desktop/Work/Cathaybk/Opendiamonds/cloud-360/backend/prompts/Azure_template.drawio.xml)，包含新的元件幾何佈局與座標。
- **GCP 模板**：GCP 部分無須任何修改，維持原樣。
- **系統提示詞同步**：已成功更新系統提示詞 [cloud_architecture_system_prompt.md](file:///Users/houguanyu/Desktop/Work/Cathaybk/Opendiamonds/cloud-360/backend/prompts/cloud_architecture_system_prompt.md) 中的 Azure 幾何範本及 JSON 呼叫範例，確保 LLM 在生成架構圖時使用正確的絕對座標與對齊邏輯。

## 變更項目
- [x] 更新 Azure 模板項目 [Q1]
- [x] 確認 GCP 模板無需修改 [Q2]
- [x] 完成系統提示詞中的 Azure JSON 範例同步 [Q3]
