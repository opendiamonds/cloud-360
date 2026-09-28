# Frontend Components — U9 advice-presentation-ui

| 元件 | 職責 | data-testid |
|---|---|---|
| `EstimateAdvicePanel` | 建議區殼、三態、SSE／REST、免責標註 | `advice-slot`（沿用 U8 錨點） |
| `AdvicePendingSkeleton` | 產生中骨架（可內聯） | `advice-pending` |
| `AdviceCategoryBlock` | 單一建議類別（saving／comparison／quality） | `advice-category-{kind}` |
| `AdviceFailedBanner` | 失敗／逾時＋重試 | `advice-failed` |
| `useAdviceStream` | fetch SSE＋AbortController（可同檔） | — |
