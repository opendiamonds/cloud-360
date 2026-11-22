# Performance Test Instructions — A1 混合雲繪圖功能 (Compound Cloud)

> Stage: build-and-test (3.6) · Phase: Construction · Scope: feature · Depth: Standard
> Intent: `261021-a1-compound-cloud-2`

---

## 1. 效能指標需求 (NFR)

- **NFR4.1 (端到端渲染延遲)**: 混合雲架構圖 XML 運算與渲染延遲在單一請求中應 $\le 1.0\text{ 秒}$。
- **NFR4.2 (圖示請求逾時上限)**: n8n 圖示獲取逾時保護硬性門檻為 $5.0\text{ 秒}$，超過即刻觸發降級本地 SVG，杜絕連線懸掛阻塞。
- **NFR4.3 (圖示快取命中效率)**: 重複圖示命中 `_ICON_CACHE` 記憶體快取，延遲 $< 1\text{ ms}$。

---

## 2. 效能基準驗證腳本

執行圖示服務與幾何佈局延遲評估測試：
```bash
PYTHONPATH=backend .venv/bin/python3 -c "
import time
from services.diagram_builder import build_compound_diagram_xml

clouds = [
    {'provider': 'azure', 'services': [{'name': 'aks', 'display_name': 'AKS'}]},
    {'provider': 'aws', 'services': [{'name': 'eks', 'display_name': 'EKS'}]},
    {'provider': 'gcp', 'services': [{'name': 'gke', 'display_name': 'GKE'}]}
]
connections = [
    {'from': 'aks', 'to': 'eks', 'protocol': 'DirectConnect'},
    {'from': 'eks', 'to': 'gke', 'protocol': 'CloudVPN'}
]

t0 = time.perf_counter()
xml = build_compound_diagram_xml(clouds=clouds, connections=connections)
t1 = time.perf_counter()
latency_ms = (t1 - t0) * 1000
print(f'Compound Diagram Generation Latency: {latency_ms:.2f} ms')
assert latency_ms < 1000, 'Generation latency exceeded 1000ms!'
"
```

