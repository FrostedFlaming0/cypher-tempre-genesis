import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import fs from 'node:fs/promises';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { Wallet, parseUnits } from 'ethers';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const dashboardRoot = path.resolve(__dirname, '..');
const tokenAddress = '0x08Df470d41C11Ba5Cb60242747D76C65Ca52c94c';
const recipientAddress = '0x7932CCa1BD502d6850842c423d21f527de47A0Ca';
const transferTopic = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef';
const transferSelector = '0xa9059cbb';

function hex32(value) {
  return `0x${BigInt(value).toString(16).padStart(64, '0')}`;
}

function padAddressTopic(address) {
  return `0x${'0'.repeat(24)}${address.toLowerCase().slice(2)}`;
}

function transferData(recipient, amountRaw) {
  return `${transferSelector}${recipient.toLowerCase().slice(2).padStart(64, '0')}${amountRaw.toString(16).padStart(64, '0')}`;
}

function encodeAbiString(value) {
  const encoded = Buffer.from(value, 'utf8').toString('hex');
  const padded = encoded.padEnd(Math.ceil(encoded.length / 64) * 64, '0');
  return `0x${'20'.padStart(64, '0')}${BigInt(encoded.length / 2).toString(16).padStart(64, '0')}${padded}`;
}

function accessMessage(config, account, txHash) {
  return config.accessMessageTemplate
    .replace('{account}', account.toLowerCase())
    .replace('{txHash}', txHash.toLowerCase());
}

async function readJson(req) {
  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  return JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}');
}

async function createSkillRoot() {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'ctdash-skill-root-'));
  await fs.mkdir(path.join(root, 'registry'), { recursive: true });
  await fs.mkdir(path.join(root, 'chain', 'blockspace', 'blobs'), { recursive: true });
  await fs.writeFile(path.join(root, 'SKILL.md'), '# Test Skill\n');
  await fs.writeFile(path.join(root, 'timechain.py'), '# test placeholder\n');
  await fs.writeFile(path.join(root, 'registry', 'modalities.json'), JSON.stringify({ modalities: [] }));
  await fs.writeFile(path.join(root, 'registry', 'senses.json'), JSON.stringify({ senses: [] }));
  await fs.writeFile(path.join(root, 'chain', 'blockspace', 'index.json'), '{}');
  return root;
}

async function startMockRpc({ payer, txHash, amountRaw }) {
  const blockNumber = 100n;
  const timestamp = BigInt(Math.floor(Date.now() / 1000));
  const calls = [];
  const server = http.createServer(async (req, res) => {
    try {
      const body = await readJson(req);
      calls.push(body.method);
      const params = body.params || [];
      let result = '0x';
      if (body.method === 'eth_call') {
        const data = String(params[0]?.data || '').toLowerCase();
        if (data === '0x313ce567') result = hex32(18n);
        else if (data === '0x95d89b41') result = encodeAbiString('CPHY');
        else if (data === '0x06fdde03') result = encodeAbiString('Cypher Tempre Token');
      } else if (body.method === 'eth_getTransactionByHash') {
        result = {
          hash: txHash,
          from: payer.address,
          to: tokenAddress,
          input: transferData(recipientAddress, amountRaw),
        };
      } else if (body.method === 'eth_getTransactionReceipt') {
        result = {
          status: '0x1',
          blockNumber: hex32(blockNumber),
          logs: [{
            address: tokenAddress,
            topics: [transferTopic, padAddressTopic(payer.address), padAddressTopic(recipientAddress)],
            data: hex32(amountRaw),
          }],
        };
      } else if (body.method === 'eth_blockNumber') {
        result = hex32(blockNumber);
      } else if (body.method === 'eth_getBlockByNumber') {
        result = { timestamp: hex32(timestamp) };
      }
      res.writeHead(200, { 'content-type': 'application/json' });
      res.end(JSON.stringify({ jsonrpc: '2.0', id: body.id, result }));
    } catch (error) {
      res.writeHead(500, { 'content-type': 'application/json' });
      res.end(JSON.stringify({ error: error.message }));
    }
  });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  const { port } = server.address();
  return {
    url: `http://127.0.0.1:${port}`,
    calls,
    close: () => new Promise((resolve) => server.close(resolve)),
  };
}

async function startDashboard({ rpcUrl, skillRoot }) {
  const serverPort = 20_000 + Math.floor(Math.random() * 20_000);
  const child = spawn(process.execPath, ['server.mjs'], {
    cwd: dashboardRoot,
    env: {
      ...process.env,
      BASE_RPC_URL: rpcUrl,
      CT_DASHBOARD_ROOT: skillRoot,
      CT_DASHBOARD_HOST: '127.0.0.1',
      CT_DASHBOARD_PORT: String(serverPort),
      CT_GATE_CONFIRMATIONS: '1',
      CT_GATE_PAYMENT_SESSION_GRACE_MS: '900000',
      CT_GATE_VERIFY_RATE_LIMIT_MAX: '10',
    },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  let output = '';
  child.stdout.on('data', (chunk) => { output += chunk.toString(); });
  child.stderr.on('data', (chunk) => { output += chunk.toString(); });
  await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(`Dashboard did not start:\n${output}`)), 10_000);
    const checkReady = () => {
      if (output.includes('Cypher Tempre Dashboard listening')) {
        clearTimeout(timer);
        resolve();
      }
    };
    child.stdout.on('data', checkReady);
    checkReady();
    child.on('exit', (code) => {
      clearTimeout(timer);
      reject(new Error(`Dashboard exited with ${code}:\n${output}`));
    });
  });
  return {
    baseUrl: `http://127.0.0.1:${serverPort}`,
    stop: () => {
      child.kill('SIGTERM');
      return new Promise((resolve) => child.once('exit', resolve));
    },
  };
}

function createClient(baseUrl) {
  let cookie = '';
  return async function request(pathname, { method = 'GET', body } = {}) {
    const response = await fetch(`${baseUrl}${pathname}`, {
      method,
      headers: {
        ...(body ? { 'content-type': 'application/json' } : {}),
        ...(cookie ? { cookie } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    });
    const setCookie = response.headers.get('set-cookie');
    if (setCookie) cookie = setCookie.split(';')[0];
    const text = await response.text();
    return {
      status: response.status,
      body: text ? JSON.parse(text) : null,
    };
  };
}

test('payment unlock requires a nonce-bound signature from the payer account', async (t) => {
  const payer = Wallet.createRandom();
  const other = Wallet.createRandom();
  const txHash = `0x${'ab'.repeat(32)}`;
  const amountRaw = parseUnits('10000', 18);
  const skillRoot = await createSkillRoot();
  const rpc = await startMockRpc({ payer, txHash, amountRaw });
  const dashboard = await startDashboard({ rpcUrl: rpc.url, skillRoot });
  t.after(async () => {
    await dashboard.stop();
    await rpc.close();
    await fs.rm(skillRoot, { recursive: true, force: true });
  });

  const request = createClient(dashboard.baseUrl);
  const configResponse = await request('/api/gate/config');
  assert.equal(configResponse.status, 200);
  const config = configResponse.body;

  const unsigned = await request('/api/gate/verify', {
    method: 'POST',
    body: { txHash },
  });
  assert.equal(unsigned.status, 400);
  assert.match(unsigned.body.error, /account|signature/i);

  const wrongSignature = await other.signMessage(accessMessage(config, payer.address, txHash));
  const wrongSigner = await request('/api/gate/verify', {
    method: 'POST',
    body: { txHash, account: payer.address, signature: wrongSignature },
  });
  assert.equal(wrongSigner.status, 400);
  assert.match(wrongSigner.body.error, /signature/i);

  const signature = await payer.signMessage(accessMessage(config, payer.address, txHash));
  const verified = await request('/api/gate/verify', {
    method: 'POST',
    body: { txHash, account: payer.address, signature },
  });
  assert.equal(verified.status, 200);
  assert.equal(verified.body.result.account, payer.address.toLowerCase());

  const summary = await request('/api/timechain/summary');
  assert.equal(summary.status, 200);
});
