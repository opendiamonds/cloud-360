# Security Design — U2: u2-compound-diagram-builder

> Stage: nfr-design (3.3) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u2-compound-diagram-builder` (kind: `library`) · **Walking Skeleton**
> 追溯上游基準：
> - [security-requirements](../nfr-requirements/security-requirements.md) (NFR3.2, NFR4.2)

---

## 1. 安全機制架構設計 (Security Architecture)

### 1.1 節點規模邊界檢驗 (NFR3.2)
```python
def validate_diagram_scale(clouds: list[CloudContainerSpec]) -> None:
    total_nodes = sum(len(c.nodes) for c in clouds)
    if total_nodes > 500:
        raise ValueError(f"Exceeded maximum node capacity limit (500): got {total_nodes}")
```

### 1.2 XML 字符轉義防護 (NFR4.2)
```python
from xml.sax.saxutils import escape

def safe_xml_attr(val: str) -> str:
    # 完整轉義 XML 關鍵字元，防止屬性注入與標籤逃逸
    return escape(str(val), entities={'"': "&quot;", "'": "&apos;"})
```

