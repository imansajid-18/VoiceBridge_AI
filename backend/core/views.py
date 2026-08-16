import json
import groq
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .agent import run_suggestion_agent
from django.utils import timezone
from .models import Contact, ConversationSession, Message, SuggestionLog, MemoryEntry
from .memory_agent import run_memory_agent, save_memory_facts

FALLBACK_REPLIES = ["Yes", "No", "Can you repeat that?"]


class SuggestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        try:
            session = ConversationSession.objects.get(id=session_id, user=request.user)
        except ConversationSession.DoesNotExist:
            return Response({"error": "Session not found"}, status=404)

        transcript = request.data.get("transcript", "").strip()
        if not transcript:
            return Response({"error": "transcript is required"}, status=400)

        message = Message.objects.create(session=session, speaker="partner", text=transcript)

        try:
            result = run_suggestion_agent(
                transcript,
                user_id=request.user.id,
                contact_id=session.contact_id,
            )
            is_fallback = False
        except (groq.APIError, json.JSONDecodeError) as e:
            print(f"[SuggestView] Falling back — {type(e).__name__}: {e}")
            result = {"replies": FALLBACK_REPLIES, "setting": "general"}
            is_fallback = True

        suggestion_log = SuggestionLog.objects.create(
            session=session,
            message=message,
            suggestions_shown=result["replies"],
            setting_tag=result["setting"],
        )

        session.save()

        return Response({**result, "fallback": is_fallback, "suggestion_log_id": suggestion_log.id})


class SelectSuggestionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        suggestion_log_id = request.data.get("suggestion_log_id")
        selected_text = request.data.get("selected")

        if not suggestion_log_id or not selected_text:
            return Response({"error": "suggestion_log_id and selected are required"}, status=400)

        try:
            log = SuggestionLog.objects.get(
                id=suggestion_log_id,
                session_id=session_id,
                session__user=request.user,
            )
        except SuggestionLog.DoesNotExist:
            return Response({"error": "Suggestion log not found"}, status=404)

        if selected_text not in log.suggestions_shown:
            return Response({"error": "Selected suggestion was not shown"}, status=400)

        log.suggestion_selected = selected_text
        log.save()
        log.session.save()

        return Response({"status": "recorded"})

class EndSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        try:
            session = ConversationSession.objects.get(id=session_id, user=request.user)
        except ConversationSession.DoesNotExist:
            return Response({"error": "Session not found"}, status=404)

        if session.status in ("ended", "discarded"):
            return Response({"error": "Session already closed"}, status=400)

        if not session.contact_id:
            session.status = "pending_decision"
            session.save()
            return Response({"status": "pending_decision"})

        try:
            facts = run_memory_agent(session.id)
            save_memory_facts(session, facts)
        except Exception as e:
            print(f"[EndSession] Memory extraction failed — {type(e).__name__}: {e}")
            facts = {"general_facts": [], "contact_facts": []}

        session.status = "ended"
        session.ended_at = timezone.now()
        session.save()
        return Response({"status": "ended", "saved_facts": facts})

class SaveAsContactView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        name = (request.data.get("name") or "").strip()
        if not name:
            return Response({"error": "name is required"}, status=400)

        try:
            session = ConversationSession.objects.get(
                id=session_id, user=request.user, status="pending_decision",
            )
        except ConversationSession.DoesNotExist:
            return Response({"error": "No session awaiting a decision"}, status=404)

        existing = Contact.objects.filter(user=request.user, name__iexact=name).first()
        if existing and not request.data.get("confirm_duplicate"):
            return Response(
                {"warning": "duplicate_name", "message": f"You already have a contact named {existing.name}."},
                status=409,
            )

        contact = Contact.objects.create(user=request.user, name=name)
        session.contact = contact
        session.status = "ended"
        session.ended_at = timezone.now()
        session.save()

        facts = run_memory_agent(session.id)
        save_memory_facts(session, facts)

        return Response({"status": "saved", "contact_id": contact.id, "saved_facts": facts})


class DiscardSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        try:
            session = ConversationSession.objects.get(
                id=session_id, user=request.user, status="pending_decision",
            )
        except ConversationSession.DoesNotExist:
            return Response({"error": "No session awaiting a decision"}, status=404)

        session.delete()
        return Response({"status": "discarded"})