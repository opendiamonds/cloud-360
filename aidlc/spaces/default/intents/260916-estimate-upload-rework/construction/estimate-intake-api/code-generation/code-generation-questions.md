# Code Generation — 釐清問題（estimate-intake-api）

> Unit: `estimate-intake-api`（U2）· service

## 計畫要點（供核可）

1. **Schema／ORM** — EstimateSet 樹＋Share／Audit／Advice 空殼；雙軌 DDL
2. **授權／RBAC** — access 模組；C1 更新；移除 C1h～C1b
3. **Service** — 上傳驗證＋U1 parse／validate；原始檔不落地
4. **Router** — `/api/cost/v1` C2；BackgroundTasks enqueue
5. **測試／OpenAPI** — TestClient 5–8 案；dump＋gen:types；無 SPA／TCMS

詳見 `code-generation-plan.md` 與 `unit-test-instructions.md`。

---

## Plan Approval

請核可上述計畫、內嵌 Testing Contract（test-after／Standard）、與 unit-test-instructions。

[Approval Fingerprint]: sha256:8e8a9b509cb8329242cfa8bca46e0d4de0716d8906de158819aee6c939c00336

- Approve Plan — 依計畫實作
- Request Changes — 修改計畫後再核可

[Answer]: Approve Plan
