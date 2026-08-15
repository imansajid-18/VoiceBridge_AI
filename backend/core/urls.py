from django.urls import path
from .views import SuggestView, SelectSuggestionView

urlpatterns = [
    path('sessions/<int:session_id>/suggest/', SuggestView.as_view(), name='suggest'),
    path('sessions/<int:session_id>/select/', SelectSuggestionView.as_view(), name='select_suggestion'),
]