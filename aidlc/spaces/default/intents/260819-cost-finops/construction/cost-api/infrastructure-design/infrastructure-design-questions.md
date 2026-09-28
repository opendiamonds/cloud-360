# Infrastructure Design — 釐清問題（cost-api）

> Stage: infrastructure-design（3.4）· Unit: `cost-api` · kind: **service**  
> 上游：`../nfr-design/`、OQ-3（`requirements.md`）。

## 已由上游定案、不重問

| 事項 | 來源 |
|---|---|
| embedded 同一 FastAPI + Postgres | ADR-C1-01 |
| 禁止帳號 API／SigV4／boto3 | practices-discovery DevSecOps |
| B1 可 stub 合閘 | bolt-plan |
| coverage 靜態 YAML 啟動載入 | FD Q4=A |

---

## Q1. OQ-3 各雲公開端點與 (a) 覆蓋清單？

A. **AWS `official_list`**（Price List 公開 JSON）；**GCP／Azure `manual_override_only`** 本 MVP（mockups M2）。URL 寫入 repo `pricing_urls.yaml` + `pricing_coverage.yaml`；host allowlist 靜態掃描。**（建議）**  
<!-- 2026-08-23：後續改為三雲 official_list，見 ADR-C1-09；本答保留為歷史紀錄。 -->
B. 三雲皆 official_list。代價：GCP／Azure 端點複雜度與 FR-2.2 展示文案衝突。  
C. Not yet defined  

[Answer]: A. **AWS 官方價；其餘 Manual Override**

---

## Q2. 查價憑證／env？

A. **不新增任何雲端 credential env**；僅可選 `COST_PRICING_STUB=1`（CI／test compose 內嵌，非 deploy 必填）。**（建議）**  
B. `AWS_PRICING_URL` 可 runtime 覆寫。代價：SSRF 風險。  
C. Not yet defined  

[Answer]: A. **無 credential；stub 僅測試**

---

## Q3. 出站網路（staging）？

A. **沿用 backend 容器既有出站**；價目 host 限 allowlist 三類：`pricing.us-east-1.amazonaws.com`（AWS）；Azure／GCP 本輪不發 HTTP。**（建議）**  
<!-- 2026-08-23：後續 ADR-C1-09 改為三雲皆可出站；本答保留為歷史紀錄。 -->
B. 新增 sidecar proxy。代價：過度工程。  
C. Not yet defined  

[Answer]: A. **既有出站 + allowlist**

---

## Plan Approval

- [x] 計畫已核可（Q1–Q3=A）
