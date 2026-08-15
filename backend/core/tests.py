import json
from unittest.mock import patch
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Contact, ConversationSession, Message, SuggestionLog


class SuggestViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.contact = Contact.objects.create(user=self.user, name="Sara")
        self.session = ConversationSession.objects.create(user=self.user, contact=self.contact)

        token = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")

    @patch("core.views.run_suggestion_agent")
    def test_suggest_returns_replies_on_success(self, mock_agent):
        mock_agent.return_value = {"replies": ["Yes", "No", "Maybe"], "setting": "general"}

        response = self.client.post(
            f"/api/sessions/{self.session.id}/suggest/",
            {"transcript": "Are you free later?"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["replies"], ["Yes", "No", "Maybe"])
        self.assertFalse(response.data["fallback"])
        self.assertTrue(SuggestionLog.objects.filter(session=self.session).exists())

    @patch("core.views.run_suggestion_agent")
    def test_suggest_falls_back_on_bad_response(self, mock_agent):
        mock_agent.side_effect = json.JSONDecodeError("bad json", "doc", 0)

        response = self.client.post(
            f"/api/sessions/{self.session.id}/suggest/",
            {"transcript": "Are you free later?"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["fallback"])
        self.assertEqual(response.data["replies"], ["Yes", "No", "Can you repeat that?"])

    def test_suggest_requires_authentication(self):
        self.client.credentials()
        response = self.client.post(
            f"/api/sessions/{self.session.id}/suggest/",
            {"transcript": "Hi"},
            format="json",
        )
        self.assertEqual(response.status_code, 401)

    def test_cannot_access_another_users_session(self):
        other_user = User.objects.create_user(username="other", password="pass123")
        other_session = ConversationSession.objects.create(user=other_user)

        response = self.client.post(
            f"/api/sessions/{other_session.id}/suggest/",
            {"transcript": "Hi"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)


class SelectSuggestionViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser2", password="testpass123")
        self.session = ConversationSession.objects.create(user=self.user)
        self.message = Message.objects.create(session=self.session, speaker="partner", text="Hi")
        self.log = SuggestionLog.objects.create(
            session=self.session,
            message=self.message,
            suggestions_shown=["Yes", "No"],
            setting_tag="general",
        )

        token = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")

    def test_select_records_choice(self):
        response = self.client.post(
            f"/api/sessions/{self.session.id}/select/",
            {"suggestion_log_id": self.log.id, "selected": "Yes"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.log.refresh_from_db()
        self.assertEqual(self.log.suggestion_selected, "Yes")

    def test_select_rejects_text_not_in_suggestions(self):
        response = self.client.post(
            f"/api/sessions/{self.session.id}/select/",
            {"suggestion_log_id": self.log.id, "selected": "Something I just invented"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.log.refresh_from_db()
        self.assertIsNone(self.log.suggestion_selected)