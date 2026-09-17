"""Delivery last-14-day CI pass/fail spark stays a ledger door, not a dashboard."""
from datetime import datetime, timedelta, timezone
import unittest

from server.delivery_spark import (
    CI_HREF,
    DAYS,
    MERGE_HREF,
    attach_ci_sparks,
    build_ci_spark,
    empty_ci_spark,
    merge_ci_sparks,
    merge_stamp,
    spark_for_repo,
    workflow_tone,
)

NOW = datetime(2026, 9, 17, 15, 0, tzinfo=timezone.utc)


def iso(hours=0, days=0):
    return (NOW - timedelta(hours=hours, days=days)).isoformat().replace('+00:00', 'Z')


def workflow(state, *, hours=0, days=0, count=1, url='https://github.com/org/repo/actions/runs/1'):
    return {
        'kind': 'workflow',
        'state': state,
        'updated_at': iso(hours=hours, days=days),
        'count': count,
        'url': url,
        'workflow_name': 'CI',
    }


def pull(event='merged', *, hours=0, days=0, url='https://github.com/org/repo/pull/9'):
    stamp = iso(hours=hours, days=days)
    return {
        'kind': 'pull_request',
        'state': 'closed' if event != 'opened' else 'open',
        'pr_event': event,
        'merged': event == 'merged',
        'merged_at': stamp if event == 'merged' else None,
        'updated_at': stamp,
        'url': url,
        'number': 9,
    }


class DeliverySparkHelperTests(unittest.TestCase):
    def test_empty_is_zero_days_and_delivery_doors(self):
        empty = empty_ci_spark()
        self.assertEqual(empty['checks'], 0)
        self.assertEqual(empty['days'], [0] * DAYS)
        self.assertEqual(empty['fails'], [0] * DAYS)
        self.assertEqual(empty['merges'], [0] * DAYS)
        self.assertEqual(empty['href'], CI_HREF)
        self.assertEqual(empty['merge_href'], MERGE_HREF)
        self.assertEqual(empty['out_href'], '')
        self.assertEqual(empty['state'], 'empty')

    def test_unreadable_is_unavailable_not_a_fake_zero_spark(self):
        payload = build_ci_spark([workflow('success')], NOW, readable=False)
        self.assertEqual(payload['state'], 'unavailable')
        self.assertEqual(payload['checks'], 0)
        self.assertEqual(payload['days'], [0] * DAYS)
        self.assertEqual(payload['out_href'], '')

    def test_buckets_last_14_days_and_drops_older_or_future(self):
        items = [
            workflow('success', days=13, hours=12),
            workflow('failure', hours=2),
            workflow('success', days=15),
            workflow('failure', hours=-5),
        ]
        payload = build_ci_spark(items, NOW)
        self.assertEqual(payload['checks'], 2)
        self.assertEqual(payload['failures'], 1)
        self.assertEqual(payload['state'], 'healthy')
        self.assertEqual(payload['days'][0], 1)
        self.assertEqual(payload['days'][-1], 1)
        self.assertEqual(payload['fails'][-1], 1)
        self.assertEqual(sum(payload['days']), 2)

    def test_pending_is_neither_pass_nor_fail(self):
        items = [workflow('in_progress'), workflow('queued'), workflow('pending')]
        payload = build_ci_spark(items, NOW)
        self.assertEqual(payload['checks'], 0)
        self.assertEqual(payload['state'], 'empty')
        self.assertEqual(workflow_tone(workflow('in_progress')), None)
        self.assertEqual(workflow_tone(workflow('success')), 'pass')
        self.assertEqual(workflow_tone(workflow('cancelled')), 'fail')

    def test_collapsed_count_weights_one_bucket(self):
        payload = build_ci_spark([workflow('success', count=3)], NOW)
        self.assertEqual(payload['checks'], 3)
        self.assertEqual(sum(payload['days']), 3)

    def test_merge_cadence_is_optional_and_ignores_open_prs(self):
        items = [
            pull('merged', days=1),
            pull('opened', hours=2),
            pull('closed', hours=3),
        ]
        payload = build_ci_spark(items, NOW)
        self.assertEqual(payload['merges_total'], 1)
        self.assertEqual(payload['checks'], 0)
        self.assertEqual(payload['state'], 'healthy')
        self.assertIsNone(merge_stamp(pull('opened')))
        self.assertIsNotNone(merge_stamp(pull('merged')))

    def test_out_door_prefers_failing_check_then_repo_actions(self):
        fail = workflow('failure', url='https://github.com/org/repo/actions/runs/9')
        ok = workflow('success', days=1, url='https://github.com/org/repo/actions/runs/8')
        payload = build_ci_spark([ok, fail], NOW, repo='org/repo')
        self.assertEqual(payload['out_href'], 'https://github.com/org/repo/actions/runs/9')
        self.assertEqual(payload['href'], '/delivery?type=workflow&repo=org/repo')
        empty = build_ci_spark([], NOW, repo='org/repo')
        self.assertEqual(empty['out_href'], '')


class DeliverySparkAttachTests(unittest.TestCase):
    def test_repo_missing_workflow_is_unavailable(self):
        spark = spark_for_repo({
            'repo': 'org/repo',
            'state': 'partial',
            'missing': ['workflow'],
            'items': [workflow('success')],
        }, NOW)
        self.assertEqual(spark['state'], 'unavailable')
        self.assertEqual(spark['checks'], 0)

    def test_attach_keeps_not_configured_and_unavailable_honest(self):
        none = attach_ci_sparks({'state': 'not_configured', 'repositories': []}, NOW)
        self.assertEqual(none['ci_spark']['state'], 'not_configured')
        down = attach_ci_sparks({'state': 'unavailable', 'repositories': []}, NOW)
        self.assertEqual(down['ci_spark']['state'], 'unavailable')
        invalid = attach_ci_sparks({'state': 'invalid_config', 'repositories': []}, NOW)
        self.assertEqual(invalid['ci_spark']['state'], 'unavailable')

    def test_attach_aggregates_readable_repos_and_skips_unavailable(self):
        payload = attach_ci_sparks({
            'state': 'partial',
            'repositories': [
                {'repo': 'org/a', 'state': 'connected', 'items': [workflow('success'), pull('merged', days=2)]},
                {'repo': 'org/b', 'state': 'unavailable', 'items': [workflow('failure')]},
            ],
        }, NOW)
        self.assertEqual(payload['ci_spark']['checks'], 1)
        self.assertEqual(payload['ci_spark']['failures'], 0)
        self.assertEqual(payload['ci_spark']['merges_total'], 1)
        self.assertEqual(payload['ci_spark']['state'], 'healthy')
        self.assertEqual(payload['repositories'][0]['ci_spark']['state'], 'healthy')
        self.assertEqual(payload['repositories'][1]['ci_spark']['state'], 'unavailable')

    def test_merge_of_empty_readable_repos_stays_empty(self):
        merged = merge_ci_sparks([empty_ci_spark(), empty_ci_spark()], snapshot_state='connected')
        self.assertEqual(merged['state'], 'empty')
        self.assertEqual(merged['checks'], 0)


if __name__ == '__main__':
    unittest.main()
