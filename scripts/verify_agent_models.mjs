// Explicit, bounded qualification: one real proposal per model, no image calls.
import fs from 'node:fs';
import path from 'node:path';
import {parseArgs} from 'node:util';
import {pathToFileURL} from 'node:url';
import {createHash, randomBytes} from 'node:crypto';
import {DatabaseSync} from 'node:sqlite';
import assert from 'node:assert/strict';
import {createService} from '../agent/server.mjs';
import {boundedJSON, deepseekProvider} from '../agent/provider.mjs';

const {values} = parseArgs({options: {
  config: {type: 'string'}, sdk: {type: 'string'}, output: {type: 'string'}, live: {type: 'boolean'},
}});
if (!values.live || !values.config || !values.sdk || !values.output)
  throw new Error('Provide --live --config --sdk --output; this makes two text requests');
process.umask(0o077);
const output = path.resolve(values.output);
fs.mkdirSync(output, {recursive: false, mode: 0o700});
const config = JSON.parse(fs.readFileSync(values.config, 'utf8'));
const lock = JSON.parse(fs.readFileSync(new URL('../agent/aginti.lock.json', import.meta.url)));
assert.equal(createHash('sha256').update(fs.readFileSync(values.sdk)).digest('hex'), lock.sha256);
const {createRestrictedApplicationRunner: createRunner} = await import(pathToFileURL(path.resolve(values.sdk)));
const listed = await fetch('https://api.deepseek.com/models', {
  headers: {Authorization: `Bearer ${config.apiKey}`}, redirect: 'error', signal: AbortSignal.timeout(20000),
});
assert.equal(listed.status, 200);
const models = (await boundedJSON(listed)).data.map(({id, name}) => ({id, name}));
fs.writeFileSync(path.join(output, 'models.json'), JSON.stringify(models, null, 2));
const evidence = [];
for (const model of ['deepseek-flash', 'deepseek-v4-pro']) {
  assert(models.some(row => row.id === model), `Model not offered: ${model}`);
  const selected = {...config, model, token: randomBytes(32).toString('hex'), dailyRequests: 2};
  const db = new DatabaseSync(path.join(output, model + '.sqlite'));
  const server = createService({config: selected, db, createRunner, provider: deepseekProvider(selected)});
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const request = {id: randomBytes(32).toString('hex'), title: 'Greeting QA', language: 'en', maximum: 1,
    items: [], history: [], text: 'Create one cheerful greeting sticker for a red panda. Caption Hello, with a natural hand wave. Propose the table now.'};
  const call = () => fetch(`http://127.0.0.1:${server.address().port}/propose`, {
    method: 'POST', headers: {'Content-Type': 'application/json', Authorization: `Bearer ${selected.token}`},
    body: JSON.stringify(request), signal: AbortSignal.timeout(85000),
  });
  const start = Date.now();
  try {
    const response = await call();
    const result = await response.json();
    fs.writeFileSync(path.join(output, model + '.json'), JSON.stringify({status: response.status, result}, null, 2));
    assert.equal(response.status, 200);
    assert.equal(result.model, model);
    assert.equal(result.proposal.items.length, 1);
    assert(result.proposal.items[0].action.length > 10);
    const replay = await call();
    assert.equal(replay.status, 200);
    assert.deepEqual(await replay.json(), result);
    assert.equal(db.prepare('SELECT COUNT(*) AS n FROM requests').get().n, 1);
    evidence.push({model, name: models.find(row => row.id === model).name,
      elapsed_seconds: (Date.now() - start) / 1000, reply: result.proposal.reply,
      items: result.proposal.items, replay_identical: true, text_requests: 1, media_requests: 0});
  } finally {
    await new Promise(resolve => server.close(resolve));
    db.close();
  }
}
fs.writeFileSync(path.join(output, 'result.json'), JSON.stringify(evidence, null, 2));
console.log(JSON.stringify(evidence, null, 2));
