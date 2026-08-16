import json
from unittest.mock import patch
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Contact, ConversationSession, Message, SuggestionLog, MemoryEntry


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

class LookupProfileTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="lpuser", password="testpass123")
        self.contact = Contact.objects.create(user=self.user, name="Sara")
        self.other_user = User.objects.create_user(username="lpother", password="testpass123")

    def test_returns_general_and_contact_facts(self):
        from core.tools import lookup_profile
        MemoryEntry.objects.create(user=self.user, contact=None, fact="Says In Sha Allah")
        MemoryEntry.objects.create(user=self.user, contact=self.contact, fact="Likes coffee")

        facts = lookup_profile(user_id=self.user.id, contact_id=self.contact.id)

        self.assertIn("Says In Sha Allah", facts)
        self.assertIn("Likes coffee", facts)

    def test_excludes_other_users_facts(self):
        from core.tools import lookup_profile
        MemoryEntry.objects.create(user=self.other_user, contact=None, fact="Not yours")

        facts = lookup_profile(user_id=self.user.id)

        self.assertEqual(facts, [])

class EndSessionViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="enduser", password="testpass123")
        self.contact = Contact.objects.create(user=self.user, name="Sara")
        token = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")

    @patch("core.views.save_memory_facts")
    @patch("core.views.run_memory_agent")
    def test_known_contact_extracts_and_saves(self, mock_agent, mock_save):
        mock_agent.return_value = {"general_facts": ["Says In Sha Allah"], "contact_facts": ["Likes coffee"]}
        session = ConversationSession.objects.create(user=self.user, contact=self.contact)

        response = self.client.post(f"/api/sessions/{session.id}/end/", {}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "ended")
        mock_agent.assert_called_once()
        mock_save.assert_called_once()
        session.refresh_from_db()
        self.assertEqual(session.status, "ended")
        self.assertIsNotNone(session.ended_at)

    @patch("core.views.run_memory_agent")
    def test_stranger_does_not_call_gemini(self, mock_agent):
        session = ConversationSession.objects.create(user=self.user, contact=None)

        response = self.client.post(f"/api/sessions/{session.id}/end/", {}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "pending_decision")
        mock_agent.assert_not_called()
        session.refresh_from_db()
        self.assertEqual(session.status, "pending_decision")

    def test_cannot_end_an_already_ended_session(self):
        session = ConversationSession.objects.create(user=self.user, contact=self.contact, status="ended")
        response = self.client.post(f"/api/sessions/{session.id}/end/", {}, format="json")
        self.assertEqual(response.status_code, 400)


class SaveDiscardTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="sduser", password="testpass123")
        self.session = ConversationSession.objects.create(
            user=self.user, contact=None, status="pending_decision",
        )
        self.message = Message.objects.create(session=self.session, speaker="partner", text="Nice to meet you")
        token = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")

    @patch("core.views.save_memory_facts")
    @patch("core.views.run_memory_agent")
    def test_save_creates_contact_and_runs_agent_once(self, mock_agent, mock_save):
        mock_agent.return_value = {"general_facts": [], "contact_facts": ["Met at a cafe"]}

        response = self.client.post(
            f"/api/sessions/{self.session.id}/save-contact/", {"name": "Ahmed"}, format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Contact.objects.filter(user=self.user, name="Ahmed").exists())
        mock_agent.assert_called_once()
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, "ended")
        self.assertEqual(self.session.contact.name, "Ahmed")

    def test_save_warns_on_duplicate_name(self):
        Contact.objects.create(user=self.user, name="Ahmed")

        response = self.client.post(
            f"/api/sessions/{self.session.id}/save-contact/", {"name": "ahmed"}, format="json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["warning"], "duplicate_name")
        self.assertEqual(Contact.objects.filter(user=self.user).count(), 1)

    @patch("core.views.run_memory_agent")
    def test_discard_deletes_everything_and_never_calls_gemini(self, mock_agent):
        session_id = self.session.id

        response = self.client.post(f"/api/sessions/{session_id}/discard/", {}, format="json")

        self.assertEqual(response.status_code, 200)
        mock_agent.assert_not_called()
        self.assertFalse(ConversationSession.objects.filter(id=session_id).exists())
        self.assertFalse(Message.objects.filter(session_id=session_id).exists())

class MemoryViewerTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="memuser", password="testpass123")
        self.other_user = User.objects.create_user(username="memother", password="testpass123")
        self.contact = Contact.objects.create(user=self.user, name="Sara")

        self.general = MemoryEntry.objects.create(user=self.user, contact=None, fact="Says In Sha Allah")
        self.contact_fact = MemoryEntry.objects.create(user=self.user, contact=self.contact, fact="Likes coffee")
        self.other_fact = MemoryEntry.objects.create(user=self.other_user, contact=None, fact="Not yours")

        token = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")

    def test_list_separates_general_and_contact_memory(self):
        response = self.client.get("/api/memory/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["general_facts"]), 1)
        self.assertEqual(response.data["general_facts"][0]["fact"], "Says In Sha Allah")
        self.assertEqual(len(response.data["contacts"]), 1)
        self.assertEqual(response.data["contacts"][0]["contact_name"], "Sara")

    def test_cannot_delete_another_users_memory(self):
        response = self.client.delete(f"/api/memory/{self.other_fact.id}/")

        self.assertEqual(response.status_code, 404)
        self.assertTrue(MemoryEntry.objects.filter(id=self.other_fact.id).exists())

    def test_delete_single_entry(self):
        response = self.client.delete(f"/api/memory/{self.general.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(MemoryEntry.objects.filter(id=self.general.id).exists())

    def test_delete_all_memory_for_a_contact(self):
        MemoryEntry.objects.create(user=self.user, contact=self.contact, fact="Studies at university")

        response = self.client.delete(f"/api/memory/contact/{self.contact.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        self.assertFalse(MemoryEntry.objects.filter(contact=self.contact).exists())
        self.assertTrue(MemoryEntry.objects.filter(id=self.general.id).exists())

class StripMarkdownFenceTests(APITestCase):
    def test_strips_json_fence(self):
        from core.memory_agent import _strip_markdown_fence
        self.assertEqual(_strip_markdown_fence('```json\n{"a": 1}\n```'), '{"a": 1}')

    def test_leaves_plain_json_alone(self):
        from core.memory_agent import _strip_markdown_fence
        self.assertEqual(_strip_markdown_fence('{"a": 1}'), '{"a": 1}')