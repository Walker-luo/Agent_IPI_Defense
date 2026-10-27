import unittest
from dashboard.app import _normalize_history_suite


class HistoryOverviewTests(unittest.TestCase):
    def test_preserves_explicit_counts_and_missing_usage(self):
        result = _normalize_history_suite({
            'task_counts': {'utility_passed': 2, 'utility_valid': 3, 'attack_successes': 1, 'security_valid': 3},
            'overhead': {'total_tokens': 100},
        }, 'travel', False)['overview']
        self.assertEqual(result['tsr'], {'success': 2, 'valid': 3})
        self.assertEqual(result['asr'], {'success': 1, 'valid': 3})
        self.assertEqual(result['tokens'], {'recorded': 100, 'complete': False})

    def test_does_not_infer_missing_denominators_or_usage(self):
        result = _normalize_history_suite({'task_counts': {'total_tasks': 9}, 'metrics': {'attack_success_rate': 0}}, 'travel', False)['overview']
        self.assertIsNone(result['tsr'])
        self.assertIsNone(result['asr'])
        self.assertIsNone(result['tokens']['recorded'])

    def test_complete_task_records_can_supply_counts_without_guessing(self):
        from dashboard.app import _history_overview_from_records
        suite = {'task_counts': {'total_tasks': 2}, 'metrics': {'attack_success_rate': 50.0},
                 'overview': {'asr': None, 'tsr': None}}
        records = [
            {'user_task_id': 'a', 'injection_task_id': 'x', 'model_id': 'm', 'sample_status': 'valid', 'attack_success': True},
            {'user_task_id': 'b', 'injection_task_id': 'x', 'model_id': 'm', 'sample_status': 'unknown', 'attack_success': False},
        ]
        _history_overview_from_records(suite, records, False)
        self.assertEqual(suite['overview']['asr'], {'success': 1, 'valid': 2, 'source': 'records_unknown'})
        suite['overview']['asr'] = None
        _history_overview_from_records(suite, records, True)
        self.assertIsNone(suite['overview']['asr'])
        suite['metrics']['attack_success_rate'] = 0
        _history_overview_from_records(suite, records, False)
        self.assertIsNone(suite['overview']['asr'])
