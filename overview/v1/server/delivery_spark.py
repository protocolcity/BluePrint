"""Delivery CI pass/fail spark — optional merge cadence.

Issue #152. Last-14-day GitHub check results and merges from the remote
activity cache. Unavailable is not a fake zero spark. Doors go to Delivery
CI/PR filters and out to the repo or failing check — not WorkLane triage,
For You Decide, or seat shifts.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from .throughput import parse_stamp

DAYS = 14
WINDOW = timedelta(days=DAYS)
CI_HREF = '/delivery?type=workflow'
MERGE_HREF = '/delivery?type=pull_request'
REPO_RE = re.compile(r'^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$')

PASS_STATES = frozenset({'success', 'completed'})
FAIL_STATES = frozenset({'failure', 'cancelled', 'timed_out', 'action_required', 'stale'})


def ci_href(repo: str = '') -> str:
    return f'{CI_HREF}&repo={repo}' if repo else CI_HREF


def merge_href(repo: str = '') -> str:
    return f'{MERGE_HREF}&repo={repo}' if repo else MERGE_HREF


def empty_ci_spark(state: str = 'empty', *, repo: str = '') -> dict:
    return {
        'days': [0] * DAYS,
        'fails': [0] * DAYS,
        'merges': [0] * DAYS,
        'checks': 0,
        'failures': 0,
        'merges_total': 0,
        'href': ci_href(repo),
        'merge_href': merge_href(repo),
        'out_href': '',
        'state': state,
    }


def workflow_tone(item: Any) -> str | None:
    """Pass or fail for a completed check. Pending is neither."""
    if not isinstance(item, dict) or item.get('kind') != 'workflow':
        return None
    state = str(item.get('state') or '').lower()
    if state in FAIL_STATES:
        return 'fail'
    if state in PASS_STATES:
        return 'pass'
    return None


def merge_stamp(item: Any):
    """UTC instant for a landed PR, else None."""
    if not isinstance(item, dict) or item.get('kind') != 'pull_request':
        return None
    if not (item.get('merged_at') or item.get('merged') or item.get('pr_event') == 'merged'):
        return None
    return parse_stamp(item.get('merged_at') or item.get('updated_at'))


def _weight(item: Any) -> int:
    try:
        count = int(item.get('count') or 1)
    except (TypeError, ValueError):
        return 1
    return count if count > 0 else 1


def _bucket(stamp: datetime, start: datetime, now: datetime) -> int | None:
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    else:
        stamp = stamp.astimezone(timezone.utc)
    if stamp < start or stamp > now:
        return None
    index = int((stamp - start).total_seconds() // 86400)
    return min(DAYS - 1, max(0, index))


def _github_out(repo: str) -> str:
    if repo and REPO_RE.fullmatch(repo):
        return f'https://github.com/{repo}/actions'
    return ''


def _out_href(items: list | None, repo: str = '') -> str:
    fail_url = ''
    check_url = ''
    pr_url = ''
    for item in items or []:
        if not isinstance(item, dict):
            continue
        url = str(item.get('url') or '')
        if not url:
            continue
        if item.get('kind') == 'workflow':
            if not check_url:
                check_url = url
            if not fail_url and workflow_tone(item) == 'fail':
                fail_url = url
        elif item.get('kind') == 'pull_request' and not pr_url:
            pr_url = url
    return fail_url or check_url or pr_url or _github_out(repo)


def build_ci_spark(items: list | None, now: datetime, *, readable: bool = True, repo: str = '') -> dict:
    """Bucket last-14d checks and merges. Unavailable is not a fake zero."""
    if not readable:
        return empty_ci_spark('unavailable', repo=repo)
    start = now - WINDOW
    days = [0] * DAYS
    fails = [0] * DAYS
    merges = [0] * DAYS
    checks = 0
    failures = 0
    merges_total = 0
    for item in items or []:
        if not isinstance(item, dict):
            continue
        tone = workflow_tone(item)
        if tone is not None:
            stamp = parse_stamp(item.get('updated_at'))
            if stamp is not None:
                index = _bucket(stamp, start, now)
                if index is not None:
                    weight = _weight(item)
                    days[index] += weight
                    checks += weight
                    if tone == 'fail':
                        fails[index] += weight
                        failures += weight
        stamp = merge_stamp(item)
        if stamp is not None:
            index = _bucket(stamp, start, now)
            if index is not None:
                merges[index] += 1
                merges_total += 1
    return {
        'days': days,
        'fails': fails,
        'merges': merges,
        'checks': checks,
        'failures': failures,
        'merges_total': merges_total,
        'href': ci_href(repo),
        'merge_href': merge_href(repo),
        'out_href': _out_href(items, repo) if (checks or merges_total) else '',
        'state': 'healthy' if (checks or merges_total) else 'empty',
    }


def spark_for_repo(repo: Any, now: datetime) -> dict:
    if not isinstance(repo, dict):
        return empty_ci_spark()
    name = str(repo.get('repo') or '')
    state = str(repo.get('state') or '')
    missing = repo.get('missing') or []
    if state in ('unavailable', 'invalid_config') or 'workflow' in missing:
        return empty_ci_spark('unavailable', repo=name)
    return build_ci_spark(repo.get('items') or [], now, repo=name)


def merge_ci_sparks(sparks: list | None, *, snapshot_state: str = '') -> dict:
    if snapshot_state == 'not_configured':
        return empty_ci_spark('not_configured')
    if snapshot_state in ('unavailable', 'invalid_config'):
        return empty_ci_spark('unavailable')
    rows = [spark for spark in (sparks or []) if isinstance(spark, dict)]
    readable = [spark for spark in rows if spark.get('state') != 'unavailable']
    if not readable:
        return empty_ci_spark('unavailable' if rows else 'empty')
    days = [0] * DAYS
    fails = [0] * DAYS
    merges = [0] * DAYS
    checks = 0
    failures = 0
    merges_total = 0
    fail_out = ''
    any_out = ''
    for spark in readable:
        spark_days = list(spark.get('days') or [])
        spark_fails = list(spark.get('fails') or [])
        spark_merges = list(spark.get('merges') or [])
        for index in range(DAYS):
            if index < len(spark_days):
                days[index] += int(spark_days[index] or 0)
            if index < len(spark_fails):
                fails[index] += int(spark_fails[index] or 0)
            if index < len(spark_merges):
                merges[index] += int(spark_merges[index] or 0)
        checks += int(spark.get('checks') or 0)
        failures += int(spark.get('failures') or 0)
        merges_total += int(spark.get('merges_total') or 0)
        out = str(spark.get('out_href') or '')
        if out and not any_out:
            any_out = out
        if out and spark.get('failures') and not fail_out:
            fail_out = out
    return {
        'days': days,
        'fails': fails,
        'merges': merges,
        'checks': checks,
        'failures': failures,
        'merges_total': merges_total,
        'href': CI_HREF,
        'merge_href': MERGE_HREF,
        'out_href': fail_out or any_out,
        'state': 'healthy' if (checks or merges_total) else 'empty',
    }


def attach_ci_sparks(payload: dict | None, now: datetime | None = None) -> dict:
    """Copy a remote-activity payload and hang honest CI sparks on it."""
    data = dict(payload or {})
    clock = now or datetime.now(timezone.utc)
    state = str(data.get('state') or '')
    repos = []
    sparks = []
    for repo in data.get('repositories') or []:
        row = dict(repo) if isinstance(repo, dict) else {}
        spark = spark_for_repo(row, clock)
        row['ci_spark'] = spark
        repos.append(row)
        sparks.append(spark)
    data['repositories'] = repos
    data['ci_spark'] = merge_ci_sparks(sparks, snapshot_state=state)
    return data
