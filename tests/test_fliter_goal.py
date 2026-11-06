from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from artifact_support import ensure_artifacts
from baseintent.benchmark_catalog import get_backend, get_suite
from experiments.common.injection_filter import benchmark_header, load_fliter
from experiments import run_partial_benchmark as runner
import serial_fixture


class FliterGoalTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(dir=ensure_artifacts('test_fliter_goal'))
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.backend = get_backend()
        self.suite = 'banking' if self.backend.id == 'agentdojo' else 'shopping'
        self.ids = list(get_suite('v1.2', self.suite).injection_tasks)[:3]
        self.path = self.root / 'fliter.json'
        self.payload = dict(schema_version='dscg.fliter.v1', benchmark=benchmark_header(),
                            excluded={self.suite: [self.ids[0]]})
        self.path.write_text(json.dumps(self.payload))

    def test_duplicate_ids_rejected(self):
        self.payload['excluded'][self.suite] *= 2
        self.path.write_text(json.dumps(self.payload))
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            load_fliter(self.path)

    def test_score_only_and_shared_goal_resume(self):
        direct = []

        def execute(suite, pipeline, task, injection_task=None, injections=None):
            if task.ID in self.ids:
                direct.append(task.ID)
            return serial_fixture.execute(suite, pipeline, task, injection_task, injections)

        options = dict(origin=True, suites=[self.suite], attack=['ignore_previous', 'important_instructions'],
                       results_dir=self.root, fliter_path=self.path)
        with serial_fixture.patched(execute_fn=execute), redirect_stdout(StringIO()):
            self.assertEqual(runner.main(**options, run_name='score'), 0)
            self.assertEqual(direct, [])
            self.assertEqual(runner.main(**options, run_name='goal', goal=True), 0)
            self.assertEqual(direct, self.ids[1:])
            self.assertEqual(runner.main(**options, run_name='goal', goal=True, reuse=True), 0)
            self.assertEqual(direct, self.ids[1:])
        summary = self.root / self.backend.id / 'offline-model_goal' / 'summary.json'
        groups = json.loads(summary.read_text())['selection_report']['groups']
        self.assertTrue(all(group['retained'] == self.ids[1:] for group in groups))
        from experiments import run_injection_precheck as precheck
        task = get_suite('v1.2', self.suite).get_injection_task_by_id(self.ids[1])
        reused, rejected = precheck._reuse(summary.parent, self.suite, task,
                                          precheck._binding(serial_fixture.MAIN, [self.suite]))
        self.assertEqual(rejected, [])
        self.assertEqual([record['status'] for record in reused], ['pass'])


    def test_all_excluded_and_retired_entry(self):
        self.payload['excluded'][self.suite] = self.ids
        self.path.write_text(json.dumps(self.payload))
        with serial_fixture.patched(), redirect_stdout(StringIO()):
            self.assertEqual(runner.main(origin=True, suites=[self.suite], attack='ignore_previous',
                run_name='empty', results_dir=self.root, fliter_path=self.path), 0)
        base = self.root / self.backend.id / 'offline-model_empty'
        self.assertIn('NO_ELIGIBLE_TARGETS', (base / 'summary.md').read_text())
        self.assertFalse(list(base.rglob('none.json')))
        with self.assertRaisesRegex(ValueError, 'use --fliter'):
            runner.main(cohort_path=self.path)
        with self.assertRaisesRegex(ValueError, 'clean'):
            runner.main(run_attack=False, goal=True)

    def test_interrupted_goal_is_not_reexecuted(self):
        calls = []

        def execute(suite, pipeline, task, injection_task=None, injections=None):
            if task.ID in self.ids:
                calls.append(task.ID)
                if len(calls) == 1:
                    raise KeyboardInterrupt
            return serial_fixture.execute(suite, pipeline, task, injection_task, injections)

        options = dict(origin=True, suites=[self.suite], attack='ignore_previous',
                       run_name='interrupted', results_dir=self.root, fliter_path=self.path, goal=True)
        with serial_fixture.patched(execute_fn=execute), redirect_stdout(StringIO()):
            self.assertEqual(runner.main(**options), 130)
            self.assertEqual(runner.main(**options, reuse=True), 1)
        self.assertEqual(calls, self.ids[1:])
        summary = self.root / self.backend.id / 'offline-model_interrupted' / 'summary.json'
        checks = json.loads(summary.read_text())['selection_report']['goal_checks']
        self.assertEqual([check['status'] for check in checks], ['error', 'pass'])

    def test_screen_emits_failed_and_errored_targets_once(self):
        from unittest.mock import patch
        from experiments import run_injection_precheck as precheck
        calls = []

        def execute(suite, pipeline, task, injection_task=None, injections=None):
            calls.append(task.ID)
            utility, security = serial_fixture.execute(suite, pipeline, task, injection_task, injections)
            if task.ID == self.ids[1]:
                raise RuntimeError('offline fixture')
            return utility and task.ID != self.ids[0], security

        with serial_fixture.patched(execute_fn=execute), redirect_stdout(StringIO()), patch.object(
                precheck, 'resolve_model_config', return_value=serial_fixture.MAIN), patch.object(
                precheck, 'make_openai_compatible_pipeline', side_effect=serial_fixture.baseline):
            options = dict(suites=[self.suite], config_path=None, run_name='screen', results_dir=self.root)
            self.assertEqual(precheck.screen(**options), 1)
            self.assertEqual(precheck.screen(**options), 1)
        self.assertEqual(calls, list(get_suite('v1.2', self.suite).injection_tasks))
        path = self.root / self.backend.id / 'offline-model_screen' / 'fliter.json'
        self.assertEqual(load_fliter(path)['excluded'][self.suite], sorted(self.ids[:2]))
