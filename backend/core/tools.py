from .models import MemoryEntry


def lookup_profile(user_id, contact_id=None):
    """
    Returns a list of known facts:
    - Always includes general facts about the user (contact=None)
    - Plus contact-specific facts, if a contact_id is given
    """
    entries = MemoryEntry.objects.filter(user_id=user_id, contact__isnull=True)

    if contact_id:
        entries = entries | MemoryEntry.objects.filter(user_id=user_id, contact_id=contact_id)

    return [entry.fact for entry in entries]