from django.urls import path
from .views import (
    SuggestView,
    SelectSuggestionView,
    EndSessionView,
    SaveAsContactView,
    DiscardSessionView,
    MemoryListView,
    MemoryEntryDeleteView,
    ContactMemoryDeleteView,
    ContactListCreateView,
    ContactDeleteView,
    SessionCreateView,
    RegisterView,
    GeneralMemoryDeleteView,
)

urlpatterns = [
    path("contacts/", ContactListCreateView.as_view(), name="contact_list_create"),
    path("contacts/<int:contact_id>/", ContactDeleteView.as_view(), name="contact_delete"),
    path("sessions/", SessionCreateView.as_view(), name="session_create"),
    path("sessions/<int:session_id>/suggest/", SuggestView.as_view(), name="suggest"),
    path(
        "sessions/<int:session_id>/select/",
        SelectSuggestionView.as_view(),
        name="select_suggestion",
    ),
    path("sessions/<int:session_id>/end/", EndSessionView.as_view(), name="end_session"),
    path(
        "sessions/<int:session_id>/save-contact/",
        SaveAsContactView.as_view(),
        name="save_as_contact",
    ),
    path(
        "sessions/<int:session_id>/discard/", DiscardSessionView.as_view(), name="discard_session"
    ),
    path("memory/", MemoryListView.as_view(), name="memory_list"),
    path("memory/<int:entry_id>/", MemoryEntryDeleteView.as_view(), name="memory_entry_delete"),
    path(
        "memory/contact/<int:contact_id>/",
        ContactMemoryDeleteView.as_view(),
        name="contact_memory_delete",
    ),
    path("register/", RegisterView.as_view(), name="register"),
    path("memory/general/", GeneralMemoryDeleteView.as_view(), name="general_memory_delete"),
]
