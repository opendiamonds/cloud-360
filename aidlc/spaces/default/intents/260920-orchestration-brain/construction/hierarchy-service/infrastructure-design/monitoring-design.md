# 監控設計 — `U7 hierarchy-service`

## 一、判定：無新增監控目標

整體監控設計屬 `U1 brain-infra` 的 `infrastructure-design`
（`construction/brain-infra/infrastructure-design/monitoring-design.md` 已交付）。
本單元不新增監控目標、告警規則或健康檢查端點——它是既有 FastAPI process 內的
router，其存活與延遲已被該 process 的既有監控涵蓋。

## 二、唯一的沿用義務：logger 命名

`logging.getLogger("cloud360.hierarchy_service")`（或同形的 `cloud360.<module>`）。

`team.md ## Code Style` 已如實記載現況：11 支模組用該形式、**5 支用 `__name__`
屬已知不一致**（`collab_router`、`design_agent`、`agent_router`、`diagram_builder`），
並明訂新模組一律用前者。本單元是新模組。

**這不是美學偏好**：logger 名稱決定日誌能不能依模組過濾，而 `__name__` 形式在
本 repo 會產生與其他 11 支不一致的前綴，使聚合查詢漏掉這些行。

## 三、刻意不新增的東西

- **不新增稽核日誌輸出**。本單元的稽核面是 `DiagramChangeRecord`（資料表），
  不是日誌。兩者刻意分開，理由見 `nfr-design/observability-design.md` §二。
- **不新增授權失敗的告警**。`BR1.1` 的拒絕是正常的業務結果（使用者沒有權限），
  不是系統異常；把它接上告警會製造常態噪音。
