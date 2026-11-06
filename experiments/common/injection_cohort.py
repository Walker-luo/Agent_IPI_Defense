"""Frozen cohort compatibility and screening evidence helpers."""
import fcntl
import hashlib
import json
import os
import shutil
from uuid import uuid4
from collections import Counter
from contextlib import contextmanager
from pathlib import Path

from baseintent.benchmark_catalog import get_suite, benchmark_identity, get_backend, same_backend
from experiments.common.partial_controls import source_revision

SCHEMA = 'baseintent.injection-screen.v2'
LEGACY_RULE = 'keep-any-valid-success; exclude-after-two-valid-failures; errors-unresolved'
RULE = 'single-attempt; keep-valid-success; skip-failure-or-error; no-retests'
COHORT_VALIDATION = {'mode': 'model_backend_suites_v1', 'cohort_digest_verified': True,
                     'screening_evidence_verified': False}
LIMITATIONS = [
    'Direct-goal failure does not prove an indirect attack cannot succeed.',
    'Native utility is retained; refusals, execution deviations and predicate ambiguity need trace review.',
    'Backend/source content is not verified; reuse checks declared backend, public model settings, task IDs and GOAL evidence.',
    'Provider model revisions may be unpinned. Reused attempt token cost is unknown.',
]


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def _replace(path, value):
    temporary = path.with_name(path.name + f'.{os.getpid()}.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


@contextmanager
def _lock(directory):
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / '.screening.lock').open('a') as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError('another invocation is using this run directory') from exc
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def _catalog(names):
    catalog = {}
    for name in names:
        suite = get_suite('v1.2', name)
        tasks = {}
        for task_id, task in suite.injection_tasks.items():
            tasks[task_id] = {'goal': task.GOAL}
        catalog[name] = {'user_task_ids': list(suite.user_tasks), 'injection_tasks': tasks}
    return catalog


def _binding(config, names):
    return {'schema_version': SCHEMA, 'benchmark': benchmark_identity(), 'suite_version': 'v1.2', 'rule': RULE,
            'main_model': config.public_dict(), 'source': source_revision(),
            'catalog': _catalog(names)}


def _source_compatible(recorded, current, check_python=True):
    return (same_backend(recorded.get('benchmark'), current.get('benchmark'))
            and same_backend(current.get('benchmark'), benchmark_identity())
            and recorded.get('agentdojo') == current.get('agentdojo'))


def _bindings_compatible(recorded, current):
    def normalize(binding):
        return {'schema_version': binding.get('schema_version'),
                'suite_version': binding.get('suite_version'), 'rule': binding.get('rule'),
                'main_model': binding.get('main_model'),
                'catalog': {name: {'user_task_ids': entry.get('user_task_ids'),
                    'injection_task_ids': list(entry.get('injection_tasks', {})),
                    'injection_tasks': {task_id: {'goal': task.get('goal')}
                                       for task_id, task in entry.get('injection_tasks', {}).items()}}
                    for name, entry in binding.get('catalog', {}).items()}}
    return (same_backend(recorded.get('benchmark'), current.get('benchmark'))
            and normalize(recorded) == normalize(current))


def _binding_error(recorded, current):
    old, new = recorded.get('main_model', {}), current.get('main_model', {})
    fields = ['schema_version'] if recorded.get('schema_version') != current.get('schema_version') else []
    fields += [f'main_model.{key}' for key in sorted(set(old) | set(new)) if old.get(key) != new.get(key)]
    if not same_backend(recorded.get('benchmark'), current.get('benchmark')):
        fields.append('benchmark')
    if recorded.get('catalog') != current.get('catalog'):
        fields.append('catalog/GOAL')
    return ('screening model/backend/task/GOAL/rule configuration changed: '
            + ', '.join(fields or ['selection rule']) + '; use a new screen run')


def _record_compatibility(root, recorded, current):
    record = {'reason': 'configuration-only transition; source equivalence not verified',
              'verification_mode': 'configuration_only', 'source_equivalence_verified': False,
              'original_binding': recorded, 'current_binding': current}
    # Pending screens rewrite these aggregates; retain each invocation's inputs
    # even when its informational source metadata has not changed.
    aggregates = [root / name for name in ('status.json', 'summary.md') if (root / name).is_file()]
    if aggregates and not (root / 'cohort.json').exists():
        destination = root / 'compatibility' / uuid4().hex
        snapshots = []
        for source in aggregates:
            target = destination / 'snapshot' / source.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            snapshots.append({'path': source.name, 'size_bytes': target.stat().st_size})
        _write_new(destination / 'configuration.json', {**record, 'previous_aggregate_snapshots': snapshots})
    if recorded == current:
        return
    path = root / 'compatibility' / (_digest(current) + '_configuration_only.json')
    if path.exists():
        if _read(path) != record:
            raise ValueError('compatibility provenance changed')
    else:
        _write_new(path, record)


def _text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return '\n'.join(c.get('content', '') for c in content if isinstance(c, dict) and c.get('type') == 'text')
    return ''


def _trace_status(path, suite_name, task, version):
    """Require a complete native direct-goal result; errors are never failures."""
    value = _read(path)
    messages = value.get('messages', [])
    if (value.get('suite_name') != suite_name or value.get('user_task_id') != task.ID
            or value.get('injection_task_id') is not None or value.get('attack_type') not in (None, 'none')
            or value.get('injections') != {} or value.get('agentdojo_package_version') != version
            or not isinstance(messages, list) or len(messages) < 2):
        raise ValueError('not a matching direct-goal trace')
    users = [m for m in messages if m.get('role') == 'user']
    if not users or _text(users[0].get('content')) != task.GOAL:
        raise ValueError('trace GOAL mismatch')
    if value.get('error'):
        return 'error', None
    if type(value.get('utility')) is not bool or not any(m.get('role') == 'assistant' for m in messages):
        raise ValueError('incomplete native utility result')
    return ('pass' if value['utility'] else 'fail'), value['utility']


def _decision(attempts, rule=RULE):
    if rule == RULE:
        if not attempts:
            return 'unresolved'
        return {'pass': 'kept', 'fail': 'excluded', 'error': 'error'}[attempts[0]['status']]
    if rule != LEGACY_RULE:
        raise ValueError('unknown screening selection rule')
    if any(a['status'] == 'pass' for a in attempts):
        return 'kept'
    if sum(a['status'] == 'fail' for a in attempts) >= 2:
        return 'excluded'
    return 'unresolved'


def _validate_cohort(path, config, suites=None):
    return _validate_cohort_data(_read(path), config, suites=suites)


def _validate_cohort_data(cohort, config, suites=None):
    """Trust the frozen list; verify its digest and selected runtime scope only."""
    if (not isinstance(cohort, dict) or cohort.get('schema_version') != SCHEMA
            or cohort.get('suite_version') != 'v1.2'
            or not isinstance(cohort.get('binding'), dict)
            or not isinstance(cohort.get('suites'), dict)):
        raise ValueError('invalid frozen cohort schema')
    if cohort.get('cohort_sha256') != _digest({k: v for k, v in cohort.items() if k != 'cohort_sha256'}):
        raise ValueError('invalid or changed frozen cohort digest')
    current = benchmark_identity()
    if (not same_backend(cohort.get('benchmark'), current)
            or not same_backend(cohort['binding'].get('benchmark'), current)):
        raise ValueError('cohort backend/version differs from current environment')
    recorded = cohort['binding'].get('main_model')
    actual = config.public_dict()
    for field in ('model_id', 'provider'):
        if (not isinstance(recorded, dict) or not isinstance(recorded.get(field), str)
                or not recorded[field] or recorded[field] != actual.get(field)):
            raise ValueError(f'cohort model identity differs: main_model.{field}')
    names = list(cohort['suites']) if suites is None else list(suites)
    if (not names or any(not isinstance(name, str) for name in names)
            or len(set(names)) != len(names) or not set(names) <= set(get_backend().suites)
            or not set(names) <= set(cohort['suites'])):
        raise ValueError('frozen cohort lacks requested suites or selection is empty/duplicated')
    for name in names:
        entry = cohort['suites'][name]
        if not isinstance(entry, dict):
            raise ValueError(f'invalid frozen cohort task lists: {name}')
        suite = get_suite('v1.2', name)
        for field, catalog in (('user_task_ids', list(suite.user_tasks)),
                               ('injection_task_ids', list(suite.injection_tasks))):
            ids = entry.get(field)
            if (not isinstance(ids, list) or any(not isinstance(task_id, str) for task_id in ids)
                    or len(set(ids)) != len(ids) or not set(ids) <= set(catalog)
                    or ids != (catalog if field == 'user_task_ids' else [i for i in catalog if i in ids])):
                raise ValueError(f'invalid frozen {field} for {name}')
    return cohort


def _validate_screen_cohort_data(cohort, config):
    """Screen creation/resumption still verifies its native evidence."""
    content = {k: v for k, v in cohort.items() if k != 'cohort_sha256'}
    rule = cohort.get('selection_rule')
    if (not same_backend(cohort.get('benchmark'), benchmark_identity()) or cohort.get('schema_version') != SCHEMA or cohort.get('cohort_sha256') != _digest(content)
            or rule not in (RULE, LEGACY_RULE) or cohort['binding'].get('rule') != rule):
        raise ValueError('invalid or changed frozen cohort')
    binding = cohort['binding']
    current = _binding(config, list(binding['catalog']))
    current['rule'] = rule  # Frozen historical cohorts retain their original decision semantics.
    if not _bindings_compatible(binding, current):
        raise ValueError(_binding_error(binding, current))
    for name, entry in binding['catalog'].items():
        decisions = cohort['decisions'][name]
        if set(decisions) != set(entry['injection_tasks']):
            raise ValueError('incomplete screening decisions')
        for task_id, decision in decisions.items():
            attempts = decision['attempts']
            if _decision(attempts, rule) == 'unresolved' or _decision(attempts, rule) != decision['status']:
                raise ValueError('unresolved or inconsistent screening decisions')
            task = get_suite('v1.2', name).get_injection_task_by_id(task_id)
            for attempt in attempts:
                for prefix in ('trace', 'manifest'):
                    path = attempt.get(prefix + '_path')
                    if path and _file_hash(path) != attempt.get(prefix + '_sha256'):
                        raise ValueError('screening evidence changed')
                if attempt.get('status') not in {'pass', 'fail'}:
                    continue
                trace = attempt['trace_path']
                if _trace_status(trace, name, task, binding['source']['agentdojo'])[0] != attempt['status']:
                    raise ValueError('screening outcome changed')
        expected = {'user_task_ids': entry['user_task_ids'],
                    'injection_task_ids': [i for i, d in decisions.items() if d['status'] == 'kept']}
        if cohort['suites'].get(name) != expected:
            raise ValueError('selected tasks disagree with screening evidence')
    return cohort


def _preflight_report(base, cohort, active, attacks, selected_tasks=None):
    """Keep unscored native preflight outcomes/cost uncertainty separate."""
    records, aggregate_costs = [], []
    for attack in attacks:
        for name in active:
            directory = base / attack / name
            summary = directory / 'summary.json'
            if summary.exists():
                value = _read(summary)
                aggregate_costs.append({'attack': attack, 'suite': name,
                    'main_overhead_including_preflight': value.get('overhead'),
                    'security_overhead_including_preflight': value.get('sec_overhead'),
                    'cost_scope': value.get('cost_scope')})
            for task_id in (selected_tasks if selected_tasks is not None else cohort['suites'])[name]['injection_task_ids']:
                path = directory / task_id / 'none' / 'none.json'
                record = {'attack': attack, 'suite': name, 'injection_task_id': task_id,
                          'trace_path': str(path.resolve()), 'status': 'missing', 'total_tokens': None}
                if path.exists():
                    try:
                        task = get_suite('v1.2', name).get_injection_task_by_id(task_id)
                        record['status'], record['native_utility'] = _trace_status(
                            path, name, task, cohort['binding']['source']['agentdojo'])
                        record['trace_sha256'] = _file_hash(path)
                        record['duration'] = _read(path).get('duration')
                    except (OSError, ValueError, KeyError, TypeError, AttributeError):
                        record['status'] = 'invalid'
                records.append(record)
    _replace(base / 'preflight_report.json', {
        'schema_version': 'baseintent.preflight-report.v2', 'benchmark': benchmark_identity(),
        'scope': 'unscored native per-attack goal prechecks; separate from original screening',
        'planned_preflight_samples': len(records), 'counts': dict(Counter(r['status'] for r in records)),
        'preflight_total_tokens': None, 'records': records, 'aggregate_run_costs': aggregate_costs,
        'cost_limitation': 'Native task traces lack separate usage; preflight Tokens remain unknown and are included in shared aggregate costs, not added again.',
    })


def run_screened(cohort_path, **options):
    raise ValueError('cohort execution is retired; use --fliter')
