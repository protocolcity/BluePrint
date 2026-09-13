"""Human attention presentation over durable work; never changes eligibility."""
from datetime import date, datetime, timezone


def _due_candidates(labels):
    """(date, kind_word, raw_date_text) for every reminder:/deadline: label,
    earliest first. Kind_word names which label produced the date, since a
    reminder: and a deadline: can both be present and disagree (review
    finding, pc-1494)."""
    candidates = []
    for label in labels:
        if not isinstance(label, str):
            continue
        for prefix, word in (('reminder:', 'Reminder'), ('deadline:', 'Deadline')):
            if label.startswith(prefix):
                raw = label[len(prefix):].strip()
                try:
                    parsed = date.fromisoformat(raw)
                except ValueError:
                    break
                candidates.append((parsed, word, raw))
                break
    candidates.sort(key=lambda c: c[0])
    return candidates


def local_today(now):
    """The host's local calendar day for a Due comparison (pc-1494 review:
    a UTC-only comparison reads tomorrow's reminder as due after ~19:00
    Chicago). ``now`` is a UTC-aware instant; converting with the bare
    ``astimezone()`` uses the host's local timezone, stdlib only."""
    return now.astimezone().date()


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
    due_candidates = _due_candidates(labels)
    if due_candidates and due_candidates[0][0] <= local_today(now):
        return 'due'
    if gate == 'timer':
        return 'watch'
    if order.get('status') in ('in_progress', 'in_review'):
        # PROTOCOL 7a: a seat's parked handoff is the integrator's queue, not
        # a person's attention (pc-1494 review) — only a live order, or one
        # parked by You (no registered-seat parker), earns Watch.
        if order.get('status') == 'in_review' and order.get('parked_by_seat'):
            return ''
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
    if any(isinstance(label, str) and (label.startswith('reminder:') or label.startswith('deadline:')) for label in labels):
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
        due_candidates = _due_candidates(labels)
        if due_candidates:
            _, word, raw = due_candidates[0]
            return f'{word} due {raw}'
        return 'Due'
    return ''
