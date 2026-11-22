# Continuous Feedback Loop & Next Iteration Proposals

> Stage: feedback-optimization (4.7) · Phase: Operation · Scope: feature · Depth: Standard
> Intent: `261021-a1-compound-cloud-2`

## 1. 本次功能交付經驗總結 (Retrospective & Learnings)
1. **Hub-and-Spoke 拓樸之可讀性**:
   - 採用中央核心雲（AWS 寬度 >= 480px）搭配左右兩翼（Azure、GCP 寬度 >= 360px）與 120px 走廊間隔，在 UI 呈現上極為清晰直觀。
2. **容錯保護的關鍵性**:
   - 前端增加 `decodeURIComponent` 與 `autoFit` 平滑縮放，以及後端在 n8n 連線異常時的灰底佔位圖降級機制，大幅提高了系統韌性與使用者體驗。

---

## 2. 建議後續迭代提案 (Next Ideation Cycle Proposals)
- **提案一：自訂跨雲核心 (Custom Hub Provider)**: 允許使用者選擇以 Azure 或 GCP 為中央核心 Hub，其餘為兩翼。
- **提案二：多子網路跨雲拓樸**: 擴充混合雲容器內部可繪製雙 AZ / 雙子網路結構。
- **提案三：四雲支援 (Multi-Cloud 4.0)**: 納入 Oracle Cloud (OCI) 或 Alibaba Cloud 支援。
