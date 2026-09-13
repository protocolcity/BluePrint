"""Configured staffing coverage; never an execution or liveness assertion."""
from collections import Counter
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs

CATEGORIES = ('you', 'unassigned', 'unknown_or_retired', 'manual', 'scheduled',
              'outside_lane_scope', 'unknown_dispatch', 'ambiguous_assignment', 'roster_unknown')
NOTE = ('Configured lanes do not prove execution, authentication or liveness. '
        'Manual lanes require explicit dispatch. You assignments may be intentional.')


def coverage(tasks, workers, *, feed_error='', roster_error='', roster_path='', desk_urls=None):
    counts = Counter({key: 0 for key in CATEGORIES})
    examples = {key: [] for key in CATEGORIES}
    for project, rows in tasks.items():
        for task in rows:
            labels = task.get('labels') or []
            seats = {str(x)[7:] for x in labels if str(x).startswith('worker:') and str(x)[7:]}
            category = 'unassigned'
            if len(seats) > 1:
                category = 'ambiguous_assignment'
            elif seats:
                seat = next(iter(seats))
                row = workers.get(seat)
                if seat == 'you':
                    category = 'you'
                elif roster_error:
                    category = 'roster_unknown'
                elif not row or row.get('enabled') is False or row.get('retired') or row.get('kind', 'lane') != 'lane':
                    category = 'unknown_or_retired'
                else:
                    url = urlparse(str(row.get('queue_url') or ''))
                    query = parse_qs(url.query)
                    projects = query.get('project') or query.get('product') or []
                    required = query.get('label') or []
                    if (url.scheme not in ('http', 'https') or not url.netloc
                            or not url.path.endswith('/api/admin/tasks/ready')
                            or (desk_urls is not None and url.netloc != urlparse(desk_urls.get(project, '')).netloc)
                            or projects != [project] or 'worker:' + seat not in required
                            or not set(required).issubset(labels)):
                        category = 'outside_lane_scope'
                    else:
                        schedule = str(row.get('schedule') or '').strip()
                        category = ('manual' if schedule == 'manual' else
                                    'scheduled' if len(schedule.split()) == 5 else 'unknown_dispatch')
            counts[category] += 1
            if len(examples[category]) < 8:
                examples[category].append({'project': project, 'id': task.get('ext_id') or task.get('id')})
    observed = dict(counts)
    incomplete = bool(feed_error or roster_error)
    lane_count = counts['manual'] + counts['scheduled']
    return {'state': 'unknown' if incomplete else 'available',
            'observed_at': datetime.now(timezone.utc).isoformat(),
            'feed': {'state': 'unavailable' if feed_error else 'available', 'error': feed_error},
            'roster': {'state': 'unavailable' if roster_error else 'available', 'path': roster_path, 'error': roster_error},
            'counts': {key: None for key in CATEGORIES} if feed_error else
                      {key: (None if roster_error and key not in ('you', 'unassigned', 'ambiguous_assignment', 'roster_unknown') else value) for key, value in observed.items()},
            'observed_counts': observed, 'examples': examples,
            'total_ready': None if feed_error else sum(counts.values()),
            'configured_lane_ready': None if incomplete else lane_count,
            'has_configured_lane_coverage': None if incomplete else lane_count > 0,
            'execution_state': 'unknown', 'note': NOTE}


def coverage_text(value):
    show = lambda x: 'unknown' if x is None else str(x)
    return ('Ready staffing: ' + ' · '.join(key + '=' + show(value['counts'].get(key)) for key in CATEGORIES)
            + '. Configured lane coverage: ' + show(value.get('has_configured_lane_coverage'))
            + '. ' + NOTE)


def snapshot_process(task_data, workers, roster_path, error=''):
    """Read queue configuration and saved readiness without probing other hosts."""
    from protocolcity.open_work_audit import _queue_url_shape
    lanes = []
    for worker, row in sorted(workers.items()):
        if row.get('kind', 'lane') != 'lane':
            continue
        url = str(row.get('queue_url') or '')
        project, findings = _queue_url_shape(worker, url)
        data = task_data.get(project)
        if error or data is None:
            findings.append(error or 'Project readiness unavailable')
            ready_n = deferred_n = None
        else:
            labels = parse_qs(urlparse(url).query).get('label', [])
            ready_n = sum(set(labels).issubset(t.get('labels') or []) for t in data['ready'])
            deferred_n = sum(t.get('status') == 'backlog' and t.get('gate_type') == 'deferred'
                             and 'worker:' + worker in (t.get('labels') or []) for t in data['all'])
            if ready_n == 0 and deferred_n:
                findings.append('Empty ready feed with deferred work; inspect gate, do not auto-thaw')
        lanes.append(dict(worker=worker, product=project, schedule=row.get('schedule'), queue_url=url,
                          ready_n=ready_n, deferred_n=deferred_n, findings=findings))
    issue_n = sum(bool(lane['findings']) for lane in lanes)
    return dict(ok=not error and not issue_n, roster=roster_path, lane_n=len(lanes),
                issue_lane_n=issue_n, lanes=lanes, error=error,
                hint='Saved readiness and queue configuration only; transport and execution are unverified.')
