from django.urls import path
from .views import SuggestView

urlpatterns = [
    path('sessions/<int:session_id>/suggest/', SuggestView.as_view(), name='suggest'),
]