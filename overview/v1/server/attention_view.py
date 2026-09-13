"""Human attention presentation over durable work; never changes eligibility."""
from datetime import date, datetime, timezone


def _dated_label(labels, prefix):
    """The date carried by the first ``prefix``-tagged label, or ``None``."""
    for label in labels:
        if isinstance(label, str) and label.startswith(prefix):
            try:
                return date.fromisoformat(label[len(prefix):].strip())
            except ValueError:
                return None
    return None


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
    due = _dated_label(labels, 'reminder:') or _dated_label(labels, 'deadline:')
    if due and due <= now.date():
        return 'due'
    if gate == 'timer':
        return 'watch'
    if order.get('status') in ('in_progress','in_review'):
        try:
            updated = datetime.fromisoformat(str(order.get('updated_at')).replace('Z','+00:00'))
            if updated.tzinfo and (now-updated).total_seconds() >= 90*60:
                return 'watch'
        except (ValueError,TypeError):
            pass
    return ''


def _duration_words(seconds):
    minutes = max(0, int(seconds // 60))
    hours, minutes = divmod(minutes, 60)
    if hours and minutes:
        return f'{hours}h {minutes}m'
    if hours:
        return f'{hours}h'
    return f'{minutes}m'


def kind_of(order, labels):
    """Item-type axis (STATES_AND_TERMS.md §5): work, todo, note, reminder, report."""
    if any(isinstance(label, str) and (label == 'inbox-report' or label.startswith('inbox-report:')) for label in labels):
        return 'report'
    if any(isinstance(label, str) and label.startswith('reminder:') for label in labels):
        return 'reminder'
    if 'you:todo' in labels or 'you:remind' in labels:
        return 'todo'
    if 'you:note' in labels:
        return 'note'
    return 'work'


def persona_text(order, labels):
    """Kind chip text for personal items and dated reminders; '' when none apply.

    `you:remind` has no date of its own (a legacy alias, STATES_AND_TERMS.md
    §6): with a `reminder:<date>` label it adds nothing, without one it reads
    as an undated todo, never "Reminder (no date)".
    """
    reminder = next((label for label in labels if isinstance(label, str) and label.startswith('reminder:')), None)
    if reminder:
        return 'Reminder ' + reminder.split(':', 1)[1]
    if 'you:todo' in labels or 'you:remind' in labels:
        return 'Your todo'
    if 'you:note' in labels:
        return 'Your note'
    return ''


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
    if computed_face == 'due':
        reminder = next((label for label in labels if isinstance(label, str) and label.startswith('reminder:')), None)
        if reminder:
            return 'Reminder due ' + reminder.split(':', 1)[1]
        deadline = next((label for label in labels if isinstance(label, str) and label.startswith('deadline:')), None)
        if deadline:
            return 'Deadline due ' + deadline.split(':', 1)[1]
        return 'Due'
    return ''
