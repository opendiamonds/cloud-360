"""Unit tests for collab ACL, welcome text, and chat message persistence helpers (A4/A5)."""

from __future__ import annotations

import json
import unittest

from fastapi import HTTPException
from hypothesis import given, settings, strategies as st

from tests.helpers import close_session, make_diagram, make_session, make_user

from services.collab_router import (
    DEFAULT_WELCOME,
    MAX_CHAT_CONTENT_CHARS,
    MAX_DIAGRAM_XML_CHARS,
    MAX_CHAT_MESSAGES,
    REVIEW_ONLY_WELCOME,
    VIEW_ONLY_WELCOME,
    _authorize_ws_user,
    _get_accessible_diagram,
    _get_or_create_chat,
    _parse_messages,
    _serialize_messages,
    _user_can_access_diagram,
    _validate_chat_messages,
    _validate_diagram_payload,
    _visible_diagrams,
    _welcome_for_user,
    _workspace_id_to_diagram_id,
)
from services.auth import create_access_token


class TestAccessHelpers(unittest.TestCase):
    def setUp(self):
        self.db = make_session()
        self.owner = make_user(self.db, username="alex", role="Project_Architect")
        self.viewer = make_user(self.db, username="ian", role="FinOps_Analyst")
        self.editor = make_user(self.db, username="hannah", role="Developer")
        self.diagram = make_diagram(self.db, owner=self.owner, title="arch")

    def tearDown(self):
        close_session(self.db)

    def test_owner_can_access(self):
        self.assertTrue(_user_can_access_diagram(self.owner, self.diagram))

    def test_stranger_cannot_access_until_shared(self):
        self.assertFalse(_user_can_access_diagram(self.viewer, self.diagram))
        self.diagram.shared_users.append(self.viewer)
        self.db.commit()
        self.db.refresh(self.viewer)
        self.assertTrue(_user_can_access_diagram(self.viewer, self.diagram))

    def test_welcome_by_role(self):
        self.assertEqual(_welcome_for_user(self.db, self.owner), DEFAULT_WELCOME)
        # FinOps_Analyst: typically view-only on arch — welcome is view or review
        welcome = _welcome_for_user(self.db, self.viewer)
        self.assertIn(welcome, (VIEW_ONLY_WELCOME, REVIEW_ONLY_WELCOME, DEFAULT_WELCOME))

    def test_editor_sees_owned_and_shared(self):
        shared = make_diagram(self.db, owner=self.owner, title="shared")
        shared.shared_users.append(self.editor)
        self.db.commit()
        self.db.refresh(self.editor)

        owned = make_diagram(self.db, owner=self.editor, title="mine")
        visible = _visible_diagrams(self.editor, self.db)
        ids = {d.id for d in visible}
        self.assertIn(owned.id, ids)
        self.assertIn(shared.id, ids)

    def test_view_only_cannot_open_own_diagram(self):
        """僅檢視／審核：只能開被分享的圖，不可開自己擁有的（語意見 collab_router）。"""
        from services.rbac import user_can_arch

        # Pick a role that can view but not edit arch, if any exists in seed
        from services.rbac_seed_data import DEFAULT_ROLE_PERMISSIONS

        view_only_role = None
        for role, story_id, can_view, can_edit, can_review in DEFAULT_ROLE_PERMISSIONS:
            if story_id != "A1":
                continue
            if (can_view or can_review) and not can_edit:
                view_only_role = role
                break

        if view_only_role is None:
            self.skipTest("seed 無僅檢視 A1 角色，略過")

        user = make_user(self.db, username="viewer_only", role=view_only_role)
        own = make_diagram(self.db, owner=user, title="own")
        self.assertTrue(user_can_arch(self.db, user.role, "view"))
        self.assertFalse(user_can_arch(self.db, user.role, "edit"))

        with self.assertRaises(HTTPException) as ctx:
            _get_accessible_diagram(own.id, user, self.db)
        self.assertEqual(ctx.exception.status_code, 403)

        # After share from architect, can open
        self.diagram.shared_users.append(user)
        self.db.commit()
        self.db.refresh(user)
        got = _get_accessible_diagram(self.diagram.id, user, self.db)
        self.assertEqual(got.id, self.diagram.id)

    def test_missing_diagram_404(self):
        with self.assertRaises(HTTPException) as ctx:
            _get_accessible_diagram(99999, self.owner, self.db)
        self.assertEqual(ctx.exception.status_code, 404)


class TestChatMessages(unittest.TestCase):
    def test_parse_empty_and_invalid(self):
        self.assertEqual(_parse_messages(""), [])
        self.assertEqual(_parse_messages("[]"), [])
        self.assertEqual(_parse_messages("not-json"), [])
        self.assertEqual(_parse_messages('{"a":1}'), [])  # not a list

    def test_parse_valid_list(self):
        raw = json.dumps([{"role": "user", "content": "hi"}])
        self.assertEqual(_parse_messages(raw), [{"role": "user", "content": "hi"}])

    def test_serialize_filters_and_truncates(self):
        messages = [{"role": "system", "content": "skip"}]
        messages += [{"role": "user", "content": "a"}] * (MAX_CHAT_MESSAGES + 5)
        out = json.loads(_serialize_messages(messages))
        self.assertEqual(len(out), MAX_CHAT_MESSAGES)
        self.assertTrue(all(m["role"] in ("user", "assistant") for m in out))
        # system 在開頭且超出視窗時被切掉；角色過濾也會丟棄 system
        self.assertNotIn("skip", [m["content"] for m in out])

    @given(
        st.lists(
            st.fixed_dictionaries(
                {
                    "role": st.sampled_from(["user", "assistant"]),
                    "content": st.text(max_size=40),
                }
            ),
            max_size=30,
        )
    )
    @settings(max_examples=30, deadline=None)
    def test_serialize_parse_round_trip(self, messages):
        raw = _serialize_messages(messages)
        back = _parse_messages(raw)
        self.assertEqual(back, [{"role": m["role"], "content": str(m["content"])} for m in messages])


class TestPayloadValidation(unittest.TestCase):
    def test_diagram_payload_accepts_drawio_xml(self):
        _validate_diagram_payload("<mxGraphModel><root /></mxGraphModel>")

    def test_diagram_payload_rejects_non_diagram_xml(self):
        with self.assertRaises(HTTPException) as ctx:
            _validate_diagram_payload("<not-a-diagram />")
        self.assertEqual(ctx.exception.status_code, 400)

    def test_diagram_payload_rejects_large_xml(self):
        xml = "<mxGraphModel>" + ("x" * MAX_DIAGRAM_XML_CHARS) + "</mxGraphModel>"
        with self.assertRaises(HTTPException) as ctx:
            _validate_diagram_payload(xml)
        self.assertEqual(ctx.exception.status_code, 400)

    def test_chat_validation_rejects_large_message(self):
        with self.assertRaises(HTTPException) as ctx:
            _validate_chat_messages(
                [{"role": "user", "content": "x" * (MAX_CHAT_CONTENT_CHARS + 1)}]
            )
        self.assertEqual(ctx.exception.status_code, 400)

    def test_workspace_id_must_be_diagram_id(self):
        self.assertEqual(_workspace_id_to_diagram_id("123"), 123)
        with self.assertRaises(HTTPException):
            _workspace_id_to_diagram_id("abc")


class TestWebSocketAuthorization(unittest.TestCase):
    def setUp(self):
        self.db = make_session()
        self.owner = make_user(self.db, username="alex", role="Project_Architect")
        self.viewer = make_user(self.db, username="viewer", role="FinOps_Analyst")
        self.diagram = make_diagram(self.db, owner=self.owner)

    def tearDown(self):
        close_session(self.db)

    def test_ws_authorizes_editor_for_owned_diagram(self):
        token = create_access_token({"sub": self.owner.username})
        user = _authorize_ws_user(str(self.diagram.id), token, self.db)
        self.assertEqual(user.id, self.owner.id)

    def test_ws_rejects_missing_token(self):
        with self.assertRaises(HTTPException) as ctx:
            _authorize_ws_user(str(self.diagram.id), None, self.db)
        self.assertEqual(ctx.exception.status_code, 401)

    def test_ws_rejects_user_without_edit_permission(self):
        self.diagram.shared_users.append(self.viewer)
        self.db.commit()
        token = create_access_token({"sub": self.viewer.username})
        with self.assertRaises(HTTPException) as ctx:
            _authorize_ws_user(str(self.diagram.id), token, self.db)
        self.assertEqual(ctx.exception.status_code, 403)


class TestGetOrCreateChat(unittest.TestCase):
    def setUp(self):
        self.db = make_session()
        self.user = make_user(self.db, username="alex", role="Project_Architect")
        self.diagram = make_diagram(self.db, owner=self.user)

    def tearDown(self):
        close_session(self.db)

    def test_create_then_reuse(self):
        chat1 = _get_or_create_chat(self.user.id, self.diagram.id, self.db)
        self.assertEqual(chat1.messages_json, "[]")
        chat1.messages_json = json.dumps([{"role": "user", "content": "hello"}])
        self.db.commit()

        chat2 = _get_or_create_chat(self.user.id, self.diagram.id, self.db)
        self.assertEqual(chat1.user_id, chat2.user_id)
        self.assertEqual(chat1.diagram_id, chat2.diagram_id)
        self.assertIn("hello", chat2.messages_json)

    def test_chat_isolated_per_user_diagram(self):
        other = make_user(self.db, username="hannah", role="Developer")
        d2 = make_diagram(self.db, owner=self.user, title="other")
        c1 = _get_or_create_chat(self.user.id, self.diagram.id, self.db)
        c2 = _get_or_create_chat(other.id, self.diagram.id, self.db)
        c3 = _get_or_create_chat(self.user.id, d2.id, self.db)
        c1.messages_json = json.dumps([{"role": "user", "content": "u1"}])
        self.db.commit()
        self.assertNotEqual(
            _parse_messages(c1.messages_json),
            _parse_messages(
                _get_or_create_chat(other.id, self.diagram.id, self.db).messages_json
            ),
        )
        self.assertEqual(c2.messages_json, "[]")
        self.assertEqual(c3.messages_json, "[]")


if __name__ == "__main__":
    unittest.main()
