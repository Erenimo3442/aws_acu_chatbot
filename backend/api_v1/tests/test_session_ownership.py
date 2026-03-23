import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from api_v1.models import ChatMessage, ChatSession


class SessionOwnershipTests(TestCase):
    def _seed_session_for_client(self, client: Client):
        response = client.post(
            "/api/v1/chat",
            data=json.dumps({"question": "Seed", "stream": False}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        session_id = response.json()["data"]["session"]["id"]
        return ChatSession.objects.get(id=session_id)

    def test_anonymous_can_read_own_session_messages(self):
        client = Client()
        chat_session = self._seed_session_for_client(client)

        response = client.get(f"/api/v1/sessions/{chat_session.id}/messages")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["session_id"], chat_session.id)

    def test_anonymous_cannot_read_other_anonymous_session(self):
        owner_client = Client()
        chat_session = self._seed_session_for_client(owner_client)

        other_client = Client()
        response = other_client.get(f"/api/v1/sessions/{chat_session.id}/messages")
        self.assertEqual(response.status_code, 401)

        other_client.post(
            "/api/v1/chat",
            data=json.dumps({"question": "other", "stream": False}),
            content_type="application/json",
        )
        response_after_cookie = other_client.get(f"/api/v1/sessions/{chat_session.id}/messages")
        self.assertEqual(response_after_cookie.status_code, 404)
        self.assertEqual(response_after_cookie.json()["error"]["code"], "NOT_FOUND")

    def test_student_cannot_read_other_student_session(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(username="owner", password="pass12345")
        intruder = user_model.objects.create_user(username="intruder", password="pass12345")

        owner_session = ChatSession.objects.create(owner_type=ChatSession.OWNER_STUDENT, owner_user=owner)
        ChatMessage.objects.create(session=owner_session, role=ChatMessage.ROLE_USER, content="hi")

        intruder_client = Client()
        intruder_client.force_login(intruder)

        response = intruder_client.get(f"/api/v1/sessions/{owner_session.id}/messages")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "NOT_FOUND")

    def test_student_can_read_own_session(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(username="owner2", password="pass12345")

        owner_session = ChatSession.objects.create(owner_type=ChatSession.OWNER_STUDENT, owner_user=owner)
        ChatMessage.objects.create(session=owner_session, role=ChatMessage.ROLE_USER, content="hello")

        owner_client = Client()
        owner_client.force_login(owner)
        response = owner_client.get(f"/api/v1/sessions/{owner_session.id}/messages")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["session_id"], owner_session.id)
