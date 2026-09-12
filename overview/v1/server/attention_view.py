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
