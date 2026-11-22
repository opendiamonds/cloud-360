# Anomaly Detection Configuration

> Stage: observability-setup (4.4) · Phase: Operation · Scope: feature · Depth: Standard
> Intent: `261021-a1-compound-cloud-2`

## 1. 異常偵測模型與指標 (CloudWatch Anomaly Detection)

### 1.1 生成耗時突增異常
- **目標指標**: `Cloud360/A1 GenerationLatency (Provider=compound)`。
- **偵測演算法**: CloudWatch 隨機森林 (Random Cut Forest) 動態頻帶模型。
- **標準差閾值**: 3 個標準差 (3 sigma)，當延遲偏離預期波形時發出預警。

### 1.2 錯誤突波偵測 (Error Spike Detection)
- **目標指標**: `Cloud360/A1 5xxErrorSpike`。
- **觸發條件**: 短時間（2分鐘內）錯誤量較前一小時基準值增加 200%。
