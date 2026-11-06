const test = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const selection = require("../dashboard/static/js/history_selection.js");
const historyCharts = require("../dashboard/static/js/history_charts.js");

function historyUI(catalog, filters) {
  const source = fs.readFileSync(path.join(__dirname, "../dashboard/static/js/history.js"), "utf8");
  class Element {
    constructor() { this.children = []; this.handlers = {}; this.style = {}; this.value = "all";
      this.classList = {add() {}, toggle() {}}; }
    append(...children) { this.children.push(...children); }
    replaceChildren(...children) { this.children = children; }
    addEventListener(name, callback) { this.handlers[name] = callback; }
    setAttribute() {}
    removeAttribute() {}
    click() {}
    remove() {}
    querySelector() { return {}; }
  }
  const nodes = new Map();
  let ready;
  const find = (root, className) => root.children.flatMap(node => [
    ...(node.className?.split(" ").includes(className) ? [node] : []), ...find(node, className),
  ]);
  const document = {
    addEventListener(name, callback) { if (name === "DOMContentLoaded") ready = callback; },
    querySelector(selector) { if (!nodes.has(selector)) nodes.set(selector, new Element()); return nodes.get(selector); },
    querySelectorAll(selector) {
      const model = selector.startsWith(".history-model-cb");
      const suite = selector.startsWith(".history-suite-cb");
      const elements = find(this.querySelector(suite ? "#history-suite-options" : model ? "#history-model-options" : "#history-run-list"), suite ? "history-suite-cb" : model ? "history-model-cb" : "history-run-cb");
      return selector.includes(":checked") ? elements.filter(item => item.checked) : elements;
    },
    createElement() { return new Element(); },
    body: new Element(),
  };
  const gate = selection.createRequestGate();
  const context = {
    document, window: {setInterval() {}, setTimeout() {}}, historySelection: selection, historyCharts, analysisRequests: gate,
    catalog, filters, suiteSelection: null,
    experimentStyles: historyCharts.createExperimentStyles(catalog), exporting: false,
    updateControls() {}, loadCatalog() {}, clearCharts() {}, renderSummaryTable() {}, renderOverview() {}, showEmpty() {}, analyze() {}, exportAnalysis() {},
    addOption(select, value, text) { const node = new Element(); node.value = value; node.textContent = text; select.append(node); },
  };
  vm.createContext(context);
  // Run the production event wiring and selection/render helpers with a small DOM adapter.
  // Chart drawing and network activity are covered separately, so this test needs neither.
  const startup = source.slice(source.indexOf('  document.addEventListener("DOMContentLoaded"'), source.indexOf("  async function loadCatalog()"));
  const helpers = source.slice(source.indexOf("  function refreshFilterResults("), source.indexOf("  async function exportAnalysis()"));
  vm.runInContext(startup + helpers, context);
  ready();
  context.renderCatalog(new Set(), false);
  const click = selector => nodes.get(selector).handlers.click();
  const selected = () => Array.from(context.selectedRunIds()).sort();
  const change = (key, value) => {
    nodes.get(`#history-${key}-select`).value = value;
    nodes.get(`#history-${key}-select`).handlers.change();
  };
  return {context, nodes, gate, click, selected, change, source};
}

test("actual filter events keep all selected versions after changing attacks and clear models across refresh", () => {
  const catalog = ["attackA", "attackB"].flatMap(attack => ["baseline", "dscg"].map(model => ({
    id: model + "/" + attack, result_folder: "partial_benchmark", model_group: model,
    model_suffix: model, attack_name: attack, label: model, source: model + "/" + attack,
    suites: [{suite_name: "workspace"}],
  })));
  const {context, nodes, gate, click, selected} = historyUI(catalog, {folder: "partial_benchmark", models: null, attack: "attackA"});
  click("#history-model-select-all");
  assert.deepEqual(selected(), ["baseline/attackA", "dscg/attackA"]);
  const pending = gate.start();
  nodes.get("#history-attack-select").value = "attackB";
  nodes.get("#history-attack-select").handlers.change();
  assert.equal(gate.isCurrent(pending), false);
  assert.deepEqual(selected(), ["baseline/attackB", "dscg/attackB"]);
  click("#history-model-clear");
  assert.deepEqual(selected(), []);
  context.renderCatalog(new Set(), false);
  assert.deepEqual(selected(), []);
});

test("backend UI refresh excludes hidden runs from actual analyze/export and rejects stale responses", async () => {
  const catalog = [
    {id: "dojo", model_group: "agentdojo/qwen_baseline", benchmark_id: "agentdojo"},
    {id: "dyn-new", model_group: "agentdyn/qwen_baseline", benchmark_id: "agentdyn"},
    {id: "dyn-old", model_group: "qwen_agentdyn_baseline", benchmark_id: "agentdyn"},
  ].map(run => ({...run, result_folder: "benchmarks", model_suffix: "qwen_baseline", source: run.model_group,
    attack_name: "tool_knowledge", suites: [{suite_name: run.benchmark_id === "agentdyn" ? "shopping" : "workspace"}]}));
  const ui = historyUI(catalog, {folder: "benchmarks", backend: "all", models: null, attack: "all"});
  ui.click("#history-model-select-all");
  assert.deepEqual(ui.nodes.get("#history-backend-select")?.children.map(n => n.value), ["all", "agentdojo", "agentdyn"]);
  const pending = ui.gate.start();
  ui.change("backend", "agentdyn");
  assert.equal(ui.gate.isCurrent(pending), false);
  assert.deepEqual(ui.selected(), ["dyn-new", "dyn-old"]);
  assert.equal(ui.nodes.get("#history-selection-count").textContent, "2 项已选");
  assert.equal(ui.nodes.get("#history-catalog-count").textContent, "2 / 3 项");
  assert.deepEqual(ui.context.document.querySelectorAll('.history-suite-cb:checked').map(n => n.value), ["shopping"]);
  // Simulate the timer's render with one manually excluded run.
  ui.context.renderCatalog(new Set(["dyn-old"]), false);
  assert.deepEqual(ui.selected(), ["dyn-old"]);
  assert.equal(ui.nodes.get("#history-backend-select").value, "agentdyn");
  const payloads = [], rendered = [];
  Object.assign(ui.context, {
    selectedMetricKeys: () => ["utility_rate"],
    renderAnalysis: data => rendered.push(data),
    URL: {createObjectURL: () => "blob:fixture", revokeObjectURL() {}},
    fetch: async (url, init) => {
      payloads.push({url, body: JSON.parse(init.body)});
      return {ok: true, json: async () => ({experiments: []}), blob: async () => ({}), headers: {get: () => null}};
    },
  });
  ui.nodes.get("#history-chart-type").value = "bar";
  vm.runInContext(ui.source.slice(ui.source.indexOf("  async function exportAnalysis()"), ui.source.indexOf("  function addOption("))
    + ui.source.slice(ui.source.indexOf("  function analysisSelectionKey()"), ui.source.indexOf("  function clearCharts()")), ui.context);
  await ui.context.analyze();
  await ui.context.exportAnalysis();
  assert.deepEqual(payloads, [
    {url: "/api/history/analyze", body: {run_ids: ["dyn-old"], suites: ["shopping"], include_task_records: false}},
    {url: "/api/history/export", body: {run_ids: ["dyn-old"], suites: ["shopping"]}},
  ]);
  assert.equal(rendered.length, 1);
  let resolveOld;
  ui.context.fetch = () => new Promise(resolve => { resolveOld = resolve; });
  const old = ui.context.analyze();
  ui.change("backend", "agentdojo");
  assert.deepEqual(ui.selected(), ["dojo"]);
  resolveOld({ok: true, json: async () => ({experiments: ["stale"]})});
  await old;
  assert.equal(rendered.length, 1);
  ui.click("#history-model-clear");
  ui.context.renderCatalog(new Set(), false);
  assert.deepEqual(ui.selected(), []);
  assert.equal(ui.nodes.get("#history-export").disabled, true);
});

test('multi-suite controls send only checked scenes and preserve explicit empty selection on refresh', async () => {
  const run = {id:'run', source:'benchmarks/model', model_group:'model_v1', result_folder:'benchmarks',
    attack_name:'tool_knowledge', suites:['banking','travel','workspace'].map(suite_name=>({suite_name}))};
  const ui = historyUI([run], {folder:'all',backend:'all',models:null,attack:'all'});
  ui.click('#history-model-select-all');
  const checked = () => ui.context.document.querySelectorAll('.history-suite-cb:checked').map(n=>n.value);
  assert.deepEqual(checked(), ['banking','travel','workspace']);
  const change = () => ui.nodes.get('#history-suite-options').handlers.change();
  ui.context.document.querySelectorAll('.history-suite-cb')[0].checked = false;
  change();
  assert.deepEqual(checked(), ['travel','workspace']);
  ui.context.renderCatalog(new Set(['run']),false);
  assert.deepEqual(checked(), ['travel','workspace']);
  const payloads = [], renders = [];
  Object.assign(ui.context, {
    selectedMetricKeys:()=>['utility_rate','attack_success_rate','total_tokens'],
    renderAnalysis:(data,settings)=>renders.push(settings),
    URL:{createObjectURL:()=> 'blob:fixture',revokeObjectURL(){}},
    fetch:async(url,init)=>{payloads.push({url,body:JSON.parse(init.body)});return {
      ok:true,json:async()=>({experiments:[]}),blob:async()=>({}),headers:{get:()=>null}};},
  });
  ui.nodes.get('#history-chart-type').value='bar';
  vm.runInContext(ui.source.slice(ui.source.indexOf('  async function exportAnalysis()'),ui.source.indexOf('  function addOption('))
    +ui.source.slice(ui.source.indexOf('  function updateControls()'),ui.source.indexOf('  function selectedMetricKeys()'))
    +ui.source.slice(ui.source.indexOf('  function analysisSelectionKey()'),ui.source.indexOf('  function clearCharts()')),ui.context);
  await ui.context.analyze(); await ui.context.exportAnalysis();
  assert.deepEqual(payloads,[
    {url:'/api/history/analyze',body:{run_ids:['run'],suites:['travel','workspace'],include_task_records:false}},
    {url:'/api/history/export',body:{run_ids:['run'],suites:['travel','workspace']}},
  ]);
  assert.deepEqual(Array.from(renders[0].suites), ['travel','workspace']);
  const pending = ui.gate.start();
  ui.context.document.querySelectorAll('.history-suite-cb').forEach(n=>{n.checked=false;});
  change();
  assert.equal(ui.gate.isCurrent(pending),false);
  assert.equal(ui.nodes.get('#history-analyze').disabled,true);
  assert.equal(ui.nodes.get('#history-export').disabled,true);
  await ui.context.analyze(); await ui.context.exportAnalysis();
  assert.equal(payloads.length,2);
  ui.context.renderCatalog(new Set(['run']),false);
  assert.deepEqual(checked(),[]);
});

test('multi-suite charts keep separate scenario values while one selected scene uses experiment comparison', () => {
  const run={id:'run',model_suffix:'model_v1',suites:['travel','workspace'].map((suite_name,i)=>({
    suite_name,metrics:{utility_rate:50+i*25,attack_success_rate:25-i*25},overhead:{total_tokens:1000+i*1000}}))};
  const ui=historyUI([{...run,model_group:'model_v1',result_folder:'benchmarks',attack_name:'tool_knowledge'}],{});
  const configs=[];
  Object.assign(ui.context,{chartTheme:()=>({}),renderChartPanel:(_wrap,_key,_title,_desc,config)=>configs.push(config)});
  vm.runInContext(ui.source.slice(ui.source.indexOf('  function renderAnalysis('),ui.source.indexOf('  function renderChartPanel(')),ui.context);
  ui.context.renderAnalysis({experiments:[run]}, {view:'bar',metrics:['utility_rate','total_tokens'],suites:['travel','workspace']});
  assert.deepEqual(Array.from(configs[0].data.labels),['travel','workspace']);
  assert.deepEqual(Array.from(configs[0].data.datasets[0].data),[50,75]);
  assert.deepEqual(Array.from(configs[1].data.datasets[0].data),[1,2]);
  configs.length=0;
  ui.context.renderAnalysis({experiments:[{...run,suites:[run.suites[0]]}]}, {view:'bar',metrics:['utility_rate'],suites:['travel']});
  assert.deepEqual(Array.from(configs[0].data.labels),['v1']);
  assert.deepEqual(Array.from(configs[0].data.datasets[0].data),[50]);
});

test('overview presents one table per result with each scene and a safe total', () => {
  const identity = {id:'agentdojo', repository:'repo', revision:'rev', suite_version:'v', implementation_sha256:'impl', catalog_sha256:'cat'};
  const suite = (suite_name, success) => ({suite_name, benchmark:identity, metrics:{},
    overview:{tsr:{success,valid:2},asr:{success:0,valid:2,source:'records'},tokens:{recorded:1000,complete:false}}});
  const run = {id:'run', model_suffix:'version', source:'results/<example>', benchmark_id:'agentdojo', attack_name:'ignore_previous', suites:[suite('banking',1),suite('travel',2)]};
  const ui = historyUI([{...run,model_group:'version',result_folder:'benchmarks'}], {});
  vm.runInContext(ui.source.slice(ui.source.indexOf('  function renderOverview('), ui.source.indexOf('  function renderSummaryTable(')), ui.context);
  ui.context.renderOverview([run]);
  const cards = ui.nodes.get('#history-overview-cards').children;
  assert.equal(cards.length, 1);
  const card = cards[0], header = card.children[0], body = card.children[1].children[0].children[1];
  assert.equal(card.style.borderLeftColor, ui.context.experimentStyles.run.color);
  assert.match(header.children[1].children[1].textContent, /results\/<example>/);
  assert.equal(header.children[2].textContent, 'ignore_previous');
  assert.equal(body.children.length, 3);
  assert.equal(body.children[0].children[0].textContent, '整体');
  assert.equal(body.children[0].children[1].children[0].textContent, '75.00%');
  assert.equal(body.children[0].children[1].children[1].textContent, '3 / 4');
  assert.equal(body.children[1].children[0].textContent, 'banking');
  assert.equal(body.children[2].children[0].textContent, 'travel');
  assert.equal(body.children[1].children[3].children[1].textContent, '可能不完整');
  ui.context.renderOverview([]);
  assert.match(ui.nodes.get('#history-overview-cards').children[0].textContent, /选择结果/);
});

test('overview keeps unverified scenes separate, retains missing states and distinguishes attacks', () => {
  const overview = (tsr,asr,tokens) => ({tsr,asr,tokens});
  const make = (id, attack_name, suites) => ({id, model_suffix:id, model_group:id, source:id, result_folder:'benchmarks',attack_name,suites});
  const runs = [make('clean','none',[
    {suite_name:'a',benchmark:null,metrics:{},overview:overview({success:0,valid:0},null,{recorded:null,complete:false})},
    {suite_name:'b',benchmark:null,metrics:{},overview:overview({success:1,valid:2,source:'records_unknown'},null,{recorded:0,complete:true})},
  ]), make('observed','tool_knowledge',[
    {suite_name:'a',benchmark:null,metrics:{attack_success_rate:20},overview:overview(null,null,{recorded:42,complete:false})},
  ])];
  const ui = historyUI(runs, {});
  vm.runInContext(ui.source.slice(ui.source.indexOf('  function renderOverview('), ui.source.indexOf('  function renderSummaryTable(')), ui.context);
  ui.context.renderOverview(runs);
  const cards = ui.nodes.get('#history-overview-cards').children;
  assert.equal(cards.length,2);
  assert.notEqual(cards[0].children[0].children[2].className,cards[1].children[0].children[2].className);
  const clean = cards[0].children[1].children[0].children[1].children;
  assert.equal(clean.length,2);
  assert.equal(clean[0].children[1].children[0].textContent,'不适用');
  assert.equal(clean[0].children[2].children[1].textContent,'良性评测');
  assert.equal(clean[0].children[3].children[0].textContent,'未记录');
  assert.match(clean[1].children[1].children[1].textContent,/明细含状态未知/);
  assert.equal(clean[1].children[3].children[0].textContent,'0');
  const row = cards[1].children[1].children[0].children[1].children[0];
  assert.equal(row.children[2].children[0].textContent,'20.00%');
  assert.equal(row.children[2].children[1].textContent,'原汇总；分子 / 分母未记录');
});

test('overview groups attacks and keeps the same natural result order in every group', () => {
  const runs = [
    ['tool_knowledge','model_v10'], ['ignore_previous','model_v2'],
    ['tool_knowledge','model_v2'], ['ignore_previous','model_v10'],
    ['tool_knowledge','model_v1'], ['ignore_previous','model_v1'],
  ].map(([attack_name,model_group]) => ({id:model_group+'/'+attack_name, model_group, model_suffix:model_group,
    source:model_group+'/'+attack_name, result_folder:'benchmarks', attack_name,
    suites:[{suite_name:'travel',benchmark:null,metrics:{},overview:{tsr:null,asr:null,tokens:{recorded:null,complete:false}}}]}));
  const ui = historyUI(runs, {});
  vm.runInContext(ui.source.slice(ui.source.indexOf('  function renderOverview('), ui.source.indexOf('  function renderSummaryTable(')), ui.context);
  ui.context.renderOverview(runs);
  const order = ui.nodes.get('#history-overview-cards').children.map(card =>
    [card.children[0].children[2].textContent, card.children[0].children[1].children[0].textContent]);
  assert.deepEqual(order, [
    ['ignore_previous','v1'], ['ignore_previous','v2'], ['ignore_previous','v10'],
    ['tool_knowledge','v1'], ['tool_knowledge','v2'], ['tool_knowledge','v10'],
  ]);
  assert.equal(runs[0].attack_name,'tool_knowledge');
});
