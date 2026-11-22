# Security Design — U1: u1-icon-service-gateway

> Stage: nfr-design (3.3) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u1-icon-service-gateway` (kind: `library`)
> 追溯上游基準：
> - [security-requirements](../nfr-requirements/security-requirements.md) (NFR3.1, NFR4.1, NFR5.1)

---

## 1. 安全機制架構設計 (Security Architecture)

### 1.1 HTTPS Client 與逾時隔離模式 (NFR3.1)
```python
def _execute_n8n_post(url: str, payload: dict) -> str:
    # 僅允許 https 協定 (NFR3.1)
    if not url.startswith("https://") and not url.startswith("http://localhost"):
        raise SecurityException("Insecure webhook URL protocol")
    # 嚴格 5.0s 逾時配置 (NFR3.1)
    with httpx.Client(timeout=5.0) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()["svg"]
```

### 1.2 機密防護日誌過濾 (NFR4.1)
- 攔截所有請求記錄，日誌不輸出憑證資訊。

### 1.3 XSS-Safe SVG 生成器 (NFR5.1)
```python
def generate_fallback_svg(service_name: str) -> str:
    # 白名單過濾：僅保留英文字母與數字，截取前 4 碼 (NFR5.1)
    sanitized = re.sub(r'[^A-Z0-9]', '', service_name.upper())[:4] or "SRV"
    return (
        f'<svg width="40" height="40" viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="40" height="40" rx="4" fill="#F1F5F9" stroke="#CBD5E1"/>'
        f'<text x="20" y="24" font-family="sans-serif" font-size="10" font-weight="bold" '
        f'text-anchor="middle" fill="#475569">{sanitized}</text>'
        f'</svg>'
    )
```
