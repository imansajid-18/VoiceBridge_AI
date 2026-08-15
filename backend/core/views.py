import groq
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import ConversationSession, Message, SuggestionLog
from .agent import run_suggestion_agent

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
        except (groq.APIError, __import__("json").JSONDecodeError) as e:
            print(f"[SuggestView] Falling back — {type(e).__name__}: {e}")
            result = {"replies": FALLBACK_REPLIES, "setting": "general"}
            is_fallback = True

        SuggestionLog.objects.create(
            session=session,
            message=message,
            suggestions_shown=result["replies"],
            setting_tag=result["setting"],
        )

        session.save()

        return Response({**result, "fallback": is_fallback})