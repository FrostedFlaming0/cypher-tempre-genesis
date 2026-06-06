import { createAppKit } from '@reown/appkit';
import { EthersAdapter } from '@reown/appkit-adapter-ethers';
import { base } from '@reown/appkit/networks';

const EIP155 = 'eip155';

function accountFromModal(modal) {
  const account = modal.getAccount?.(EIP155);
  const address = account?.address || modal.getAddress?.(EIP155);
  const provider = modal.getWalletProvider?.();
  return { account, address, provider };
}

function normalizeProvider(provider) {
  if (provider?.request) return provider;
  if (provider?.provider?.request) return provider.provider;
  return null;
}

export function createCypherTempreWalletConnect({ projectId, metadata }) {
  if (!projectId) throw new Error('WalletConnect project ID is not configured.');

  const modal = createAppKit({
    projectId,
    adapters: [new EthersAdapter()],
    networks: [base],
    defaultNetwork: base,
    metadata,
    enableWalletConnect: true,
    enableInjected: true,
    enableEIP6963: true,
    enableCoinbase: true,
    enableBaseAccount: true,
    enableReconnect: true,
    enableNetworkSwitch: true,
    themeMode: 'dark',
    themeVariables: {
      '--w3m-font-family': 'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
      '--w3m-accent': '#ffffff',
      '--w3m-color-mix': '#000000',
      '--w3m-color-mix-strength': 24,
      '--w3m-border-radius-master': '1px',
    },
    features: {
      analytics: false,
      email: false,
      socials: false,
      swaps: false,
      onramp: false,
      history: false,
    },
  });

  return {
    modal,
    async connect({ timeoutMs = 180_000 } = {}) {
      await modal.ready?.();

      const existing = accountFromModal(modal);
      const existingProvider = normalizeProvider(existing.provider);
      if (existing.address && existingProvider) {
        return { provider: existingProvider, account: existing.address };
      }

      return new Promise((resolve, reject) => {
        let settled = false;
        const cleanup = [];
        const finish = (error, value) => {
          if (settled) return;
          settled = true;
          clearTimeout(timer);
          for (const unsubscribe of cleanup) {
            try {
              unsubscribe?.();
            } catch {
              // Best-effort listener cleanup.
            }
          }
          if (error) reject(error);
          else resolve(value);
        };
        const inspect = (accountState) => {
          const current = accountFromModal(modal);
          const address = accountState?.address || current.address;
          const provider = normalizeProvider(current.provider);
          if (address && provider) finish(null, { provider, account: address });
        };
        const timer = setTimeout(() => {
          finish(new Error('WalletConnect approval timed out. Try again and approve the connection in your wallet.'));
        }, timeoutMs);

        cleanup.push(modal.subscribeAccount?.(inspect, EIP155));
        cleanup.push(modal.subscribeProviders?.(() => inspect()));
        modal.open({ view: 'Connect', namespace: EIP155 }).then(() => inspect()).catch((error) => finish(error));
      });
    },
    getAccount() {
      return accountFromModal(modal).address || null;
    },
    getProvider() {
      return normalizeProvider(accountFromModal(modal).provider);
    },
  };
}
