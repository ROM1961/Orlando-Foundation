# WalletConnect Integration Guide

## Overview

This guide explains how to integrate WalletConnect into your Vault Wallet, allowing users to connect external wallets like MetaMask, Rainbow, Trust Wallet, etc.

## Prerequisites

1. **WalletConnect Project ID** (Free)
   - Go to: https://cloud.walletconnect.com
   - Sign up/Login
   - Create a new project
   - Copy your Project ID

## Installation

### Frontend Dependencies

```bash
cd frontend
yarn add @web3modal/wagmi wagmi viem @tanstack/react-query
```

## Configuration

### Step 1: Get WalletConnect Project ID

1. Visit https://cloud.walletconnect.com
2. Create account / Login
3. Click "Create Project"
4. Name: "Vault Wallet"
5. Copy the **Project ID**

### Step 2: Update Frontend Environment

Add to `/app/frontend/.env`:
```
REACT_APP_WALLETCONNECT_PROJECT_ID=your_project_id_here
```

### Step 3: Create WalletConnect Config

Create `/app/frontend/src/wagmi.config.js`:

```javascript
import { defaultWagmiConfig } from '@web3modal/wagmi/react/config'
import { mainnet } from 'wagmi/chains'

const projectId = process.env.REACT_APP_WALLETCONNECT_PROJECT_ID

const metadata = {
  name: 'Vault Wallet',
  description: 'Multi-signature DeFi Wallet',
  url: 'https://vault-wallet-frontend.onrender.com',
  icons: ['https://ipfs.io/ipfs/bafkreicuf2opanzlgdcg2r3uh2jkhc64rqo75ddf6fhveuj3etkx2uhazu']
}

const chains = [mainnet]

export const config = defaultWagmiConfig({
  chains,
  projectId,
  metadata
})
```

### Step 4: Wrap App with WalletConnect Providers

Update `/app/frontend/src/index.js`:

```javascript
import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { WagmiProvider } from 'wagmi';
import { createWeb3Modal } from '@web3modal/wagmi/react';
import { config } from './wagmi.config';

// Create QueryClient
const queryClient = new QueryClient();

// Create Web3Modal
const projectId = process.env.REACT_APP_WALLETCONNECT_PROJECT_ID;
createWeb3Modal({
  wagmiConfig: config,
  projectId,
  enableAnalytics: true,
  enableOnramp: true
});

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <WagmiProvider config={config}>
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </WagmiProvider>
  </React.StrictMode>
);
```

### Step 5: Add Connect Wallet Button

Update Dashboard.jsx to add WalletConnect button:

```javascript
import { useWeb3Modal } from '@web3modal/wagmi/react';
import { useAccount, useDisconnect } from 'wagmi';

// In Dashboard component:
const { open } = useWeb3Modal();
const { address, isConnected } = useAccount();
const { disconnect } = useDisconnect();

// Add button in header:
<div className="flex gap-2">
  {isConnected ? (
    <>
      <span className="text-sm text-gray-400">
        Connected: {address?.substring(0, 6)}...{address?.substring(address.length - 4)}
      </span>
      <Button onClick={() => disconnect()} variant="outline">
        Disconnect
      </Button>
    </>
  ) : (
    <Button onClick={() => open()} className="btn-primary">
      Connect Wallet
    </Button>
  )}
  <Button onClick={handleLogout} variant="outline">
    Logout
  </Button>
</div>
```

## Features Enabled by WalletConnect

### 1. Import Connected Wallet

When user connects via WalletConnect, you can import their address:

```javascript
const handleImportConnectedWallet = async () => {
  if (!address) {
    toast.error("Please connect wallet first");
    return;
  }
  
  // Create vault with connected address
  await axios.post(`${API}/vaults/create`, {
    label: `Connected Wallet (${address.substring(0, 6)}...)`,
    vault_type: "watch-only",
    required_signatures: 1,
    owner_addresses: [address]
  }, getAuthHeaders());
  
  toast.success("Wallet imported!");
  fetchVaults();
};
```

### 2. Sign Transactions with Connected Wallet

For wallets connected via WalletConnect, you can request signatures:

```javascript
import { useSendTransaction } from 'wagmi';

const { sendTransaction } = useSendTransaction();

const handleSendWithWalletConnect = async () => {
  if (!isConnected) {
    toast.error("Connect wallet first");
    return;
  }
  
  sendTransaction({
    to: recipientAddress,
    value: parseEther(amount),
  });
};
```

### 3. Multi-Wallet Management

Users can:
- Have internal wallets (created by app)
- Connect external wallets (MetaMask, etc.)
- Switch between both
- View balances for all wallets

## Security Considerations

### Watch-Only vs Full Control

**Internal Wallets (Created by App)**
- ✅ Can send transactions
- ✅ Private key encrypted in database
- ⚠️ Private key managed by app

**Connected Wallets (WalletConnect)**
- ✅ Can send transactions (via user's wallet app)
- ✅ User controls private key
- ✅ More secure (private key never leaves user's device)
- ⚠️ Requires user to approve each transaction

**Imported Wallets (Address Only)**
- ❌ Cannot send transactions
- ✅ Can only view balances
- ✅ Most secure (no private key involved)

## Testing

### Local Testing

1. Install dependencies
2. Add Project ID to .env
3. Run frontend: `yarn start`
4. Click "Connect Wallet"
5. Scan QR with MetaMask mobile or use browser extension

### Supported Wallets

- MetaMask
- Rainbow
- Trust Wallet
- Coinbase Wallet
- Ledger
- Trezor
- 200+ more wallets

## Production Deployment

### Step 1: Update Environment Variables

**Frontend (Render):**
```
REACT_APP_WALLETCONNECT_PROJECT_ID=your_project_id
```

### Step 2: Update Package.json

Ensure dependencies are added:
```json
{
  "dependencies": {
    "@web3modal/wagmi": "^4.0.0",
    "wagmi": "^2.0.0",
    "viem": "^2.0.0",
    "@tanstack/react-query": "^5.0.0"
  }
}
```

### Step 3: Redeploy

```bash
git add .
git commit -m "Add WalletConnect integration"
git push origin main
```

Render will auto-deploy.

## Advanced Features

### 1. Sign Messages

```javascript
import { useSignMessage } from 'wagmi';

const { signMessage } = useSignMessage();

const handleSign = async () => {
  const signature = await signMessage({ message: 'Hello from Vault Wallet!' });
  console.log('Signature:', signature);
};
```

### 2. Switch Networks

```javascript
import { useSwitchChain } from 'wagmi';

const { switchChain } = useSwitchChain();

const handleSwitchToMainnet = () => {
  switchChain({ chainId: 1 });
};
```

### 3. Read Contract Data

```javascript
import { useReadContract } from 'wagmi';

const { data: balance } = useReadContract({
  address: '0x...',
  abi: erc20Abi,
  functionName: 'balanceOf',
  args: [address]
});
```

## Support & Resources

- **WalletConnect Docs**: https://docs.walletconnect.com
- **Web3Modal Docs**: https://docs.walletconnect.com/web3modal/react/about
- **Wagmi Docs**: https://wagmi.sh
- **Discord**: https://discord.gg/walletconnect

## Troubleshooting

### Issue: "Invalid Project ID"
**Solution**: Check that REACT_APP_WALLETCONNECT_PROJECT_ID is set correctly

### Issue: "Failed to connect"
**Solution**: Make sure your domain is whitelisted in WalletConnect dashboard

### Issue: "Transaction failed"
**Solution**: Check that user has approved the transaction in their wallet app

## Next Steps

1. ✅ Get WalletConnect Project ID
2. ✅ Install dependencies
3. ✅ Add configuration
4. ✅ Implement connect button
5. ✅ Test with MetaMask
6. ✅ Deploy to production
