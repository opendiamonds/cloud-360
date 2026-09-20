# Code Generation — 釐清問題（estimate-parser）

> Unit: estimate-parser（U1）· library

## 計畫要點（供核可）

1. **依賴** — openpyxl==3.1.5
2. **parse** — CSV／XLSX 讀取、雲別判定、NFR3.1 資源上限、NFR3.2 錯誤契約
3. **validate** — BR4.1–4.4 機械檢查
4. **邊界腳本** — 改掃 parser／validator／讀取器（FR9.6）
5. **測試** — unittest + ≥3 Hypothesis PBT

詳見 code-generation-plan.md 與 unit-test-instructions.md。

---

## Plan Approval

請核可上述計畫、內嵌 Testing Contract（test-after／Standard）、與 unit-test-instructions。

[Approval Fingerprint]: sha256:22798b84dd074e06e781ec2932f52429a20e2409f30f63494bbfc815a59d9ecc

- Approve Plan — 依計畫實作
- Request Changes — 修改計畫後再核可

[Answer]: Approve Plan
