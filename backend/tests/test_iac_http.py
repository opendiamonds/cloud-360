"""
@purpose IaC HTTP：D1/D2/D3 授權、缺 diagram_id、HIGH 仍可下載
@api POST /api/iac/generate
@api POST /api/iac/advice
@api POST /api/iac/scan-advice
@api POST /api/iac/scan
@api POST /api/iac/secrets/rewrite
@api GET /api/iac/session
@api GET /api/iac/download
@api GET /api/iac/readiness
@api POST /api/iac/save
@api POST /api/iac/files
@story US6.1 BR1.10
"""

from __future__ import annotations

import json
import unittest
from types import SimpleNamespace

import tests.helpers  # noqa: F401  — mock psycopg2 before database/main
from database import get_db
from iac.iac_session import get_session, reset_session
from iac.iac_types import IacGateError, Resource
from main import app
from services.auth import get_current_user
from starlette.testclient import TestClient
from tests.helpers import close_session, make_diagram, make_session, make_user

_GENERATE = "/api/iac/generate"
_SCAN = "/api/iac/scan"
_REWRITE = "/api/iac/secrets/rewrite"
_SESSION = "/api/iac/session"
_DOWNLOAD = "/api/iac/download"
_READINESS = "/api/iac/readiness"
_SAVE = "/api/iac/save"
_FILES = "/api/iac/files"
_READY_XML = '<mxGraphModel><root><mxCell id="2" value="vpc" vertex="1"/></root></mxGraphModel>'
_DRAFT_FIELDS = {"draft_id", "diagram_id", "status", "module_tree", "created_at"}
_FILE_FIELDS = {"path", "content"}


class IacHttpTests(unittest.TestCase):
    def setUp(self):
        self.db = make_session()
        self.client = TestClient(app)
        self.session = reset_session()
        self.session.agent_invoke = lambda summary: "note"
        self.session.diagram_loader = lambda diagram_id, user, db: [
            Resource("web", "aws", "node")
        ]

        def _db():
            yield self.db

        app.dependency_overrides[get_db] = _db

    def tearDown(self):
        app.dependency_overrides.clear()
        reset_session()
        close_session(self.db)

    def _as(self, role: str, username: str):
        user = make_user(self.db, username=username, role=role)
        app.dependency_overrides[get_current_user] = lambda: user
        return user

    def test_generate_without_d1_edit_is_403(self):
        """
        @purpose 沒有 D1 edit 時 POST /generate 是 403
        @given Security_Reviewer（D1 只能 view）與合法 diagram_id
        @step POST /api/iac/generate
        @pass status 403
        @api POST /api/iac/generate
        @story US6.1
        """
        self._as("Security_Reviewer", "iac-sec")
        response = self.client.post(_GENERATE, json={"diagram_id": 1})
        self.assertEqual(response.status_code, 403)

    def test_generate_with_d1_edit_returns_draft_fields(self):
        """
        @purpose 有 D1 edit 且 diagram_id 合法時回 200 與草稿欄位集合
        @given Project_Architect 與 stub generator
        @step POST /api/iac/generate
        @pass status 200；body 只有 draft；draft 欄位集合與三個 tf 檔一致
        @api POST /api/iac/generate
        @story US6.1 US2.2
        """
        self._as("Project_Architect", "iac-arch")
        response = self.client.post(_GENERATE, json={"diagram_id": 1})
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(set(body), {"draft"})
        draft = body["draft"]
        self.assertEqual(set(draft), _DRAFT_FIELDS)
        self.assertEqual(draft["status"], "succeeded")
        self.assertEqual(draft["diagram_id"], 1)
        self.assertEqual(set(draft["module_tree"]), {"files"})
        paths = set()
        for entry in draft["module_tree"]["files"]:
            self.assertEqual(set(entry), _FILE_FIELDS)
            paths.add(entry["path"])
        self.assertTrue({"main.tf", "variables.tf", "outputs.tf"} <= paths)

    def test_generate_stream_emits_draft_then_advice(self):
        """
        @purpose 串流先送出本機草稿，再送對該草稿的 AI 說明
        @given Project_Architect；agent 回傳「先回答」，且看得到 main.tf 內容
        @step POST /api/iac/generate，Accept 為 text/event-stream
        @pass progress 早於 main.tf，main.tf 早於「先回答」，agent 只被叫一次
        @api POST /api/iac/generate
        @story US2.1
        """
        calls = []

        def invoke(summary):
            calls.append(summary)
            return "先回答"

        self.session.agent_invoke = invoke
        self._as("Project_Architect", "iac-arch-stream")
        response = self.client.post(
            _GENERATE,
            json={"diagram_id": 1},
            headers={"Accept": "text/event-stream"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("text/event-stream", response.headers["content-type"])
        body = response.text
        self.assertLess(body.find("正在產生 IaC 草稿"), body.find("main.tf"))
        self.assertLess(body.find("main.tf"), body.find("先回答"))
        self.assertEqual(len(calls), 1)
        files = calls[0].get("files") or []
        self.assertIn("main.tf", {item.get("path") for item in files})

    def test_advice_stream_follows_saved_draft(self):
        """
        @purpose JSON 先回草稿，建議改走獨立串流
        @given Project_Architect 已有一份成功草稿
        @step POST /api/iac/generate，再 POST /api/iac/advice
        @pass 草稿回應不含建議文字；建議串流含「先回答」
        @api POST /api/iac/generate
        @api POST /api/iac/advice
        @story US2.1
        """
        self._as("Project_Architect", "iac-arch-advice")
        created = self.client.post(_GENERATE, json={"diagram_id": 1})
        self.assertEqual(created.status_code, 200, created.text)
        self.assertNotIn("先回答", created.text)
        calls = []

        def invoke(summary):
            calls.append(summary)
            return "先回答"

        self.session.agent_invoke = invoke
        response = self.client.post(
            "/api/iac/advice",
            json={"diagram_id": 1},
            headers={"Accept": "text/event-stream"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("text/event-stream", response.headers["content-type"])
        self.assertIn("先回答", response.text)
        self.assertEqual(len(calls), 1)

    def test_scan_advice_uses_the_latest_report_and_is_reloaded(self):
        """
        @purpose 掃描建議讀最新成功報告，並在重啟後從資料庫讀回
        @given Platform_Engineer 已儲存草稿，Checkov 有一項未通過
        @step POST /api/iac/scan-advice，重置記憶體後 GET /api/iac/session
        @pass 串流含「先處理公開存取」；session 的 scan_advice 等於該句
        @api POST /api/iac/scan-advice
        @api GET /api/iac/session
        @story US3.1
        """
        user = self._as("Platform_Engineer", "iac-pe-scan-advice")
        diagram = make_diagram(self.db, owner=user, title="掃描建議")
        created = self.client.post(_GENERATE, json={"diagram_id": diagram.id})
        self.assertEqual(created.status_code, 200, created.text)
        saved = self.client.post("/api/iac/save", json={"diagram_id": diagram.id})
        self.assertEqual(saved.status_code, 200, saved.text)

        def _failed(files, timeout):
            payload = {
                "results": {
                    "failed_checks": [
                        {
                            "check_id": "CKV_AWS_18",
                            "check_name": "Ensure the S3 bucket has access logging",
                            "severity": "HIGH",
                            "file_path": "main.tf",
                            "resource": "aws_s3_bucket.web",
                        }
                    ]
                }
            }
            return SimpleNamespace(returncode=1, stdout=json.dumps(payload))

        report = get_session().scan(user.id, diagram.id, runner=_failed)
        self.assertEqual(report.status, "succeeded")
        self.assertTrue(report.checks)

        def invoke(summary):
            self.assertEqual(summary.get("story"), "scan")
            self.assertEqual(summary["checks"][0]["status"], "failed")
            return "先處理公開存取。"

        self.session.agent_invoke = invoke
        response = self.client.post("/api/iac/scan-advice", json={"diagram_id": diagram.id})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("先處理公開存取。", response.text)

        reset_session()
        loaded = self.client.get(_SESSION, params={"diagram_id": str(diagram.id)})
        self.assertEqual(loaded.status_code, 200, loaded.text)
        self.assertEqual(loaded.json()["scan_advice"], "先處理公開存取。")

    def test_scan_advice_without_a_report_is_422(self):
        """
        @purpose 還沒有成功掃描時不能產生掃描建議
        @given Platform_Engineer 已產生草稿，尚未掃描
        @step POST /api/iac/scan-advice
        @pass status 422，error.code 為 missing_scan_report
        @api POST /api/iac/scan-advice
        @story US3.1
        """
        self._as("Platform_Engineer", "iac-pe-no-scan")
        created = self.client.post(_GENERATE, json={"diagram_id": 8})
        self.assertEqual(created.status_code, 200, created.text)
        response = self.client.post("/api/iac/scan-advice", json={"diagram_id": 8})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "missing_scan_report")

    def test_scan_without_d2_edit_is_403(self):
        """
        @purpose 沒有 D2 edit 時 POST /scan 是 403
        @given Project_Architect（D2 只能 view）
        @step POST /api/iac/scan
        @pass status 403
        @api POST /api/iac/scan
        @story US3.1
        """
        self._as("Project_Architect", "iac-arch-scan")
        response = self.client.post(_SCAN, json={"diagram_id": 1})
        self.assertEqual(response.status_code, 403)

    def test_rewrite_without_d3_edit_is_403(self):
        """
        @purpose 沒有 D3 edit 時 POST /secrets/rewrite 是 403
        @given Project_Architect（D3 只能 view）
        @step POST /api/iac/secrets/rewrite
        @pass status 403
        @api POST /api/iac/secrets/rewrite
        @story US4.1
        """
        self._as("Project_Architect", "iac-arch-rewrite")
        response = self.client.post(_REWRITE, json={"diagram_id": 1})
        self.assertEqual(response.status_code, 403)

    def test_session_without_d1_view_is_403(self):
        """
        @purpose 沒有 D1 view 時 GET /session 是 403
        @given FinOps_Analyst
        @step GET /api/iac/session?diagram_id=1
        @pass status 403
        @api GET /api/iac/session
        @story US6.1
        """
        self._as("FinOps_Analyst", "iac-finops")
        response = self.client.get(_SESSION, params={"diagram_id": "1"})
        self.assertEqual(response.status_code, 403)

    def test_download_with_view_only_is_403(self):
        """
        @purpose 只有 D1 view、沒有 edit 時 GET /download 是 403
        @given Project_Editor
        @step GET /api/iac/download?diagram_id=1
        @pass status 403
        @api GET /api/iac/download
        @story US5.2
        """
        self._as("Project_Editor", "iac-editor")
        response = self.client.get(_DOWNLOAD, params={"diagram_id": "1"})
        self.assertEqual(response.status_code, 403)

    def test_download_zip_when_max_severity_is_high(self):
        """
        @purpose maxSeverity 為 HIGH 時下載仍是 zip
        @given D1 edit 已產生草稿，掃描報告 max_severity 為 HIGH
        @step GET /api/iac/download
        @pass status 200，content-type 為 application/zip，內容以 PK 開頭
        @api GET /api/iac/download
        @story BR1.10 US5.1
        """
        user = self._as("Project_Architect", "iac-arch-zip")
        created = self.client.post(_GENERATE, json={"diagram_id": 7})
        self.assertEqual(created.status_code, 200, created.text)

        def _high(files, timeout):
            payload = {
                "results": {
                    "failed_checks": [
                        {
                            "check_id": "CKV_AWS_1",
                            "check_name": "wide",
                            "severity": "HIGH",
                            "file_path": "main.tf",
                        }
                    ]
                }
            }
            return SimpleNamespace(returncode=1, stdout=json.dumps(payload))

        report = get_session().scan(user.id, 7, runner=_high)
        self.assertEqual(report.max_severity, "HIGH")
        response = self.client.get(_DOWNLOAD, params={"diagram_id": "7"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.headers["content-type"].startswith("application/zip"))
        self.assertIn('filename="iac-7.zip"', response.headers["content-disposition"])
        self.assertTrue(response.content.startswith(b"PK"))

    def test_generate_missing_diagram_id_is_422(self):
        """
        @purpose 缺 diagram_id 是 422 missing_diagram_id，不是 404
        @given 有 D1 edit 的 Project_Architect 與空 body
        @step POST /api/iac/generate
        @pass status 422 且 error.code 為 missing_diagram_id
        @api POST /api/iac/generate
        @story US6.1
        """
        self._as("Project_Architect", "iac-arch-missing")
        response = self.client.post(_GENERATE, json={})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "missing_diagram_id")
        self.assertNotEqual(response.status_code, 404)

    def test_generate_busy_is_429(self):
        """
        @purpose session 回 generate_busy 時 HTTP 是 429，不是 200 或 404
        @given D1 edit，generate_http 丟出 generate_busy
        @step POST /api/iac/generate
        @pass status 429 且 error.code 為 generate_busy
        @api POST /api/iac/generate
        @story US6.1
        """
        self._as("Project_Architect", "iac-busy")

        def _busy(user, diagram_id, db, request_id=""):
            raise IacGateError("generate_busy", "Too many in-flight generate requests.")

        self.session.generate_http = _busy
        response = self.client.post(_GENERATE, json={"diagram_id": 1})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()["error"]["code"], "generate_busy")

    def test_generate_timeout_is_504(self):
        """
        @purpose generate 逾時是 504，且不會改成 200
        @given D1 edit，session.generate_http 回 generate_timeout
        @step POST /api/iac/generate
        @pass status 504 且 error.code 為 generate_timeout
        @api POST /api/iac/generate
        @story US2.3
        """
        self._as("Project_Architect", "iac-timeout")

        def _timeout(user, diagram_id, db, request_id=""):
            raise IacGateError("generate_timeout", "Generate timed out. Retry the request.")

        self.session.generate_http = _timeout
        response = self.client.post(_GENERATE, json={"diagram_id": 1})
        self.assertEqual(response.status_code, 504)
        self.assertEqual(response.json()["error"]["code"], "generate_timeout")

    def test_generate_rejects_diagram_with_no_nodes(self):
        """
        @purpose 沒有節點的架構圖在產生前被拒絕，不會進入模型
        @given D1 edit，diagram loader 回傳空資源
        @step POST /api/iac/generate
        @pass status 422 且 error.code 為 diagram_empty
        @api POST /api/iac/generate
        @story US2.1
        """
        self._as("Project_Architect", "iac-empty")
        self.session.diagram_loader = lambda diagram_id, user, db: []
        response = self.client.post(_GENERATE, json={"diagram_id": 1})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "diagram_empty")

    def test_readiness_classifies_visible_diagrams(self):
        """
        @purpose 產生前可以分辨可產生、沒有節點、無法解析的架構圖
        @given 三張自己的架構圖，分別有節點、空白、壞掉的 XML
        @step GET /api/iac/readiness
        @pass status 200；三張圖的 status 分別是 ready、empty、unreadable
        @api GET /api/iac/readiness
        @story US2.1
        """
        user = self._as("Project_Architect", "iac-ready")
        make_diagram(self.db, owner=user, title="有節點", xml_data=_READY_XML)
        make_diagram(self.db, owner=user, title="空白", xml_data="<mxGraphModel/>")
        make_diagram(self.db, owner=user, title="壞掉", xml_data="not-xml")
        response = self.client.get(_READINESS)
        self.assertEqual(response.status_code, 200, response.text)
        by_title = {row["title"]: row["status"] for row in response.json()["diagrams"]}
        self.assertEqual(by_title["有節點"], "ready")
        self.assertEqual(by_title["空白"], "empty")
        self.assertEqual(by_title["壞掉"], "unreadable")

    def test_save_persists_succeeded_draft_for_session(self):
        """
        @purpose 產生完成後可把草稿和 AI 建議存進資料庫，清掉記憶體後 session 仍讀得到 main.tf 與建議
        @given Project_Architect 已產生 diagram 1 的草稿
        @step POST /api/iac/save，body 含 advice，接著重置記憶體並 GET /api/iac/session
        @pass save 為 200；session 的 draft 含 main.tf，advice 等於存入的句子
        @api POST /api/iac/save
        @api GET /api/iac/session
        @story US6.1
        """
        user = self._as("Project_Architect", "iac-save")
        diagram = make_diagram(self.db, owner=user, title="可儲存")
        generated = self.client.post(_GENERATE, json={"diagram_id": diagram.id})
        self.assertEqual(generated.status_code, 200, generated.text)
        saved = self.client.post(
            _SAVE,
            json={"diagram_id": diagram.id, "advice": "使用前請確認資源類型。"},
        )
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertEqual(saved.json()["diagram_id"], diagram.id)
        reset_session()
        session = self.client.get(_SESSION, params={"diagram_id": str(diagram.id)})
        self.assertEqual(session.status_code, 200, session.text)
        body = session.json()
        files = body["draft"]["module_tree"]["files"]
        self.assertIn("main.tf", {item["path"] for item in files})
        self.assertEqual(body["advice"], "使用前請確認資源類型。")

    def test_save_persists_the_scan_with_the_draft(self):
        """
        @purpose 儲存會把這份草稿的掃描結果一起寫入，換草稿後不再讀回舊掃描
        @given Platform_Engineer 已產生草稿且 Checkov 有一項未通過
        @step POST /api/iac/save，重置記憶體後 GET /api/iac/session；再改檔並儲存
        @pass 第一次 session 的 latest_scan 含 CKV_AWS_18；第二次 latest_scan 為 null
        @api POST /api/iac/save
        @api GET /api/iac/session
        @story US3.1
        """
        user = self._as("Platform_Engineer", "iac-save-scan")
        diagram = make_diagram(self.db, owner=user, title="連掃描一起存")
        created = self.client.post(_GENERATE, json={"diagram_id": diagram.id})
        self.assertEqual(created.status_code, 200, created.text)

        def _failed(files, timeout):
            payload = {
                "results": {
                    "failed_checks": [
                        {
                            "check_id": "CKV_AWS_18",
                            "check_name": "Ensure the S3 bucket has access logging",
                            "severity": "HIGH",
                            "file_path": "main.tf",
                            "resource": "aws_s3_bucket.web",
                        }
                    ]
                }
            }
            return SimpleNamespace(returncode=1, stdout=json.dumps(payload))

        report = get_session().scan(user.id, diagram.id, runner=_failed)
        self.assertEqual(report.status, "succeeded")
        self.session.agent_invoke = lambda summary: "先處理公開存取。"
        advice = self.client.post("/api/iac/scan-advice", json={"diagram_id": diagram.id})
        self.assertEqual(advice.status_code, 200, advice.text)
        saved = self.client.post(_SAVE, json={"diagram_id": diagram.id, "advice": "使用前請確認資源類型。"})
        self.assertEqual(saved.status_code, 200, saved.text)

        reset_session()
        loaded = self.client.get(_SESSION, params={"diagram_id": str(diagram.id)})
        self.assertEqual(loaded.status_code, 200, loaded.text)
        body = loaded.json()
        self.assertEqual(body["latest_scan"]["status"], "succeeded")
        self.assertEqual(body["latest_scan"]["max_severity"], "HIGH")
        self.assertEqual(body["latest_scan"]["checks"][0]["id"], "CKV_AWS_18")
        self.assertEqual(body["scan_advice"], "先處理公開存取。")
        self.assertEqual(body["advice"], "使用前請確認資源類型。")

        files = body["draft"]["module_tree"]["files"]
        edited = [
            {"path": item["path"], "content": "# edited after scan\n" if item["path"] == "main.tf" else item["content"]}
            for item in files
        ]
        replaced = self.client.post(_FILES, json={"diagram_id": diagram.id, "files": edited})
        self.assertEqual(replaced.status_code, 200, replaced.text)
        saved_again = self.client.post(_SAVE, json={"diagram_id": diagram.id})
        self.assertEqual(saved_again.status_code, 200, saved_again.text)
        reset_session()
        again = self.client.get(_SESSION, params={"diagram_id": str(diagram.id)})
        self.assertEqual(again.status_code, 200, again.text)
        self.assertIsNone(again.json()["latest_scan"])

    def test_replace_files_updates_the_draft_and_drops_the_scan(self):
        """
        @purpose 直接改三個 .tf 後，session 讀到新內容，舊掃描不再沿用
        @given Project_Architect 已產生草稿
        @step POST /api/iac/files，main.tf 換成一行註解，再 GET /api/iac/session
        @pass files 為 200；session 的 main.tf 含該註解，latest_scan 為 null
        @api POST /api/iac/files
        @api GET /api/iac/session
        @story US2.2
        """
        user = self._as("Project_Architect", "iac-edit")
        diagram = make_diagram(self.db, owner=user, title="可編輯")
        generated = self.client.post(_GENERATE, json={"diagram_id": diagram.id})
        self.assertEqual(generated.status_code, 200, generated.text)
        files = generated.json()["draft"]["module_tree"]["files"]
        edited = [
            {"path": item["path"], "content": "# edited by hand\n" if item["path"] == "main.tf" else item["content"]}
            for item in files
        ]
        replaced = self.client.post(_FILES, json={"diagram_id": diagram.id, "files": edited})
        self.assertEqual(replaced.status_code, 200, replaced.text)
        session = self.client.get(_SESSION, params={"diagram_id": str(diagram.id)})
        self.assertEqual(session.status_code, 200, session.text)
        body = session.json()
        main = next(item["content"] for item in body["draft"]["module_tree"]["files"] if item["path"] == "main.tf")
        self.assertIn("# edited by hand", main)
        self.assertIsNone(body["latest_scan"])

    def test_replace_files_rejects_a_partial_set(self):
        """
        @purpose 少檔或改檔名不能取代草稿
        @given Project_Architect 已產生草稿
        @step POST /api/iac/files，只送 main.tf
        @pass status 422 且 error.code 為 invalid_files
        @api POST /api/iac/files
        @story US2.2
        """
        user = self._as("Project_Architect", "iac-edit-bad")
        diagram = make_diagram(self.db, owner=user, title="拒絕缺檔")
        generated = self.client.post(_GENERATE, json={"diagram_id": diagram.id})
        self.assertEqual(generated.status_code, 200, generated.text)
        rejected = self.client.post(
            _FILES,
            json={"diagram_id": diagram.id, "files": [{"path": "main.tf", "content": "# only one\n"}]},
        )
        self.assertEqual(rejected.status_code, 422, rejected.text)
        self.assertEqual(rejected.json()["error"]["code"], "invalid_files")

    def test_scan_uses_saved_draft_after_memory_reset(self):
        """
        @purpose 記憶體清空後，掃描會用資料庫裡該架構圖已存的 IaC
        @given Platform_Engineer 已產生並儲存 diagram 的草稿，接著重置記憶體
        @step POST /api/iac/scan，body 只有 diagram_id
        @pass status 200，report.status 為 succeeded
        @api POST /api/iac/scan
        @story US3.1
        """
        user = self._as("Platform_Engineer", "iac-scan-saved")
        diagram = make_diagram(self.db, owner=user, title="可掃描")
        generated = self.client.post(_GENERATE, json={"diagram_id": diagram.id})
        self.assertEqual(generated.status_code, 200, generated.text)
        saved = self.client.post(_SAVE, json={"diagram_id": diagram.id})
        self.assertEqual(saved.status_code, 200, saved.text)
        fresh = reset_session()
        fresh.agent_invoke = lambda summary: "note"
        fresh.checkov_runner = lambda files, timeout: SimpleNamespace(returncode=0, stdout="")
        response = self.client.post(_SCAN, json={"diagram_id": diagram.id})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["report"]["status"], "succeeded")

    def test_scan_uploaded_tf_does_not_require_a_diagram(self):
        """
        @purpose 上傳 .tf 文字可以掃描，不必先有架構圖草稿
        @given Platform_Engineer，Checkov runner 回傳空結果
        @step POST /api/iac/scan，body 只有 files
        @pass 合法 main.tf 為 200；路徑跳出目錄的檔案為 422 且 code 為 scan_failed
        @api POST /api/iac/scan
        @story US3.1
        """
        self._as("Platform_Engineer", "iac-scan-upload")
        self.session.checkov_runner = lambda files, timeout: SimpleNamespace(returncode=0, stdout="")
        accepted = self.client.post(
            _SCAN,
            json={"files": [{"path": "main.tf", "content": 'resource "null_resource" "x" {}'}]},
        )
        self.assertEqual(accepted.status_code, 200, accepted.text)
        self.assertEqual(accepted.json()["report"]["status"], "succeeded")
        rejected = self.client.post(
            _SCAN,
            json={"files": [{"path": "../main.tf", "content": "x"}]},
        )
        self.assertEqual(rejected.status_code, 422, rejected.text)
        self.assertEqual(rejected.json()["error"]["code"], "scan_failed")

    def test_scan_failure_names_the_checkov_reason(self):
        """
        @purpose 掃描失敗時回應帶出可顯示的原因代碼
        @given Platform_Engineer 已產生草稿，Checkov 指令不存在
        @step POST /api/iac/scan
        @pass status 422，error.code 為 scan_failed，error.reason 為 checkov_missing
        @api POST /api/iac/scan
        @story US3.1
        """
        user = self._as("Platform_Engineer", "iac-scan-missing")
        diagram = make_diagram(self.db, owner=user, title="缺掃描器")
        generated = self.client.post(_GENERATE, json={"diagram_id": diagram.id})
        self.assertEqual(generated.status_code, 200, generated.text)

        def _missing(files, timeout):
            raise FileNotFoundError("checkov")

        self.session.checkov_runner = _missing
        response = self.client.post(_SCAN, json={"diagram_id": diagram.id})
        self.assertEqual(response.status_code, 422, response.text)
        error = response.json()["error"]
        self.assertEqual(error["code"], "scan_failed")
        self.assertEqual(error["reason"], "checkov_missing")


if __name__ == "__main__":
    unittest.main()
