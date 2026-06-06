# cyphertempre.ai Static Site

Use `dashboard/public` as the production static publish directory for
`https://cyphertempre.ai`.

## Recommended Hostinger Setup

Hostinger works well for this because the public site is static. Upload the
contents of `dashboard/public` into the domain's `public_html` folder.

1. In Hostinger hPanel, open Websites and manage `cyphertempre.ai`.
2. Disable/remove the URL redirect or forwarding placeholder.
3. Open File Manager for the domain.
4. Open `public_html`.
5. Delete placeholder files such as `default.php` or the current redirect
   placeholder, if present.
6. Upload every file from `dashboard/public` into `public_html`, including:

```text
   index.html
   styles.css
   app.js
   config.js
   reown-wallet.js
   _headers
   .htaccess
```

7. Visit `https://cyphertempre.ai`.
8. Start the local bridge on the user's machine:

```bash
cd dashboard
npm install
npm run bridge
```

The bridge prints a pairing code. Enter that code on the website.

For the standard WalletConnect modal, create a public project ID at
`https://cloud.reown.com`, then edit `config.js` before upload:

```js
window.CYPHER_TEMPRE_PUBLIC_CONFIG = {
  walletConnectProjectId: 'your_reown_project_id',
};
```

If `walletConnectProjectId` is blank, the site still supports browser-injected
wallets. Pasted Base transaction hashes still require a signature from the
payment sender before the local bridge unlocks.

If hPanel offers Git deployment for your plan, set the deploy/publish path to
`dashboard/public`. If it only supports File Manager/FTP, upload the contents of
that folder directly.

## Cloudflare Pages Alternative

1. Remove the current domain redirect/forwarding placeholder at the registrar or
   DNS host.
2. Create a Cloudflare Pages project connected to this repository.
3. Use these build settings:

```text
Build command: none
Build output directory: dashboard/public
Root directory: /
```

4. Add custom domains:

```text
cyphertempre.ai
www.cyphertempre.ai
```

5. Point DNS at the Pages target Cloudflare gives you. If Cloudflare manages the
   zone, it creates the required records automatically. If another registrar
   manages DNS, remove URL forwarding and add the Pages CNAME/flattened apex
   records shown in the Pages custom domain screen.
6. Keep HTTPS enabled.

## User Flow In Production

1. User opens `https://cyphertempre.ai`.
2. User starts the local bridge:

```bash
cd dashboard
npm install
npm run bridge
```

After uploading a new static ZIP, restart the local bridge too. The hosted site
is only the UI shell; payment verification, redeemed-hash storage, and Timechain
file reads happen in the local `dashboard/server.mjs` process.

3. The bridge prints a pairing code.
4. User enters the pairing code on `cyphertempre.ai`.
5. The hosted page calls the local bridge at `http://127.0.0.1:8788`.
6. User connects the payer wallet through WalletConnect/browser wallet, sends
   `10,000 CPHY` on Base to `cyberphysics.base.eth`, or pastes that payer
   wallet's transaction hash.
7. The payer wallet signs the local bridge's current session challenge, binding
   the session nonce, account, and transaction hash.
8. The local bridge verifies the signature and Base CPHY payment, redeems that
   transaction hash locally once, and reads local Timechain files.

No hosted service stores agent Timechain data. The public site is static; the
local bridge is the only process that reads local skill files.

The local bridge prevents reused payment hashes on the same machine by writing
`chain/dashboard-used-payments.json` under the configured local Timechain root.
Global one-use redemption across all users would require either a small hosted
redemption ledger or an on-chain access contract.

## Staging

For staging domains, start the bridge with:

```bash
CT_DASHBOARD_PUBLIC_ORIGINS=https://staging.cyphertempre.ai npm run bridge
```

For local public-site development:

```bash
CT_DASHBOARD_PUBLIC_ORIGINS=http://localhost:4173 npm run bridge
```
