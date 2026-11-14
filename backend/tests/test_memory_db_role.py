"""合併前必修第 20／29 列：記憶專用資料庫角色 `cloud360_memory`。

2026-10-31 使用者裁決「SQL 建角色，部署另設密碼」：
- `schema_rbac.sql` 以可重跑寫法建立角色，**不帶密碼、不含任何 psql 變數**（它的兩條
  執行路徑——initdb 與 `run_meta_schema_migration.py` 的 DBAPI cursor——都無法傳入
  psql 變數）；只授與 `memory` schema 的權限並撤銷 `public` 的權限。
- 密碼由 `deploy/initdb/02-memory-role-password.sh` 以 `MEMORY_DB_PASSWORD` 設定。
- backend 以主連線的主機與資料庫 ＋ 該角色組出記憶專用連線；未設定時**不退回**擁有者帳號。

角色在真實 PostgreSQL 上的邊界（讀不到 public、寫得進 memory）由 CI 的 memory-schema
job 以該角色連線跑 `backend/scripts/verify_memory_role.sql` 驗證；本檔驗本機可驗的部分：
SQL 文字的形狀、連線字串的組法、未設定時的行為、`render-env.sh` 與密碼 script 的拒絕
條件，以及部署／CI 的接線。

**突變驗證**（結果記於 `brain-infra` 的 `code-summary.md`）：
  M1 `CREATE ROLE` 改成帶 `PASSWORD :'pw'` → 案例 1 紅；
  M2 拿掉 `REVOKE ALL ON ALL TABLES IN SCHEMA public` → 案例 2 紅；
  M3 連線字串保留主連線的使用者名稱 → 案例 3 紅；
  M4 `get_memory_session` 未設定時退回 `SessionLocal` → 案例 4 紅；
  M5 `render-env.sh` 拿掉 MEMORY_DB_PASSWORD 的必填檢查 → 案例 5 紅；
  M6 密碼 script 拿掉空值檢查 → 案例 6 紅；
  M7 部署步驟拿掉 `::add-mask::` → 案例 7 紅。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from sqlalchemy.engine import make_url

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
sys.path.insert(0, str(BACKEND / "scripts"))

import database  # noqa: E402
import run_meta_schema_migration as meta  # noqa: E402

SCHEMA = REPO / "schema_rbac.sql"
PASSWORD_SCRIPT = REPO / "deploy" / "initdb" / "02-memory-role-password.sh"
RENDERER = REPO / "deploy" / "render-env.sh"


def _strip_sql_comments(sql: str) -> str:
    return "\n".join(line.split("--", 1)[0] for line in sql.splitlines())


def _statements(sql: str) -> list:
    return [" ".join(st.split()) for st in _strip_sql_comments(sql).split(";") if st.strip()]


def _i_block() -> str:
    (_, text), = meta.extract_blocks(SCHEMA.read_text(encoding="utf-8"), ("I",))
    return text


def _run(cmd, env_overrides, cwd=REPO):
    env = {k: v for k, v in os.environ.items() if k != "MEMORY_DB_PASSWORD"}
    env.update(env_overrides)
    return subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True)


class MemoryRoleSqlTest(unittest.TestCase):
    def test_role_is_created_idempotently_without_password_or_psql_variables(self):
        """
        @purpose schema_rbac.sql 以可重跑形狀建角色，不帶密碼、不含 psql 變數（兩條執行路徑都能跑）
        @given schema_rbac.sql 的 I) 區塊（以 run_meta_schema_migration.extract_blocks 解析）
        @step 找 CREATE ROLE 敘述與其外層的 pg_roles 判斷；掃整份檔的 psql 變數與 meta-command
        @pass CREATE ROLE cloud360_memory LOGIN 在 IF NOT EXISTS (… pg_roles …) 之內、不含 PASSWORD；全檔無 :'x'／:"x"／反斜線 meta-command
        @story US4.1
        """
        block = _strip_sql_comments(_i_block())
        m = re.search(
            r"IF NOT EXISTS \(SELECT 1 FROM pg_roles WHERE rolname = 'cloud360_memory'\) THEN\s*CREATE ROLE cloud360_memory LOGIN\s*;",
            block,
        )
        self.assertIsNotNone(m, "角色建立必須以 pg_roles 判斷包住，使重跑安全")
        creates = [st for st in _statements(_i_block()) if "CREATE ROLE" in st.upper()]
        self.assertTrue(creates)
        for st in creates:
            self.assertNotIn("PASSWORD", st.upper(), st)
        whole = _strip_sql_comments(SCHEMA.read_text(encoding="utf-8"))
        self.assertIsNone(re.search(r":'[A-Za-z_]+'|:\"[A-Za-z_]+\"", whole), "含 psql 變數")
        self.assertEqual(
            [ln for ln in whole.splitlines() if ln.lstrip().startswith("\\")], [],
            "含 psql meta-command（DBAPI 路徑無法執行）",
        )

    def test_role_privileges_open_only_the_memory_schema(self):
        """
        @purpose 授給 cloud360_memory 的權限只涉及 memory schema，並撤銷 public 的表、序列與 CREATE
        @given schema_rbac.sql 的 I) 區塊
        @step 列出所有以 cloud360_memory 為對象的 GRANT／ALTER DEFAULT PRIVILEGES／REVOKE
        @pass 每條 GRANT 都限定 SCHEMA memory；三條 REVOKE（tables、sequences、CREATE）都在
        @story US4.1
        """
        statements = _statements(_i_block())
        grants = [s for s in statements if s.upper().startswith(("GRANT", "ALTER DEFAULT")) and "cloud360_memory" in s]
        self.assertGreaterEqual(len(grants), 5, grants)
        for st in grants:
            self.assertIn("SCHEMA memory", st, st)
            self.assertNotIn("public", st.lower(), st)
        revokes = {s for s in statements if s.upper().startswith("REVOKE") and "cloud360_memory" in s}
        self.assertEqual(
            revokes,
            {
                "REVOKE ALL ON ALL TABLES IN SCHEMA public FROM cloud360_memory",
                "REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM cloud360_memory",
                "REVOKE CREATE ON SCHEMA public FROM cloud360_memory",
            },
        )


class MemoryConnectionTest(unittest.TestCase):
    def test_memory_url_swaps_identity_and_keeps_host_and_database(self):
        """
        @purpose 記憶專用連線字串＝主連線的主機、埠、資料庫 ＋ cloud360_memory 與其密碼；不適用時回 None
        @given database.build_memory_database_url
        @step 以 PostgreSQL、裸 postgresql://、SQLite、空密碼與含特殊字元的密碼各呼叫一次
        @pass 使用者換成 cloud360_memory、密碼原樣（可往返解析）、主機與資料庫不變；SQLite 與空密碼回 None
        @story US4.1
        """
        url = database.build_memory_database_url(
            "postgresql+psycopg://postgres:owner-pw@db:5432/cloud360", "m@:/pw"
        )
        parsed = make_url(url)
        self.assertEqual(parsed.username, database.MEMORY_DB_ROLE)
        self.assertEqual(parsed.password, "m@:/pw")
        self.assertEqual((parsed.host, parsed.port, parsed.database), ("db", 5432, "cloud360"))
        self.assertNotIn("owner-pw", url)
        bare = make_url(database.build_memory_database_url("postgresql://u:p@h/d", "x"))
        self.assertEqual(bare.drivername, "postgresql+psycopg")
        self.assertIsNone(database.build_memory_database_url("sqlite:///:memory:", "x"))
        self.assertIsNone(database.build_memory_database_url("postgresql+psycopg://u:p@h/d", ""))
        self.assertIsNone(database.build_memory_database_url("postgresql+psycopg://u:p@h/d", None))

    def test_unconfigured_memory_session_refuses_instead_of_falling_back(self):
        """
        @purpose 未設定時取記憶 session 會明確失敗，不退回擁有者帳號
        @given 測試環境（MEMORY_DB_PASSWORD 未設）
        @step 呼叫 memory_db_boundary_enabled() 與 get_memory_session()
        @pass 前者 False；後者拋 MemoryDatabaseNotConfigured
        @story US4.1
        """
        self.assertFalse(database.memory_db_boundary_enabled())
        with self.assertRaises(database.MemoryDatabaseNotConfigured):
            database.get_memory_session()


class MemoryPasswordPlumbingTest(unittest.TestCase):
    BASE = {
        "POSTGRES_PASSWORD": "test-only-value-pg",
        "JWT_SECRET": "test-only-value-jwt",
        "REDIS_PASSWORD": "test-only-value-redis",
    }

    def render(self, **extra):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "rendered.env"
            res = _run(["bash", str(RENDERER), str(out)], {**self.BASE, "HOME": tmp, **extra})
            return res, (out.read_text(encoding="utf-8") if out.exists() else "")

    def test_render_env_requires_and_writes_memory_db_password(self):
        """
        @purpose render-env.sh：MEMORY_DB_PASSWORD 缺值或含 $ 時拒絕；正常值逐字寫入
        @given 其餘必填值皆為測試假值
        @step 不設 → 設為空字串 → 設為 ab$cd → 設為正常值，各渲染一次
        @pass 前三者非零退出且 stderr 點名它、不產生檔；第四者零退出且有 MEMORY_DB_PASSWORD=<值>
        @story US4.1
        """
        res, rendered = self.render()
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("MEMORY_DB_PASSWORD", res.stderr)
        self.assertEqual(rendered, "")
        # 空字串與未設定不同：`set -u` 擋得住未設定，擋不住空字串——必填檢查擋的是這個。
        res, rendered = self.render(MEMORY_DB_PASSWORD="")
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("missing required value(s): MEMORY_DB_PASSWORD", res.stderr)
        self.assertEqual(rendered, "")
        res, rendered = self.render(MEMORY_DB_PASSWORD="ab$cd")
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("MEMORY_DB_PASSWORD", res.stderr)
        res, rendered = self.render(MEMORY_DB_PASSWORD="test-only-value-memory")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("\nMEMORY_DB_PASSWORD=test-only-value-memory\n", "\n" + rendered)

    def test_password_script_refuses_bad_values_and_keeps_password_off_command_lines(self):
        """
        @purpose 密碼 script 拒絕空值與含 $ 的值；密碼只經 \\getenv 進 psql，不出現在任何命令列
        @given deploy/initdb/02-memory-role-password.sh
        @step 以空值與 ab$cd 各執行一次（兩者都在呼叫 psql 之前結束）；靜態檢查 psql 的呼叫方式
        @pass 兩次皆非零退出且 stderr 說明原因；script 以 \\getenv 讀密碼，沒有 -v／-c 帶它，也沒有 echo 它
        @story US4.1
        """
        res = _run(["bash", str(PASSWORD_SCRIPT)], {"MEMORY_DB_PASSWORD": ""})
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("MEMORY_DB_PASSWORD is empty", res.stderr)
        res = _run(["bash", str(PASSWORD_SCRIPT)], {"MEMORY_DB_PASSWORD": "ab$cd"})
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("contains '$'", res.stderr)
        text = PASSWORD_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("\\getenv memory_db_password MEMORY_DB_PASSWORD", text)
        self.assertIn("PASSWORD :'memory_db_password'", text)
        code = [ln for ln in text.splitlines() if not ln.lstrip().startswith("#")]
        for ln in code:
            if "MEMORY_DB_PASSWORD" in ln and ("-v " in ln or "-c " in ln):
                self.fail(f"密碼以 psql 參數傳入（會出現在命令列）：{ln}")
            if "echo" in ln and "${MEMORY_DB_PASSWORD}" in ln:
                self.fail(f"密碼被印出：{ln}")
        self.assertTrue(os.access(PASSWORD_SCRIPT, os.X_OK), "initdb 以可執行檔執行它（否則會被 source）")

    def test_deploy_ci_and_compose_wiring(self):
        """
        @purpose 部署、CI 與兩份 compose 的接線齊備（缺一處就是一條無聲的設定斷點）
        @given deploy.yml、ci.yml、兩份 compose
        @step 讀四個檔
        @pass deploy.yml 的必要 secret 檢查含它、設密碼步驟先 mask 再以 stdin 餵 script；
              ci.yml 以 cloud360_memory 跑 verify_memory_role.sql；deploy compose 的 backend
              無 fallback 地讀它；test compose 掛載 02 script，db 與 backend 的預設值相同
        @story US4.1
        """
        deploy = (REPO / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
        self.assertIn('[ -n "${MEMORY_DB_PASSWORD}" ] || missing="${missing} MEMORY_DB_PASSWORD"', deploy)
        step = deploy.split("- name: Set the memory-only database role password", 1)[1].split("- name:", 1)[0]
        self.assertIn('echo "::add-mask::${MEMORY_DB_PASSWORD}"', step)
        self.assertLess(step.index("::add-mask::"), step.index("exec -T"))
        self.assertIn("bash -s < deploy/initdb/02-memory-role-password.sh", step)
        ci = (REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertRegex(ci, r"psql -U cloud360_memory -d cloud360 \\\s*\n\s*-v ON_ERROR_STOP=1 -v uid=\"\$\{UID_FIXTURE\}\" -f backend/scripts/verify_memory_role.sql")
        deploy_compose = (REPO / "deploy" / "docker-compose.deploy.yml").read_text(encoding="utf-8")
        self.assertIn("      MEMORY_DB_PASSWORD: ${MEMORY_DB_PASSWORD}\n", deploy_compose)
        test_compose = (REPO / "deploy" / "docker-compose.test.yml").read_text(encoding="utf-8")
        self.assertIn(
            "./initdb/02-memory-role-password.sh:/docker-entrypoint-initdb.d/02-memory-role-password.sh:ro",
            test_compose,
        )
        defaults = re.findall(r"MEMORY_DB_PASSWORD: \$\{MEMORY_DB_PASSWORD:-([^}]*)\}", test_compose)
        self.assertEqual(len(defaults), 2, defaults)
        self.assertEqual(defaults[0], defaults[1])


if __name__ == "__main__":
    unittest.main()
