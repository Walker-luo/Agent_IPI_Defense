"""Offline wiring regression using only canned replies and an in-memory runtime."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import yaml

from agentdojo.functions_runtime import FunctionCall, FunctionsRuntime
from dscg.model_config import ModelConfig
from dscg.pipelines import defended
from experiments import run_partial_benchmark

REQUEST = 'Record PLACEHOLDER_ALPHA in the simulated list.'
CONFIG = ModelConfig(model_id='fixture', api_key='fixture', base_url='https://offline.invalid', provider='custom')
WRITE = dict(effect='write', source='local', sink='none', sensitivity='internal',
             idempotent=False, reversible=True)
READ = dict(effect='read', source='local', sink='none', sensitivity='internal',
            idempotent=True, reversible=False)


def reply(payload):
    return SimpleNamespace(choices=[SimpleNamespace(
        message=SimpleNamespace(content=json.dumps(payload), refusal=None), finish_reason='stop')],
        usage=None)


class L3SwitchTests(unittest.TestCase):
    def run_fixture(self, checker, tool, verdict=None, *, batches=None, read_text='PLACEHOLDER_NEUTRAL'):
        effects = []
        runtime = FunctionsRuntime()

        @runtime.register_function
        def record_placeholder(label: str) -> str:
            """Record a placeholder.

            Args:
                label: The placeholder label.
            """
            effects.append(label)
            return 'recorded'

        @runtime.register_function
        def record_other_placeholder(label: str) -> str:
            """Record a placeholder in another list.

            Args:
                label: The placeholder label.
            """
            effects.append(label)
            return 'recorded'

        @runtime.register_function
        def read_placeholder() -> str:
            """Read a neutral test marker."""
            return read_text

        main, audit = Mock(), Mock()
        main.chat.completions.create.side_effect = [
            reply({'tasks': [{'intent': 'Record placeholder', 'anchor_id': 'r1',
                              'relation': {'kind': 'independent'}}]}),
            reply({'tool_permissions': {'record_placeholder': True, 'record_other_placeholder': False}}),
        ]
        audit.chat.completions.create.side_effect = (
            [reply(verdict)] if verdict is not None else AssertionError('unexpected audit'))
        metadata = dict(record_placeholder=WRITE, record_other_placeholder=WRITE, read_placeholder=READ)
        cli_flags = ['--audit-router-mode', 'off', '--prompt-profile', 'static-task-v354']
        if not checker:
            cli_flags.append('--no-checker')
        with patch.object(run_partial_benchmark, 'main', return_value=0) as run:
            self.assertEqual(run_partial_benchmark.cli(cli_flags), 0)
        options = run.call_args.kwargs
        self.assertTrue(options['use_sandbox'])
        self.assertIs(options['use_security_checker'], checker)
        with patch.object(defended, 'create_openai_client', side_effect=[main, audit] if checker else [main]):
            pipeline, _, security_tracker = defended.make_defended_pipeline(
                model_config=CONFIG, sec_model_config=CONFIG, tool_metadata=metadata,
                use_security_checker=options['use_security_checker'],
                use_sandbox=options['use_sandbox'], audit_router_mode=options['audit_router_mode'],
                l1_projection_mode=options['l1_projection_mode'], prompt_profile=options['prompt_profile'])
        self.assertEqual(security_tracker is not None, checker)
        self.assertIs(pipeline.dscg_optimization_config['use_security_checker'], checker)
        self.assertTrue(pipeline.dscg_optimization_config['input_isolation'])
        self.assertTrue(pipeline.dscg_optimization_config['authorization_precheck'])
        self.assertEqual(pipeline.dscg_optimization_config['audit_router_mode'], 'off')
        if batches is None:
            args = {} if tool == 'read_placeholder' else {'label': 'PLACEHOLDER_ALPHA'}
            batches = [[FunctionCall(function=tool, args=args, id='candidate-1')]]
        planner = Mock()

        def plan(query, runtime, env, messages, extra_args):
            index = planner.query.call_count - 1
            tool_calls = batches[index] if index < len(batches) else []
            response = {'role': 'assistant', 'content': [], 'tool_calls': tool_calls}
            return query, runtime, env, [*messages, response], extra_args

        planner.query.side_effect = plan
        pipeline.task_executor.llm = planner
        _, _, _, messages, diagnostics = pipeline.query(REQUEST, runtime)
        self.assertEqual(main.chat.completions.create.call_count, 2)
        self.assertEqual(set(diagnostics['dscg_authorizations'][-1]['allowed_tools']),
                         {'record_placeholder', 'read_placeholder'})
        self.assertEqual(len(diagnostics['dscg_action_ledger']), sum(map(len, batches)))
        return effects, audit.chat.completions.create.call_count, messages, diagnostics

    def test_two_step_multiline_placeholder_pair(self):
        read_text = "label: PLACEHOLDER_ALPHA\nnote: 'neutral fixture'\n"
        parsed_text = yaml.safe_load(yaml.safe_dump({'text': read_text}))['text']
        self.assertEqual(parsed_text, read_text)
        ledger_keys = set()
        for decision, label, reason in (
            ('allow', 'PLACEHOLDER_ALPHA', 'ALIGNED'),
            ('deny', 'PLACEHOLDER_BETA', 'OFF_TASK_ACTION'),
        ):
            for checker in (True, False):
                with self.subTest(decision=decision, checker=checker):
                    read = FunctionCall(function='read_placeholder', args={}, id='read-1')
                    write = FunctionCall(function='record_placeholder', args={'label': label}, id='write-1')
                    verdict = dict(decision=decision, confidence=0.9, reason_code=reason,
                                   violations=[] if decision == 'allow' else [reason])
                    effects, calls, messages, diagnostics = self.run_fixture(
                        checker, None, verdict if checker else None, batches=[[read], [write]], read_text=parsed_text)
                    ledger = diagnostics['dscg_action_ledger']
                    self.assertEqual([(a['call_id'], a['state']) for a in ledger],
                                     [('read-1', 'executed'),
                                      ('write-1', 'blocked' if checker and decision == 'deny' else 'executed')])
                    self.assertEqual(diagnostics['dscg_layer_routing']['precheck_allowed_batches'], 2)
                    result = next(m for m in messages if m['role'] == 'tool' and m['tool_call_id'] == 'read-1')
                    self.assertEqual(result['content'][0]['content'], read_text)
                    self.assertEqual(calls, int(checker))
                    self.assertEqual(effects, [] if checker and decision == 'deny' else [label])
                    ledger_keys.add((decision, checker))
        self.assertEqual(ledger_keys, {('allow', True), ('allow', False), ('deny', True), ('deny', False)})

    def test_mixed_batch_only_blocks_the_nonexempt_write(self):
        read = FunctionCall(function='read_placeholder', args={}, id='read-1')
        write = FunctionCall(function='record_placeholder', args={'label': 'PLACEHOLDER_BETA'}, id='write-1')
        verdict = dict(decision='deny', violations=['OFF_TASK_ACTION'],
                       confidence=0.9, reason_code='OFF_TASK_ACTION')
        for checker in (True, False):
            with self.subTest(checker=checker):
                effects, calls, _, diagnostics = self.run_fixture(
                    checker, None, verdict if checker else None, batches=[[read, write]])
                self.assertEqual((effects, calls), (([], 1) if checker else (['PLACEHOLDER_BETA'], 0)))
                self.assertEqual([(a['call_id'], a['state']) for a in diagnostics['dscg_action_ledger']],
                                 [('read-1', 'executed'), ('write-1', 'blocked' if checker else 'executed')])
                if checker:
                    self.assertEqual(diagnostics['dscg_audit_decisions'][-1]['approved_actions'], 1)
                    self.assertEqual(diagnostics['dscg_audit_decisions'][-1]['blocked_actions'], 1)

    def test_missing_prior_evidence_abstain_blocks_the_write(self):
        verdict = dict(decision='abstain', violations=['MISSING_EVIDENCE'],
                       confidence=0.5, reason_code='MISSING_EVIDENCE')
        effects, calls, messages, diagnostics = self.run_fixture(True, 'record_placeholder', verdict)
        self.assertEqual((effects, calls), ([], 1))
        self.assertFalse(any(m['role'] == 'tool' and m.get('tool_call_id') == 'read-1' for m in messages))
        self.assertEqual(diagnostics['dscg_audit_decisions'][-1]['reason_code'], 'MISSING_EVIDENCE')
        self.assertEqual(diagnostics['dscg_audit_decisions'][-1]['final_reason_code'], 'AUDIT_ABSTAIN')
        self.assertEqual(diagnostics['dscg_action_ledger'][0]['state'], 'blocked')

    def test_l3_deny_changes_the_effect_for_the_same_valid_candidate(self):
        verdict = dict(decision='deny', violations=['OFF_TASK_ACTION'],
                       confidence=0.9, reason_code='OFF_TASK_ACTION')
        full = self.run_fixture(True, 'record_placeholder', verdict)
        no_l3 = self.run_fixture(False, 'record_placeholder')
        self.assertEqual((full[0], full[1]), ([], 1))
        self.assertEqual((no_l3[0], no_l3[1]), (['PLACEHOLDER_ALPHA'], 0))
        self.assertEqual(full[3]['dscg_layer_routing']['precheck_allowed_batches'], 1)
        self.assertEqual(no_l3[3]['dscg_layer_routing']['precheck_allowed_batches'], 1)
        self.assertEqual(full[3]['dscg_audit_decisions'][0]['final_reason_code'], 'AUDIT_DENY')
        self.assertEqual(full[3]['dscg_action_ledger'][0]['blocked_by'], 'L3')
        self.assertEqual(no_l3[3]['dscg_action_ledger'][0]['state'], 'executed')
        self.assertFalse(no_l3[3].get('dscg_audit_decisions'))

    def test_l3_allow_preserves_the_effect(self):
        verdict = dict(decision='allow', violations=[], confidence=0.9, reason_code='ALIGNED')
        for checker in (True, False):
            with self.subTest(checker=checker):
                effects, calls, _, diagnostics = self.run_fixture(checker, 'record_placeholder',
                                                                  verdict if checker else None)
                self.assertEqual((effects, calls), (['PLACEHOLDER_ALPHA'], int(checker)))
                self.assertEqual(diagnostics['dscg_action_ledger'][0]['state'], 'executed')

    def test_l2_rejection_precedes_l3(self):
        for checker in (True, False):
            with self.subTest(checker=checker):
                effects, calls, _, diagnostics = self.run_fixture(checker, 'record_other_placeholder')
                self.assertEqual((effects, calls), ([], 0))
                self.assertEqual(diagnostics['dscg_layer_routing']['precheck_rejected_batches'], 1)
                self.assertEqual(diagnostics['dscg_action_ledger'][0]['blocked_by'], 'L2')

    def test_fixed_read_exemption_preserves_execution_without_model_audit(self):
        for checker in (True, False):
            with self.subTest(checker=checker):
                effects, calls, messages, diagnostics = self.run_fixture(checker, 'read_placeholder')
                self.assertEqual((effects, calls), ([], 0))
                self.assertEqual(diagnostics['dscg_action_ledger'][0]['state'], 'executed')
                self.assertEqual(sum(m['role'] == 'tool' for m in messages), 1)
                self.assertEqual(diagnostics['dscg_layer_routing'].get('non_sensitive_read_bypass_batches',0),
                                 int(checker))


if __name__ == '__main__':
    unittest.main()
