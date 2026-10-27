const test = require('node:test');
const assert = require('node:assert/strict');
const {overviewGroups} = require('../dashboard/static/js/history_selection.js');

test('overview totals valid counts within one recorded benchmark, never across runs', () => {
  const suite = (name, tsr, asr, tokens) => ({suite_name:name, benchmark:{id:'dojo',repository:'repo',revision:'rev',suite_version:'v',implementation_sha256:'impl',catalog_sha256:'catalog'}, overview:{tsr, asr, tokens}});
  const result = overviewGroups([{id:'a', suites:[
    suite('travel', {success:2, valid:3}, {success:1, valid:3}, {recorded:100, complete:true}),
    suite('slack', {success:3, valid:4}, {success:0, valid:4}, {recorded:200, complete:false}),
  ]}, {id:'b', suites:[suite('travel', {success:0, valid:1}, null, {recorded:null, complete:false})]}]);
  assert.equal(result.length, 2);
  assert.deepEqual(result[0].tsr, {success:5, valid:7});
  assert.deepEqual(result[0].asr, {success:1, valid:7});
  assert.deepEqual(result[0].tokens, {recorded:300, complete:false});
  assert.equal(result[1].asr, null);
  assert.equal(result[1].tokens.recorded, null);
});

test('unknown or conflicting benchmark identities and missing counts remain separate or unknown', () => {
  const suites = [
    {suite_name:'a', benchmark:null, overview:{tsr:{success:1,valid:1},asr:null,tokens:{recorded:0,complete:false}}},
    {suite_name:'b', benchmark:{id:'other'}, overview:{tsr:null,asr:null,tokens:{recorded:null,complete:false}}},
  ];
  const groups = overviewGroups([{id:'run',suites}]);
  assert.equal(groups.length, 2);
  assert.equal(groups[1].tsr, null);
  assert.equal(groups[0].tokens.recorded, 0);
});
