"""`U23 project-pages-ui` 的靜態鎖（`BR87.7` ＋ `security-design.md` §二之四 ＋ nfr-design `R-02`）。

五條 `ast` 斷言，其中第 2、3 條擴及四個讀取方法（`U14` ADR-0022 D-8），掃 `backend/` 下全部
`.py`（排除測試目錄 `tests*/` 與 `__pycache__/`）：

1. `BR87.7`：`list_projects_by_ids`／`list_systems_unscoped` 的呼叫只出現在
   `services/membership_facade.py` 的 `MembershipFacade` 類別內。
2. `HierarchyFacade` 的三個寫入方法 `create_system`／`delete_project`／`delete_system`
   與四個讀取方法 `describe_work_target`／`list_projects`／`list_systems`／
   `resolve_work_target`：`project_visible` 為 keyword-only 且**無預設值**（fail-closed）。
3. 對這七個屬性名的每一個呼叫，若接收者不是 `hierarchy_service` 模組名，必須帶
   `project_visible=` 且其值是對屬性 `project_visibility` 的呼叫——不得是
   `Lambda`／`Name`／`Constant`（擋住 router 或大腦傳 `lambda _: True`）。唯一例外
   `S3_EXCEPTIONS`：`services/session_store.py` 的 `resolve_work_target`——接收者是建構時
   注入的轉接器（`brain_gateway._HierarchyResolver`），判定由轉接器注入（ADR-0022 D-8）；
   以 `(檔案, 方法名)` 精確比對，且必須恰一筆、該呼叫點確實存在（`S3b`）。讀取方法的
   呼叫點下限 5（`_names_for` 1、`_build_catalog` 3、`_HierarchyResolver` 1）。
4. `project_visibility` 的定義只出現在 `MembershipFacade` 類別內。
5. `hierarchy_service` 的三個寫入函式，不論 `Attribute`（`hierarchy_service.delete_project(...)`）
   或 `Name`（`from services.hierarchy_service import delete_project` 後裸呼叫）形式，
   只准出現在 `services/hierarchy_facade.py`；且任何檔案都不得以 `from … import`
   匯入這三個名稱。

這些都是「繞過一旦發生是**靜默的**」那一類：多一個呼叫端直呼 unscoped 方法、或寫入
路徑被傳入恆真的判定，不會有任何錯誤，只會沒有檢查。測試是唯一的機械強制。
受測對象沒有 HTTP 端點，故各測試的規格註解不寫 `@api`。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path

import ast
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]

UNSCOPED_METHODS = {"list_projects_by_ids", "list_systems_unscoped"}
WRITE_METHODS = {"create_system", "delete_project", "delete_system"}
# `U14` ADR-0022 D-8：大腦的三條讀取／設定路徑經這四個方法，同受可見性守門。
GUARDED_READS = {"describe_work_target", "list_projects", "list_systems", "resolve_work_target"}
GUARDED_METHODS = WRITE_METHODS | GUARDED_READS
# 精確例外：(檔案, 方法名)。接收者是注入的轉接器，由轉接器自己注入判定。
S3_EXCEPTIONS = {("services/session_store.py", "resolve_work_target")}
FACADE_FILE = "services/hierarchy_facade.py"
MEMBERSHIP_FACADE_FILE = "services/membership_facade.py"


def application_files():
    """`backend/` 下的應用程式碼（排除測試目錄與快取）。"""
    out = []
    for path in sorted(BACKEND_DIR.rglob("*.py")):
        rel = path.relative_to(BACKEND_DIR)
        top = rel.parts[0]
        if top.startswith("tests") or "__pycache__" in rel.parts:
            continue
        if any(part.startswith(".") for part in rel.parts):
            continue
        out.append((rel.as_posix(), ast.parse(path.read_text(encoding="utf-8"))))
    return out


def walk_with_class(tree: ast.AST):
    """走訪全部節點，附帶「最近一層的類別名」（不在類別內為 `None`）。"""
    stack = [(tree, None)]
    while stack:
        node, cls = stack.pop()
        yield node, cls
        inner = node.name if isinstance(node, ast.ClassDef) else cls
        for child in ast.iter_child_nodes(node):
            stack.append((child, inner))


def receiver_is_module(call: ast.Call, module: str) -> bool:
    func = call.func
    return (
        isinstance(func, ast.Attribute)
        and isinstance(func.value, ast.Name)
        and func.value.id == module
    )


class ProjectVisibilityStaticTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.files = application_files()

    def test_S1_unscoped_methods_called_only_by_membership_facade(self):
        """第 1 條（`BR87.7`）。

        @purpose 兩個不做擁有者檢查的列舉來源，只能由 `MembershipFacade` 以成員可見性呼叫。
        @story AC12.1.3
        """
        sites = []
        for rel, tree in self.files:
            for node, cls in walk_with_class(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr in UNSCOPED_METHODS
                ):
                    sites.append(
                        (
                            rel,
                            cls,
                            node.func.attr,
                            node.lineno,
                            receiver_is_module(node, "hierarchy_service"),
                        )
                    )
        self.assertTrue(sites, "找不到任何呼叫——掃描範圍可能錯了")

        def allowed(site) -> bool:
            rel, cls, _attr, _line, service = site
            if service:
                # service 層的同名函式（`hierarchy_service.list_projects_by_ids`）只准由
                # facade 的同名方法呼叫——否則等於直呼 service 層、繞過 `K2`。
                return rel == FACADE_FILE and cls == "HierarchyFacade"
            return rel == MEMBERSHIP_FACADE_FILE and cls == "MembershipFacade"

        offenders = [s for s in sites if not allowed(s)]
        self.assertEqual(offenders, [], "unscoped 方法只准由 MembershipFacade 呼叫")

    def test_S2_project_visible_is_required_keyword_only(self):
        """第 2 條：三個寫入方法與四個讀取方法的 `project_visible` 為 keyword-only 且無預設值。

        @purpose 漏傳判定必須在呼叫當下 `TypeError`（fail-closed），不得靜默略過守門。
        @story AC12.6.2
        """
        tree = dict(self.files)[FACADE_FILE]
        found = set()
        for node, cls in walk_with_class(tree):
            if (
                isinstance(node, ast.FunctionDef)
                and cls == "HierarchyFacade"
                and node.name in GUARDED_METHODS
            ):
                names = [a.arg for a in node.args.kwonlyargs]
                self.assertIn("project_visible", names, node.name)
                default = node.args.kw_defaults[names.index("project_visible")]
                self.assertIsNone(default, f"{node.name} 的 project_visible 不得有預設值")
                positional = [a.arg for a in node.args.args + node.args.posonlyargs]
                self.assertNotIn("project_visible", positional, node.name)
                found.add(node.name)
        self.assertEqual(found, GUARDED_METHODS)

    def test_S3_every_write_call_injects_project_visibility(self):
        """第 3 條：非 service 層的寫入與讀取呼叫都帶 `project_visible=<…>.project_visibility(...)`。

        @purpose 擋住呼叫端傳入恆真的判定（`lambda _: True`）而讓守門形同虛設（含大腦的
                 名稱推送、對象目錄與直接設定作業對象三條讀取路徑，ADR-0022 D-8）。
        @story AC12.6.2
        """
        checked = 0
        read_sites = 0
        for rel, tree in self.files:
            for node, _cls in walk_with_class(tree):
                if not (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr in GUARDED_METHODS
                ):
                    continue
                if receiver_is_module(node, "hierarchy_service"):
                    continue
                if (rel, node.func.attr) in S3_EXCEPTIONS:
                    continue
                checked += 1
                if node.func.attr in GUARDED_READS:
                    read_sites += 1
                kw = {k.arg: k.value for k in node.keywords if k.arg}
                where = f"{rel}:{node.lineno}"
                self.assertIn("project_visible", kw, f"{where} 缺 project_visible")
                value = kw["project_visible"]
                self.assertIsInstance(value, ast.Call, f"{where} 的 project_visible 不是呼叫")
                self.assertIsInstance(value.func, ast.Attribute, where)
                self.assertEqual(value.func.attr, "project_visibility", where)
        self.assertGreaterEqual(checked, 3, "router 的三個寫入呼叫應被掃到")
        self.assertGreaterEqual(read_sites, 5, "大腦的五個讀取呼叫點應被掃到")

    def test_S3b_exception_list_is_exact(self):
        """第 3 條的例外清單恰一筆，且該呼叫點確實存在（ADR-0022 D-8）。

        @purpose 例外清單只能精確豁免「接收者是注入轉接器」的那一個呼叫點；多一筆或指向不存在的
                 呼叫，都會讓未來的繞過以「已列例外」的樣貌通過第 3 條。
        @story AC12.6.2
        """
        self.assertEqual(S3_EXCEPTIONS, {("services/session_store.py", "resolve_work_target")})
        hits = []
        for rel, tree in self.files:
            for node, _cls in walk_with_class(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and (rel, node.func.attr) in S3_EXCEPTIONS
                ):
                    hits.append((rel, node.func.attr, node.lineno))
        self.assertEqual(len(hits), 1, f"例外呼叫點應恰一處：{hits}")

    def test_S4_project_visibility_defined_only_in_membership_facade(self):
        """第 4 條：`project_visibility` 只定義在 `MembershipFacade` 類別內。

        @purpose 守門判定只有一個合法來源，且它只由唯一的可見性定義組出。
        @story AC12.6.2
        """
        defs = []
        for rel, tree in self.files:
            for node, cls in walk_with_class(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
                    node.name == "project_visibility"
                ):
                    defs.append((rel, cls))
        self.assertEqual(defs, [(MEMBERSHIP_FACADE_FILE, "MembershipFacade")])

    def test_S5_service_write_functions_called_only_from_hierarchy_facade(self):
        """第 5 條（nfr-design `R-02`）：service 層三個寫入函式只由 `hierarchy_facade.py` 呼叫。

        @purpose 直呼 service 層會完整繞過 `K2`、可見性守門與擁有者檢查，且繞過是靜默的。
        @story AC12.6.2
        """
        attribute_sites = []
        name_sites = []
        imports = []
        for rel, tree in self.files:
            for node, _cls in walk_with_class(tree):
                if isinstance(node, ast.ImportFrom) and node.module in (
                    "services.hierarchy_service",
                    "hierarchy_service",
                ):
                    bad = [a.name for a in node.names if a.name in WRITE_METHODS or a.name == "*"]
                    if bad:
                        imports.append((rel, node.lineno, bad))
                if not isinstance(node, ast.Call):
                    continue
                if (
                    isinstance(node.func, ast.Attribute)
                    and node.func.attr in WRITE_METHODS
                    and receiver_is_module(node, "hierarchy_service")
                ):
                    attribute_sites.append(rel)
                if (
                    isinstance(node.func, ast.Name)
                    and node.func.id in WRITE_METHODS
                    and rel != "services/hierarchy_service.py"
                ):
                    name_sites.append((rel, node.lineno, node.func.id))
        self.assertTrue(attribute_sites, "找不到 hierarchy_facade 對 service 層的呼叫——掃描範圍可能錯了")
        self.assertEqual(set(attribute_sites), {FACADE_FILE})
        self.assertEqual(name_sites, [], "service 層寫入函式不得以裸名稱呼叫")
        self.assertEqual(imports, [], "不得以 from … import 匯入 service 層寫入函式")


if __name__ == "__main__":
    unittest.main()
