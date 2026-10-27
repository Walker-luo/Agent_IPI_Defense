((root) => {
  const unique = (values) => Array.from(new Set(values)).sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
  const backendId = run => run.benchmark_id || "unknown";
  function filterRuns(catalog, { folder = "all", backend = "all", models = null, attack = "all" } = {}) {
    return catalog.filter(run => (folder === "all" || run.result_folder === folder)
      && (backend === "all" || backendId(run) === backend)
      && (models === null || models.includes(run.model_group))
      && (attack === "all" || run.attack_name === attack));
  }
  function resolveFilters(catalog, requested = {}) {
    const folders = unique(catalog.map(run => run.result_folder));
    const folder = folders.includes(requested.folder) ? requested.folder : "all";
    const backends = unique(filterRuns(catalog, { folder }).map(backendId));
    const backend = backends.includes(requested.backend) ? requested.backend : "all";
    const models = unique(filterRuns(catalog, { folder, backend }).map(run => run.model_group));
    let selectedModels = Array.isArray(requested.models)
      ? unique(requested.models.filter(model => models.includes(model))) : null;
    if (requested.models?.length && !selectedModels.length) selectedModels = null;
    const attacks = unique(filterRuns(catalog, {
      folder, backend, models: selectedModels?.length === 0 ? null : selectedModels,
    }).map(run => run.attack_name));
    const attack = attacks.includes(requested.attack) ? requested.attack : "all";
    return { folders, backends, models, attacks, filters: { folder, backend, models: selectedModels, attack } };
  }
  function visibleSelection(visible, selected, all = false) {
    const ids = new Set(selected);
    return visible.filter(run => all || ids.has(run.id)).map(run => run.id);
  }
  function attackLabel(name) {
    return ({ unknown: "未记录攻击", mixed: "混合攻击（历史汇总）", none: "无攻击" })[name] || name;
  }
  function backendLabel(name) {
    return ({agentdojo: "AgentDojo", agentdyn: "AgentDyn", unknown: "未记录基准", mixed: "混合／身份不完整"})[name] || name;
  }
  function createRequestGate() {
    let revision = 0;
    return {
      start: () => ++revision,
      invalidate: () => { revision += 1; },
      isCurrent: request => request === revision,
    };
  }
  function overviewGroups(experiments) {
    return experiments.flatMap(run => {
      const suites = run.suites || [];
      const identity = suites[0]?.benchmark;
      const sameIdentity = identity && ["id", "repository", "revision", "suite_version", "implementation_sha256", "catalog_sha256"].every(key => identity[key]) && suites.every(suite => suite.benchmark &&
        JSON.stringify(suite.benchmark) === JSON.stringify(identity));
      const groups = sameIdentity ? [suites] : suites.map(suite => [suite]);
      return groups.filter(group => group.length).map(group => {
        const counts = key => {
          const values = group.map(suite => suite.overview?.[key]);
          if (values.some(value => !value)) return null;
          const result = values.reduce((sum, value) => ({success: sum.success + value.success, valid: sum.valid + value.valid}), {success: 0, valid: 0});
          if (values.some(value => value.source === "records_unknown")) result.source = "records_unknown";
          else if (values.some(value => value.source === "records")) result.source = "records";
          return result;
        };
        const usage = group.map(suite => suite.overview?.tokens);
        const recorded = usage.filter(value => value?.recorded != null);
        return {run, suites: group.map(suite => suite.suite_name), tsr: counts("tsr"), asr: counts("asr"),
          reported: group.length === 1 ? group[0].metrics : null,
          tokens: {recorded: recorded.length ? recorded.reduce((sum, value) => sum + value.recorded, 0) : null,
                   complete: recorded.length === group.length && usage.every(value => value.complete)}};
      });
    });
  }
  const api = { filterRuns, resolveFilters, visibleSelection, attackLabel, backendLabel, createRequestGate, overviewGroups };
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.BaseIntentHistorySelection = api;
})(typeof window === "undefined" ? globalThis : window);
