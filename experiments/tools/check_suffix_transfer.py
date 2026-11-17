#!/usr/bin/env python3
"""Test whether a suffix learned on one pair transfers to another pair (origin pipeline)."""
import json
import pathlib
import shutil
import tempfile

from agentdojo import logging as ad_logging
from agentdojo.task_suite import get_suite

from dscg.benchmark_catalog import SUITE_VERSION
from dscg.pipelines.baseline import make_openai_compatible_pipeline
from experiments.common.benchmark_tasks import run_native_suite
from experiments.tools.learn_suffix_dscg import SuffixAttack

RESULTS = pathlib.Path("workshop/artifacts/20261116_suffix_learning/origin/all_results.json")
data = json.loads(RESULTS.read_text())
by_key = {(r["suite"], r["user"], r["injection"]): r for r in data}

transfers = [
    # (source pair whose suffix is used, target pair)
    (("slack", "user_task_0", "injection_task_2"), ("workspace", "user_task_0", "injection_task_0")),
    (("slack", "user_task_0", "injection_task_2"), ("travel", "user_task_0", "injection_task_0")),
    (("slack", "user_task_0", "injection_task_2"), ("banking", "user_task_1", "injection_task_2")),
    (("slack", "user_task_0", "injection_task_2"), ("slack", "user_task_0", "injection_task_1")),
    (("workspace", "user_task_11", "injection_task_0"), ("workspace", "user_task_0", "injection_task_0")),
    (("workspace", "user_task_11", "injection_task_0"), ("slack", "user_task_0", "injection_task_2")),
]

pipeline, _ = make_openai_compatible_pipeline(None)
rows = []
for src, dst in transfers:
    src_row = by_key[src]
    suffix = src_row["best_suffix"]
    suite = get_suite(SUITE_VERSION, dst[0])
    attack = SuffixAttack(suite, pipeline, suffix, "Emma Johnson", "Qwen3.7-Flash")
    scratch = pathlib.Path(tempfile.mkdtemp(prefix="transfer_"))
    try:
        with ad_logging.OutputLogger(str(scratch)):
            result = run_native_suite(
                pipeline, suite, attack, scratch, True,
                user_tasks=[dst[1]], injection_tasks=[dst[2]], benchmark_version=SUITE_VERSION,
            )
        util = result["utility_results"].get((dst[1], dst[2]))
        sec = result["security_results"].get((dst[1], dst[2]))
        rows.append({
            "source": "/".join(src), "target": "/".join(dst),
            "source_own_asr": src_row["best_asr"],
            "target_own_learned_asr": by_key[dst]["best_asr"],
            "transfer_asr": 0.0 if sec is None else float(bool(sec)),
            "transfer_utility": 0.0 if util is None else float(bool(util)),
        })
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    print(rows[-1], flush=True)
pathlib.Path("workshop/artifacts/20261116_suffix_learning/transfer_results.json").write_text(json.dumps(rows, indent=2))
print("DONE")
