from django.contrib import admin
from .models import Contact, ConversationSession, Message, SuggestionLog, MemoryEntry

admin.site.register(Contact)
admin.site.register(ConversationSession)
admin.site.register(Message)
admin.site.register(SuggestionLog)
admin.site.register(MemoryEntry)