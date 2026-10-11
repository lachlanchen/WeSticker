import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {guardedFetch} from '../server/aginti-runner.mjs';

const submit = 'https://grsaiapi.com/v1/draw/nano-banana';
const options = {method: 'POST', body: JSON.stringify({prompt: 'Hello'})};

test('paid submission occurs once, including restart and retries', async () => {
  const folder = await fs.mkdtemp(path.join(os.tmpdir(), 'aginti-test-'));
  let calls = 0;
  const network = async (_, opts) => {
    calls++; assert.equal(opts.redirect, 'error');
    return Response.json({data: {id: 'provider-job'}});
  };
  try {
    const first = guardedFetch(folder, network);
    assert.equal((await (await first(submit, options)).json()).data.id, 'provider-job');
    await first(submit, options);
    await guardedFetch(folder, network)(submit, options);
    assert.equal(calls, 1);
    await assert.rejects(first(submit, {...options, body: 'changed'}), /changed/);
    assert.equal(calls, 1);
  } finally { await fs.rm(folder, {recursive: true}); }
});

test('lost reply is held across restarts rather than charged again', async () => {
  const folder = await fs.mkdtemp(path.join(os.tmpdir(), 'aginti-test-'));
  let calls = 0;
  const network = async () => { calls++; throw new Error('fetch failed'); };
  try {
    await assert.rejects(guardedFetch(folder, network)(submit, options), /fetch failed/);
    await assert.rejects(guardedFetch(folder, network)(submit, options), /uncertain/);
    assert.equal(calls, 1);
  } finally { await fs.rm(folder, {recursive: true}); }
});

test('transient HTTP response cannot cause a second POST', async () => {
  const folder = await fs.mkdtemp(path.join(os.tmpdir(), 'aginti-test-'));
  let calls = 0;
  const network = async () => { calls++; return new Response('{}', {status: 503}); };
  try {
    const transport = guardedFetch(folder, network);
    for (let i = 0; i < 3; i++) assert.equal((await transport(submit, options)).status, 503);
    assert.equal(calls, 1);
    await assert.rejects(transport('https://other.example/charge', options), /Unexpected/);
    await assert.rejects(transport('https://other.example/image', {headers: {Authorization: 'secret'}}), /Unexpected/);
  } finally { await fs.rm(folder, {recursive: true}); }
});
