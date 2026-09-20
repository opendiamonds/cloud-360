# Security Requirements — cost-budget-banner

> Unit: `cost-budget-banner` · B2

## ADR-0006

| 面向 | 判定 |
|---|---|
| IAM | **適用** — `C1b.edit` budget；`C1.view` banner |
| Encryption | 沿用 |
| Network | 僅 REST 同 prefix |
| Audit | budget 變更寫 `cost_audit_event` |

## SEC-B-1 橫幅資訊暴露

- `GET /banner` 只含**使用者可見**圖的超支摘要；不含他人私有圖

## SEC-B-2 無永久 dismiss

- 禁止 localStorage「永不再顯示」（AC-7.3）

## SEC-B-3 Session dismiss

- 僅 hide DOM；reload 後再 GET；不削弱 RBAC
