"""`U13 brain-gateway` 的啟動、掛載、DEMO 移除與單一行程守門測試（`BR67.11`、`BR61.1`；`NFR13.32`、`NFR13.33`；
帶入項 16、31、33）。

本檔是 `backend/tests/` 內**第一批**會觸發 startup 的測試（`with TestClient(main.app)`），故在測試內自備 startup 需要的
全部變數，並把與本單元無關的外部檢查（LLM 金鑰、嵌入、`init_db`）換成替身——CI 的 backend job 只設 `JWT_SECRET`
（`cicd-pipeline.md` 約束 C-b）。
"""

import tests.helpers  # noqa: F401  -- installs the psycopg stub before services import

import importlib.util
import os
import unittest
from pathlib import Path
from unittest import mock

import yaml
from starlette.routing import WebSocketRoute
from starlette.testclient import TestClient

import main
import services.membership_facade as membership_facade
from services import brain_gateway as G
from tests.brain_gateway_fakes import WS_PATH, protocols, recv_json
from tests.helpers import close_session, make_session, make_user

REPO = Path(__file__).resolve().parents[2]
_ENV = {
    "REDIS_URL": "redis://127.0.0.1:1/0",
    "REDIS_USER": "brain-test",
    "REDIS_PASSWORD": "not-a-real-password",
    "BRAIN_SESSION_HISTORY_MAX": "50",
    "BRAIN_ROUTER_CONFIDENCE_THRESHOLD": "0.7",
}


def _quiet_startup():
    """把與本單元無關的三個 startup 步驟換成替身；其餘（session、路由門檻、閘道建立）照真的跑。"""
    return (
        mock.patch.object(main, "configure_provider_env"),
        mock.patch.object(main, "configure_embedding_env"),
        mock.patch.object(main, "init_db"),
    )


class StartupOrderTest(unittest.TestCase):
    def test_gateway_is_built_after_routing_config_and_before_init_db_and_shut_down(self):
        """
        @purpose 閘道元件在 configure_intent_routing_env 之後、init_db 之前建立（router 建構會讀門檻設定）；shutdown 只關自己的元件。
        @given 以記錄器取代三個步驟
        @step 進入 with TestClient(main.app) | 呼叫順序為 configure_intent_routing_env → build_brain_gateway → init_db
        @step 離開 | 閘道的 shutdown 被呼叫 1 次
        @pass 順序與關閉皆正確
        @story US8.1
        """
        order = []
        captured = {}
        fake_gateway = mock.Mock()
        with mock.patch.object(main, "configure_provider_env"), mock.patch.object(main, "configure_embedding_env"), \
                mock.patch.object(main, "configure_session_env"), \
                mock.patch.object(main, "configure_intent_routing_env", side_effect=lambda: order.append("routing")), \
                mock.patch.object(main, "build_brain_gateway", side_effect=lambda app, **kw: captured.update(kw) or order.append("gateway") or fake_gateway), \
                mock.patch.object(main, "init_db", side_effect=lambda: order.append("init_db")):
            with TestClient(main.app):
                pass
        self.assertEqual(order, ["routing", "gateway", "init_db"])
        # ADR-0022 D-6：唯一組裝點傳入真實的 MembershipFacade（漏傳＝啟動失敗，G7 突變）。
        self.assertIs(captured["membership_facade_factory"], membership_facade.MembershipFacade)
        fake_gateway.shutdown.assert_called_once()
        del main.app.state.brain_gateway

    def test_build_without_membership_facade_factory_is_type_error(self):
        """
        @purpose membership_facade_factory 必填、無預設（ADR-0022 D-6）：漏傳必須在組裝當下 TypeError，
                 不得以恆可見（靜默繞過）或恆不可見（大腦失效）的預設值啟動。
        @given Redis client、redis-py 例外型別與 IntentRouter 的建構以 mock 隔離；三個 Redis 變數已設
        @step 不帶 membership_facade_factory 呼叫 build_brain_gateway(app) | 拋 TypeError
        @step 帶入 MembershipFacade 呼叫 | 回傳 BrainGateway，且其 membership_facade_factory 即為傳入者
        @pass 漏傳即失敗、正確組裝可建立
        @story US8.1
        """
        with mock.patch.dict(os.environ, _ENV, clear=False), \
                mock.patch.object(G, "build_redis_client", return_value=mock.Mock()), \
                mock.patch.object(G, "redis_py_error_types", return_value=()), \
                mock.patch.object(G, "IntentRouter", return_value=mock.Mock()):
            with self.assertRaises(TypeError):
                G.build_brain_gateway(main.app)
            gateway = G.build_brain_gateway(main.app, membership_facade_factory=membership_facade.MembershipFacade)
            try:
                self.assertIs(gateway.membership_facade_factory, membership_facade.MembershipFacade)
            finally:
                gateway.shutdown()


class StartupFailureTest(unittest.TestCase):
    def tearDown(self):
        if hasattr(main.app.state, "brain_gateway"):
            main.app.state.brain_gateway.shutdown()
            del main.app.state.brain_gateway

    def test_missing_redis_settings_or_default_user_fail_startup(self):
        """
        @purpose REDIS_URL／REDIS_USER／REDIS_PASSWORD 缺任一，或 REDIS_USER=default，後端必須拒絕啟動（不得靜默降級）。
        @given 四種壞設定
        @step 各自進入 with TestClient(main.app) | 皆拋例外（KeyError 或 ValueError）
        @pass 四案皆啟動失敗
        @story US8.1
        """
        cases = [{k: v for k, v in _ENV.items() if k != drop} for drop in ("REDIS_URL", "REDIS_USER", "REDIS_PASSWORD")]
        cases.append({**_ENV, "REDIS_USER": "default"})
        p1, p2, p3 = _quiet_startup()
        with p1, p2, p3:
            for env in cases:
                with self.subTest(env=sorted(env)), mock.patch.dict(os.environ, env, clear=False):
                    for key in ("REDIS_URL", "REDIS_USER", "REDIS_PASSWORD"):
                        if key not in env:
                            os.environ.pop(key, None)
                    with self.assertRaises((KeyError, ValueError)):
                        with TestClient(main.app):
                            pass

    @unittest.skipUnless(importlib.util.find_spec("redis"), "redis-py 未安裝於本機（CI 的 requirements.txt 會安裝）")
    def test_unreachable_redis_does_not_block_startup_but_handshake_closes_1011(self):
        """
        @purpose Redis 暫時不可達不阻止後端啟動（client 延遲連線），而在握手時以 1011 呈現。
        @given REDIS_URL 指向不可達位址；認證改走測試 DB
        @step 進入 with TestClient(main.app) | 正常啟動
        @step 有效帳號連線並送 hello | 1011
        @pass 啟動成功、握手 1011
        @story US8.1
        """
        db = make_session()
        try:
            from sqlalchemy.orm import sessionmaker
            from services.auth import create_access_token

            make_user(db, username="alice", role="Project_Architect")
            p1, p2, p3 = _quiet_startup()
            with p1, p2, p3, mock.patch.dict(os.environ, _ENV, clear=False):
                with TestClient(main.app) as client:
                    main.app.state.brain_gateway.session_factory = sessionmaker(bind=db._test_engine)
                    with client.websocket_connect(WS_PATH, subprotocols=protocols(create_access_token({"sub": "alice"}))) as ws:
                        ws.send_json({"v": 1, "type": "hello", "payload": {"v": 1}})
                        self.assertEqual(recv_json(ws, timeout=20).get("__close__"), 1011)
        finally:
            close_session(db)


class MountingTest(unittest.TestCase):
    def test_exactly_one_brain_websocket_route_and_demo_is_gone(self):
        """
        @purpose 同一路徑不得有兩個 WebSocket handler（DEMO 與正式閘道並存時先註冊者勝出且無聲）；DEMO 模組整支移除（[IG2]=A）。
        @given main.app 的路由表
        @step 找出路徑為 /api/brain/ws 的 WebSocket 路由 | 恰 1 條，端點屬 services.brain_gateway
        @step 查 services.brain_router 模組 | 不存在
        @step 不觸發 startup 直接連線 | 1011（閘道元件不存在）
        @pass 三項成立
        @story US8.1
        """
        routes = [r for r in main.app.routes if isinstance(r, WebSocketRoute) and r.path == WS_PATH]
        self.assertEqual(len(routes), 1)
        self.assertEqual(routes[0].endpoint.__module__, G.__name__)
        self.assertIsNone(importlib.util.find_spec("services.brain_router"))
        client = TestClient(main.app)
        with client.websocket_connect(WS_PATH, subprotocols=protocols("x")) as ws:
            self.assertEqual(recv_json(ws).get("__close__"), 1011)


class SingleProcessGuardTest(unittest.TestCase):
    """`NFR13.33`＋帶入項 16：多 worker 會讓扇出與推播**靜默**失效，以機械檢查擋住無聲改動。"""

    NAMES = ("WEB_CONCURRENCY", "UVICORN_WORKERS")

    def test_dockerfile_compose_and_templates_keep_a_single_worker(self):
        """
        @purpose 單一行程假設不得被無聲打破：Dockerfile 不加 --workers、不設 worker 數的環境變數；兩份 compose 的 backend 服務
                 不覆寫 command、沒有 env_file（否則 deploy/.env 裡的 WEB_CONCURRENCY 會無聲生效）、environment 不含那兩個名稱；
                 範本與 render-env.sh 不含那兩個名稱。
        @given repo 內的 Dockerfile、兩份 compose、兩份 .env.example、render-env.sh
        @step 逐一檢查 | 全部不成立即紅燈
        @pass 單一 worker 的設定面守住
        @story US8.1
        """
        dockerfile = (REPO / "backend" / "Dockerfile").read_text(encoding="utf-8")
        cmd = [line for line in dockerfile.splitlines() if line.startswith("CMD") and "uvicorn" in line]
        self.assertEqual(len(cmd), 1)
        self.assertNotIn("--workers", cmd[0])
        self.assertNotIn("--ws-max-size", cmd[0])  # NFR13.19：不動全域上限（協作 WS 收整張架構圖）
        for name in self.NAMES:
            self.assertNotIn(name, dockerfile)
        for compose in ("docker-compose.deploy.yml", "docker-compose.test.yml"):
            backend = yaml.safe_load((REPO / "deploy" / compose).read_text(encoding="utf-8"))["services"]["backend"]
            with self.subTest(compose=compose):
                self.assertNotIn("command", backend)
                self.assertNotIn("env_file", backend)
                environment = backend.get("environment") or {}
                keys = environment.keys() if isinstance(environment, dict) else [e.split("=", 1)[0] for e in environment]
                for name in self.NAMES:
                    self.assertNotIn(name, keys)
        for path in ("deploy/.env.example", "backend/.env.example", "deploy/render-env.sh"):
            text_of = (REPO / path).read_text(encoding="utf-8")
            for name in self.NAMES:
                self.assertNotIn(name, text_of, path)


if __name__ == "__main__":
    unittest.main()
