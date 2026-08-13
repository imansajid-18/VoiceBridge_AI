from django.contrib.auth.models import User
from django.db import models


class Contact(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contacts')
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class ConversationSession(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('ended', 'Ended'),
        ('pending_decision', 'Pending Decision'),
        ('discarded', 'Discarded'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    contact = models.ForeignKey(Contact, on_delete=models.SET_NULL, null=True, blank=True, related_name='sessions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    last_activity_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Session {self.id} ({self.status})"


class Message(models.Model):
    SPEAKER_CHOICES = [('partner', 'Partner'), ('user', 'User')]
    session = models.ForeignKey(ConversationSession, on_delete=models.CASCADE, related_name='messages')
    speaker = models.CharField(max_length=10, choices=SPEAKER_CHOICES)
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.speaker}: {self.text[:30]}"


class SuggestionLog(models.Model):
    session = models.ForeignKey(ConversationSession, on_delete=models.CASCADE, related_name='suggestion_logs')
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='suggestion_logs')
    suggestions_shown = models.JSONField()
    suggestion_selected = models.TextField(null=True, blank=True)
    setting_tag = models.CharField(max_length=20, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)


class MemoryEntry(models.Model):
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, null=True, blank=True, related_name='memory_entries')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='memory_entries')
    fact = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.fact[:50]