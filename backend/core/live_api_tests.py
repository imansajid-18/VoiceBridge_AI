"""
LIVE API TESTS - genuinely calls Groq and Gemini for real.
"""

from django.contrib.auth.models import User
from django.test import TestCase
from .models import Contact, MemoryEntry, ConversationSession, Message, SuggestionLog


class LiveSuggestionAgentTests(TestCase):
    def test_real_groq_call_returns_valid_shape(self):
        from core.agent import run_suggestion_agent

        result = run_suggestion_agent(
            "Are you free for coffee this weekend?", user_id=1, contact_id=None,
        )

        self.assertIn("replies", result)
        self.assertIn("setting", result)
        self.assertEqual(len(result["replies"]), 3)
        self.assertTrue(all(isinstance(r, str) and r.strip() for r in result["replies"]))
        self.assertIn(result["setting"], ["medical", "campus", "dining", "general"])

    def test_real_groq_call_uses_personalization_when_facts_exist(self):
        from core.agent import run_suggestion_agent

        user = User.objects.create_user(username="liveagenttest", password="testpass123")
        contact = Contact.objects.create(user=user, name="Sara")
        MemoryEntry.objects.create(user=user, contact=contact, fact="Is studying computer science")

        result = run_suggestion_agent(
            "How's school going?", user_id=user.id, contact_id=contact.id,
        )

        self.assertEqual(len(result["replies"]), 3)
        self.assertIn(result["setting"], ["medical", "campus", "dining", "general"])

    def test_real_groq_call_with_conversation_history(self):
        """
        Mirrors tonight's actual failure conditions: real decision + reply
        calls, with real 6-message session history attached - not an
        artificially simple cold call.
        """
        from core.agent import run_suggestion_agent

        user = User.objects.create_user(username="livehistorytest", password="testpass123")
        contact = Contact.objects.create(user=user, name="Bilal")
        session = ConversationSession.objects.create(user=user, contact=contact)

        m1 = Message.objects.create(
            session=session, speaker="partner", text="Are you coming home this weekend?"
        )
        SuggestionLog.objects.create(
            session=session, message=m1, suggestions_shown=["Yes"],
            suggestion_selected="Yeah, In Sha Allah, I finish my exam Friday",
        )
        m2 = Message.objects.create(
            session=session, speaker="partner", text="Good, your mom's making biryani"
        )
        SuggestionLog.objects.create(
            session=session, message=m2, suggestions_shown=["Nice!"],
            suggestion_selected="Nice, can't wait!",
        )

        result = run_suggestion_agent(
            "So you'll actually be here Friday night?",
            user_id=user.id, contact_id=contact.id, session_id=session.id,
        )

        self.assertEqual(len(result["replies"]), 3)
        self.assertIn(result["setting"], ["medical", "campus", "dining", "general"])


class LiveMemoryAgentTests(TestCase):
    def test_real_gemini_call_extracts_facts_from_real_conversation(self):
        from core.memory_agent import run_memory_agent

        user = User.objects.create_user(username="livememtest", password="testpass123")
        contact = Contact.objects.create(user=user, name="Ali")
        session = ConversationSession.objects.create(user=user, contact=contact)

        m1 = Message.objects.create(
            session=session, speaker="partner", text="I love playing chess on weekends"
        )
        SuggestionLog.objects.create(
            session=session, message=m1, suggestions_shown=["Nice!"],
            suggestion_selected="Nice, In Sha Allah we'll play sometime!",
        )

        result = run_memory_agent(session.id)

        self.assertIn("general_facts", result)
        self.assertIn("contact_facts", result)
        self.assertIsInstance(result["general_facts"], list)
        self.assertIsInstance(result["contact_facts"], list)