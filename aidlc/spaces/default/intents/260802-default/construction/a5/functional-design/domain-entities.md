# A5 Domain Entities — Sharing & Real-time Collab

> Unit `U-A5` · Story A5  
> Retrospective FD（對齊 `a5/code/sharing-collab-summary.md`）


### 實體關係

```text
UserDiagram *──* User  （via diagram_shares）
       │
       └── WS room = diagram / workspace id → XML fan-out
```

### diagram_shares

| 欄位 | 說明 |
|---|---|
| `user_id` | PK/FK 被分享者 |
| `diagram_id` | PK/FK |

細粒度 **can_view／can_edit／can_review** 目前由產品／RBAC 與分享流程語意決定（見 role-permission-design）；ORM 關聯表為複合 PK。實作細節以 `collab_router` ACL 為準。

### 即時通道（非表）

| 名稱 | 說明 |
|---|---|
| `CollabSession` | WS `/api/collab/ws/{workspace_id}` |
| `XmlBroadcast` | 畫布 XML 雙向廣播 |
| `CursorPresence` | **未實作**（故事 AC） |
