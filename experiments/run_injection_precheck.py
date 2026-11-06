"""Single-attempt injection-goal screening with compact reports and immutable evidence."""
import argparse
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import sys
import threading
import time

from agentdojo import benchmark, logging
from baseintent.benchmark_catalog import get_suite, benchmark_identity, validate_backend, get_backend, get_suites, same_backend
from baseintent.model_config import resolve_model_config
from baseintent.paths import RESULTS_DIR
from baseintent.pipelines.baseline import make_openai_compatible_pipeline
from experiments import run_partial_benchmark as shared
from experiments.common.partial_controls import source_revision, guard_run
from experiments.common.result_paths import resolve_run_path
from experiments.common.injection_cohort import (
    RULE, _digest, _file_hash, _read, _write_new, _replace,
    _lock, _binding, _trace_status, _decision,
    _bindings_compatible, _binding_error, _source_compatible, _record_compatibility, run_screened,
)

from experiments.common.injection_filter import SCHEMA as FLITER_SCHEMA, benchmark_header, load_fliter
from baseintent.task_diagnostics import load_task_trace

SCREEN_SCHEMA = 'baseintent.fliter-screen.v1'


def _goal_status(path, suite, task, version):
    status, utility = _trace_status(path, suite, task, version)
    trace = load_task_trace(path)
    if (trace.get('baseintent_infrastructure_failure') or
            ('baseintent_diagnostics' in trace and trace.get('baseintent_diagnostics_status') != 'complete')):
        return 'error', None
    return status, utility


def run_measurement_goals(base, selections, binding, factory, *, progress=False):
    binding = {**binding, 'source': {'agentdojo': benchmark_identity()['package_version']}}
    records = []
    for name, selection in selections.items():
        suite = get_suite('v1.2', name)
        for task_id in selection['injections']:
            task = suite.get_injection_task_by_id(task_id)
            attempts = _attempts(base / 'goal', name, task_id, binding)
            record = attempts[0] if attempts else _native_attempt(
                _attempt_directory(base / 'goal', name, task_id), suite, task, None, binding, factory=factory)
            record = {**record, 'suite': name, 'injection_task_id': task_id, 'cached': bool(attempts)}
            records.append(record)
            if progress:
                print(f"GOAL {name}/{task_id}: {record['status']}", flush=True)
    return records


class Progress:
    """Compact, flushed output; waiting notices do not touch model execution."""

    def __init__(self):
        self.started = time.monotonic()
        self._output_lock = threading.Lock()

    def emit(self, message):
        with self._output_lock:
            print(f'[预检 {time.monotonic() - self.started:.1f}s] {message}', flush=True)

    @contextmanager
    def waiting(self, label, interval=15):
        stopped = threading.Event()
        started = time.monotonic()
        def notices():
            while not stopped.wait(interval):
                self.emit(f'{label} 等待中，已执行 {time.monotonic() - started:.0f}s')
        worker = threading.Thread(target=notices, daemon=True, name='injection-precheck-progress')
        worker.start()
        try:
            yield
        finally:
            stopped.set()
            worker.join()

def _reuse(reuse_from, suite_name, task, binding):
    if reuse_from is None:
        return [], []
    root = Path(reuse_from).resolve()
    rejected, compatible = [], []
    goal_plan = root / 'goal_plan.json'
    if goal_plan.exists():
        try:
            plan = _read(goal_plan)
            groups = [v for k, v in plan['groups'].items()
                      if k.endswith(f'/{suite_name}/run_manifest.json')]
            if (plan.get('schema_version') != 'baseintent.benchmark-plan.v3' or plan.get('goal') is not True
                    or not same_backend(plan['benchmark'], binding['benchmark']) or not groups
                    or any(g['profile'] != 'baseline' or g['agentdojo_defense'] is not None
                           or g['main_model'] != binding['main_model']
                           or task.ID not in g['task_selection']['injections'] for g in groups)):
                raise ValueError('measurement GOAL differs from baseline screening')
            attempt = root / 'goal' / 'attempts' / suite_name / task.ID / 'attempt_0001'
            record_path = attempt / 'attempt.json'
            record = _read(record_path)
            marker = _read(attempt / 'attempt_manifest.json')
            trace = attempt / 'direct_goal' / suite_name / task.ID / 'none' / 'none.json'
            goal_binding = {**plan, 'source': {'agentdojo': binding['source']['agentdojo']}}
            if (not trace.resolve().is_relative_to(root) or marker['binding_sha256'] != _digest(goal_binding)
                    or marker['suite_name'] != suite_name or marker['task_id'] != task.ID
                    or record['trace_sha256'] != _file_hash(trace)):
                raise ValueError('unbound measurement GOAL')
            status, utility = _goal_status(trace, suite_name, task, binding['source']['agentdojo'])
            if status != record['status']:
                raise ValueError('measurement GOAL outcome differs')
            return [dict(origin='reused', status=status, native_utility=utility, trace_path=str(trace),
                         trace_sha256=_file_hash(trace), manifest_path=str(goal_plan),
                         manifest_sha256=_file_hash(goal_plan), api_accounting=None, total_tokens=None)], []
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            return [], [{'reason': 'incompatible_or_incomplete_measurement_goal'}]
    for path in sorted(root.glob(f'*/{suite_name}/{task.ID}/none/none.json')):
        try:
            if not path.resolve().is_relative_to(root):
                raise ValueError('trace outside supplied run')
            manifest_path = path.parents[2] / 'run_manifest.json'
            manifest = _read(manifest_path)
            selection = manifest['task_selection']
            if (not str(manifest.get('schema_version', '')).startswith('baseintent.')
                    or not same_backend(manifest.get('benchmark'), benchmark_identity()) or manifest.get('profile') != 'baseline' or manifest.get('main_model') != binding['main_model']
                    or not _source_compatible(manifest['source'], binding['source'], check_python=False)
                    or manifest.get('agentdojo_defense') is not None
                    or selection.get('suite_version') != 'v1.2' or task.ID not in selection.get('injections', [])):
                raise ValueError('historical configuration mismatch')
            status, utility = _trace_status(path, suite_name, task, binding['source']['agentdojo'])
            trace_hash = _file_hash(path)
            compatible.append({'origin': 'reused', 'status': status, 'native_utility': utility,
                    'trace_path': str(path.resolve()), 'trace_sha256': trace_hash,
                    'manifest_path': str(manifest_path.resolve()), 'manifest_sha256': _file_hash(manifest_path),
                    'reuse_checks': ['baseline', 'public-model-config', 'backend-metadata',
                                     'agentdojo-version', 'suite-version', 'task-id', 'GOAL', 'complete-native-result'],
                    'api_accounting': None, 'total_tokens': None})
            break  # First compatible record only; do not search for a second-chance success.
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            rejected.append({'path': str(path), 'reason': 'incompatible_or_incomplete_direct_goal_record'})
    return compatible, rejected


def _attempt_directory(root, suite_name, task_id):
    parent = root / 'attempts' / suite_name / task_id
    parent.mkdir(parents=True, exist_ok=True)
    number = 1
    while True:
        path = parent / f'attempt_{number:04d}'
        try:
            path.mkdir()
            return path
        except FileExistsError:
            number += 1


def _native_attempt(directory, suite, task, config, binding, *, factory=None):
    record = {'origin': 'fresh', 'status': 'error', 'native_utility': None,
              'started_at': datetime.now(timezone.utc).isoformat(),
              'trace_path': None, 'trace_sha256': None, 'api_accounting': None, 'total_tokens': None}
    _write_new(directory / 'attempt_manifest.json', {'benchmark': benchmark_identity(), 'binding_sha256': _digest(binding),
               'suite_name': suite.name, 'task_id': task.ID, 'started_at': record['started_at']})
    trackers = ()
    try:
        if factory is None:
            pipeline, tracker = make_openai_compatible_pipeline(model_config=config)
            trackers = (tracker,)
        else:
            pipeline, *trackers = factory()
        from experiments.common.benchmark_tasks import _TaskPipelineProbe
        probe = _TaskPipelineProbe(pipeline)
        pipeline.name = 'direct_goal'
        trace = directory / 'direct_goal' / suite.name / task.ID / 'none' / 'none.json'
        with logging.OutputLogger(str(directory)):
            benchmark.run_task_without_injection_tasks(suite, probe, task, directory, True, benchmark_version='v1.2')
        record['status'], record['native_utility'] = _goal_status(trace, suite.name, task, binding['source']['agentdojo'])
        if probe.error:
            record.update(status='error', native_utility=None, error_type=probe.error['reason_code'])
    except Exception as exc:
        # Preserve native traces; provider exception text can contain private input.
        record['error_type'] = type(exc).__name__
        from baseintent.request_compatibility import api_error_diagnostics
        diagnostic = api_error_diagnostics(exc)
        if diagnostic is not None:
            record['api_error'] = diagnostic
    finally:
        trace = directory / 'direct_goal' / suite.name / task.ID / 'none' / 'none.json'
        if trace.exists():
            record.update(trace_path=str(trace.resolve()), trace_sha256=_file_hash(trace))
        snapshots = [tracker.snapshot() for tracker in trackers if tracker is not None and hasattr(tracker, 'snapshot')]
        if snapshots:
            phases = [phase for model in snapshots for phase in model.values()]
            record['api_accounting'] = {'models': snapshots}
            if phases and not any(p.get('missing_usage_calls', 0) or p.get('failed_calls', 0) for p in phases):
                record['total_tokens'] = sum(p.get('total_tokens', 0) for p in phases)
            if any(p.get('failed_calls', 0) for p in phases):
                record.update(status='error', native_utility=None, error_type='RECORDED_API_FAILURE')
        record['finished_at'] = datetime.now(timezone.utc).isoformat()
        _write_new(directory / 'attempt.json', record)
    return record


def _attempts(root, suite_name, task_id, binding, *, frozen=False):
    attempts = []
    for directory in sorted((root / 'attempts' / suite_name / task_id).glob('attempt_*')):
        path = directory / 'attempt.json'
        try:
            if not path.exists():
                marker = _read(directory / 'attempt_manifest.json')
                if (marker.get('binding_sha256') != _digest(binding) or marker.get('suite_name') != suite_name
                        or marker.get('task_id') != task_id):
                    raise ValueError('unbound interrupted attempt')
                trace = directory / 'direct_goal' / suite_name / task_id / 'none' / 'none.json'
                task = get_suite('v1.2', suite_name).get_injection_task_by_id(task_id)
                status, utility = _goal_status(trace, suite_name, task, binding['source']['agentdojo'])
                _write_new(path, {'origin': 'recovered', 'status': status, 'native_utility': utility,
                    'trace_path': str(trace.resolve()), 'trace_sha256': _file_hash(trace),
                    'started_at': marker['started_at'], 'api_accounting': None, 'total_tokens': None,
                    'recovery': 'native result completed before attempt bookkeeping; usage unknown'})
            record = _read(path)
            if record['status'] not in {'pass', 'fail', 'error'}:
                raise ValueError('invalid attempt status')
            for prefix in ('trace', 'manifest'):
                if record.get(prefix + '_path') and _file_hash(record[prefix + '_path']) != record[prefix + '_sha256']:
                    raise ValueError('attempt evidence changed')
        except (OSError, ValueError, KeyError, TypeError):
            if frozen:
                raise ValueError('frozen screening evidence changed') from None
            record = {'status': 'error', 'origin': 'incomplete', 'error_type': 'MissingOrChangedAttemptEvidence',
                      'attempt_directory': str(directory.resolve()), 'total_tokens': None}
        attempts.append(record)
    return attempts


def _report(root, binding, decisions, rejected):
    counts = Counter(d['status'] for tasks in decisions.values() for d in tasks.values())
    attempts = [a for tasks in decisions.values() for d in tasks.values() for a in d['attempts']]
    report = {'schema_version': SCREEN_SCHEMA, 'benchmark': benchmark_identity(), 'binding_sha256': _digest(binding), 'counts': dict(counts),
              'expected_targets': sum(len(e['injection_tasks']) for e in binding['catalog'].values()),
              'processed_targets': sum(counts.values()),
              'selection_rule': RULE, 'attempt_counts': dict(Counter(a['status'] for a in attempts)),
              'selection_report': {'decisions': decisions}, 'reuse_rejection_counts': dict(rejected), 'known_attempt_tokens': sum(a.get('total_tokens') or 0 for a in attempts),
              'unknown_cost_attempts': sum(a.get('total_tokens') is None for a in attempts)}
    _replace(root / 'status.json', report)
    lines = ['# Injection 目标直接预检', '', '范围：无防御 baseline；不执行注入攻击。', '',
             '每目标一次，成功保留，失败或错误跳过；错误不计作有效失败。', '',
             '| 场景 | 已处理/目标 | 保留 | 排除 | 错误跳过 |', '| --- | --- | --- | --- | --- |']
    for name, tasks in decisions.items():
        c = Counter(d['status'] for d in tasks.values())
        lines.append(f"| {name} | {len(tasks)}/{len(binding['catalog'][name]['injection_tasks'])} | {c['kept']} | {c['excluded']} | {c['error']} |")
    lines += ['', f"已知尝试 Tokens：{report['known_attempt_tokens']}；成本未知尝试：{report['unknown_cost_attempts']}。", '',
              '详情见[排除名单](fliter.json)与[原始尝试](attempts/)。直接失败不证明间接攻击不能成功。']
    (root / 'summary.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return report


def screen(*, config_path, run_name, results_dir=None, reuse_from=None, suites=None):
    backend = get_backend()
    suites = list(backend.suites) if suites is None else list(suites)
    if not suites or len(set(suites)) != len(suites) or not set(suites) <= set(backend.suites):
        raise ValueError(f'suites must select from {", ".join(backend.suites)}')
    progress = Progress()
    progress.emit('启动，正在读取配置与任务目录。')
    config = resolve_model_config(config_path=config_path)
    current_binding = {**_binding(config, suites), 'schema_version': SCREEN_SCHEMA}
    root = resolve_run_path(results_dir or RESULTS_DIR / 'injection_precheck', backend.id,
                            config.model_id, run_name, allow_legacy=True)
    if (root / 'cohort.json').exists():
        raise ValueError('historical cohort is read-only; use a new screen name')
    if root.exists() and not (root / 'screen_manifest.json').is_file():
        raise ValueError('existing screen directory lacks a complete binding; use a new screen name')
    if reuse_from is not None and not Path(reuse_from).is_dir():
        raise ValueError('--reuse-from must be an existing benchmark run directory')
    with _lock(root):
        manifest_path = root / 'screen_manifest.json'
        resumed = manifest_path.exists()
        binding = _read(manifest_path) if resumed else current_binding
        compatible = _bindings_compatible(binding, current_binding)
        if not compatible:
            raise ValueError(_binding_error(binding, current_binding))
        guard_run(manifest_path, binding)
        frozen = (root / 'fliter.json').is_file()
        if not frozen:
            _record_compatibility(root, binding, current_binding)
        total = sum(len(e['injection_tasks']) for e in binding['catalog'].values())
        progress.emit(f'模型={config.model_id}；目标={total}；模式={"续跑" if resumed else "首次运行"}；输出={root}')
        progress.emit(f'复用来源={reuse_from or "未指定"}；每目标只测一次：成功保留，失败/错误跳过。')
        decisions, rejected = {}, Counter()
        ordinal = 0
        if (root / 'status.json').exists():
            previous = _read(root / 'status.json')
            rejected.update(previous.get('reuse_rejection_counts', {}))
            rejected.update(r['reason'] for r in previous.get('reuse_rejections', []))
        for name, entry in binding['catalog'].items():
            suite = get_suite('v1.2', name)
            decisions[name] = {}
            for task_id in entry['injection_tasks']:
                ordinal += 1
                label = f'[{ordinal}/{total}] {name}/{task_id}'
                task = suite.get_injection_task_by_id(task_id)
                attempts = _attempts(root, name, task_id, binding, frozen=frozen)
                if frozen and not attempts:
                    raise ValueError('frozen screening attempt is missing')
                if not attempts:
                    reused, rejected_records = _reuse(reuse_from, name, task, binding)
                    rejected.update(r['reason'] for r in rejected_records)
                    for record in reused:
                        _write_new(_attempt_directory(root, name, task_id) / 'attempt.json', record)
                        attempts.append(record)
                if not attempts:
                    directory = _attempt_directory(root, name, task_id)
                    progress.emit(f'{label} 开始尝试（仅一次）。')
                    started = time.monotonic()
                    with progress.waiting(label):
                        attempt = _native_attempt(directory, suite, task, config, binding)
                    attempts.append(attempt)
                    tokens = attempt.get('total_tokens')
                    progress.emit(f'{label} 结果={attempt["status"]}；耗时={time.monotonic() - started:.1f}s；'
                                  f'Tokens={tokens if tokens is not None else "未知"}'
                                  + (f'；错误类型={attempt.get("error_type", "NativeTraceError")}' if attempt['status'] == 'error' else ''))
                decisions[name][task_id] = {'status': _decision(attempts), 'attempts': attempts}
                if frozen:
                    continue
                report = _report(root, binding, decisions, rejected)
                counts = report['counts']
                progress.emit(f'{label} 判定={decisions[name][task_id]["status"]}；累计：'
                              f'保留={counts.get("kept", 0)} 排除={counts.get("excluded", 0)} 错误跳过={counts.get("error", 0)}。')
        if frozen:
            excluded = {name: sorted(task_id for task_id, d in tasks.items() if d['status'] != 'kept')
                        for name, tasks in decisions.items()}
            if load_fliter(root / 'fliter.json')['excluded'] != excluded:
                raise ValueError('frozen fliter evidence differs')
            return int(any(d['status'] == 'error' for tasks in decisions.values() for d in tasks.values()))
        report = _report(root, binding, decisions, rejected)
        if report['counts'].get('unresolved', 0):
            progress.emit(f'存在待解决目标，未生成名单；以同一条 screen 命令续跑。报告：{root / "summary.md"}；明细：{root / "status.json"}')
            return 1
        fliter = {'schema_version': FLITER_SCHEMA, 'benchmark': benchmark_header(),
                  'excluded': {name: sorted(task_id for task_id, decision in tasks.items()
                                            if decision['status'] != 'kept')
                               for name, tasks in sorted(decisions.items())}}
        path = root / 'fliter.json'
        if path.exists():
            if load_fliter(path) != fliter:
                raise ValueError('frozen fliter evidence differs')
        else:
            _write_new(path, fliter)
        progress.emit(f'完成：{dict(report["counts"])}。名单：{path}')
        return int(bool(report['counts'].get('error', 0)))


def cli(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == 'benchmark':
        print('旧入口已退役，请用 experiments.run_benchmark --fliter。', flush=True)
        return 2
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    sub = commands.add_parser('screen', help='直接预检 injection GOAL 并冻结筛选名单')
    sub.add_argument('--suites', nargs='+', metavar='SUITE', help='选择当前环境支持的场景；默认全部场景')
    sub.add_argument('--model-config', dest='config_path')
    sub.add_argument('--name', dest='run_name', required=True)
    sub.add_argument('--results-dir', help='默认 results/injection_precheck')
    sub.add_argument('--reuse-from', help='只读复用兼容 baseline 预检记录')
    options = vars(parser.parse_args(argv))
    options.pop('command')
    try:
        return screen(**options)
    except KeyboardInterrupt:
        print('预检已中断，已有记录保留；更新完成后以同一条 screen 命令续跑。', flush=True)
        return 130
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f'预检配置错误：{exc}' if isinstance(exc, ValueError)
              else f'预检记录不可用：{type(exc).__name__}', flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(cli())
