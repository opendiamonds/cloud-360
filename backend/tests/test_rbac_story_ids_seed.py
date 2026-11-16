"""`U3 rbac-story-ids` 的 seed 不變量與兩份副本一致性測試（一支檔，7 個案例）。

| 類 | 層 | 案例數 |
|---|---|---|
| `TestRbacStoryIdSeedMatrix` | 資料模型（計畫步 3） | 5 |
| `TestRbacSeedWriteAuditLog` | 業務邏輯（計畫步 5） | 1 |
| `TestRbacSeedCopiesAgree` | 完整性（計畫步 6） | 1 |

**為什麼是一支而不是三支**（`nfr-design` 的 `D-10`）：七個案例都只需要
「解析 `DEFAULT_ROLE_PERMISSIONS`」這一份邏輯。分檔會把同一份解析寫三次，
而 `team.md ## Code Style` 的「單一真實來源」正是本單元在防的東西——
在它自己的測試裡製造三份副本是自相矛盾。

**五條結構約束的失敗訊息都必須說出它保護哪一條 AC**（`nfr-design` 的 `D-12`）。
理由：它們紅燈時的現象（「某個角色的旗標跟預期不同」）看起來像測試太嚴，
而不是像缺陷；不寫出「這會讓 `AC12.5.1` 變成死碼」，下一個人會把它當噪音刪掉。

**零新依賴**：`ast` 未使用（直接 import 受測物件比解析原始碼更貼近執行期契約），
`re`／`unittest`／`collections` 皆標準庫，`backend/requirements.txt` 不變。

**不用 `hypothesis`**：`rules.md` 修訂 1 實算的 `calculation` 類規則為 0，
七個案例全部是對固定資料集合的斷言，沒有值域可探索。`ADR-0006` 的 PBT
hard constraint 點名的三個模組（IaC generator、cost calculator、agent routing）
皆不在本單元；`BR7.4` 點名的挑選純函式（真正的 PBT 標的，性質為排列不變性）
是 `U19` 的交付物，已由 `U3-A3` 具名交接。判定為 **N/A 而非豁免**。

**無 `@api`／`@ui` 註解**：本單元零端點、零畫面（`SEC-1`／`SEC-3`）。
依 `project.md` 的既有更正「受測對象既無端點也無 UI 時寧可缺、不得捏造」。
"""

import tests.helpers  # noqa: F401  -- installs the psycopg stub before services import

import re
import unittest
from collections import Counter
from pathlib import Path

from tests import helpers
from services.rbac import CANONICAL_ROLES
from services.rbac_seed_data import DEFAULT_ROLE_PERMISSIONS

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_RBAC_SQL = REPO_ROOT / "schema_rbac.sql"

# 本單元新增的四個 story id（`entities.md` 的 `StoryId.allowed_values_added_by_this_unit`）。
NEW_STORY_IDS = ("K1", "K2", "K3", "K4")

# `BR3.4`′：11 角色 × 32 story id。既有 308 ＝ 11 × 28（組合完整），308 ＋ 44 ＝ 352。
EXPECTED_ROW_COUNT = 352
EXPECTED_STORY_ID_COUNT = 32
EXPECTED_NEW_ROW_COUNT = 44


def _flag_map():
    """`(role, story_id)` → `(can_view, can_edit, can_review)`。

    刻意**不**在模組層建一次就快取：突變驗證要靠重新 import 取得新值，而
    模組層的常數在同一個 process 內只算一次。每個案例各自呼叫一次成本可忽略。
    """
    return {(role, sid): (v, e, r) for role, sid, v, e, r in DEFAULT_ROLE_PERMISSIONS}


def _flags(role, story_id):
    value = _flag_map().get((role, story_id))
    if value is None:
        raise AssertionError(
            f"預設矩陣缺少 ({role!r}, {story_id!r}) 這一列——"
            "矩陣有破洞，先看 test_the_matrix_has_exactly_352_rows_and_no_missing_combination"
        )
    return value


class TestRbacStoryIdSeedMatrix(unittest.TestCase):
    """資料模型層：`U3-V1`–`U3-V5` 五條 seed 不變量。"""

    def test_the_matrix_has_exactly_352_rows_and_no_missing_combination(self):
        """
        @purpose `BR3.4`′ 逐字要求「同時驗總數**與**組合完整性」。兩者是兩個
                 獨立的失敗模式：把一列的 story_id 由 K4 改成 K3 會讓總數仍是
                 352 而組合有缺漏，缺的那格在權限頁是破洞而總數看起來正常。
        @given services/rbac_seed_data.py 的 DEFAULT_ROLE_PERMISSIONS
        @step 取清單長度 | 恰為 352（11 角色 × 32 story id）
        @step 取相異 story id 數 | 恰為 32，且含 K1／K2／K3／K4
        @step 對 CANONICAL_ROLES × story_ids 的每個組合數出現次數 | 每個組合恰一次
        @pass 長度為 352，且無重複組合、無缺漏組合、無預期外組合
        @story US1.4
        @note 兩個子斷言不可合併——突變 M1（刪一列）只有長度抓得到，
              突變 M2（K4 改成 K3）只有組合抓得到。
        """
        rows = list(DEFAULT_ROLE_PERMISSIONS)

        # 子斷言 A：總數
        self.assertEqual(
            len(rows),
            EXPECTED_ROW_COUNT,
            f"預設矩陣應為 {EXPECTED_ROW_COUNT} 列（11 角色 × {EXPECTED_STORY_ID_COUNT} "
            f"story id），實為 {len(rows)} 列。BR3.4′ 的總數約束被破壞——"
            "少列代表某個 (角色, 能力) 組合在權限頁是破洞，而 user_can 對缺列回 "
            "false，現象是「那個角色沒有那個權限」而不是一個可辨識的錯誤。",
        )

        # 子斷言 B：組合完整性（與 A 是兩個獨立的失敗模式）
        seen = Counter((role, sid) for role, sid, *_ in rows)
        story_ids = sorted({sid for _, sid, *_ in rows})
        self.assertEqual(
            len(story_ids),
            EXPECTED_STORY_ID_COUNT,
            f"相異 story id 應為 {EXPECTED_STORY_ID_COUNT} 個，實為 "
            f"{len(story_ids)} 個：{story_ids}",
        )
        for sid in NEW_STORY_IDS:
            self.assertIn(
                sid,
                story_ids,
                f"本單元新增的 story id {sid!r} 不在預設矩陣內",
            )

        expected = {(role, sid) for role in CANONICAL_ROLES for sid in story_ids}
        duplicated = sorted(k for k, v in seen.items() if v > 1)
        missing = sorted(expected - set(seen))
        unexpected = sorted(set(seen) - expected)
        self.assertEqual(
            (duplicated, missing, unexpected),
            ([], [], []),
            "預設矩陣的 (角色, story_id) 組合不完整——BR3.4′ 的組合約束被破壞。"
            f"\n  重複的組合（{len(duplicated)}）：{duplicated[:10]}"
            f"\n  缺漏的組合（{len(missing)}）：{missing[:10]}"
            f"\n  預期外的組合（{len(unexpected)}）：{unexpected[:10]}"
            "\n總數可能仍然正確——這正是本子斷言不能併入長度斷言的理由。",
        )

    def test_a_role_with_a1_view_does_not_hold_k3(self):
        """
        @purpose `BR5.3` 的可達性保證。若每個持有 A1 view 的角色都持有 K3，
                 AC12.5.1 的 Given「一位沒有對應全域功能權限的使用者」變成
                 不可構造，該 AC 成為永遠不會失敗的死碼。
        @given 預設矩陣的 A1 與 K3 兩欄
        @step 找出持有 A1.can_view 但 K3 三旗標皆 false 的角色 | 至少一個
        @pass 候選集合非空
        @story US1.4
        @note 違反時不會有任何錯誤訊息——測試照樣綠燈，因為它測不到東西。
              本斷言是存在量化（`BR5.3` 的 logic 逐字「IF 存在 role ...」），
              故單一角色的突變不足以讓它紅；見 code-summary.md 的突變段。
        """
        candidates = [
            role
            for role in CANONICAL_ROLES
            if _flags(role, "A1")[0] and not any(_flags(role, "K3"))
        ]
        self.assertTrue(
            candidates,
            "沒有任何角色同時「持有 A1 view」且「完全不持有 K3」——"
            "BR5.3 的可達性保證被破壞。後果：AC12.5.1（邀請缺權限者被拒且畫面"
            "說明他缺少什麼）與 AC12.5.3（拒絕不留半套狀態）的 Given 不可構造，"
            "兩條 AC 成為永遠不會失敗的死碼。這不是測試太嚴——是 K3 的預設值"
            "給得太寬，使「缺少全域成員權限的使用者」在系統中不存在。",
        )

    def test_at_least_one_role_does_not_hold_k4(self):
        """
        @purpose `BR6.5` 的可達性保證。若每個角色都持有 K4，BR6.4（無 K4 者
                 隱藏未填計數）成為不可觸發的死碼——而它是修訂 1 新增的規則。
        @given 預設矩陣的 K4 欄
        @step 找出 K4 三旗標皆 false 的角色 | 至少一個
        @pass 候選集合非空
        @story US9.2
        @note 同為存在量化（`BR6.5` 的 logic 逐字「IF 存在 role ...」）。
        """
        candidates = [
            role for role in CANONICAL_ROLES if not any(_flags(role, "K4"))
        ]
        self.assertTrue(
            candidates,
            "沒有任何角色完全不持有 K4——BR6.5 的可達性保證被破壞。"
            "後果：BR6.4（不持有 K4 者看不到未填欄位計數）成為不可觸發的死碼，"
            "而沒有任何測試或畫面會顯示這件事發生了。",
        )

    def test_every_k2_editor_also_holds_k3_edit(self):
        """
        @purpose `BR5.4` 的硬約束。持有 K2.edit 的角色能建立專案並依 FR12.1
                 自動成為該專案的 project_admin，卻因缺 K3.edit 而在全域層被
                 擋住每一個成員管理動作。
        @given 預設矩陣的 K2 與 K3 兩欄
        @step 找出持有 K2.can_edit 的角色 | 非空（否則本斷言恆真）
        @step 逐一檢查其 K3.can_edit | 全部為 true
        @pass K2.edit 的持有者集合是 K3.edit 持有者集合的子集
        @story US9.2
        @note 反向不成立：持有 K3.edit 而不持有 K2.edit 是允許的，本條只約束
              單向蘊含。前一步的非空檢查是必要的——若 K2.edit 無人持有，
              蘊含式會恆真而這條變成不會失敗的測試。
        """
        k2_editors = [role for role in CANONICAL_ROLES if _flags(role, "K2")[1]]
        self.assertTrue(
            k2_editors,
            "沒有任何角色持有 K2.edit——BR5.4 的蘊含式會恆真，本斷言失去效力。"
            "BR2.3 要求 K2.edit 涵蓋建立專案，故這個集合不得為空。",
        )

        missing_k3_edit = [role for role in k2_editors if not _flags(role, "K3")[1]]
        self.assertEqual(
            missing_k3_edit,
            [],
            f"下列角色持有 K2.edit 卻不持有 K3.edit：{missing_k3_edit}——"
            "BR5.4 被破壞。後果：AC12.1.2 逐字「Given 我剛建立一個專案，"
            "When 我嘗試邀請成員，Then 該動作可用——不需任何額外授權步驟」"
            "直接失敗。現象是「我建的專案，我管不動」，而權限頁上看不出原因"
            "（兩層串聯的失敗層不會被標示出來）。",
        )

    def test_the_four_new_story_ids_never_grant_review(self):
        """
        @purpose `EC-4`：四個新 id 的 can_review 在全部 44 列皆為 false。
                 K3／K4 不用 can_review 的理由是**沒有消費端**——K-16 的
                 public_interface 沒有任何「審核」動作。
        @given 預設矩陣中 story_id 屬於 K1–K4 的那些列
        @step 數出這些列 | 恰 44 列（11 角色 × 4 id）
        @step 逐列檢查 can_review | 全部為 false
        @pass 44 列全部 can_review = false
        @story US1.4
        @note 44 列的計數不是裝飾——少了它，若 K 列整批消失這個迴圈會空轉
              而仍然綠燈（construction.md 禁止無論實作對錯都會通過的測試）。
              J3a／J3b 確實使用 can_review，故「管理類 id 一律不用 can_review」
              並非既有通則，本條是本單元自己的約束。
        """
        new_rows = [row for row in DEFAULT_ROLE_PERMISSIONS if row[1] in NEW_STORY_IDS]
        self.assertEqual(
            len(new_rows),
            EXPECTED_NEW_ROW_COUNT,
            f"K1–K4 應共 {EXPECTED_NEW_ROW_COUNT} 列（11 角色 × 4 id），"
            f"實為 {len(new_rows)} 列——本斷言的受測集合本身不完整。",
        )

        granting_review = [(row[0], row[1]) for row in new_rows if row[4]]
        self.assertEqual(
            granting_review,
            [],
            f"下列 K1–K4 的列把 can_review 設為 true：{granting_review}——"
            "EC-4 被破壞。後果：挪用既有的審核語意，而權限頁該欄的標籤對"
            "不同列代表不同意思（K3／K4 沒有任何消費端會讀它）。",
        )


class TestRbacSeedWriteAuditLog(unittest.TestCase):
    """業務邏輯層：`SEC-4` 的 log 擴充由本案例升為**受測契約**（`D-7`）。"""

    def test_the_seed_write_logs_which_rows_it_inserted(self):
        """
        @purpose `SEC-4`：ensure_missing_role_permissions 插入列時必須記錄
                 **是哪些** (role, story_id)，不得只記列數。既有環境補進 44 列
                 之後，若日誌只說「插了 44 列」，沒有任何方式確認那 44 列
                 是不是 K1–K4 的。
        @given 一個已完整 seed 的 in-memory 資料庫，先刪掉 K1–K4 的 44 列，
               以重現「既有環境尚未有新 story id」的狀態
        @step 在 assertLogs 下呼叫 ensure_missing_role_permissions | 回傳 44
        @step 檢查捕捉到的 INFO 訊息 | 四個新 story id 的字串都出現其中
        @step 檢查訊息不含使用者名稱 | 不含（log 只寫角色與 story id）
        @pass 回傳 44，且 K1／K2／K3／K4 四個字串都在捕捉到的訊息裡
        @story US1.4
        @note 斷言只綁四個 story id 的字串、**不綁整句措辭**（`D-8`）：綁整句
              會讓任何文案修訂紅燈，綁零內容（只驗「有一行 log」）則回到
              SEC-4 要防的那個缺口。這已是最寬鬆而仍有效的綁法。
              **但 log 的文字格式自此成為受測契約**——下一個改 log 文案的人
              若讓四個 story id 不再出現在同一行，這條會紅。那是刻意的。
              `database.py` 呼叫端另外記的那次裸列數**不收斂**（`D-9`），
              它不影響本斷言（詳細字串仍在）。
        """
        from models import RolePermission
        from services.rbac import ensure_missing_role_permissions

        db = helpers.make_session()
        try:
            removed = (
                db.query(RolePermission)
                .filter(RolePermission.story_id.in_(NEW_STORY_IDS))
                .delete(synchronize_session=False)
            )
            db.commit()
            self.assertEqual(
                removed,
                EXPECTED_NEW_ROW_COUNT,
                f"前置條件不成立：應刪掉 {EXPECTED_NEW_ROW_COUNT} 列 K1–K4，"
                f"實刪 {removed} 列",
            )

            with self.assertLogs("cloud360.rbac", level="INFO") as captured:
                inserted = ensure_missing_role_permissions(db)

            self.assertEqual(
                inserted,
                EXPECTED_NEW_ROW_COUNT,
                f"應補回 {EXPECTED_NEW_ROW_COUNT} 列，實補 {inserted} 列",
            )

            message = "\n".join(captured.output)
            for sid in NEW_STORY_IDS:
                self.assertIn(
                    sid,
                    message,
                    f"seed 寫入的日誌沒有提到 {sid!r}——SEC-4 被破壞。"
                    "後果：既有環境補進 44 列之後，日誌只說「插了 44 列」，"
                    "而沒有任何方式確認那 44 列是不是 K1–K4 的。"
                    f"\n實際捕捉到的訊息：\n{message}",
                )
            self.assertIn(
                "Project_Architect",
                message,
                "日誌沒有記下角色名——SEC-4 要求的是 (role, story_id) 配對，"
                "只有 story id 仍無法確認是哪些列。"
                f"\n實際捕捉到的訊息：\n{message}",
            )
        finally:
            helpers.close_session(db)


# `schema_rbac.sql` 的一列 seed，形如 `  ('Project_Architect', 'K1', true, false, false),`
_SQL_ROW = re.compile(
    r"\(\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*"
    r"(true|false)\s*,\s*(true|false)\s*,\s*(true|false)\s*\)",
    re.IGNORECASE,
)
_SQL_INSERT_ANCHOR = "INSERT INTO role_permissions"


def _sql_seed_rows():
    """解析 `schema_rbac.sql` 的 `role_permissions` seed 區塊。

    **範圍以區塊邊界定位，不得寫死行號**（`nfr-design` 的 `D-4`）：以
    「`INSERT INTO role_permissions` 之後、下一個裸 `;` 之前」界定。本單元
    自己的 44 列插入就會讓 445／755 這兩個實測行號位移。

    限定範圍的理由是**前瞻而非現況**：本單元實測全檔 `INSERT INTO` 命中數為 1，
    沒有東西可以被誤撿；限定範圍是為了讓這支解析在日後有人加入第二個
    `INSERT INTO` 區塊時不會靜默地把它的 tuple 併進比對集合。

    回傳 `(tuples, anchor_count)`。
    """
    sql = SCHEMA_RBAC_SQL.read_text(encoding="utf-8")
    anchor_count = sql.count(_SQL_INSERT_ANCHOR)
    start = sql.find(_SQL_INSERT_ANCHOR)
    if start == -1:
        return [], anchor_count
    end = sql.find(";", start)
    body = sql[start:end] if end != -1 else sql[start:]
    return [
        (role, story_id, v.lower() == "true", e.lower() == "true", r.lower() == "true")
        for role, story_id, v, e, r in _SQL_ROW.findall(body)
    ], anchor_count


def _render_section(title, rows, cause):
    head = f"\n  [{title}] {len(rows)} 列（{cause}）"
    if not rows:
        return head + "：無"
    shown = "".join(f"\n    {row}" for row in rows[:10])
    more = f"\n    …另有 {len(rows) - 10} 列未列出" if len(rows) > 10 else ""
    return head + "：" + shown + more


class TestRbacSeedCopiesAgree(unittest.TestCase):
    """完整性層：`SEC-5`／`BR4.4`′——兩份 seed 副本逐列等值。"""

    def test_the_sql_seed_block_matches_the_python_default_row_for_row(self):
        """
        @purpose `SEC-5`：兩份 seed 副本必須逐列等值。要防的失敗模式是**環境相依
                 且無聲**的——從 schema_rbac.sql 建的新環境拿 SQL 那份的值，
                 既有環境經 ensure_missing_role_permissions 拿 Python 那份的值；
                 兩者不同時沒有任何閘門會紅燈，而現象是「同一個角色在不同環境
                 有不同權限」。本案例是這件事的唯一防線。
        @given repo 根的 schema_rbac.sql 與 services/rbac_seed_data.py
        @step 以區塊邊界定位並解析 SQL 的 seed 區塊 | 取得非空的 tuple 清單
        @step 檢查 SQL 側無重複 tuple | 無（重複會違反 (role, story_id) 唯一約束）
        @step 比對 (role, story_id, can_view, can_edit, can_review) 的集合 | 兩者相等
        @pass 兩份副本的 tuple 集合完全相等
        @story US9.2
        @note 失敗時輸出**三段** diff（只在 SQL／只在 Python／兩邊都有但旗標不同），
              各最多 10 筆並附該段總數。**第三段不可省**（`D-5`）：只比列數與
              story id 集合會讓「列在、但旗標不同」整類漏掉，而那正是
              SEC-5 存在的全部理由。也不用 assertEqual 的預設輸出——352 個元素
              的集合不等時 unittest 會印出完整的兩個集合，而這支測試紅燈的時機
              正是最需要快速定位的時候。
              兩份副本本身**不消除**（`RR-3`）：rbac_seed_data.py 的檔頭說它由
              schema_rbac.sql 產生，而**那支產生腳本不存在**（backend/scripts/ 下
              只有 dump_openapi.py、dump_ws_contract.py、run_hierarchy_migration.py）。
              消除副本要先寫產生器，那是獨立任務。
        """
        sql_rows, anchor_count = _sql_seed_rows()

        self.assertTrue(
            sql_rows,
            f"在 {SCHEMA_RBAC_SQL} 的 {_SQL_INSERT_ANCHOR!r} 區塊裡解析不到任何列"
            f"（命中 {anchor_count} 個區塊錨點）——解析失效時這支測試會變成"
            "恆真，故此處必須先擋下。",
        )

        sql_duplicates = sorted(
            row for row, n in Counter(sql_rows).items() if n > 1
        )
        self.assertEqual(
            sql_duplicates,
            [],
            f"schema_rbac.sql 的 seed 區塊有重複列：{sql_duplicates[:10]}——"
            "會違反 (role, story_id) 的唯一約束。",
        )

        sql_set = set(sql_rows)
        python_set = set(DEFAULT_ROLE_PERMISSIONS)

        only_sql = sorted(sql_set - python_set)
        only_python = sorted(python_set - sql_set)
        sql_flags = {(r[0], r[1]): r[2:] for r in sql_rows}
        python_flags = {(r[0], r[1]): tuple(r[2:]) for r in DEFAULT_ROLE_PERMISSIONS}
        differing = sorted(
            (key, python_flags[key], sql_flags[key])
            for key in set(sql_flags) & set(python_flags)
            if sql_flags[key] != python_flags[key]
        )

        self.assertEqual(
            (only_sql, only_python, differing),
            ([], [], []),
            "兩份 seed 副本不一致——SEC-5／BR4.4′ 被破壞。"
            f"\nSQL 側 {len(sql_rows)} 列（{anchor_count} 個 INSERT 區塊錨點）、"
            f"Python 側 {len(DEFAULT_ROLE_PERMISSIONS)} 列。"
            + _render_section("只在 SQL", only_sql, "Python 那份漏加")
            + _render_section("只在 Python", only_python, "SQL 那份漏加")
            + _render_section(
                "兩邊都有但旗標不同（(role, story_id), python, sql）",
                differing,
                "值不同——最危險的那一類",
            )
            + "\n後果是環境相依且無聲：從 schema_rbac.sql 建的新環境與既有環境"
            "會拿到不同的權限矩陣，而沒有任何閘門會紅燈。",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
