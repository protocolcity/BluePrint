"""Bounded local operations reports, scheduled by WorkForce.

These deterministic checks do not dispatch agents or alter project work orders.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

JOBS = {'chief-of-staff': 'Daily operations brief', 'health-patrol': 'Operations health check',
        'workspace-efficiency': 'Workspace efficiency check'}


def run_job(root, job):
    root = Path(root).resolve()
    stamp = datetime.now(timezone.utc).isoformat()
    command = [sys.executable, '-m', 'protocolcity.open_work_audit', '--json', '--feeds',
               '--process', '--url', 'http://127.0.0.1:8799/api/scene',
               '--roster', str(root / '.protocolcity/workforce/local/roster.json')]
    if job != 'health-patrol': command.extend(['--history', '--decay'])
    env = dict(os.environ, WORKSPACE_ROOT=str(root))
    try:
        result = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True, timeout=90)
        audit = json.loads(result.stdout)
        if result.returncode or not audit.get('reachable'):
            raise ValueError('WorkLane audit unavailable')
        summary = '{} open work orders · {} ready · {} in progress/review'.format(
            audit['total_open'], audit['total_ready'], audit['total_in_motion'])
        state = 'completed'
        detail = 'Read-only audit completed. Work-order status does not prove agent activity.'
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired) as exc:
        audit = {}; state = 'failed'; summary = 'Operations check failed'; detail = str(exc)
    receipt = dict(job=job, title=JOBS[job], observed_at=stamp, state=state,
                   summary=summary, detail=detail, mode='deterministic report', audit=audit)
    directory = root / '.blueprint/job-reports'
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / (job + '.json')
    pending = target.with_suffix('.pending')
    pending.write_text(json.dumps(receipt, indent=2) + '\n'); pending.replace(target)
    reports = root / '.protocolcity/ops/reports' / job
    reports.mkdir(parents=True, exist_ok=True)
    day = datetime.now().astimezone().date().isoformat()
    text = '# {} · {}\n\n{}\n\n{}\n\n'.format(JOBS[job], day, summary, detail)
    text += 'This scheduled script reports evidence. It does not plan, route, claim, close, or implement work. Remote agent coverage must be connected separately.\n\n'
    text += '```json\n' + json.dumps(audit, indent=2) + '\n```\n'
    (reports / (day + '-automated.md')).write_text(text)
    print('{}: {} · {}'.format(job, state, summary))
    return 0 if state == 'completed' else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True, type=Path)
    parser.add_argument('--job', required=True, choices=sorted(JOBS))
    args = parser.parse_args()
    if not args.workspace.is_dir(): parser.error('Workspace does not exist')
    return run_job(args.workspace, args.job)


if __name__ == '__main__':
    raise SystemExit(main())
