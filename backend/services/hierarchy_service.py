"""
hierarchy_service.py — `U7 hierarchy-service` 的服務層

**本層沒有第二道角色檢查**（`BR1.3`，誠實宣告而非遺漏）：授權判定只有一份，
在 `hierarchy_facade.HierarchyFacade`。那是契約 `K-07` 選的模型。
後果：同進程直呼本模組的函式會**完整繞過 RBAC**，且繞過是**靜默的**
——不會有錯誤，只會沒有檢查。`BR1.5` 要求以可執行的 import 掃查守住這一點，
而**本單元無法自己驗證它**（`OPEN-H2`）。

錯誤處理形狀沿用 `team.md` 的既有慣例：DB／驗證錯誤**直接 raise**，
不以 `try/except` 吞掉；`try/except` 只用在外部依賴邊界，而本模組沒有。
"""

from __future__ import annotations

import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from models import DiagramChangeRecord, Project, System, UserDiagram
from services.hierarchy_facade import (
    HierarchyConflictError,
    HierarchyNotFound,
    HierarchyValidationError,
)

logger = logging.getLogger("cloud360.hierarchy_service")

SOURCE_BRAIN_ORCHESTRATION = "brain_orchestration"
ALLOWED_CHANGE_SOURCES = frozenset({SOURCE_BRAIN_ORCHESTRATION})
"""`BR5.3`：`U4` 的 DDL CHECK 只允許這一個值。

`U4` 的欄位註解（`schema_rbac.sql:418`）逐字：「Adding a future writer =
add an enum value, **no schema migration**」——擴充允許值不是 schema 變更。
"""


# ---------------------------------------------------------------------------
# 名稱驗證（`BR3.1`）
# ---------------------------------------------------------------------------


def _validated_name(name: str) -> str:
    """`BR3.1`：去除前後空白後長度必須大於 0。

    DDL 另有 `CHECK (length(trim(name)) > 0)`；本函式存在的理由是讓錯誤訊息
    對使用者有意義，而不是讓資料庫丟一個約束名稱出來。
    """
    if name is None:
        raise HierarchyValidationError("名稱不得為空")
    trimmed = name.strip()
    if not trimmed:
        raise HierarchyValidationError("名稱不得為空白")
    return trimmed


# ---------------------------------------------------------------------------
# 擁有者檢查（`BR6.1` 讀取範圍 ＋ `BR6.5` 寫入範圍）
#
# 三者都 raise `HierarchyNotFound`，**刻意與真正的不存在回同一種結果**
# ——否則回應本身就是一個存在性預言機（`BR6.1` 逐字：回「查不到」而非
# 「無權限」，不以錯誤碼洩漏該資源存在）。
# ---------------------------------------------------------------------------


def assert_project_owned_by(db: Session, *, project_id: int, user_id: int) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None or project.owner_user_id != user_id:
        raise HierarchyNotFound(f"查不到專案 {project_id}")
    return project


def assert_system_owned_by(db: Session, *, system_id: int, user_id: int) -> System:
    system = db.query(System).filter(System.id == system_id).first()
    if system is None:
        raise HierarchyNotFound(f"查不到系統 {system_id}")
    # 系統的擁有者是**其所屬專案的**擁有者——systems 表本身沒有 owner 欄位。
    assert_project_owned_by(db, project_id=system.project_id, user_id=user_id)
    return system


def assert_diagram_owned_by(
    db: Session, *, diagram_id: int, user_id: int
) -> UserDiagram:
    """`BR6.3`：以架構圖自身的 `user_id`（NOT NULL）判定，**不上溯系統**。"""
    diagram = db.query(UserDiagram).filter(UserDiagram.id == diagram_id).first()
    if diagram is None or diagram.user_id != user_id:
        raise HierarchyNotFound(f"查不到架構圖 {diagram_id}")
    return diagram


# ---------------------------------------------------------------------------
# 建立路徑（`BR2.x`／`BR3.x`）
# ---------------------------------------------------------------------------


def create_project_nocommit(
    db: Session, *, owner_user_id: int, name: str
) -> Project:
    """`W1` 的**不 commit** 變體。`BR2.1`：建立路徑的單一寫入端。

    **為什麼需要這一支**（`U19` 的 `OPEN-ND19-5`，blocking）：`[ND1]`=A 要求
    「建立專案」與「寫入建立者的成員列」在**同一個交易**內（`NFR12.18`），
    而下面的 `create_project()` **自己 `db.commit()`**。天真的組合實作因此是
    **兩個交易**：`U7` 先 commit、`U19` 再寫成員列並 commit，兩者之間若失敗就
    留下一個**零成員專案**——正是 `[ND1]` 要消除的那個狀態，而 `BR2.1` 的守門
    只在「減少管理者」時觸發，擋不住「一開始就沒有」。

    故**交易邊界歸呼叫端**。本函式 `flush()` 而不 `commit()`：`flush` 會把
    `INSERT` 送到資料庫並取回 `project.id`（組合寫入需要它），但不結束交易，
    所以任一步失敗時兩個寫入一起回滾。

    `create_project()` 保留原樣的對外行為（它只是本函式 ＋ `commit`），
    故既有呼叫端與既有測試完全不受影響。

    `BR3.3`（誠實宣告）：同名檢查到 flush 之間有 TOCTOU 空窗——唯一性是
    **最佳努力而非不變量**，因為 DDL 刻意沒有唯一索引（`[F5]`=C）。
    **名稱永遠不是鍵。**
    """
    trimmed = _validated_name(name)
    # BR3.2：同擁有者範圍內檢查同名。
    existing = (
        db.query(Project)
        .filter(Project.owner_user_id == owner_user_id, Project.name == trimmed)
        .first()
    )
    if existing is not None:
        raise HierarchyConflictError(f"已有同名專案：{trimmed}")
    project = Project(
        name=trimmed,
        owner_user_id=owner_user_id,
        is_default=False,  # BR2.3：新建者一律為否；True 只由遷移程式寫入
    )
    db.add(project)
    db.flush()
    return project


def create_project(db: Session, *, owner_user_id: int, name: str) -> Project:
    """`W1`。`BR2.1`：建立路徑的單一寫入端（兩個使用者入口共用）。

    **自己 commit**，故**不可**用於需要與其他寫入同交易的組合路徑——那一條走
    `create_project_nocommit()`（見它的 docstring：`U19` 的 `OPEN-ND19-5`）。
    """
    project = create_project_nocommit(db, owner_user_id=owner_user_id, name=name)
    db.commit()
    db.refresh(project)
    logger.info("建立專案 %s（擁有者 %s）", project.id, owner_user_id)
    return project


def create_system(db: Session, *, project_id: int, name: str) -> System:
    """`W2`。呼叫端已完成 `BR6.5` 的擁有者檢查與 `BR2.2` 的存在驗證。"""
    trimmed = _validated_name(name)
    existing = (
        db.query(System)
        .filter(System.project_id == project_id, System.name == trimmed)
        .first()
    )
    if existing is not None:
        raise HierarchyConflictError(f"該專案下已有同名系統：{trimmed}")
    system = System(project_id=project_id, name=trimmed, is_default=False)
    db.add(system)
    db.commit()
    db.refresh(system)
    logger.info("建立系統 %s（專案 %s）", system.id, project_id)
    return system


# ---------------------------------------------------------------------------
# 刪除路徑（`BR4.x`）—— **任何情況都不級聯**
# ---------------------------------------------------------------------------


def delete_project(db: Session, *, project_id: int) -> None:
    """`W6`（專案）。呼叫端已完成 `BR6.5` 的擁有者檢查。"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        raise HierarchyNotFound(f"查不到專案 {project_id}")
    # BR4.2：預設組不可刪除（保護遷移的冪等性載體）
    if project.is_default:
        raise HierarchyConflictError("預設專案不可刪除")
    # BR4.4：底下仍有系統即拒絕，**訊息須含剩餘系統數**
    remaining = db.query(System).filter(System.project_id == project_id).count()
    if remaining > 0:
        raise HierarchyConflictError(
            f"專案底下仍有 {remaining} 個系統，請先刪除它們"
        )
    db.delete(project)
    db.commit()
    logger.info("刪除專案 %s", project_id)


def delete_system(db: Session, *, system_id: int) -> None:
    """`W6`（系統）。呼叫端已完成 `BR6.5` 的擁有者檢查。"""
    system = db.query(System).filter(System.id == system_id).first()
    if system is None:
        raise HierarchyNotFound(f"查不到系統 {system_id}")
    if system.is_default:
        raise HierarchyConflictError("預設系統不可刪除")
    # BR4.3：仍有架構圖歸屬於它即拒絕。保護的是「遷移後歸屬為空的架構圖
    # 列數必須為 0」——那是 `U4` 擁有且已有測試的不變量。
    # 註：DDL 的 ON DELETE RESTRICT 也會擋，但訊息對使用者無意義。
    remaining = (
        db.query(UserDiagram).filter(UserDiagram.system_id == system_id).count()
    )
    if remaining > 0:
        raise HierarchyConflictError(
            f"系統底下仍有 {remaining} 張架構圖，請先移動或刪除它們"
        )
    db.delete(system)
    db.commit()
    logger.info("刪除系統 %s", system_id)


# ---------------------------------------------------------------------------
# 列舉型讀取（`BR6.1`）
# ---------------------------------------------------------------------------


def list_projects(db: Session, *, owner_user_id: int) -> List[Project]:
    """`BR6.1`：只回傳擁有者等於請求者的列。"""
    return (
        db.query(Project)
        .filter(Project.owner_user_id == owner_user_id)
        .order_by(Project.id)
        .all()
    )


def list_systems(db: Session, *, project_id: int) -> List[System]:
    """呼叫端已確認該專案屬請求者（`BR6.1`）。"""
    return (
        db.query(System)
        .filter(System.project_id == project_id)
        .order_by(System.id)
        .all()
    )


def resolve_work_target(
    db: Session,
    *,
    owner_user_id: int,
    project_id: Optional[int] = None,
    system_id: Optional[int] = None,
    diagram_id: Optional[int] = None,
) -> dict:
    """`W3`。唯讀且冪等（`BR2.4`）。每一層都套 `BR6.1` 的擁有者範圍。"""
    resolved: dict = {"projectId": None, "systemId": None, "diagramId": None}
    if project_id is not None:
        assert_project_owned_by(db, project_id=project_id, user_id=owner_user_id)
        resolved["projectId"] = project_id
    if system_id is not None:
        system = assert_system_owned_by(
            db, system_id=system_id, user_id=owner_user_id
        )
        resolved["systemId"] = system_id
        resolved["projectId"] = system.project_id
    if diagram_id is not None:
        diagram = assert_diagram_owned_by(
            db, diagram_id=diagram_id, user_id=owner_user_id
        )
        resolved["diagramId"] = diagram_id
        # 架構圖的歸屬權威來源是 system_id，而它**可能為空**
        # （`OPEN-H11`：新建的圖從未被指派系統）。為空時不推導上層，
        # 且**不**因此拒絕——圖本身的擁有者已驗證過。
        if diagram.system_id is not None:
            resolved["systemId"] = diagram.system_id
            system = db.query(System).filter(System.id == diagram.system_id).first()
            if system is not None:
                resolved["projectId"] = system.project_id
    return resolved


# ---------------------------------------------------------------------------
# 變更紀錄（`BR5.x`／`BR6.3`）
# ---------------------------------------------------------------------------


def record_diagram_change(
    db: Session,
    *,
    diagram_id: int,
    requirement_summary: str,
    requirement_label: str,
    actor_user_id: int,
    source: str = SOURCE_BRAIN_ORCHESTRATION,
) -> DiagramChangeRecord:
    """`W4`。非冪等（`BR2.4`）。"""
    # BR5.3：來源值必須在允許值集合內。
    if source not in ALLOWED_CHANGE_SOURCES:
        raise HierarchyValidationError(
            f"不支援的變更來源：{source}（允許值："
            f"{sorted(ALLOWED_CHANGE_SOURCES)}）"
        )
    # BR5.4：來源需求摘要非空白（空摘要的紀錄對查詢端毫無價值）。
    if requirement_summary is None or not requirement_summary.strip():
        raise HierarchyValidationError("來源需求摘要不得為空白")
    record = DiagramChangeRecord(
        diagram_id=diagram_id,
        source=source,
        # BR5.6：由呼叫端明確傳入「實際造成異動的人」，
        # **不是** session 擁有者。本函式刻意沒有預設值。
        actor_user_id=actor_user_id,
        requirement_summary=requirement_summary.strip(),
        requirement_label=(requirement_label or "").strip(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_diagram_changes(
    db: Session,
    *,
    owner_user_id: int,
    label: Optional[str] = None,
    system_id: Optional[int] = None,
) -> List[DiagramChangeRecord]:
    """`W5`／`W8`。`BR6.3`：以架構圖的 `user_id` 判定可見性，不上溯系統。

    **以 `system_id` 為條件時，`system_id` 為空的圖一律查不到**
    ——那是 `OPEN-H11` 的直接後果（新建的圖從未被指派系統歸屬），
    不是本函式的缺陷。以 `label` 查詢不受影響。
    """
    query = (
        db.query(DiagramChangeRecord)
        .join(UserDiagram, DiagramChangeRecord.diagram_id == UserDiagram.id)
        .filter(UserDiagram.user_id == owner_user_id)
    )
    if label is not None:
        query = query.filter(DiagramChangeRecord.requirement_label == label)
    if system_id is not None:
        query = query.filter(UserDiagram.system_id == system_id)
    return query.order_by(DiagramChangeRecord.id).all()


# ---------------------------------------------------------------------------
# 判定支援型查詢（`BR6.4`）—— **不套列範圍**
#
# 只回傳最小欄位：`bool`／`int`／`int`。不回傳 model 物件、不回傳名稱、
# 不回傳任何可列舉的集合，故只能驗證一個**已知**識別碼、不能枚舉未知的。
# ---------------------------------------------------------------------------


def project_exists(db: Session, *, project_id: int) -> bool:
    return (
        db.query(Project.id).filter(Project.id == project_id).first() is not None
    )


def get_project_owner(db: Session, *, project_id: int) -> int:
    row = db.query(Project.owner_user_id).filter(Project.id == project_id).first()
    if row is None:
        raise HierarchyNotFound(f"查不到專案 {project_id}")
    return int(row[0])


def get_project_of_system(db: Session, *, system_id: int) -> int:
    row = db.query(System.project_id).filter(System.id == system_id).first()
    if row is None:
        raise HierarchyNotFound(f"查不到系統 {system_id}")
    return int(row[0])
