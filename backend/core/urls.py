from django.urls import path
from .views import (
    SuggestView, SelectSuggestionView, EndSessionView,
    SaveAsContactView, DiscardSessionView,
)

urlpatterns = [
    path('sessions/<int:session_id>/suggest/', SuggestView.as_view(), name='suggest'),
    path('sessions/<int:session_id>/select/', SelectSuggestionView.as_view(), name='select_suggestion'),
    path('sessions/<int:session_id>/end/', EndSessionView.as_view(), name='end_session'),
    path('sessions/<int:session_id>/save-contact/', SaveAsContactView.as_view(), name='save_as_contact'),
    path('sessions/<int:session_id>/discard/', DiscardSessionView.as_view(), name='discard_session'),
]