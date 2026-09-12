"""Explicit local dispatch through the selected workspace's WorkForce daemon."""
import json
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .local_projectors import resolve_daemon_path, resolve_roster_path
from .operations import age_seconds, read_json
from datetime import datetime, timezone


def _request(url, data=None):
    request = Request(url, data=data, headers={'Content-Type': 'application/json'})
    try:
        with urlopen(request, timeout=5) as response:
            return json.load(response)
    except HTTPError as exc:
        if exc.code == 409:
            try:
                payload = json.loads(exc.read(4096))
                reason = payload.get('msg') if isinstance(payload, dict) else None
            except (ValueError, OSError):
                reason = None
            if reason == 'queue empty':
                raise RuntimeError('No assigned work is ready to run. Check assigned work for review, completion or gates.') from exc
            if isinstance(reason, str) and reason.strip():
                raise RuntimeError('WorkForce did not start this run: ' + reason[:300]) from exc
        raise RuntimeError('WorkForce declined dispatch. Refresh to see its current state.') from exc
    except (URLError, TimeoutError, ValueError) as exc:
        raise RuntimeError('WorkForce did not confirm the request. Refresh before retrying.') from exc


def dispatch_agent(binder, identity):
    if not binder or not isinstance(identity, str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,79}', identity):
        raise ValueError('A workspace and registered worker are required.')
    root = Path(binder).resolve()
    roster_path = resolve_roster_path(root)
    roster = read_json(roster_path, root) or {}
    row = roster.get('workers', {}).get(identity)
    if not isinstance(row, dict) or not row.get('command') or row.get('enabled') is False:
        raise ValueError('This worker is unavailable for dispatch.')
    daemon_path = resolve_daemon_path(root)
    heartbeat = read_json(daemon_path, root) or {}
    age = age_seconds(heartbeat.get('last_tick'), datetime.now(timezone.utc))
    if age is None or age > 120:
        raise RuntimeError('WorkForce heartbeat is unavailable or stale.')
    if identity in heartbeat.get('in_flight', []):
        raise RuntimeError('This worker already has a run in progress.')
    receipt = read_json(root / 'local/workforce/deployment.json', root) or {}
    origin = receipt.get('api_origin', '')
    parsed = urlparse(origin)
    if parsed.scheme != 'http' or parsed.hostname not in ('localhost', '127.0.0.1') or parsed.username or parsed.password or parsed.path not in ('', '/') or parsed.query or parsed.fragment:
        raise RuntimeError('A verified local WorkForce connection is required.')
    live = _request(origin.rstrip('/') + '/api/workers')
    engine = live.get('engine', {})
    if engine.get('pid') != heartbeat.get('pid') or Path(engine.get('local_root') or '/').resolve() != daemon_path.resolve().parent:
        raise RuntimeError('WorkForce serves a different workspace or process. Refresh the connection.')
    registered = next((w for w in live.get('workers', []) if w.get('name') == identity), None)
    if not registered or registered.get('identity') != row.get('identity', identity):
        raise RuntimeError('WorkForce worker identity does not match this workspace.')
    result = _request(origin.rstrip('/') + '/api/dispatch/' + identity, data=b'{}')
    if not result.get('ok'):
        raise RuntimeError(result.get('msg') or 'WorkForce declined dispatch.')
    return {'ok': True, 'message': result.get('msg') or 'Dispatch accepted.'}
