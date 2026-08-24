"""
Organized into three layers

UNIT TESTS         - exercise one function directly. No HTTP layer at all.
INTEGRATION TESTS  - exercise one real endpoint through Django's actual URL
                      routing, views, and database. External AI providers
                      (Groq, Gemini) are mocked; everything we own is real.
END-TO-END TESTS    - chain several real endpoints together in one continuous
                      session, each step's real response driving the next -
                      the same sequence an actual frontend session produces.
"""

import json
from unittest.mock import patch, MagicMock
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Contact, ConversationSession, Message, SuggestionLog, MemoryEntry
import groq


# ======================================================================
# UNIT TESTS
# ======================================================================

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


class StripMarkdownFenceTests(APITestCase):
    def test_strips_json_fence(self):
        from core.memory_agent import _strip_markdown_fence

        self.assertEqual(_strip_markdown_fence('```json\n{"a": 1}\n```'), '{"a": 1}')

    def test_leaves_plain_json_alone(self):
        from core.memory_agent import _strip_markdown_fence

        self.assertEqual(_strip_markdown_fence('{"a": 1}'), '{"a": 1}')


class BuildConversationTextTests(APITestCase):
    def test_interleaves_in_actual_order_with_named_contact(self):
        from core.memory_agent import _build_conversation_text

        user = User.objects.create_user(username="ordertest", password="testpass123")
        contact = Contact.objects.create(user=user, name="Ali")
        session = ConversationSession.objects.create(user=user, contact=contact)
        m1 = Message.objects.create(session=session, speaker="partner", text="First")
        SuggestionLog.objects.create(
            session=session, message=m1, suggestions_shown=["A"], suggestion_selected="Reply1"
        )
        m2 = Message.objects.create(session=session, speaker="partner", text="Second")
        SuggestionLog.objects.create(
            session=session, message=m2, suggestions_shown=["B"], suggestion_selected="Reply2"
        )

        text = _build_conversation_text(session.id)
        self.assertEqual(
            text,
            "Ali said: First\nUser replied: Reply1\nAli said: Second\nUser replied: Reply2",
        )

    def test_uses_generic_label_for_stranger_session(self):
        from core.memory_agent import _build_conversation_text

        user = User.objects.create_user(username="strangertest", password="testpass123")
        session = ConversationSession.objects.create(user=user, contact=None)
        Message.objects.create(session=session, speaker="partner", text="Hello")

        text = _build_conversation_text(session.id)
        self.assertEqual(text, "the other person said: Hello")


class RecentHistoryMessagesTests(APITestCase):
    def test_includes_recent_exchanges_excluding_current_message(self):
        from core.agent import _recent_history_messages

        user = User.objects.create_user(username="histuser", password="testpass123")
        session = ConversationSession.objects.create(user=user)

        m1 = Message.objects.create(
            session=session, speaker="partner", text="Are you free for coffee?"
        )
        SuggestionLog.objects.create(
            session=session,
            message=m1,
            suggestions_shown=["Sure"],
            suggestion_selected="Sure, what time?",
        )
        m2 = Message.objects.create(session=session, speaker="partner", text="How about 5pm?")
        SuggestionLog.objects.create(
            session=session,
            message=m2,
            suggestions_shown=["Works"],
            suggestion_selected="Works for me!",
        )
        Message.objects.create(session=session, speaker="partner", text="Great, see you then")

        history = _recent_history_messages(session.id, limit=6)

        self.assertEqual(
            history[0],
            {"role": "user", "content": 'The other person said: "Are you free for coffee?"'},
        )
        self.assertEqual(history[1], {"role": "assistant", "content": "Sure, what time?"})
        self.assertEqual(
            history[2], {"role": "user", "content": 'The other person said: "How about 5pm?"'}
        )
        self.assertEqual(history[3], {"role": "assistant", "content": "Works for me!"})
        self.assertEqual(len(history), 4)

    def test_respects_limit(self):
        from core.agent import _recent_history_messages

        user = User.objects.create_user(username="histuser2", password="testpass123")
        session = ConversationSession.objects.create(user=user)
        for i in range(10):
            Message.objects.create(session=session, speaker="partner", text=f"Message {i}")

        history = _recent_history_messages(session.id, limit=3)
        partner_lines = [h for h in history if h["role"] == "user"]
        self.assertEqual(len(partner_lines), 3)
        
class RunSuggestionAgentDecisionFailureTests(APITestCase):
    class _FakeAPIError(groq.APIError):
        def __init__(self):
            pass

    @patch("core.agent.lookup_profile")
    @patch("core.agent.client")
    def test_continues_without_personalization_if_decision_call_fails(self, mock_client, mock_lookup):
        reply_message = MagicMock()
        reply_message.content = '{"replies": ["A", "B", "C"], "setting": "general"}'
        reply_response = MagicMock()
        reply_response.choices = [MagicMock(message=reply_message)]

        mock_client.chat.completions.create.side_effect = [
            self._FakeAPIError(),
            reply_response,
        ]

        from core.agent import run_suggestion_agent
        result = run_suggestion_agent("Hi", user_id=1, contact_id=5)

        self.assertEqual(result["replies"], ["A", "B", "C"])
        mock_lookup.assert_not_called()

class RunSuggestionAgentToolCallTests(APITestCase):
    @patch("core.agent.lookup_profile")
    @patch("core.agent.client")
    def test_uses_looked_up_facts_in_second_call(self, mock_client, mock_lookup):
        mock_lookup.return_value = ["Some fact"]

        decision_message = MagicMock()
        decision_message.tool_calls = [MagicMock(id="call_1", function=MagicMock(arguments="{}"))]
        decision_response = MagicMock()
        decision_response.choices = [MagicMock(message=decision_message)]

        reply_message = MagicMock()
        reply_message.content = (
            '{"replies": ["Real personalized reply", "B", "C"], "setting": "general"}'
        )
        reply_response = MagicMock()
        reply_response.choices = [MagicMock(message=reply_message)]

        mock_client.chat.completions.create.side_effect = [decision_response, reply_response]

        from core.agent import run_suggestion_agent

        result = run_suggestion_agent("Hi", user_id=1, contact_id=5)

        self.assertEqual(result["replies"], ["Real personalized reply", "B", "C"])
        mock_lookup.assert_called_once_with(user_id=1, contact_id=5)
        self.assertEqual(mock_client.chat.completions.create.call_count, 2)

    @patch("core.agent.lookup_profile")
    @patch("core.agent.client")
    def test_skips_lookup_when_no_tool_call(self, mock_client, mock_lookup):
        decision_message = MagicMock()
        decision_message.tool_calls = None
        decision_response = MagicMock()
        decision_response.choices = [MagicMock(message=decision_message)]

        reply_message = MagicMock()
        reply_message.content = '{"replies": ["Generic", "reply", "here"], "setting": "general"}'
        reply_response = MagicMock()
        reply_response.choices = [MagicMock(message=reply_message)]

        mock_client.chat.completions.create.side_effect = [decision_response, reply_response]

        from core.agent import run_suggestion_agent

        run_suggestion_agent("Hi", user_id=1, contact_id=None)

        mock_lookup.assert_not_called()

    @patch("core.agent.lookup_profile")
    @patch("core.agent.client")
    def test_filters_trailing_empty_reply_instead_of_discarding_good_ones(self, mock_client, mock_lookup):
        decision_message = MagicMock()
        decision_message.tool_calls = None
        decision_response = MagicMock()
        decision_response.choices = [MagicMock(message=decision_message)]

        reply_message = MagicMock()
        reply_message.content = '{"replies": ["Hey!", "Nice to meet you!", "What\'s up?", ""], "setting": "general"}'
        reply_response = MagicMock()
        reply_response.choices = [MagicMock(message=reply_message)]

        mock_client.chat.completions.create.side_effect = [decision_response, reply_response]

        from core.agent import run_suggestion_agent
        result = run_suggestion_agent("Hi", user_id=1, contact_id=None)

        self.assertEqual(result["replies"], ["Hey!", "Nice to meet you!", "What's up?"])


# ======================================================================
# INTEGRATION TESTS
# ======================================================================

class RegisterViewTests(APITestCase):
    def test_register_creates_user_and_returns_token(self):
        response = self.client.post(
            "/api/register/",
            {"username": "newuser", "password": "a-strong-pass-99"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn("access", response.data)
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_register_rejects_duplicate_username(self):
        User.objects.create_user(username="taken", password="a-strong-pass-99")
        response = self.client.post(
            "/api/register/",
            {"username": "taken", "password": "a-strong-pass-99"},
            format="json",
        )
        self.assertEqual(response.status_code, 409)

    def test_register_rejects_weak_password(self):
        response = self.client.post(
            "/api/register/",
            {"username": "weakpassuser", "password": "12345"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(username="weakpassuser").exists())


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

    @patch("core.views.run_suggestion_agent")
    def test_suggest_falls_back_on_valid_json_wrong_keys(self, mock_agent):
        mock_agent.return_value = {"answers": ["Yes"], "context": "general"}
        response = self.client.post(
            f"/api/sessions/{self.session.id}/suggest/",
            {"transcript": "Are you free later?"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["fallback"])

    @patch("core.views.run_suggestion_agent")
    def test_suggest_falls_back_when_fewer_than_three_replies(self, mock_agent):
        mock_agent.return_value = {"replies": ["Yes", "No"], "setting": "general"}
        response = self.client.post(
            f"/api/sessions/{self.session.id}/suggest/",
            {"transcript": "Hi"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["fallback"])

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

    def test_select_accepts_custom_text_with_flag(self):
        response = self.client.post(
            f"/api/sessions/{self.session.id}/select/",
            {
                "suggestion_log_id": self.log.id,
                "selected": "Something totally different",
                "is_custom": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)

    def test_select_still_rejects_unlisted_text_without_flag(self):
        response = self.client.post(
            f"/api/sessions/{self.session.id}/select/",
            {"suggestion_log_id": self.log.id, "selected": "Not shown, not flagged"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_suggest_rejects_null_transcript_cleanly(self):
        response = self.client.post(
            f"/api/sessions/{self.session.id}/suggest/", {"transcript": None}, format="json",
        )
        self.assertEqual(response.status_code, 400)


class EndSessionViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="enduser", password="testpass123")
        self.contact = Contact.objects.create(user=self.user, name="Sara")
        token = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")

    @patch("core.views.save_memory_facts")
    @patch("core.views.run_memory_agent")
    def test_known_contact_extracts_and_saves(self, mock_agent, mock_save):
        mock_agent.return_value = {
            "general_facts": ["Says In Sha Allah"],
            "contact_facts": ["Likes coffee"],
        }
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
    def test_end_survives_memory_agent_crash(self, mock_agent):
        mock_agent.side_effect = ValueError("Gemini returned something unparseable")
        session = ConversationSession.objects.create(user=self.user, contact=self.contact)

        response = self.client.post(f"/api/sessions/{session.id}/end/", {}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "ended")
        session.refresh_from_db()
        self.assertEqual(session.status, "ended")

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
        session = ConversationSession.objects.create(
            user=self.user, contact=self.contact, status="ended"
        )
        response = self.client.post(f"/api/sessions/{session.id}/end/", {}, format="json")
        self.assertEqual(response.status_code, 400)


class SaveDiscardTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="sduser", password="testpass123")
        self.session = ConversationSession.objects.create(
            user=self.user,
            contact=None,
            status="pending_decision",
        )
        self.message = Message.objects.create(
            session=self.session, speaker="partner", text="Nice to meet you"
        )
        token = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")

    @patch("core.views.save_memory_facts")
    @patch("core.views.run_memory_agent")
    def test_save_creates_contact_and_runs_agent_once(self, mock_agent, mock_save):
        mock_agent.return_value = {"general_facts": [], "contact_facts": ["Met at a cafe"]}

        response = self.client.post(
            f"/api/sessions/{self.session.id}/save-contact/",
            {"name": "Ahmed"},
            format="json",
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
            f"/api/sessions/{self.session.id}/save-contact/",
            {"name": "ahmed"},
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["warning"], "duplicate_name")
        self.assertEqual(Contact.objects.filter(user=self.user).count(), 1)

    @patch("core.views.run_memory_agent")
    def test_save_survives_memory_agent_crash(self, mock_agent):
        mock_agent.side_effect = ValueError("Gemini returned something unparseable")
        response = self.client.post(
            f"/api/sessions/{self.session.id}/save-contact/",
            {"name": "Ahmed"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, "ended")

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

        self.general = MemoryEntry.objects.create(
            user=self.user, contact=None, fact="Says In Sha Allah"
        )
        self.contact_fact = MemoryEntry.objects.create(
            user=self.user, contact=self.contact, fact="Likes coffee"
        )
        self.other_fact = MemoryEntry.objects.create(
            user=self.other_user, contact=None, fact="Not yours"
        )

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
        MemoryEntry.objects.create(
            user=self.user, contact=self.contact, fact="Studies at university"
        )

        response = self.client.delete(f"/api/memory/contact/{self.contact.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        self.assertFalse(MemoryEntry.objects.filter(contact=self.contact).exists())
        self.assertTrue(MemoryEntry.objects.filter(id=self.general.id).exists())

    def test_delete_all_general_memory(self):
        response = self.client.delete("/api/memory/general/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(MemoryEntry.objects.filter(id=self.general.id).exists())
        self.assertTrue(MemoryEntry.objects.filter(id=self.contact_fact.id).exists())


class ContactCrudTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="cruduser", password="testpass123")
        self.other_user = User.objects.create_user(username="crudother", password="testpass123")
        token = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")

    def test_list_only_returns_own_contacts(self):
        Contact.objects.create(user=self.user, name="Sara")
        Contact.objects.create(user=self.other_user, name="NotMine")

        response = self.client.get("/api/contacts/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Sara")

    def test_create_contact(self):
        response = self.client.post("/api/contacts/", {"name": "Ahmed"}, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertTrue(Contact.objects.filter(user=self.user, name="Ahmed").exists())

    def test_create_warns_on_duplicate(self):
        Contact.objects.create(user=self.user, name="Ahmed")

        response = self.client.post("/api/contacts/", {"name": "ahmed"}, format="json")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(Contact.objects.filter(user=self.user).count(), 1)

    def test_cannot_delete_another_users_contact(self):
        other = Contact.objects.create(user=self.other_user, name="NotMine")

        response = self.client.delete(f"/api/contacts/{other.id}/")

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Contact.objects.filter(id=other.id).exists())


class SessionCreateTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="sessuser", password="testpass123")
        self.contact = Contact.objects.create(user=self.user, name="Sara")
        token = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")

    def test_create_session_with_contact(self):
        response = self.client.post(
            "/api/sessions/", {"contact_id": self.contact.id}, format="json"
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["contact_name"], "Sara")

    def test_create_session_without_contact_is_allowed(self):
        response = self.client.post("/api/sessions/", {}, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.data["contact_id"])

    def test_cannot_start_session_with_another_users_contact(self):
        other_user = User.objects.create_user(username="sessother", password="testpass123")
        other_contact = Contact.objects.create(user=other_user, name="NotMine")

        response = self.client.post(
            "/api/sessions/", {"contact_id": other_contact.id}, format="json"
        )

        self.assertEqual(response.status_code, 404)


# ======================================================================
# END-TO-END TESTS
# Real HTTP calls only, chained together - no ORM shortcuts to pre-seed
# state. Each step's genuine response drives the next call, exactly the
# sequence a real frontend session produces. Only Groq and Gemini are
# mocked; everything we own is exercised for real, in the real order.
# ======================================================================

class EndToEndFlowTests(APITestCase):
    @patch("core.views.run_memory_agent")
    @patch("core.views.run_suggestion_agent")
    def test_full_conversation_to_saved_and_retrievable_memory(self, mock_suggest, mock_memory):
        """
        The actual core promise of this whole project: talk to a known
        contact, memory gets extracted and saved automatically, and it's
        genuinely retrievable afterward through the same API a real
        Memory Viewer screen calls. Register -> create contact -> start
        session -> suggest -> select -> end -> read memory back.
        """
        register_response = self.client.post(
            "/api/register/",
            {"username": "e2euser", "password": "a-strong-pass-99"},
            format="json",
        )
        self.assertEqual(register_response.status_code, 201)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {register_response.data['access']}")

        contact_response = self.client.post("/api/contacts/", {"name": "Sara"}, format="json")
        self.assertEqual(contact_response.status_code, 201)
        contact_id = contact_response.data["id"]

        session_response = self.client.post(
            "/api/sessions/", {"contact_id": contact_id}, format="json"
        )
        self.assertEqual(session_response.status_code, 201)
        session_id = session_response.data["session_id"]

        mock_suggest.return_value = {
            "replies": ["Sure, coffee sounds great!", "Maybe, what time?", "Sorry, busy this weekend"],
            "setting": "dining",
        }
        suggest_response = self.client.post(
            f"/api/sessions/{session_id}/suggest/",
            {"transcript": "Are you free for coffee this weekend?"},
            format="json",
        )
        self.assertEqual(suggest_response.status_code, 200)
        self.assertFalse(suggest_response.data["fallback"])

        select_response = self.client.post(
            f"/api/sessions/{session_id}/select/",
            {
                "suggestion_log_id": suggest_response.data["suggestion_log_id"],
                "selected": "Sure, coffee sounds great!",
            },
            format="json",
        )
        self.assertEqual(select_response.status_code, 200)

        mock_memory.return_value = {
            "general_facts": ["Uses casual, friendly phrasing"],
            "contact_facts": ["Enjoys coffee", "Free to meet up on weekends"],
        }
        end_response = self.client.post(f"/api/sessions/{session_id}/end/", {}, format="json")
        self.assertEqual(end_response.status_code, 200)
        self.assertEqual(end_response.data["status"], "ended")
        self.assertIn("Enjoys coffee", end_response.data["saved_facts"]["contact_facts"])

        memory_response = self.client.get("/api/memory/")
        self.assertEqual(memory_response.status_code, 200)
        contact_memory = next(
            c for c in memory_response.data["contacts"] if c["contact_id"] == contact_id
        )
        facts = [f["fact"] for f in contact_memory["facts"]]
        self.assertIn("Enjoys coffee", facts)
        self.assertIn("Free to meet up on weekends", facts)

        general_facts = [f["fact"] for f in memory_response.data["general_facts"]]
        self.assertIn("Uses casual, friendly phrasing", general_facts)

    @patch("core.views.run_memory_agent")
    @patch("core.views.run_suggestion_agent")
    def test_full_stranger_flow_with_consent_before_saving(self, mock_suggest, mock_memory):
        """
        The other core pipeline: a stranger conversation must never touch
        Gemini until the user explicitly consents by naming and saving
        them. Register -> Skip -> suggest -> select -> end (pending) ->
        save-contact (only now does memory extraction happen) -> verify.
        """
        register_response = self.client.post(
            "/api/register/",
            {"username": "strangere2e", "password": "a-strong-pass-99"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {register_response.data['access']}")

        session_response = self.client.post("/api/sessions/", {}, format="json")
        session_id = session_response.data["session_id"]
        self.assertIsNone(session_response.data["contact_id"])

        mock_suggest.return_value = {
            "replies": ["Nice to meet you!", "Hello!", "Hey there"],
            "setting": "general",
        }
        suggest_response = self.client.post(
            f"/api/sessions/{session_id}/suggest/", {"transcript": "Hi, I'm Ahmed"}, format="json",
        )
        self.client.post(
            f"/api/sessions/{session_id}/select/",
            {
                "suggestion_log_id": suggest_response.data["suggestion_log_id"],
                "selected": "Nice to meet you!",
            },
            format="json",
        )

        end_response = self.client.post(f"/api/sessions/{session_id}/end/", {}, format="json")
        self.assertEqual(end_response.status_code, 200)
        self.assertEqual(end_response.data["status"], "pending_decision")
        mock_memory.assert_not_called()

        mock_memory.return_value = {
            "general_facts": [],
            "contact_facts": ["Introduced themselves as Ahmed"],
        }
        save_response = self.client.post(
            f"/api/sessions/{session_id}/save-contact/", {"name": "Ahmed"}, format="json",
        )
        self.assertEqual(save_response.status_code, 200)
        mock_memory.assert_called_once()

        contact_id = save_response.data["contact_id"]
        memory_response = self.client.get("/api/memory/")
        contact_memory = next(
            c for c in memory_response.data["contacts"] if c["contact_id"] == contact_id
        )
        self.assertIn(
            "Introduced themselves as Ahmed", [f["fact"] for f in contact_memory["facts"]]
        )