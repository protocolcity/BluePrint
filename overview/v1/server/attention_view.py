"""Human attention presentation over durable work; never changes eligibility."""
from datetime import datetime, timezone


def face(order, labels, now):
    gate = order.get('gate_type') or ''
    note = str(order.get('gate_note') or '').strip().lower()
    if gate in ('deferred', 'tracking'):
        return ''
    parked = note.startswith(('deferred:', 'umbrella')) or any(
        text in note for text in ('post-northstar', 'not claimable', 'withheld from ready', 'thaw when', 'parked:', 'far future'))
    if gate == 'human' and parked:
        return ''
    if any(label == 'inbox-report' or label.startswith('inbox-report:') for label in labels if isinstance(label,str)):
        return 'read'
    if gate == 'human' or 'gate:human' in labels or 'needs:founder-decision' in labels:
        return 'decide'
    if any(isinstance(label,str) and label.startswith('reminder:') for label in labels):
        return 'note'
    if gate == 'timer':
        return 'watch'
    if order.get('status') in ('in_progress','in_review'):
        try:
            updated = datetime.fromisoformat(str(order.get('updated_at')).replace('Z','+00:00'))
            if updated.tzinfo and (now-updated).total_seconds() >= 90*60:
                return 'watch'
        except (ValueError,TypeError):
            pass
    if any(label in labels for label in ('you:note','you:todo','you:remind')):
        return 'note'
    return ''


def _duration_words(seconds):
    minutes = max(0, int(seconds // 60))
    hours, minutes = divmod(minutes, 60)
    if hours and minutes:
        return f'{hours}h {minutes}m'
    if hours:
        return f'{hours}h'
    return f'{minutes}m'


def face_reason(order, labels, computed_face, now):
    """Name the rule that produced ``computed_face`` (STATES_AND_TERMS.md §1.4).

    Presentation only — never changes which face is computed.
    """
    if computed_face == 'decide':
        note = str(order.get('gate_note') or '').strip()
        if order.get('gate_type') == 'human' and note:
            return note
        return 'A decision is needed to move this forward'
    if computed_face == 'read':
        return 'A report was written for you'
    if computed_face == 'watch':
        if order.get('gate_type') == 'timer':
            return 'Held by a timer gate'
        try:
            updated = datetime.fromisoformat(str(order.get('updated_at')).replace('Z', '+00:00'))
        except (ValueError, TypeError):
            updated = None
        if updated and updated.tzinfo:
            return f'No update for {_duration_words((now - updated).total_seconds())}'
        return 'No recent update'
    if computed_face == 'note':
        reminder = next((label for label in labels if isinstance(label, str) and label.startswith('reminder:')), None)
        if reminder:
            return 'Reminder set for ' + reminder.split(':', 1)[1]
        return 'Your own note'
    return ''
