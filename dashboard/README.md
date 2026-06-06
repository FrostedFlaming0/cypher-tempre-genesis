# Cypher Tempre Dashboard

Local-first dashboard for auditing a Cypher Tempre `cypher-tempre-self-model`
skill directory. The server binds to `127.0.0.1` by default, reads only the
configured local Timechain root, and keeps unlock state in memory.

## Local Run

```bash
cd dashboard
npm install
npm run dev
```

Open `http://127.0.0.1:8788`.

To point at a specific skill instance:

```bash
CT_DASHBOARD_ROOT=/path/to/cypher-tempre-self-model npm run dev
```

## Token Gate

The dashboard requires a fresh Base-chain ERC-20 transfer and a payer-wallet
signature before serving local Timechain data:

- Token: `0x08Df470d41C11Ba5Cb60242747D76C65Ca52c94c`
- Amount: `10,000`
- Recipient name: `cyberphysics.base.eth`
- Default recipient address: `0x7932CCa1BD502d6850842c423d21f527de47A0Ca`

The server verifies:

- A pasted Base transaction hash points to a fresh payment for the current
  dashboard session.
- The unlock request includes a `personal_sign` signature over the current
  session nonce, payer account, transaction hash, token, recipient, amount, and
  Base chain id.
- The recovered signer matches the submitted account, and the on-chain
  transaction sender matches that same account.
- The transaction is on Base and succeeded.
- The transaction is a direct ERC-20 `transfer`.
- The token emitted a `Transfer` log to the configured recipient.
- The value is at least `10,000` tokens using the token contract decimals.
- The block timestamp is not older than the local session challenge grace
  window, which defaults to 15 minutes.
- The transaction hash has not already been redeemed by this local bridge.

No Timechain content is uploaded or persisted by the dashboard. Payment unlocks
are in-memory only for the local server process. Redeemed payment transaction
hashes are stored locally in the configured Timechain root at
`chain/dashboard-used-payments.json` so a payment hash cannot be reused by the
same local bridge after restart.

Environment overrides:

```bash
BASE_RPC_URL=https://mainnet.base.org
CT_GATE_RECIPIENT_ADDRESS=0x...
CT_GATE_RECIPIENT_NAME=cyberphysics.base.eth
CT_GATE_AMOUNT=10000
CT_GATE_CONFIRMATIONS=1
CT_GATE_PAYMENT_SESSION_GRACE_MS=900000
CT_WALLETCONNECT_PROJECT_ID=your_reown_project_id
CT_GATE_VERIFY_RATE_LIMIT_MAX=6
CT_GATE_VERIFY_IP_RATE_LIMIT_MAX=30
```

For local UI development only:

```bash
CT_DASHBOARD_DEV_UNLOCK=1 npm run dev
```

## cyphertempre.ai Deployment Model

Deploy `dashboard/public` as the static website for `https://cyphertempre.ai`.
The hosted site is only the UI shell. Each user runs the local bridge on their
own machine:

```bash
cd dashboard
npm install
npm run bridge
```

The bridge prints a one-time pairing code. The code must contain at least eight
letters or digits and is compared in constant time. The user enters that code on
`cyphertempre.ai`; the site receives an in-memory local bridge token and then
calls `http://127.0.0.1:8788/api/...` from the browser. Chain data is read by
the local bridge and rendered in the user's browser. It is not uploaded to the
hosted site.

Requests from `https://cyphertempre.ai` and other configured public origins must
pair with the local bridge. Direct same-origin requests to the loopback bridge
without an `Origin` header are treated as local development/direct-local mode
only when both the Host header and socket address are loopback.

WalletConnect/Reown AppKit is supported for desktop wallet connection. Create a
project at `https://cloud.reown.com`, then put the public project ID in
`dashboard/public/config.js` before uploading the static files:

```js
window.CYPHER_TEMPRE_PUBLIC_CONFIG = {
  walletConnectProjectId: 'your_reown_project_id',
};
```

If the project ID is blank, the dashboard still works with any injected browser
wallet already present on the page. A wallet signature from the payment sender
is required even when the transaction hash is pasted manually.
After dependency updates, rebuild the WalletConnect bundle before publishing:

```bash
npm run build:walletconnect
```

Default public origins allowed by the bridge:

```text
https://cyphertempre.ai
https://www.cyphertempre.ai
```

Override them for staging:

```bash
CT_DASHBOARD_PUBLIC_ORIGINS=https://staging.cyphertempre.ai,http://localhost:4173 npm run bridge
```

The static publish directory includes `_headers` with a CSP that permits the
hosted page to call the local bridge on `127.0.0.1:8788`, Base RPCs, and the
WalletConnect/Reown relays used by AppKit. For Hostinger/Apache hosting,
`dashboard/public/.htaccess` provides equivalent security headers and the
static-app fallback.
