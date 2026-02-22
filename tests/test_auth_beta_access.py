import asyncio
import hashlib
import os
import shutil
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

TEST_DIR = tempfile.mkdtemp(prefix="tutors_nightmare_tests_")
TEST_DB_PATH = os.path.join(TEST_DIR, "test.db")
os.environ["DB_PATH"] = TEST_DB_PATH

import db  # noqa: E402
import main  # noqa: E402

INVITE_CODE = "beta-secret"


def _invite_hash(code: str) -> str:
    digest = hashlib.sha256(code.encode("utf-8")).hexdigest()
    return f"sha256${digest}"


class AuthBetaAccessTests(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEST_DIR, ignore_errors=True)

    def setUp(self):
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)

        asyncio.run(db.init_db())
        asyncio.run(db.set_beta_invite_code_hash(_invite_hash(INVITE_CODE)))

        self.llm_patcher = patch(
            "main.llm.generate_reply",
            new=AsyncMock(return_value="Stubbed assistant response"),
        )
        self.llm_patcher.start()

    def tearDown(self):
        self.llm_patcher.stop()

    def _register(self, client: TestClient, username: str, invite_code: str = INVITE_CODE):
        return client.post(
            "/api/auth/register",
            json={
                "username": username,
                "password": "supersecure1",
                "display_name": username.capitalize(),
                "invite_code": invite_code,
            },
        )

    def test_register_fails_with_wrong_invite_code(self):
        with TestClient(main.app) as client:
            response = self._register(client, "alice", invite_code="wrong-code")
            self.assertEqual(response.status_code, 401)

    def test_register_success_sets_session_cookie(self):
        with TestClient(main.app) as client:
            response = self._register(client, "alice")
            self.assertEqual(response.status_code, 200)
            self.assertIn("session_token", response.cookies)

    def test_duplicate_username_rejected(self):
        with TestClient(main.app) as client:
            first = self._register(client, "alice")
            second = self._register(client, "alice")
            self.assertEqual(first.status_code, 200)
            self.assertEqual(second.status_code, 409)

    def test_login_success_and_failure(self):
        with TestClient(main.app) as client:
            self.assertEqual(self._register(client, "alice").status_code, 200)

            bad_login = client.post(
                "/api/auth/login",
                json={"username": "alice", "password": "wrongpassword"},
            )
            self.assertEqual(bad_login.status_code, 401)

            good_login = client.post(
                "/api/auth/login",
                json={"username": "alice", "password": "supersecure1"},
            )
            self.assertEqual(good_login.status_code, 200)
            self.assertIn("session_token", good_login.cookies)

    def test_unauthenticated_access_is_blocked(self):
        with TestClient(main.app) as client:
            page_response = client.get("/", follow_redirects=False)
            self.assertEqual(page_response.status_code, 302)
            self.assertIn("/auth?next=", page_response.headers.get("location", ""))

            chat_response = client.post(
                "/api/chat",
                json={
                    "messages": [{"role": "user", "text": "Hello"}],
                    "language": "en",
                    "mode": "chat",
                    "is_primary_lang": False,
                    "primary_lang": "es",
                    "secondary_lang": "en",
                },
            )
            self.assertEqual(chat_response.status_code, 401)

    def test_authenticated_user_can_access_protected_endpoints(self):
        with TestClient(main.app) as client:
            self.assertEqual(self._register(client, "alice").status_code, 200)

            me_response = client.get("/api/me")
            self.assertEqual(me_response.status_code, 200)

            chat_response = client.post(
                "/api/chat",
                json={
                    "messages": [{"role": "user", "text": "Hello"}],
                    "language": "en",
                    "mode": "chat",
                    "is_primary_lang": False,
                    "primary_lang": "es",
                    "secondary_lang": "en",
                },
            )
            self.assertEqual(chat_response.status_code, 200)

    def test_user_cannot_fetch_other_users_conversation(self):
        with TestClient(main.app) as client_a:
            self.assertEqual(self._register(client_a, "alice").status_code, 200)
            chat_response = client_a.post(
                "/api/chat",
                json={
                    "messages": [{"role": "user", "text": "Hello from A"}],
                    "language": "en",
                    "mode": "chat",
                    "is_primary_lang": False,
                    "primary_lang": "es",
                    "secondary_lang": "en",
                },
            )
            self.assertEqual(chat_response.status_code, 200)
            conversation_id = chat_response.json()["conversation_id"]

        with TestClient(main.app) as client_b:
            self.assertEqual(self._register(client_b, "bob").status_code, 200)
            forbidden_response = client_b.get(f"/api/conversations/{conversation_id}")
            self.assertEqual(forbidden_response.status_code, 404)

    def test_logout_invalidates_session(self):
        with TestClient(main.app) as client:
            self.assertEqual(self._register(client, "alice").status_code, 200)
            self.assertEqual(client.get("/api/me").status_code, 200)

            logout_response = client.post("/api/auth/logout")
            self.assertEqual(logout_response.status_code, 200)

            me_after_logout = client.get("/api/me")
            self.assertEqual(me_after_logout.status_code, 401)

    def test_profile_patch_persists_preferences(self):
        with TestClient(main.app) as client:
            self.assertEqual(self._register(client, "alice").status_code, 200)

            patch_response = client.patch(
                "/api/me",
                json={
                    "display_name": "Alice QA",
                    "preferred_primary_lang": "fr",
                    "preferred_secondary_lang": "en",
                },
            )
            self.assertEqual(patch_response.status_code, 200)

            me_response = client.get("/api/me")
            self.assertEqual(me_response.status_code, 200)
            payload = me_response.json()
            self.assertEqual(payload["display_name"], "Alice QA")
            self.assertEqual(payload["preferred_primary_lang"], "fr")
            self.assertEqual(payload["preferred_secondary_lang"], "en")


if __name__ == "__main__":
    unittest.main()
