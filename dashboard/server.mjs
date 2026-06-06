import crypto from 'node:crypto';
import { execFile } from 'node:child_process';
import fs from 'node:fs/promises';
import fsSync from 'node:fs';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';
import { verifyMessage } from 'ethers';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '..');
const publicDir = path.join(__dirname, 'public');
const execFileAsync = promisify(execFile);

const HOST = process.env.CT_DASHBOARD_HOST || '127.0.0.1';
const PORT = Number(process.env.CT_DASHBOARD_PORT || 8788);
const BASE_CHAIN_ID = 8453;
const BASE_CHAIN_ID_HEX = '0x2105';
const BASE_RPC_URL = process.env.BASE_RPC_URL || 'https://mainnet.base.org';
const TOKEN_ADDRESS = checksumish(process.env.CT_GATE_TOKEN || '0x08Df470d41C11Ba5Cb60242747D76C65Ca52c94c');
const TOKEN_SYMBOL_FALLBACK = process.env.CT_GATE_TOKEN_SYMBOL || 'CPHY';
const TOKEN_DECIMALS_FALLBACK = Number(process.env.CT_GATE_TOKEN_DECIMALS || 18);
const REQUIRED_TOKEN_AMOUNT = process.env.CT_GATE_AMOUNT || '10000';
const RECIPIENT_NAME = process.env.CT_GATE_RECIPIENT_NAME || 'cyberphysics.base.eth';
const RECIPIENT_ADDRESS = checksumish(process.env.CT_GATE_RECIPIENT_ADDRESS || '0x7932CCa1BD502d6850842c423d21f527de47A0Ca');
const REQUIRED_CONFIRMATIONS = Math.max(1, Number(process.env.CT_GATE_CONFIRMATIONS || 1));
const PAYMENT_SESSION_GRACE_MS = Math.max(120_000, Number(process.env.CT_GATE_PAYMENT_SESSION_GRACE_MS || 24 * 60 * 60_000));
const WALLETCONNECT_PROJECT_ID = process.env.CT_WALLETCONNECT_PROJECT_ID || '';
const SESSION_TTL_MS = Math.max(10 * 60_000, Number(process.env.CT_DASHBOARD_SESSION_TTL_MS || 4 * 60 * 60_000));
const DEV_UNLOCK = process.env.CT_DASHBOARD_DEV_UNLOCK === '1';
const MAX_RING_DETAIL_BYTES = Number(process.env.CT_DASHBOARD_MAX_RING_DETAIL_BYTES || 512_000);
const MAX_BLOB_PREVIEW_BYTES = Number(process.env.CT_DASHBOARD_MAX_BLOB_PREVIEW_BYTES || 128_000);
const DOMAIN_BLOB_TEXT_LIMIT = Number(process.env.CT_DASHBOARD_DOMAIN_BLOB_TEXT_LIMIT || 64_000);
const BRIDGE_TOKEN_TTL_MS = Math.max(10 * 60_000, Number(process.env.CT_DASHBOARD_BRIDGE_TOKEN_TTL_MS || 24 * 60 * 60_000));
const PUBLIC_ORIGINS = new Set(
  (process.env.CT_DASHBOARD_PUBLIC_ORIGINS || 'https://cyphertempre.ai,https://www.cyphertempre.ai')
    .split(',')
    .map((origin) => origin.trim().replace(/\/$/, ''))
    .filter(Boolean),
);
const LOCAL_ORIGIN_HOSTS = new Set(['localhost', '127.0.0.1', '::1', '[::1]']);
const BRIDGE_PAIR_CODE = normalizePairingCode(process.env.CT_DASHBOARD_PAIR_CODE || crypto.randomBytes(5).toString('hex'));

const TRANSFER_TOPIC = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef';
const TRANSFER_SELECTOR = '0xa9059cbb';
const ERC20_CALLS = {
  decimals: '0x313ce567',
  symbol: '0x95d89b41',
  name: '0x06fdde03',
};

const sessions = new Map();
const bridgeTokens = new Map();
let tokenMetaCache = null;
let timechainRoot = null;
let usedPaymentsCache = null;

function checksumish(value) {
  if (!/^0x[0-9a-fA-F]{40}$/.test(value || '')) {
    throw new Error(`Invalid EVM address: ${value}`);
  }
  return value;
}

function lower(value) {
  return String(value || '').toLowerCase();
}

function evmAddressFrom(value) {
  if (!value) return null;
  if (typeof value === 'object') {
    return evmAddressFrom(value.address || value.caipAddress || value.account);
  }
  const text = String(value).trim();
  const direct = text.match(/^0x[0-9a-fA-F]{40}$/);
  if (direct) return direct[0];
  const caip = text.match(/(?:^|:)((?:0x)[0-9a-fA-F]{40})$/);
  return caip ? caip[1] : null;
}

function usableSignature(value) {
  const text = String(value || '').trim();
  return /^0x[0-9a-fA-F]{64,}$/.test(text) ? text : null;
}

function padAddressTopic(address) {
  return `0x${'0'.repeat(24)}${lower(address).slice(2)}`;
}

function parseUnitsDecimal(amount, decimals) {
  const [whole, frac = ''] = String(amount).trim().split('.');
  if (!/^\d+$/.test(whole) || !/^\d*$/.test(frac)) {
    throw new Error(`Invalid decimal amount: ${amount}`);
  }
  const padded = (frac + '0'.repeat(decimals)).slice(0, decimals);
  return BigInt(`${whole}${padded}`.replace(/^0+/, '') || '0');
}

function toHexQuantity(value) {
  return `0x${BigInt(value).toString(16)}`;
}

function sha256Hex(buffer) {
  return crypto.createHash('sha256').update(buffer).digest('hex');
}

function normalizePairingCode(value) {
  const compact = String(value || '').toUpperCase().replace(/[^A-Z0-9]/g, '');
  return compact.length >= 8 ? compact : compact.padEnd(8, '0');
}

function displayPairingCode(value) {
  return normalizePairingCode(value).replace(/(.{4})(?=.)/g, '$1-');
}

function createSession() {
  const id = crypto.randomBytes(32).toString('hex');
  const nonce = crypto.randomBytes(24).toString('hex');
  const now = Date.now();
  sessions.set(id, {
    id,
    nonce,
    createdAt: now,
    expiresAt: now + SESSION_TTL_MS,
    unlocked: DEV_UNLOCK,
    account: null,
    txHash: null,
  });
  return sessions.get(id);
}

function bridgeRecord(req) {
  const token = String(req.headers['x-ct-bridge-token'] || '').trim();
  if (!token) return null;
  const record = bridgeTokens.get(token);
  if (!record || record.expiresAt < Date.now()) {
    bridgeTokens.delete(token);
    return null;
  }
  return record;
}

function getSession(req, res) {
  const record = bridgeRecord(req);
  if (record) {
    let session = record.sessionId ? sessions.get(record.sessionId) : null;
    if (!session || session.expiresAt < Date.now()) {
      session = createSession();
      record.sessionId = session.id;
    }
    record.expiresAt = Date.now() + BRIDGE_TOKEN_TTL_MS;
    session.expiresAt = Date.now() + SESSION_TTL_MS;
    return session;
  }

  const cookies = parseCookies(req.headers.cookie || '');
  let session = cookies.ctdash ? sessions.get(cookies.ctdash) : null;
  if (!session || session.expiresAt < Date.now()) {
    session = createSession();
    res.setHeader('Set-Cookie', `ctdash=${session.id}; HttpOnly; SameSite=Strict; Path=/; Max-Age=${Math.floor(SESSION_TTL_MS / 1000)}`);
  }
  return session;
}

function parseCookies(header) {
  const out = {};
  for (const part of header.split(';')) {
    const [key, ...rest] = part.trim().split('=');
    if (key) out[key] = rest.join('=');
  }
  return out;
}

function allowedOrigin(req) {
  const origin = req.headers.origin;
  if (!origin) return true;
  try {
    const url = new URL(origin);
    if (LOCAL_ORIGIN_HOSTS.has(url.hostname)) return true;
    return PUBLIC_ORIGINS.has(url.origin);
  } catch {
    return false;
  }
}

function isRemoteOrigin(req) {
  const origin = req.headers.origin;
  if (!origin) return false;
  try {
    return !LOCAL_ORIGIN_HOSTS.has(new URL(origin).hostname);
  } catch {
    return true;
  }
}

function applyCorsHeaders(req, res) {
  const origin = req.headers.origin;
  if (!origin || !allowedOrigin(req)) return;
  res.setHeader('Access-Control-Allow-Origin', origin);
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'content-type, x-ct-bridge-token');
  res.setHeader('Access-Control-Max-Age', '600');
  res.setHeader('Vary', 'Origin, Access-Control-Request-Headers, Access-Control-Request-Method');
  if (req.headers['access-control-request-private-network']) {
    res.setHeader('Access-Control-Allow-Private-Network', 'true');
  }
}

function requireBridgePairing(req) {
  if (!isRemoteOrigin(req)) return;
  if (bridgeRecord(req)) return;
  const error = new Error('Pair this browser with the local Cypher Tempre bridge first.');
  error.status = 401;
  throw error;
}

function securityHeaders() {
  return {
    'Content-Security-Policy': [
      "default-src 'self'",
      "script-src 'self'",
      "style-src 'self' 'unsafe-inline'",
      "connect-src 'self' https://mainnet.base.org https://base-rpc.publicnode.com https://*.walletconnect.com wss://*.walletconnect.com https://*.reown.com wss://*.reown.com https://*.web3modal.org",
      "img-src 'self' data: blob: https:",
      "font-src 'self'",
      "object-src 'none'",
      "base-uri 'none'",
      "form-action 'none'",
      "frame-ancestors 'none'",
    ].join('; '),
    'Cross-Origin-Opener-Policy': 'same-origin',
    'Cross-Origin-Resource-Policy': 'same-origin',
    'Referrer-Policy': 'no-referrer',
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
  };
}

async function rpc(method, params) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 15_000);
  try {
    const response = await fetch(BASE_RPC_URL, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ jsonrpc: '2.0', id: 1, method, params }),
      signal: controller.signal,
    });
    const body = await response.json();
    if (body.error) throw new Error(body.error.message || JSON.stringify(body.error));
    return body.result;
  } finally {
    clearTimeout(timer);
  }
}

function decodeAbiString(hex) {
  if (!hex || hex === '0x') return '';
  const body = hex.slice(2);
  if (body.length <= 64) return Buffer.from(body.replace(/^0+/, ''), 'hex').toString('utf8').replace(/\0+$/g, '');
  const offset = Number(BigInt(`0x${body.slice(0, 64)}`)) * 2;
  const length = Number(BigInt(`0x${body.slice(offset, offset + 64)}`)) * 2;
  return Buffer.from(body.slice(offset + 64, offset + 64 + length), 'hex').toString('utf8');
}

async function getTokenMeta() {
  if (tokenMetaCache) return tokenMetaCache;
  const readCall = async (data) => rpc('eth_call', [{ to: TOKEN_ADDRESS, data }, 'latest']);
  const [decimalsRaw, symbolRaw, nameRaw] = await Promise.allSettled([
    readCall(ERC20_CALLS.decimals),
    readCall(ERC20_CALLS.symbol),
    readCall(ERC20_CALLS.name),
  ]);
  const decimals = decimalsRaw.status === 'fulfilled' ? Number(BigInt(decimalsRaw.value)) : TOKEN_DECIMALS_FALLBACK;
  const symbol = symbolRaw.status === 'fulfilled' ? decodeAbiString(symbolRaw.value) || TOKEN_SYMBOL_FALLBACK : TOKEN_SYMBOL_FALLBACK;
  const name = nameRaw.status === 'fulfilled' ? decodeAbiString(nameRaw.value) || 'Cypher Tempre Token' : 'Cypher Tempre Token';
  const amountRaw = parseUnitsDecimal(REQUIRED_TOKEN_AMOUNT, decimals);
  tokenMetaCache = {
    address: TOKEN_ADDRESS,
    name,
    symbol,
    decimals,
    requiredAmount: REQUIRED_TOKEN_AMOUNT,
    requiredAmountRaw: amountRaw.toString(),
  };
  return tokenMetaCache;
}

function accessMessage(session, account, txHash) {
  return [
    'Cypher Tempre Dashboard access',
    `Session: ${session.nonce}`,
    `Account: ${lower(account)}`,
    `Payment transaction: ${lower(txHash)}`,
    `Token: ${lower(TOKEN_ADDRESS)}`,
    `Recipient: ${lower(RECIPIENT_ADDRESS)}`,
    `Amount: ${REQUIRED_TOKEN_AMOUNT}`,
    `Chain: Base (${BASE_CHAIN_ID})`,
  ].join('\n');
}

function httpError(message, status = 400) {
  const error = new Error(message);
  error.status = status;
  return error;
}

function usedPaymentsPath() {
  return ensureInsideRoot(path.join(timechainRoot, 'chain', 'dashboard-used-payments.json'));
}

async function loadUsedPayments() {
  if (usedPaymentsCache) return usedPaymentsCache;
  const ledger = await readJsonSafe(usedPaymentsPath(), { version: 1, used: {} });
  usedPaymentsCache = {
    version: 1,
    used: ledger && typeof ledger.used === 'object' && !Array.isArray(ledger.used) ? ledger.used : {},
  };
  return usedPaymentsCache;
}

async function requirePaymentUnused(txHash) {
  const ledger = await loadUsedPayments();
  const key = lower(txHash);
  if (ledger.used[key]) {
    const error = new Error('This payment transaction hash has already been redeemed by this local bridge.');
    error.status = 409;
    throw error;
  }
}

async function markPaymentUsed(record) {
  const ledger = await loadUsedPayments();
  const key = lower(record.txHash);
  if (ledger.used[key]) {
    const error = new Error('This payment transaction hash has already been redeemed by this local bridge.');
    error.status = 409;
    throw error;
  }
  ledger.used[key] = {
    txHash: key,
    account: lower(record.account),
    amountRaw: String(record.amountRaw),
    blockNumber: String(record.blockNumber),
    confirmations: String(record.confirmations),
    redeemedAt: new Date().toISOString(),
  };
  const file = usedPaymentsPath();
  await fs.mkdir(path.dirname(file), { recursive: true });
  const tmp = `${file}.${process.pid}.${Date.now()}.tmp`;
  await fs.writeFile(tmp, JSON.stringify(ledger, null, 2));
  await fs.rename(tmp, file);
}

async function verifyPayment({ session, account, txHash, signature }) {
  if (!/^0x[0-9a-fA-F]{64}$/.test(txHash || '')) throw httpError('Invalid transaction hash.');
  await requirePaymentUnused(txHash);

  const signedAccount = evmAddressFrom(account);
  const signedMessage = usableSignature(signature);
  if (signedAccount && signedMessage) {
    const candidates = [
      accessMessage(session, signedAccount, txHash),
      account && String(account) !== signedAccount ? accessMessage(session, account, txHash) : null,
    ].filter(Boolean);
    const recovered = candidates.some((message) => {
      try {
        return lower(verifyMessage(message, signedMessage)) === lower(signedAccount);
      } catch {
        return false;
      }
    });
    if (!recovered) {
      throw httpError('Wallet signature does not match the payer account.');
    }
  }

  const [tx, receipt, latestHex] = await Promise.all([
    rpc('eth_getTransactionByHash', [txHash]),
    rpc('eth_getTransactionReceipt', [txHash]),
    rpc('eth_blockNumber', []),
  ]);
  if (!tx || !receipt) throw httpError('Transaction is not indexed on Base yet.', 404);
  if (receipt.status !== '0x1') throw httpError('Transaction failed on-chain.');
  const payer = lower(tx.from);
  if (signedAccount && payer !== lower(signedAccount)) throw httpError('Payment transaction was not sent by the signed account.');
  if (lower(tx.to) !== lower(TOKEN_ADDRESS)) throw httpError('Payment transaction is not a direct call to the configured token contract.');
  if (!lower(tx.input || tx.data || '').startsWith(TRANSFER_SELECTOR)) {
    throw httpError('Payment transaction is not an ERC-20 transfer call.');
  }

  const latest = BigInt(latestHex);
  const blockNumber = BigInt(receipt.blockNumber);
  const confirmations = latest >= blockNumber ? latest - blockNumber + 1n : 0n;
  if (confirmations < BigInt(REQUIRED_CONFIRMATIONS)) {
    throw httpError(`Waiting for confirmations (${confirmations}/${REQUIRED_CONFIRMATIONS}).`, 425);
  }

  const block = await rpc('eth_getBlockByNumber', [receipt.blockNumber, false]);
  const blockTimeMs = Number(BigInt(block.timestamp)) * 1000;
  if (blockTimeMs + PAYMENT_SESSION_GRACE_MS < session.createdAt) {
    const hours = Math.round(PAYMENT_SESSION_GRACE_MS / 3_600_000);
    throw httpError(`Payment is older than this dashboard session grace window (${hours}h). Open the dashboard, then pay from this session.`);
  }

  const required = BigInt((await getTokenMeta()).requiredAmountRaw);
  const fromTopic = padAddressTopic(payer);
  const toTopic = padAddressTopic(RECIPIENT_ADDRESS);
  const matching = receipt.logs.find((log) => (
    lower(log.address) === lower(TOKEN_ADDRESS)
    && lower(log.topics?.[0]) === TRANSFER_TOPIC
    && lower(log.topics?.[1]) === lower(fromTopic)
    && lower(log.topics?.[2]) === lower(toTopic)
    && BigInt(log.data || '0x0') >= required
  ));
  if (!matching) {
    throw httpError(`No ${REQUIRED_TOKEN_AMOUNT}+ ${(await getTokenMeta()).symbol} Transfer log to ${RECIPIENT_NAME}.`);
  }
  await markPaymentUsed({
    txHash,
    account: payer,
    amountRaw: BigInt(matching.data || '0x0').toString(),
    blockNumber,
    confirmations,
  });

  session.unlocked = true;
  session.account = payer;
  session.txHash = lower(txHash);
  session.expiresAt = Date.now() + SESSION_TTL_MS;
  return {
    account: session.account,
    txHash: session.txHash,
    confirmations: confirmations.toString(),
    blockNumber: blockNumber.toString(),
  };
}

async function discoverTimechainRoot() {
  const explicit = process.env.CT_DASHBOARD_ROOT || process.env.CT_TIMECHAIN_ROOT;
  const candidates = [
    explicit,
    path.join(os.homedir(), '.codex', 'skills', 'cypher-tempre-self-model'),
    path.join(os.homedir(), '.claude', 'skills', 'cypher-tempre-self-model'),
    path.join(os.homedir(), '.openclaw', 'workspace', 'skills', 'cypher-tempre-self-model'),
    path.join(repoRoot, 'skills', 'codex', 'cypher-tempre-self-model'),
  ].filter(Boolean);
  for (const candidate of candidates) {
    const resolved = path.resolve(candidate);
    if (await isSkillRoot(resolved)) return await fs.realpath(resolved);
  }
  throw new Error('No Cypher Tempre skill root found. Set CT_DASHBOARD_ROOT to a local cypher-tempre-self-model directory.');
}

async function isSkillRoot(root) {
  const required = ['SKILL.md', 'timechain.py', 'registry/modalities.json', 'registry/senses.json'];
  for (const rel of required) {
    if (!fsSync.existsSync(path.join(root, rel))) return false;
  }
  return true;
}

function ensureInsideRoot(target) {
  const resolved = path.resolve(target);
  const prefix = `${timechainRoot}${path.sep}`;
  if (resolved !== timechainRoot && !resolved.startsWith(prefix)) {
    throw new Error('Path escapes configured Timechain root.');
  }
  return resolved;
}

async function readJsonSafe(file, fallback) {
  try {
    return JSON.parse(await fs.readFile(file, 'utf8'));
  } catch {
    return fallback;
  }
}

async function loadRings() {
  const ringsPath = ensureInsideRoot(path.join(timechainRoot, 'chain', 'rings.jsonl'));
  if (!fsSync.existsSync(ringsPath)) return [];
  const text = await fs.readFile(ringsPath, 'utf8');
  return text.split(/\r?\n/).filter(Boolean).map((line, lineIndex) => {
    try {
      return JSON.parse(line);
    } catch (error) {
      return { index: lineIndex, ring_type: 'parse-error', payload: { error: error.message }, ring_hash: null };
    }
  });
}

async function loadRegistries() {
  const modalitiesPath = ensureInsideRoot(path.join(timechainRoot, 'registry', 'modalities.json'));
  const sensesPath = ensureInsideRoot(path.join(timechainRoot, 'registry', 'senses.json'));
  const emergentPath = ensureInsideRoot(path.join(timechainRoot, 'registry', 'emergent.json'));
  const modalities = (await readJsonSafe(modalitiesPath, { modalities: [] })).modalities || [];
  const senses = (await readJsonSafe(sensesPath, { senses: [] })).senses || [];
  const emergentRaw = await readJsonSafe(emergentPath, {});
  const emergent = Array.isArray(emergentRaw) ? emergentRaw : Object.values(emergentRaw).flat().filter(Boolean);
  return { modalities, senses, emergent };
}

async function loadBlockspace() {
  const indexPath = ensureInsideRoot(path.join(timechainRoot, 'chain', 'blockspace', 'index.json'));
  const blobsDir = ensureInsideRoot(path.join(timechainRoot, 'chain', 'blockspace', 'blobs'));
  const index = await readJsonSafe(indexPath, {});
  const entries = Object.entries(index).map(([hash, meta]) => ({
    hash,
    size: Number(meta.size || 0),
    filename: meta.filename || '',
    mime: meta.mime || '',
    added_at: meta.added_at || '',
  }));
  let blobFiles = [];
  try {
    blobFiles = await fs.readdir(blobsDir);
  } catch {
    blobFiles = [];
  }
  return {
    entries,
    blobFiles,
    totalBytes: entries.reduce((sum, entry) => sum + entry.size, 0),
  };
}

async function verifyChainWithPython() {
  const script = `
import json, hashlib, sys
from pathlib import Path
root = Path(sys.argv[1]).resolve()
rings_path = root / "chain" / "rings.jsonl"
genesis_prev = "0" * 64
def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
def h(data):
    return hashlib.sha256(data).hexdigest()
def ring_hash(ring):
    return h(canonical({k: v for k, v in ring.items() if k != "ring_hash"}))
ok = True
report = []
rings = []
if rings_path.exists():
    for line in rings_path.read_text().splitlines():
        line = line.strip()
        if line:
            rings.append(json.loads(line))
if not rings:
    print(json.dumps({"ok": True, "report": ["empty chain"], "rings": 0}))
    raise SystemExit
prev = genesis_prev
for i, ring in enumerate(rings):
    if ring.get("index") != i:
        ok = False
        report.append(f"ring {i}: index mismatch (got {ring.get('index')})")
    if ring.get("prev_hash") != prev:
        ok = False
        report.append(f"ring {i}: prev_hash broken")
    recomputed = ring_hash(ring)
    if recomputed != ring.get("ring_hash"):
        ok = False
        report.append(f"ring {i}: ring_hash mismatch")
    for ref in ring.get("blockspace_refs", []):
        bh = ref.get("hash")
        blob = root / "chain" / "blockspace" / "blobs" / str(bh)
        if not blob.exists():
            ok = False
            report.append(f"ring {i}: blockspace blob missing ({ref.get('role')})")
        elif h(blob.read_bytes()) != bh:
            ok = False
            report.append(f"ring {i}: blockspace blob corrupted ({ref.get('role')})")
    prev = ring.get("ring_hash")
if ok:
    report.append(f"verified {len(rings)} rings -> chain intact, all hashes link, blockspace consistent")
print(json.dumps({"ok": ok, "report": report, "rings": len(rings)}))
`;
  try {
    const { stdout } = await execFileAsync('python3', ['-c', script, timechainRoot], {
      timeout: 20_000,
      maxBuffer: 1024 * 1024,
    });
    return JSON.parse(stdout);
  } catch (error) {
    return {
      ok: null,
      report: [`python verifier unavailable: ${error.message}`],
      rings: null,
    };
  }
}

function countBy(items, getKey) {
  const counts = new Map();
  for (const item of items) {
    const key = getKey(item) || 'unknown';
    counts.set(key, (counts.get(key) || 0) + 1);
  }
  return [...counts.entries()].sort((a, b) => b[1] - a[1]).map(([name, count]) => ({ name, count }));
}

function compactRing(ring) {
  const payload = ring.payload || {};
  const labels = payload.labels || {};
  const summary = payload.summary || payload.synthesis || payload.context || payload.event || payload.task || ring.ring_type;
  return {
    index: ring.index,
    type: ring.ring_type,
    timestamp: ring.timestamp,
    hash: ring.ring_hash,
    prevHash: ring.prev_hash,
    brightness: ring.poq?.brightness ?? null,
    blockspaceRefs: ring.blockspace_refs || [],
    summary: truncate(String(summary || ''), 360),
    keywords: labels.keywords || [],
    entities: labels.entities || [],
    modalities: (labels.modalities || []).map((x) => x.name || x.id).slice(0, 8),
    senses: (labels.senses || []).map((x) => x.name || x.id).slice(0, 8),
  };
}

function truncate(value, limit) {
  return value.length > limit ? `${value.slice(0, limit - 1)}…` : value;
}

function ringText(ring) {
  return JSON.stringify(ring.payload || {}) + ' ' + (ring.ring_type || '') + ' ' + JSON.stringify(ring.blockspace_refs || []);
}

function estimateTokens(text) {
  return Math.ceil((text || '').split(/\s+/).filter(Boolean).length * 1.25);
}

const DOMAIN_RULES = [
  ['Timechain & Self-Model', ['timechain', 'ring', 'poq', 'modality', 'modalities', 'sense', 'senses', 'continuum', 'chronosynaptic', 'cambium', 'immune', 'self-model', 'recursive', 'genesis']],
  ['Code & Software', ['code', 'repo', 'repository', 'function', 'class', 'python', 'javascript', 'typescript', 'test', 'commit', 'git', 'source', 'linux', 'bitcoin', 'kubernetes']],
  ['Security & Audit', ['audit', 'vulnerability', 'exploit', 'tamper', 'risk', 'verify', 'verification', 'consensus', 'policy', 'rollback', 'compliance']],
  ['Finance & Markets', ['nasdaq', 'market', 'trading', 'trade', 'drawdown', 'price', 'volume', 'return', 'cagr', 'token', 'wallet', 'payment']],
  ['Blockchain & Web3', ['ethereum', 'base', 'erc20', 'wallet', 'transaction', 'contract', 'bitcoin', 'chain', 'block', 'hash', 'token', 'onchain']],
  ['Biology & Genomics', ['genome', 'dna', 'chromosome', 'sequence', 'entropy', 'gene', 'genomic', 'basepair', 'grch']],
  ['Data Science & Statistics', ['data', 'dataset', 'json', 'csv', 'statistics', 'quantile', 'distribution', 'outlier', 'regression', 'model']],
  ['Documents & Writing', ['document', 'report', 'readme', 'markdown', 'summary', 'poster', 'writing', 'changelog']],
  ['Design & Frontend', ['dashboard', 'frontend', 'ui', 'browser', 'react', 'css', 'layout', 'visual']],
  ['Operations & Packaging', ['release', 'package', 'zip', 'install', 'deploy', 'ci', 'selftest', 'version']],
  ['Law & Governance', ['legal', 'regulation', 'fiduciary', 'sec', 'finra', 'governance', 'compliance']],
  ['Research & Knowledge', ['research', 'paper', 'finding', 'evidence', 'hypothesis', 'analysis', 'source']],
];

async function buildDomains(rings, blockspace) {
  const domains = new Map();
  const add = (name, score, ring, term, tokens) => {
    if (!domains.has(name)) {
      domains.set(name, { name, score: 0, rings: new Set(), terms: new Map(), approxTokens: 0 });
    }
    const d = domains.get(name);
    d.score += score;
    d.approxTokens += tokens;
    if (ring != null) d.rings.add(ring);
    d.terms.set(term, (d.terms.get(term) || 0) + 1);
  };

  for (const ring of rings) {
    const text = ringText(ring).toLowerCase();
    const tokens = estimateTokens(text);
    for (const [domain, terms] of DOMAIN_RULES) {
      for (const term of terms) {
        const hits = text.split(term).length - 1;
        if (hits > 0) add(domain, hits, ring.index, term, tokens);
      }
    }
    const labels = ring.payload?.labels || {};
    for (const keyword of labels.keywords || []) {
      add(`Keyword: ${String(keyword).slice(0, 36)}`, 0.25, ring.index, keyword, Math.max(1, Math.round(tokens / 12)));
    }
    const data = ring.payload?.data || {};
    if (data.language) add(`Language: ${data.language}`, 2, ring.index, data.language, tokens);
    if (data.top_dir) add(`Top Dir: ${data.top_dir}`, 1, ring.index, data.top_dir, tokens);
    if (data.path_role) add(`Role: ${data.path_role}`, 1, ring.index, data.path_role, tokens);
  }

  for (const entry of blockspace.entries) {
    const textBits = [entry.filename, entry.mime].join(' ').toLowerCase();
    for (const [domain, terms] of DOMAIN_RULES) {
      for (const term of terms) {
        const hits = textBits.split(term).length - 1;
        if (hits > 0) add(domain, hits, null, term, estimateTokens(textBits));
      }
    }
    if (entry.size && entry.size <= DOMAIN_BLOB_TEXT_LIMIT && /^[0-9a-f]{64}$/i.test(entry.hash)) {
      try {
        const blobPath = ensureInsideRoot(path.join(timechainRoot, 'chain', 'blockspace', 'blobs', entry.hash));
        const buffer = await fs.readFile(blobPath);
        if (looksText(buffer)) {
          const text = buffer.toString('utf8').toLowerCase();
          for (const [domain, terms] of DOMAIN_RULES) {
            for (const term of terms) {
              const hits = text.split(term).length - 1;
              if (hits > 0) add(domain, Math.min(hits, 20), null, term, estimateTokens(text));
            }
          }
        }
      } catch {
        // Blob disappeared or is unreadable; integrity status will surface elsewhere.
      }
    }
  }

  return [...domains.values()]
    .filter((d) => d.score >= 1)
    .sort((a, b) => b.score - a.score)
    .slice(0, 10)
    .map((d) => ({
      name: d.name,
      score: Number(d.score.toFixed(2)),
      ringCount: d.rings.size,
      approxTokens: d.approxTokens,
      evidenceTerms: [...d.terms.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8).map(([term, count]) => ({ term, count })),
      sampleRings: [...d.rings].slice(0, 8),
    }));
}

function looksText(buffer) {
  if (!buffer.length) return true;
  const sample = buffer.subarray(0, Math.min(buffer.length, 4096));
  let suspicious = 0;
  for (const byte of sample) {
    if (byte === 0 || (byte < 7) || (byte > 14 && byte < 32)) suspicious += 1;
  }
  return suspicious / sample.length < 0.02;
}

async function buildSummary() {
  const [rings, registries, blockspace] = await Promise.all([loadRings(), loadRegistries(), loadBlockspace()]);
  const verification = await verifyChainWithPython();
  const latest = rings.at(-1) || null;
  const poqScores = rings.map((ring) => ring.poq?.brightness).filter((n) => typeof n === 'number');
  const continuumRings = rings.filter((ring) => ring.ring_type === 'continuum');
  const maxContinuumTokens = Math.max(0, ...continuumRings.map((ring) => ring.payload?.state?.metrics?.approx_tokens_ingested || 0));
  const domains = await buildDomains(rings, blockspace);

  return {
    root: timechainRoot,
    generatedAt: new Date().toISOString(),
    verification,
    stats: {
      rings: rings.length,
      modalities: registries.modalities.length,
      senses: registries.senses.length,
      emergent: registries.emergent.length,
      blockspaceEntries: blockspace.entries.length,
      blockspaceFiles: blockspace.blobFiles.length,
      blockspaceBytes: blockspace.totalBytes,
      blockspaceRefs: rings.reduce((sum, ring) => sum + (ring.blockspace_refs || []).length, 0),
      continuumBlocks: continuumRings.length,
      approxContinuumTokens: maxContinuumTokens,
      averageBrightness: poqScores.length ? poqScores.reduce((a, b) => a + b, 0) / poqScores.length : null,
    },
    latest: latest ? compactRing(latest) : null,
    ringTypes: countBy(rings, (ring) => ring.ring_type),
    modalityCategories: countBy(registries.modalities, (item) => item.category),
    senseCategories: countBy(registries.senses, (item) => item.category),
    domains,
  };
}

async function ringDetail(index) {
  const rings = await loadRings();
  const ring = rings.find((item) => Number(item.index) === Number(index));
  if (!ring) return null;
  const raw = JSON.stringify(ring);
  if (Buffer.byteLength(raw, 'utf8') > MAX_RING_DETAIL_BYTES) {
    return { ...compactRing(ring), payload: { notice: `Ring payload is larger than ${MAX_RING_DETAIL_BYTES} bytes; compact view only.` } };
  }
  return ring;
}

async function listRings(url) {
  const rings = await loadRings();
  const query = (url.searchParams.get('q') || '').toLowerCase();
  const type = url.searchParams.get('type') || '';
  const filtered = rings.filter((ring) => {
    if (type && ring.ring_type !== type) return false;
    if (!query) return true;
    return ringText(ring).toLowerCase().includes(query);
  });
  return {
    total: filtered.length,
    rings: filtered.map(compactRing).reverse(),
  };
}

async function listBlockspace() {
  const blockspace = await loadBlockspace();
  return {
    total: blockspace.entries.length,
    totalBytes: blockspace.totalBytes,
    entries: blockspace.entries.sort((a, b) => b.size - a.size),
  };
}

async function blobPreview(hash) {
  if (!/^[0-9a-f]{64}$/i.test(hash || '')) throw new Error('Invalid blockspace hash.');
  const blobPath = ensureInsideRoot(path.join(timechainRoot, 'chain', 'blockspace', 'blobs', hash));
  const stat = await fs.stat(blobPath);
  const buffer = await fs.readFile(blobPath);
  const actual = sha256Hex(buffer);
  const text = looksText(buffer);
  return {
    hash,
    size: stat.size,
    verified: actual === lower(hash),
    text,
    preview: text ? buffer.subarray(0, MAX_BLOB_PREVIEW_BYTES).toString('utf8') : '',
    truncated: text && buffer.length > MAX_BLOB_PREVIEW_BYTES,
  };
}

async function jsonBody(req) {
  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  const raw = Buffer.concat(chunks).toString('utf8');
  if (!raw) return {};
  if (raw.length > 20_000) throw new Error('Request body too large.');
  return JSON.parse(raw);
}

function bridgeStatus(req) {
  const paired = Boolean(bridgeRecord(req));
  return {
    ok: true,
    bridge: 'cypher-tempre-local',
    host: HOST,
    port: PORT,
    paired,
    remoteOrigin: isRemoteOrigin(req),
    rootDetected: Boolean(timechainRoot),
    publicOrigins: [...PUBLIC_ORIGINS],
  };
}

function createBridgeToken() {
  const token = crypto.randomBytes(32).toString('hex');
  const now = Date.now();
  bridgeTokens.set(token, {
    token,
    createdAt: now,
    expiresAt: now + BRIDGE_TOKEN_TTL_MS,
    sessionId: null,
  });
  return token;
}

function sendJson(res, status, body) {
  res.writeHead(status, {
    ...securityHeaders(),
    'content-type': 'application/json; charset=utf-8',
    'cache-control': 'no-store',
  });
  res.end(JSON.stringify(body, null, 2));
}

function requireUnlocked(session) {
  if (!session.unlocked) {
    const error = new Error('Dashboard locked. Verify a fresh Base payment first.');
    error.status = 402;
    throw error;
  }
}

async function serveStatic(req, res, url) {
  const rel = url.pathname === '/' ? 'index.html' : decodeURIComponent(url.pathname.slice(1));
  const target = path.resolve(publicDir, rel);
  if (target !== publicDir && !target.startsWith(`${publicDir}${path.sep}`)) {
    sendJson(res, 403, { error: 'Forbidden' });
    return;
  }
  const file = fsSync.existsSync(target) && fsSync.statSync(target).isFile() ? target : path.join(publicDir, 'index.html');
  const ext = path.extname(file);
  const types = {
    '.html': 'text/html; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.js': 'text/javascript; charset=utf-8',
    '.svg': 'image/svg+xml',
  };
  res.writeHead(200, {
    ...securityHeaders(),
    'content-type': types[ext] || 'application/octet-stream',
    'cache-control': 'no-store',
  });
  fsSync.createReadStream(file).pipe(res);
}

async function handle(req, res) {
  if (!allowedOrigin(req)) {
    sendJson(res, 403, { error: 'Cross-origin access denied.' });
    return;
  }
  applyCorsHeaders(req, res);
  if (req.method === 'OPTIONS') {
    res.writeHead(204, {
      ...securityHeaders(),
      'cache-control': 'no-store',
    });
    res.end();
    return;
  }
  const url = new URL(req.url, `http://${req.headers.host || `${HOST}:${PORT}`}`);
  try {
    if (url.pathname === '/api/bridge/status') {
      sendJson(res, 200, bridgeStatus(req));
      return;
    }
    if (url.pathname === '/api/bridge/pair' && req.method === 'POST') {
      const body = await jsonBody(req);
      if (normalizePairingCode(body.code) !== BRIDGE_PAIR_CODE) {
        const error = new Error('Pairing code did not match this local bridge.');
        error.status = 401;
        throw error;
      }
      const bridgeToken = createBridgeToken();
      sendJson(res, 200, {
        ok: true,
        paired: true,
        bridgeToken,
        expiresInSeconds: Math.floor(BRIDGE_TOKEN_TTL_MS / 1000),
      });
      return;
    }
    requireBridgePairing(req);
    const session = getSession(req, res);
    if (url.pathname === '/api/gate/config') {
      const token = await getTokenMeta();
      sendJson(res, 200, {
        locked: !session.unlocked,
        devUnlock: DEV_UNLOCK,
        chain: { id: BASE_CHAIN_ID, idHex: BASE_CHAIN_ID_HEX, name: 'Base' },
        token,
        recipient: { name: RECIPIENT_NAME, address: RECIPIENT_ADDRESS },
        walletConnect: { projectId: WALLETCONNECT_PROJECT_ID },
        confirmations: REQUIRED_CONFIRMATIONS,
        nonce: session.nonce,
        account: session.account,
        txHash: session.txHash,
        accessMessageTemplate: [
          'Cypher Tempre Dashboard access',
          `Session: ${session.nonce}`,
          'Account: {account}',
          'Payment transaction: {txHash}',
          `Token: ${lower(TOKEN_ADDRESS)}`,
          `Recipient: ${lower(RECIPIENT_ADDRESS)}`,
          `Amount: ${REQUIRED_TOKEN_AMOUNT}`,
          `Chain: Base (${BASE_CHAIN_ID})`,
        ].join('\n'),
      });
      return;
    }
    if (url.pathname === '/api/gate/verify' && req.method === 'POST') {
      const body = await jsonBody(req);
      const result = await verifyPayment({ session, ...body });
      sendJson(res, 200, { ok: true, result });
      return;
    }
    if (url.pathname === '/api/timechain/summary') {
      requireUnlocked(session);
      sendJson(res, 200, await buildSummary());
      return;
    }
    if (url.pathname === '/api/timechain/rings') {
      requireUnlocked(session);
      sendJson(res, 200, await listRings(url));
      return;
    }
    const ringMatch = url.pathname.match(/^\/api\/timechain\/rings\/(\d+)$/);
    if (ringMatch) {
      requireUnlocked(session);
      const ring = await ringDetail(ringMatch[1]);
      if (!ring) sendJson(res, 404, { error: 'Ring not found.' });
      else sendJson(res, 200, ring);
      return;
    }
    if (url.pathname === '/api/blockspace') {
      requireUnlocked(session);
      sendJson(res, 200, await listBlockspace());
      return;
    }
    const blobMatch = url.pathname.match(/^\/api\/blockspace\/([0-9a-fA-F]{64})$/);
    if (blobMatch) {
      requireUnlocked(session);
      sendJson(res, 200, await blobPreview(blobMatch[1]));
      return;
    }
    if (url.pathname.startsWith('/api/')) {
      sendJson(res, 404, { error: 'Not found.' });
      return;
    }
    await serveStatic(req, res, url);
  } catch (error) {
    sendJson(res, error.status || 500, { error: error.message || 'Unexpected error.' });
  }
}

timechainRoot = await discoverTimechainRoot();
const server = http.createServer((req, res) => {
  handle(req, res).catch((error) => sendJson(res, 500, { error: error.message || 'Unexpected error.' }));
});

server.on('error', (error) => {
  console.error(`Dashboard server failed to listen on ${HOST}:${PORT}: ${error.message}`);
  process.exitCode = 1;
});

server.listen(PORT, HOST, () => {
  console.log(`Cypher Tempre Dashboard listening on http://${HOST}:${PORT}`);
  console.log(`Timechain root: ${timechainRoot}`);
  console.log(`Gate: ${REQUIRED_TOKEN_AMOUNT} ${TOKEN_SYMBOL_FALLBACK} on Base -> ${RECIPIENT_NAME} (${RECIPIENT_ADDRESS})`);
  console.log(`Public origins: ${[...PUBLIC_ORIGINS].join(', ')}`);
  console.log(`Bridge pairing code: ${displayPairingCode(BRIDGE_PAIR_CODE)}`);
  console.log('Enter that pairing code on cyphertempre.ai to connect this local bridge.');
  if (DEV_UNLOCK) console.log('DEV UNLOCK ENABLED: token gate bypassed for local development.');
});
