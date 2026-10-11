"""
memory_service.py — `U8 memory-service` 的業務協調與資料存取

**契約（同進程呼叫端依賴，請勿變更）**

本層**假設授權已通過**。授權判定全部在 `MemoryFacade`（契約 `K-08` 的
`sole_entry`）；本層的任何函式都**不**判定擁有者、不判定角色。
把判定搬進來會讓授權有第二份實作，而 `sole_entry` 的保證隨即失效。

兩條禁令（`logical-components.md §一` 的元件表）：

- **不得拋 `HTTPException`**。本層是交易邊界的持有者，HTTP 關注點混進來會讓
  交易範圍難以推理；且 `U11` 的同進程呼叫路徑沒有 HTTP 回應可回。
- **不得有模組層可變容器**（`NFR4.20`）。repo 內有三處既有的行程內狀態容器
  （`collab_router` 的連線字典、`advice_orchestrator` 的
  `_executor`／`_progress`／`_inflight`、`pricing_client` 的磁碟快取），
  而 `NFR4` 明確把它們排除在本 intent 之外——本單元不得照抄那個形狀。
  本檔的模組層名字全部是**常數**（`SEARCH_SQL` 等）與函式。

## 交易邊界（`NFR4.21`／`BR4.2`／`BR5.3`）

`delete` ＋ 稽核、`widen_scope` ＋ 稽核各為**單一交易**：兩者都是
「`db.add(...)` ＋ 變更 ＋ **一次** `commit()`」。

**不得以兩次 `commit()` 實作。** 拆開會產生「記憶沒了但沒稽核」的半套狀態，
直接違反 `FR4.7`，而且**事後無法補救**——已經不知道刪了什麼。
這與 `U9` 的清除路徑是同一條紀律。

## 為什麼檢索走原生 SQL（不是 ORM）

`memory_records.embedding` 的型別是 pgvector 的 `vector(1024)`，而它的距離
運算子在沒有 `pgvector` Python 套件的情況下**無法以 SQLAlchemy 表達式寫出**
——而 `NFR8.20` 的第一項判準逐字是「`requirements.txt` 的 diff 為空」。

這同時是 `S15` 存在的理由（`infrastructure-design/cicd-pipeline.md §三之二`）：
該查詢在 SQLite 上**編不出來**，故它的正確性只能在真實 PostgreSQL 上驗。
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Optional, Sequence, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

from models import MemoryAuditEvent, MemoryRecord
from services.memory_types import (
    AUDIT_ACTION_DELETED_BY_USER,
    AUDIT_ACTION_SCOPE_CHANGED,
    EPISODIC_RETENTION_DAYS,
    MEMORY_KINDS,
    VISIBILITY_SCOPE_PLATFORM,
    ScoredCandidate,
)

logger = logging.getLogger("cloud360.memory_service")

EVENT_DENIED = "memory_authz_denied"
EVENT_SEARCH_EMPTY = "memory_search_empty"

DEFAULT_SEARCH_LIMIT = 10
MAX_SEARCH_LIMIT = 50
"""`NFR7.29`：檢索 `limit` 的**伺服器端上限**。

呼叫端指定超過時**收斂到該上限而非照辦**——這是 DoS 面的處置
（`security-design.md §五` 的 **D** 列），不是輸入驗證：超大 `limit` 不是錯誤，
它只是不會被照辦。
"""

DEFAULT_LIST_PAGE_SIZE = 50
MAX_LIST_PAGE_SIZE = 200
"""`NFR7.28`：列出路徑的分頁上限。不得一次回傳某使用者的全部記憶。"""


# ---------------------------------------------------------------------------
# 檢索的單一 SQL（`performance-design.md §一`）
# ---------------------------------------------------------------------------

SEARCH_SQL = """
SELECT id,
       kind,
       owner_user_id,
       visibility_scope,
       content,
       embedding_model,
       created_at,
       expires_at,
       embedding <=> CAST(:query_vector AS vector) AS distance
  FROM memory.memory_records
 WHERE (owner_user_id = :principal_user_id OR visibility_scope = :platform_scope)
   AND embedding_model = :embedding_model
   AND embedding IS NOT NULL
   AND kind = ANY(CAST(:kinds AS varchar[]))
 ORDER BY embedding <=> CAST(:query_vector AS vector)
 LIMIT :limit
"""
"""**一次 SQL，兩道過濾，一次排序。** 這是正確性而非效能。

| 做法 | 後果 |
|---|---|
| **單一 SQL（本常數）** | `LIMIT` 作用在**已過濾**的集合上，故回傳筆數正確 |
| 先查再於應用層過濾 | `LIMIT n` 在過濾**前**取 n 筆，過濾後可能剩不足 n——**檢索筆數錯**，且不可見的列會先進入進程（洩漏面擴大） |

兩道過濾缺一不可，且理由不同：

- `owner_user_id = ... OR visibility_scope = 'platform'` 是 `BR2.2`（**授權**）。
- `embedding_model = ...` 是 `BR3.2`（**向量空間分群**）。少了它，型別、維度、
  索引與查詢全部仍然合法，但結果是跨向量空間的垃圾**且不報錯**——這是本單元
  唯一完全靜默的失敗模式。
- `embedding IS NOT NULL` 是 `BR3.3`：fulltext 模式寫入的列不被向量檢索看到，
  而**這不是錯誤**。

`ORDER BY` 的運算子 `<=>`（cosine 距離）**必須與 HNSW 索引的 opclass
`vector_cosine_ops` 相符**（`schema_rbac.sql` 的 `I)` 區塊）。不相符時索引被
**靜默忽略**——查詢仍然正確、仍回精確最近鄰，只是退化為循序掃描，而在空表上
延遲看起來一樣好。這是 `S14` 以 `EXPLAIN` 而非延遲斷言的理由，已實測：
`<=>` 對 `vector_cosine_ops` 得 `Index Scan`，`<->` 對同一個索引得 `Seq Scan`
（即使 `enable_seqscan = off`）。

**本常數與 `verify_memory_schema.sql` 的 `S15` 是同一個查詢的兩份物化**，
由 `tests/test_memory_contract.py` 的 `C6` 鎖住三個承載語意的子句
——`team.md` 的「單一真實來源」逐字要求「新增副本的同一個 PR 必須一併新增
鎖住兩者一致的測試」。
"""


def _normalise_kinds(kinds: Optional[Sequence[str]]) -> List[str]:
    """未指定時三種皆為候選（`BR3.1` 逐字）。

    集合外的值在此**被濾掉而非拒絕**：呼叫端（facade）已驗過封閉集合，
    本層再濾一次是為了讓 SQL 的 `= ANY(...)` 不會收到垃圾值。
    """
    if not kinds:
        return list(MEMORY_KINDS)
    return [k for k in kinds if k in MEMORY_KINDS] or list(MEMORY_KINDS)


def clamp_search_limit(limit: Optional[int]) -> int:
    """`NFR7.29`：把 `limit` 收斂到伺服器端上限。

    **收斂而非拒絕**：超大 `limit` 不是錯誤。非正值回預設——`LIMIT 0` 會回空集合
    而呼叫端無從分辨「沒有結果」與「我送了 0」。
    """
    if limit is None or limit <= 0:
        return DEFAULT_SEARCH_LIMIT
    return min(limit, MAX_SEARCH_LIMIT)


def clamp_page_size(page_size: Optional[int]) -> int:
    """`NFR7.28`：列出路徑的每頁筆數上限。語意同 `clamp_search_limit`。"""
    if page_size is None or page_size <= 0:
        return DEFAULT_LIST_PAGE_SIZE
    return min(page_size, MAX_LIST_PAGE_SIZE)


def parse_memory_id(raw: object) -> Optional[int]:
    """把對外的不透明識別字轉成持久層的整數鍵；轉不出來回 `None`。

    `K-08` 的方法簽章逐字 `memory_id: str`，而 `entities.md` 把 `memoryId` 定為
    「對外為不透明識別字」。**回 `None` 而不是拋例外**是刻意的：呼叫端
    （facade）把它與「查無此列」收斂成同一個 `MemoryNotFound`，使
    `DELETE /api/memory/records/abc` 得到 404 而不是 422。

    那不只是美觀問題——422 會告訴攻擊者「id 必須是整數」，而
    `[D1]`=A 的整個目的就是不讓刪除路徑回答關於 id 空間的任何問題。
    """
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# 寫入（`functional-spec.md §1.1`）
# ---------------------------------------------------------------------------


def expiry_for(kind: str, created_at: datetime) -> Optional[datetime]:
    """`EC1`：只有 `episodic` 有保存期上界（`createdAt` ＋ 90 天）。

    `semantic`／`procedure` 回 `None`——`FR4.5` 的 90 天**只**約束 `episodic`，
    把它套到長期記憶是反方向的錯誤（`S7` 的後半段正是在驗這一點）。

    **`semantic`／`procedure` 因此沒有任何保存期上界**，已記為 `D8-5`
    （**無自然承接站**，須於核可關卡重新提交使用者）。本函式不自行補一個。
    """
    if kind != "episodic":
        return None
    return created_at + timedelta(days=EPISODIC_RETENTION_DAYS)


def create_record(
    db: Session,
    *,
    owner_user_id: int,
    kind: str,
    content: str,
    embedding_model: str,
    embedding: Optional[Sequence[float]] = None,
) -> MemoryRecord:
    """建立一則記憶並回傳它。**不產生稽核事件**（`BR7.4`）。

    `owner_user_id` 與 `visibility_scope` 由呼叫端（facade）依 `BR1.1`／`BR2.1`
    決定；本層**不**從任何酬載取它們——那個忽略動作發生在 facade，而本層連
    酬載都看不到。這個分工是 `NFR7.20`／`NFR7.21` 得以只有一個落點的原因。

    ## `embedding` 走原生 SQL，與檢索同一個理由、同一個方向

    `embedding` 不在 ORM 鏡像內（`NFR8.20`，見 `models.py` 的區塊註解），
    故它**不能**由 ORM 的 `INSERT` 帶上。`code-generation-plan.md §1.2` 的
    理由逐字是「向量路徑本來就走原生 SQL……ORM 只服務非向量路徑」——
    而那句話必須**同時**套用在讀與寫兩個方向上。只套用在讀的那一半會得到一個
    功能完整但永遠寫不進向量的實作：每一列的 `embedding` 都是 NULL，於是
    `SEARCH_SQL` 的 `embedding IS NOT NULL` 把它們全部濾掉，
    **相似度檢索永遠回空集合而不報任何錯**（`BR3.3` 會讓它看起來完全正常）。

    故：八個可鏡像的欄位走 ORM，`embedding` 隨後以 `UPDATE` ＋
    `CAST(:v AS vector)` 補上，**兩者在同一個交易內**（一次 `commit()`）。

    **SQLite 上刻意跳過那個 `UPDATE`**：那裡根本沒有 `embedding` 欄位
    （ORM 是建表來源）。這是 `S15` 必須在真實 PostgreSQL 上跑的同一個理由
    ——向量路徑在 SQLite 上不存在，不是語意不同。
    """
    created_at = datetime.now(timezone.utc)
    record = MemoryRecord(
        kind=kind,
        owner_user_id=owner_user_id,
        visibility_scope="owner",
        content=content,
        embedding_model=embedding_model,
        created_at=created_at,
        expires_at=expiry_for(kind, created_at),
    )
    db.add(record)
    # `flush` 而非 `commit`：要先取得 `record.id` 才能下那條 `UPDATE`，
    # 而兩者必須落在同一個交易內（否則會出現一列有記憶無向量的中間狀態，
    # 且它與 fulltext 模式寫入的列在資料上不可區分）。
    db.flush()
    if embedding is not None and _supports_vector(db):
        db.execute(
            text(
                "UPDATE memory.memory_records "
                "SET embedding = CAST(:embedding AS vector) WHERE id = :id"
            ),
            {"embedding": _vector_literal(embedding), "id": record.id},
        )
    db.commit()
    db.refresh(record)
    return record


def _supports_vector(db: Session) -> bool:
    """該 session 的後端是否有 pgvector 的 `vector` 型別。

    以 dialect 名稱判斷而非 try/except：後者會把一個真正的寫入失敗
    （例如維度不符）吞成「這個後端不支援向量」，而那正是
    `ADR-008`／`BR3.5` 不允許的靜默降級。dialect 是確定性的事實。
    """
    bind = db.get_bind()
    return bind is not None and bind.dialect.name == "postgresql"


# ---------------------------------------------------------------------------
# 讀取（`functional-spec.md §1.2`／`§1.3`）
# ---------------------------------------------------------------------------


def _visible_to(query, principal_user_id: int):
    """`BR2.2` 的可見範圍過濾，**在 SQL 的 `WHERE` 內**。

    `security-design.md §1.1`：不可見的列從未離開資料庫，且 `LIMIT` 作用在
    已過濾的集合上。應用層事後篩會讓洩漏面擴大且分頁筆數錯。

    **本函式是列出路徑的那一份；檢索路徑的同一條過濾在 `SEARCH_SQL` 內。**
    兩份物化是 ORM 與原生 SQL 的必然結果（§為什麼檢索走原生 SQL），
    由 `C6` 鎖住 `SEARCH_SQL` 側的存在性。
    """
    return query.filter(
        (MemoryRecord.owner_user_id == principal_user_id)
        | (MemoryRecord.visibility_scope == VISIBILITY_SCOPE_PLATFORM)
    )


def list_records(
    db: Session,
    *,
    principal_user_id: int,
    kinds: Optional[Sequence[str]] = None,
    offset: int = 0,
    page_size: Optional[int] = None,
) -> List[MemoryRecord]:
    """列出呼叫者可見的記憶，依 `createdAt` 遞減（`functional-spec.md §1.3`）。

    **不做相似度**，故 `embeddingModel` 不參與過濾——這是 `BR3.2` 不適用的
    唯一讀取路徑（`§1.3` 逐字寫下來以免被誤套）。

    `id` 進入排序鍵是刻意的：`created_at` 的精度之下同一批寫入可能同值，
    而只以它排序時分頁會**重複或漏掉列**（相鄰頁的邊界不穩定），
    且那是靜默的。與 `NFR3.24` 的次級鍵同一個理由，不同的落點。
    """
    size = clamp_page_size(page_size)
    query = _visible_to(db.query(MemoryRecord), principal_user_id)
    kind_filter = _normalise_kinds(kinds)
    query = query.filter(MemoryRecord.kind.in_(kind_filter))
    return (
        query.order_by(MemoryRecord.created_at.desc(), MemoryRecord.id.desc())
        .offset(max(offset, 0))
        .limit(size)
        .all()
    )


def search_records(
    db: Session,
    *,
    principal_user_id: int,
    query_vector: Sequence[float],
    embedding_model: str,
    kinds: Optional[Sequence[str]] = None,
    limit: Optional[int] = None,
) -> List[Tuple[MemoryRecord, float]]:
    """相似度檢索：**一次 SQL**，回 `(列, 距離)` 配對（`functional-spec.md §1.2`）。

    **此路徑在 SQLite 上編不出來**（無向量型別、無距離運算子），故它的正確性
    由 `verify_memory_schema.sql` 的 `S15` 在真實 PostgreSQL 上驗。

    回傳順序已是距離遞增（相似度遞減）。同分時的決定性次級鍵由
    `memory_ranking.rank_candidates` 施加——**那一步刻意不在 SQL 裡**，
    因為它是純函式層的 `NFR3.24` 落點，而純函式才寫得出 property-based 測試。
    """
    effective_limit = clamp_search_limit(limit)
    kind_filter = _normalise_kinds(kinds)
    vector_literal = _vector_literal(query_vector)

    rows = db.execute(
        text(SEARCH_SQL),
        {
            "query_vector": vector_literal,
            "principal_user_id": principal_user_id,
            "platform_scope": VISIBILITY_SCOPE_PLATFORM,
            "embedding_model": embedding_model,
            "kinds": list(kind_filter),
            "limit": effective_limit,
        },
    ).mappings().all()

    if not rows:
        _log_empty_search(
            db,
            principal_user_id=principal_user_id,
            embedding_model=embedding_model,
            kinds=kind_filter,
        )
        return []

    records = [
        (
            MemoryRecord(
                id=row["id"],
                kind=row["kind"],
                owner_user_id=row["owner_user_id"],
                visibility_scope=row["visibility_scope"],
                content=row["content"],
                embedding_model=row["embedding_model"],
                created_at=row["created_at"],
                expires_at=row["expires_at"],
            ),
            float(row["distance"]),
        )
        for row in rows
    ]
    return records


def _vector_literal(values: Sequence[float]) -> str:
    """把向量轉成 pgvector 的文字形式。

    以文字 ＋ `CAST(... AS vector)` 傳遞，而**不是**以 `pgvector` 套件的型別
    ——`NFR8.20` 要求 `requirements.txt` 的 diff 為空。
    """
    return "[" + ",".join(repr(float(v)) for v in values) + "]"


def scored_candidates(
    pairs: Iterable[Tuple[MemoryRecord, float]],
) -> List[ScoredCandidate]:
    """把 `(列, 距離)` 轉成純函式層的輸入。

    **距離取負號成為分數**：`<=>` 是距離（越小越相似），而
    `rank_candidates` 以分數**遞減**為主鍵。少了這個取負號，排序方向會整個反過來
    ——最不相似的列會排在最前面，而結果**仍然是決定性的**，所以
    `NFR3.24` 的字面仍然滿足。這是本轉換唯一的風險點，由
    `test_memory_authz` 之外的 `C6` 無法覆蓋，故 `rank_candidates` 的
    PBT 第 2 條性質（分數序列非遞增）是它唯一的機械防線。
    """
    return [
        ScoredCandidate(identifier=str(record.id), score=-distance)
        for record, distance in pairs
    ]


def _log_empty_search(
    db: Session,
    *,
    principal_user_id: int,
    embedding_model: str,
    kinds: Sequence[str],
) -> None:
    """`NFR7.34`：空結果時記錄**兩道過濾各自之後**的候選筆數。

    這一條的全部價值在於區分兩種長得一樣的空結果：

    | 可見範圍過濾後 | 加上模型過濾後 | 診斷 |
    |---|---|---|
    | 0 | 0 | 這個使用者真的沒有可見的記憶 |
    | **> 0** | **0** | **換過提供者而舊列未重新 embed**——`BR3.2` 把它們分到了另一個向量空間 |

    沒有這兩個數字，第二種情況看起來就是「沒有記憶」，而它其實是一個
    設定問題，且是本單元唯一完全靜默的失敗模式的可觀察面。

    **只記數字，不記內容**（`NFR7.31`／`NFR6.21`）：`content` 與 `embedding`
    不得出現在日誌中。本函式連列的 id 都不記——筆數就足以區分上表兩列。
    """
    try:
        visible = (
            _visible_to(db.query(MemoryRecord), principal_user_id)
            .filter(MemoryRecord.kind.in_(list(kinds)))
            .count()
        )
        same_model = (
            _visible_to(db.query(MemoryRecord), principal_user_id)
            .filter(MemoryRecord.kind.in_(list(kinds)))
            .filter(MemoryRecord.embedding_model == embedding_model)
            .count()
        )
    except Exception as exc:  # pragma: no cover - 診斷路徑不得讓檢索失敗
        # 外部依賴邊界（第二次查詢）：降級但**不靜默**，留下可搜尋的 WARN。
        logger.warning(
            "%s principal=%s embedding_model=%s counts_unavailable=%s",
            EVENT_SEARCH_EMPTY,
            principal_user_id,
            embedding_model,
            type(exc).__name__,
        )
        return
    logger.info(
        "%s principal=%s embedding_model=%s visible_candidates=%s "
        "same_model_candidates=%s",
        EVENT_SEARCH_EMPTY,
        principal_user_id,
        embedding_model,
        visible,
        same_model,
    )


def get_record(db: Session, memory_id: int) -> Optional[MemoryRecord]:
    """取一則記憶，**不做任何授權過濾**。

    呼叫端只有 `MemoryFacade`，而它在取列**之後**判擁有者（刪除路徑）
    ——那個順序是 `[D1]`=A 存在的原因：要知道擁有者必須先取列。
    """
    return db.query(MemoryRecord).filter(MemoryRecord.id == memory_id).first()


# ---------------------------------------------------------------------------
# 變更（各自單一交易，`NFR4.21`）
# ---------------------------------------------------------------------------


def delete_with_audit(
    db: Session, *, record: MemoryRecord, actor_user_id: int
) -> None:
    """刪除 ＋ 寫 `deleted_by_user` 稽核，**單一交易**（`BR4.2`／`NFR4.21`）。

    **一次 `commit()`。** 兩次 commit 會產生「記憶沒了但沒稽核」的半套狀態，
    直接違反 `FR4.7`，且事後無法補救。

    稽核列**刻意先 `add` 再刪記憶**：順序對結果沒有影響（同一交易），
    但它讓「稽核是這個操作的一部分」在程式碼上一眼看得出來。
    `memory_id` 在記憶被刪後仍然有效，因為該欄**沒有外鍵**（`DG-1`）
    ——這正是 `S11` 在真實 PostgreSQL 上斷言的那件事。
    """
    db.add(
        MemoryAuditEvent(
            memory_id=record.id,
            actor_user_id=actor_user_id,
            action=AUDIT_ACTION_DELETED_BY_USER,
            occurred_at=datetime.now(timezone.utc),
        )
    )
    db.delete(record)
    db.commit()


def widen_scope_with_audit(
    db: Session,
    *,
    record: MemoryRecord,
    actor_user_id: int,
    new_scope: str,
) -> MemoryRecord:
    """放寬可見範圍 ＋ 寫 `scope_changed` 稽核，**單一交易**（`BR5.3`）。

    稽核必須帶**前後兩個值**（`AC4.3.1` 要求稽核答得出「由什麼範圍改成什麼」），
    而 `EC4` 要求兩者非空且彼此不同——方向與「不同」由呼叫端（facade）的
    `BR5.2` 保證，本層只負責把它們寫對。
    """
    previous = record.visibility_scope
    record.visibility_scope = new_scope
    db.add(
        MemoryAuditEvent(
            memory_id=record.id,
            actor_user_id=actor_user_id,
            action=AUDIT_ACTION_SCOPE_CHANGED,
            previous_scope=previous,
            new_scope=new_scope,
            occurred_at=datetime.now(timezone.utc),
        )
    )
    db.commit()
    db.refresh(record)
    return record


# ---------------------------------------------------------------------------
# 稽核查詢（`functional-spec.md §1.6`）
# ---------------------------------------------------------------------------


def list_audit_events(
    db: Session,
    *,
    memory_id: Optional[int] = None,
    offset: int = 0,
    page_size: Optional[int] = None,
) -> List[Tuple[MemoryAuditEvent, bool]]:
    """列出稽核事件，回 `(事件, 該記憶是否仍存在)` 配對。

    **第二個元素是 `BR6.3` 的那一位**：`memory_id` 指不到記憶的事件
    **仍須回傳**，並讓呼叫端**可分辨**該狀態。過濾掉它會讓 `FR4.7` 在 90 天後
    變成空話——稽核存在的全部理由就是記憶消失之後還答得出「誰刪的」。

    存在性以**一次**額外查詢解析（`IN` 一組 id），不是逐列查詢——後者會讓一頁
    50 列變成 51 次往返。

    **本路徑無可見範圍過濾，這是刻意的**：授權由呼叫端的角色判定承擔
    （`BR6.1`，`Platform_Admin`／`Platform_Owner`），而擁有者**看不到**自己
    記憶的稽核事件（`[FD2]` 的選項 B 被否決的理由：同一個端點會有兩種過濾語意，
    而 `AC4.3.3` 的「被拒絕」在擁有者身上會變成「回空集合」）。
    """
    size = clamp_page_size(page_size)
    query = db.query(MemoryAuditEvent)
    if memory_id is not None:
        query = query.filter(MemoryAuditEvent.memory_id == memory_id)
    events = (
        query.order_by(
            MemoryAuditEvent.occurred_at.desc(), MemoryAuditEvent.id.desc()
        )
        .offset(max(offset, 0))
        .limit(size)
        .all()
    )
    if not events:
        return []
    referenced = {event.memory_id for event in events}
    alive = {
        row[0]
        for row in db.query(MemoryRecord.id)
        .filter(MemoryRecord.id.in_(referenced))
        .all()
    }
    return [(event, event.memory_id in alive) for event in events]


def count_audit_events(db: Session, *, memory_id: Optional[int] = None) -> int:
    """稽核事件總數。`NFR7.26` 的「寫入後列數不變」斷言需要它。"""
    query = db.query(MemoryAuditEvent)
    if memory_id is not None:
        query = query.filter(MemoryAuditEvent.memory_id == memory_id)
    return query.count()


# ---------------------------------------------------------------------------
# 拒絕日誌（`NFR7.30`／`NFR7.31`）
# ---------------------------------------------------------------------------


def log_denied(
    *, reason: str, memory_id: Optional[str], principal_user_id: int
) -> None:
    """授權被拒時記一筆 **WARN 級**結構化日誌（`NFR7.30`）。

    三個欄位（`principal`／`memory_id`／`reason`）齊備，且**只有這三個**。

    ## 這個函式是 `[D1]`=A 之後唯一能看見枚舉行為的東西

    刪除路徑的「不存在」與「非擁有者」對外**是同一個 404**，故**日誌是
    區分兩者的唯一手段**（`security-design.md §二之二`）。少了 `reason="owner"`
    這一筆，營運端就無法分辨「使用者誤刪已刪除的記憶」與「有人在走訪 id 空間」。

    ## 欄位白名單，不是黑名單（`NFR6.21`／`NFR7.31`）

    允許：principal 識別字、`memoryId`、`kind`、`reason`、過濾後筆數。
    **禁止**：`content`、`embedding`、以及**整個模型物件**。

    `logger.warning(f"denied: {memory}")` 會把 `content` 帶進日誌，而它在功能上
    完全正常、測試也會綠。本 repo 為 public 且 Actions log 公開可讀
    （`project.md` 逐字「一次意外 echo 即等同公開發布」），而本單元處理的是
    **個人對話歷程**。

    故本函式的簽章刻意**只接受純量**：沒有一個參數的型別是 `MemoryRecord`，
    所以「順手把整列傳進來」在型別上就是錯的。`memory_id` 為 `str`——它是
    呼叫端送來的那個不透明識別字，不是從資料庫查到的任何東西。
    """
    logger.warning(
        "%s principal=%s memory_id=%s reason=%s",
        EVENT_DENIED,
        principal_user_id,
        memory_id,
        reason,
    )


__all__ = [
    "DEFAULT_LIST_PAGE_SIZE",
    "DEFAULT_SEARCH_LIMIT",
    "EVENT_DENIED",
    "EVENT_SEARCH_EMPTY",
    "MAX_LIST_PAGE_SIZE",
    "MAX_SEARCH_LIMIT",
    "SEARCH_SQL",
    "clamp_page_size",
    "clamp_search_limit",
    "count_audit_events",
    "create_record",
    "delete_with_audit",
    "expiry_for",
    "get_record",
    "list_audit_events",
    "list_records",
    "log_denied",
    "parse_memory_id",
    "scored_candidates",
    "search_records",
    "widen_scope_with_audit",
]
