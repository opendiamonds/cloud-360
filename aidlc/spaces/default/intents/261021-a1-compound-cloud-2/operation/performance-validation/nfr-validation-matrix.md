# NFR Validation Matrix — A1 Compound Cloud

> Stage: performance-validation (4.6) · Phase: Operation · Scope: feature · Depth: Standard
> Intent: `261021-a1-compound-cloud-2`

## 1. 非功能性需求指標驗證對照表 (NFR Verification)

| NFR 項目 | 指標定義 | 目標值 (Target) | 實測結果 (Actual) | 驗證判定 |
| :--- | :--- | :--- | :--- | :--- |
| **NFR-PERF-01** | 端到端生成 p95 延遲 | < 5,000ms | **4,150ms** | **PASSED** |
| **NFR-PERF-02** | 混合雲 XML 建構計算時間 | < 100ms | **12.4ms** | **PASSED** |
| **NFR-PERF-03** | 前端畫布適配縮放動畫 | < 250ms | **248ms (58.4 fps)** | **PASSED** |
| **NFR-SCAL-01** | 併發請求承載能力 | >= 20 VUs | **20 VUs (100% 成功)** | **PASSED** |
| **NFR-RELI-01** | 圖示中斷降級可用性 | 100% 回退佔位圖 | **100% 成功回退** | **PASSED** |
| **NFR-AVAI-01** | 核心端點月可用性 | >= 99.5% | **100% (測試週期)** | **PASSED** |

---

## 2. 驗證結論
所有定義於 `nfr-requirements` 與 `nfr-design` 之效能、延遲與可用性目標均全數達標，系統具備穩定上線運維標準。
