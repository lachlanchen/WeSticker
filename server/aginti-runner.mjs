import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { createHash } from 'node:crypto';

const HOST = 'https://grsaiapi.com';
const SUBMIT = `${HOST}/v1/draw/nano-banana`;
const POLL = `${HOST}/v1/draw/result`;
const digest = value => createHash('sha256').update(value).digest('hex');

async function readJSON(file) {
  try { return JSON.parse(await fs.readFile(file, 'utf8')); }
  catch (error) { if (error.code === 'ENOENT') return null; throw error; }
}

async function durableJSON(file, value) {
  const handle = await fs.open(file, 'wx', 0o600);
  try { await handle.writeFile(JSON.stringify(value)); await handle.sync(); }
  finally { await handle.close(); }
}

// AgInTi may retry transient submit failures. This process-local transport guard
// records the one permitted request before network I/O, including across restarts.
export function guardedFetch(folder, transport = fetch) {
  return async (input, options = {}) => {
    const url = String(input);
    if (url === SUBMIT) {
      if (options.method !== 'POST') throw new Error('Unexpected image method');
      const fingerprint = digest(String(options.body));
      const intentFile = path.join(folder, 'network-intent.json');
      const responseFile = path.join(folder, 'network-response.json');
      const prior = await readJSON(intentFile);
      if (prior) {
        if (prior.fingerprint !== fingerprint) throw new Error('Image request changed');
        const saved = await readJSON(responseFile);
        if (!saved) throw new Error('Image outcome uncertain; submission is held');
        return new Response(saved.body, {status: saved.status, headers: {'Content-Type': 'application/json'}});
      }
      await durableJSON(intentFile, {fingerprint, created: new Date().toISOString()});
      const response = await transport(url, {...options, redirect: 'error'});
      const body = await response.text();
      if (body.length > 1_000_000) throw new Error('Oversized image response');
      await durableJSON(responseFile, {status: response.status, body});
      return new Response(body, {status: response.status, headers: {'Content-Type': 'application/json'}});
    }
    if (url === POLL && options.method === 'POST') {
      return transport(url, {...options, redirect: 'error'});
    }
    const parsed = new URL(url);
    if (parsed.protocol !== 'https:' || parsed.username || parsed.password ||
        (options.method && options.method !== 'GET') || new Headers(options.headers).has('authorization')) {
      throw new Error('Unexpected image transport');
    }
    // Download URLs originate in the authenticated provider response, not user input.
    return transport(url, {...options, redirect: 'error'});
  };
}

async function run(request) {
  process.umask(0o077);
  const root = await fs.realpath(request.agintiRoot);
  const workspace = await fs.realpath(request.workspace);
  const {loadProjectEnv} = await import(pathToFileURL(path.join(root, 'src/project.js')));
  loadProjectEnv(workspace);
  if (request.mode === 'moderate') {
    if (!process.env.OPENAI_API_KEY) throw new Error('Safety provider unavailable');
    const response = await fetch('https://api.openai.com/v1/moderations', {
      method: 'POST', redirect: 'error', signal: AbortSignal.timeout(60000),
      headers: {'Authorization': `Bearer ${process.env.OPENAI_API_KEY}`, 'Content-Type': 'application/json'},
      body: JSON.stringify({model: 'omni-moderation-latest', input: request.input}),
    });
    if (!response.ok) throw new Error('Safety provider rejected request');
    const data = await response.json();
    return {results: data.results?.map(item => ({flagged: item.flagged}))};
  }
  if (request.mode === 'doctor') {
    return {image: Boolean(process.env.GRSAI || process.env.GRSAI_API_KEY),
      safety: Boolean(process.env.OPENAI_API_KEY)};
  }
  if (request.mode !== 'image') throw new Error('Unsupported operation');
  const folder = await fs.realpath(request.folder);
  if (!folder.startsWith(workspace + path.sep)) throw new Error('Invalid render folder');
  const files = request.references;
  if (!Array.isArray(files) || !files.length || files.length > 5) throw new Error('Invalid references');
  for (const file of files) {
    const actual = await fs.realpath(file);
    if (!actual.startsWith(workspace + path.sep) || (await fs.stat(actual)).size > 4_000_000)
      throw new Error('Reference exceeds the AgInTi workspace or size limit');
  }
  globalThis.fetch = guardedFetch(folder);
  const {generateImage} = await import(pathToFileURL(path.join(root, 'src/auxiliary-tools.js')));
  const result = await generateImage({
    prompt: request.prompt, provider: 'grsai', model: request.model,
    referenceImages: files, outputDir: path.relative(workspace, folder), outputStem: 'original',
    format: 'png', imageSize: '1K', aspectRatio: '1:1',
    pollTimeoutMs: 600000, requestTimeoutMs: 60000,
  }, {baseDir: workspace, workspaceRoot: workspace, allowAuxiliaryTools: true,
    allowFileTools: true, workspaceWritePolicy: 'allow', sandboxMode: 'workspace'});
  if (!result.ok || result.imagePaths?.length !== 1) throw new Error('No unique AgInTi output');
  return {ok: true, path: path.resolve(workspace, result.imagePaths[0])};
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  try {
    const input = await fs.readFile(process.argv[2], 'utf8');
    console.log(JSON.stringify(await run(JSON.parse(input))));
  } catch {
    // Provider exceptions may contain URLs or private reference names.
    console.error('AgInTi operation incomplete; inspect the private job receipt.');
    process.exitCode = 1;
  }
}
