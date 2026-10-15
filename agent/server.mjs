import http from 'node:http';
import fs from 'node:fs';
import {createHash, timingSafeEqual} from 'node:crypto';
import {DatabaseSync} from 'node:sqlite';
import {pathToFileURL} from 'node:url';
import {validateRequest, instructions, proposalSchema} from './contract.mjs';
import {deepseekProvider} from './provider.mjs';

const hash = value => createHash('sha256').update(value).digest('hex');
const MAX_BODY = 65536;
function send(res, status, data) {
  if (res.destroyed) return;
  res.writeHead(status, {'Content-Type': 'application/json', 'Cache-Control': 'no-store'});
  res.end(JSON.stringify(data));
}

export function createService({config, db, createRunner, provider}) {
  if (typeof config.token !== 'string' || config.token.length < 48 ||
      !Number.isInteger(config.dailyRequests) || config.dailyRequests < 1 || config.dailyRequests > 1000)
    throw new Error('CONFIG_INVALID');
  db.exec(`PRAGMA journal_mode=WAL;
    CREATE TABLE IF NOT EXISTS requests(id TEXT PRIMARY KEY, digest TEXT NOT NULL,
      created INTEGER NOT NULL, state TEXT NOT NULL, result TEXT);
    UPDATE requests SET state='uncertain' WHERE state='working';`);
  const expireReplies = () => db.prepare(
    'UPDATE requests SET result=NULL WHERE created<? AND result IS NOT NULL'
  ).run(Date.now() - 86400000);
  expireReplies();
  const retention = setInterval(expireReplies, 60000);
  retention.unref();
  let active = false;
  const pending = new Set();
  const trackedProvider = {supportsImages: false, complete(...args) {
    const task = Promise.resolve().then(() => provider.complete(...args));
    pending.add(task);
    task.then(() => pending.delete(task), () => pending.delete(task));
    return task;
  }};
  const server = http.createServer(async (req, res) => {
    if (req.method === 'GET' && req.url === '/health') {
      return send(res, 200, {ok: true, app: 'westicker-agent', engine: 'aginti-deepseek',
        model: config.model, protocol: 'aginti-restricted-application-v1', tools: [],
        codexFallback: false, busy: active || pending.size > 0});
    }
    const supplied = Buffer.from(req.headers.authorization || '');
    const expected = Buffer.from(`Bearer ${config.token}`);
    if (supplied.length !== expected.length || !timingSafeEqual(supplied, expected)) return send(res, 401, {error: 'UNAUTHORIZED'});
    if (req.method !== 'POST' || req.url !== '/propose') return send(res, 404, {error: 'NOT_FOUND'});
    let body;
    try {
      if (Number(req.headers['content-length']) > MAX_BODY || !req.headers['content-type']?.startsWith('application/json')) throw new Error();
      let bytes = 0;
      const chunks = [];
      for await (const chunk of req) {
        bytes += chunk.length;
        if (bytes > MAX_BODY) throw new Error();
        chunks.push(chunk);
      }
      body = validateRequest(JSON.parse(Buffer.concat(chunks).toString('utf8')));
    } catch { return send(res, 400, {error: 'INVALID_INPUT'}); }
    const digest = hash(JSON.stringify(body));
    expireReplies();
    const prior = db.prepare('SELECT * FROM requests WHERE id=?').get(body.id);
    if (prior) {
      if (prior.digest !== digest) return send(res, 409, {error: 'REQUEST_CHANGED'});
      if (prior.state === 'ready' && prior.result) return send(res, 200, JSON.parse(prior.result));
      return send(res, 409, {error: 'REQUEST_HELD'});
    }
    if (active || pending.size) return send(res, 429, {error: 'BUSY'});
    const today = Math.floor(Date.now() / 86400000) * 86400000;
    if (db.prepare('SELECT COUNT(*) AS n FROM requests WHERE created>=?').get(today).n >= config.dailyRequests)
      return send(res, 429, {error: 'DAILY_LIMIT'});
    active = true;
    const abort = new AbortController();
    const disconnect = () => { if (!res.writableEnded) abort.abort(); };
    res.on('close', disconnect);
    db.prepare("INSERT INTO requests VALUES(?,?,?,'working',NULL)").run(body.id, digest, Date.now());
    try {
      const runner = createRunner({provider: trackedProvider, tools: [], instructions: instructions(body),
        outputSchema: proposalSchema(body.maximum),
        limits: {maxSteps: 1, maxToolCalls: 1, maxConcurrency: 1, timeoutMs: 60000,
          maxOutputTokens: 3500, maxContextBytes: 65536, maxResultBytes: 32768}});
      const result = await runner.run({input: [{type: 'text', text: JSON.stringify({
        title: body.title, items: body.items, request: body.text})}], history: body.history}, {signal: abort.signal});
      if (abort.signal.aborted) throw new Error('CANCELLED');
      const payload = {id: body.id, engine: 'aginti-deepseek', model: config.model,
        proposal: result.proposal, usage: result.usage};
      db.prepare("UPDATE requests SET state='ready',result=? WHERE id=?").run(JSON.stringify(payload), body.id);
      send(res, 200, payload);
    } catch {
      db.prepare("UPDATE requests SET state='failed' WHERE id=?").run(body.id);
      send(res, 502, {error: 'AGENT_INCOMPLETE'});
    } finally {
      res.removeListener('close', disconnect);
      active = false;
    }
  });
  server.on('close', () => clearInterval(retention));
  server.requestTimeout = 15000;
  server.headersTimeout = 10000;
  server.keepAliveTimeout = 5000;
  return server;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  process.umask(0o077);
  try {
    const config = JSON.parse(fs.readFileSync(process.env.WESTICKER_AGENT_CONFIG || '/run/secrets/agent.json', 'utf8'));
    if (config.codexFallback) throw new Error('FALLBACK_NOT_QUALIFIED');
    const {createRestrictedApplicationRunner} = await import('/opt/aginti/src/restricted-application.js');
    const db = new DatabaseSync('/data/requests.sqlite');
    const provider = deepseekProvider(config);
    const server = createService({config, db, createRunner: createRestrictedApplicationRunner, provider});
    server.listen(8001, '0.0.0.0');
    process.on('SIGTERM', () => server.close(() => { db.close(); process.exit(0); }));
  } catch { console.error('WeSticker agent configuration/startup failed.'); process.exitCode = 1; }
}
