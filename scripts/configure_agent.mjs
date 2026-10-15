// Operator-only provisioning. Only the selected key is copied; no .env is mounted.
import fs from 'node:fs';
import path from 'node:path';
import {parseArgs, parseEnv} from 'node:util';
import {randomBytes} from 'node:crypto';

const {values} = parseArgs({options: {'deepseek-env': {type: 'string'}, output: {type: 'string'},
  'daily-requests': {type: 'string', default: '100'}, model: {type: 'string', default: 'deepseek-flash'}}});
if (!values['deepseek-env'] || !values.output) throw new Error('Provide --deepseek-env and --output');
const daily = Number(values['daily-requests']);
if (!Number.isInteger(daily) || daily < 1 || daily > 1000) throw new Error('Invalid daily budget');
if (!['deepseek-flash', 'deepseek-v4-flash', 'deepseek-v4-pro'].includes(values.model)) throw new Error('Invalid model');
const source = parseEnv(fs.readFileSync(values['deepseek-env'], 'utf8'));
const key = source.DEEPSEEK_API_KEY;
if (!key || key.length < 20 || /\s/.test(key)) throw new Error('DeepSeek credential is missing');
const directory = path.resolve(values.output);
fs.mkdirSync(directory, {recursive: true, mode: 0o700});
const configPath = path.join(directory, 'agent.json'), tokenPath = path.join(directory, 'agent-token');
if (fs.existsSync(configPath) || fs.existsSync(tokenPath)) throw new Error('Existing credentials are preserved');
const token = randomBytes(32).toString('hex');
fs.writeFileSync(configPath, JSON.stringify({model: values.model, apiKey: key, token,
  dailyRequests: daily, codexFallback: false}, null, 2) + '\n', {flag: 'wx', mode: 0o600});
fs.writeFileSync(tokenPath, token + '\n', {flag: 'wx', mode: 0o600});
console.log(JSON.stringify({configured: true, model: values.model, dailyRequests: daily, codexFallback: false}));
