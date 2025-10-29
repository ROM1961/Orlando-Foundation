import { useState, useEffect } from "react";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import { Wallet, Send, ArrowDownToLine, History, LogOut, Plus, TrendingUp, DollarSign } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Dashboard = ({ setIsAuthenticated }) => {
  const [vaults, setVaults] = useState([]);
  const [selectedVault, setSelectedVault] = useState(null);
  const [balance, setBalance] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [protocols, setProtocols] = useState([]);
  const [loading, setLoading] = useState(false);
  const [createVaultOpen, setCreateVaultOpen] = useState(false);
  const [sendTxOpen, setSendTxOpen] = useState(false);
  const [defiDialogOpen, setDefiDialogOpen] = useState(false);
  const [defiAction, setDefiAction] = useState({ protocol: "", action: "" });
  
  const [newVault, setNewVault] = useState({
    label: "",
    vault_type: "multi-sig",
    required_signatures: 2,
    owner_addresses: [""],
    private_key: ""  // For importing existing wallet
  });
  
  const [importMode, setImportMode] = useState(false);
  
  const [sendTx, setSendTx] = useState({
    to_address: "",
    amount: "",
    token: "ETH"
  });
  
  const [defiTx, setDefiTx] = useState({
    token: "USDC",
    amount: ""
  });

  // Morpho Blue state
  const [morphoDialogOpen, setMorphoDialogOpen] = useState(false);
  const [morphoAction, setMorphoAction] = useState(""); // supply, borrow, repay, withdraw
  const [morphoAmount, setMorphoAmount] = useState("");
  const [morphoPosition, setMorphoPosition] = useState(null);
  const [morphoMarketInfo, setMorphoMarketInfo] = useState(null);

  const username = localStorage.getItem("username");
  const token = localStorage.getItem("token");

  const getAuthHeaders = () => ({
    headers: { Authorization: `Bearer ${token}` }
  });

  useEffect(() => {
    fetchVaults();
    fetchProtocols();
  }, []);

  useEffect(() => {
    if (selectedVault) {
      fetchBalance();
      fetchTransactions();
      fetchMorphoPosition();
    }
  }, [selectedVault]);

  useEffect(() => {
    fetchMorphoMarketInfo();
  }, []);

  const fetchVaults = async () => {
    try {
      const response = await axios.get(`${API}/vaults`, getAuthHeaders());
      setVaults(response.data);
      if (response.data.length > 0 && !selectedVault) {
        setSelectedVault(response.data[0]);
      }
    } catch (error) {
      console.error("Vault fetch error:", error);
      if (error.response?.status === 401) {
        toast.error("Session expired. Please login again.");
        setTimeout(() => window.location.href = "/", 2000);
      } else {
        toast.error(error.response?.data?.detail || "Failed to fetch vaults");
      }
    }
  };

  const fetchBalance = async () => {
    if (!selectedVault) return;
    try {
      const response = await axios.get(`${API}/vaults/${selectedVault.id}/balance`, getAuthHeaders());
      setBalance(response.data);
    } catch (error) {
      toast.error("Failed to fetch balance");
    }
  };

  const fetchTransactions = async () => {
    if (!selectedVault) return;
    try {
      const response = await axios.get(`${API}/vaults/${selectedVault.id}/transactions`, getAuthHeaders());
      setTransactions(response.data);
    } catch (error) {
      console.error("Failed to fetch transactions");
    }
  };

  const fetchProtocols = async () => {
    try {
      const response = await axios.get(`${API}/defi/protocols`, getAuthHeaders());
      setProtocols(response.data);
    } catch (error) {
      console.error("Failed to fetch protocols");
    }
  };

  const fetchMorphoPosition = async () => {
    if (!selectedVault) return;
    try {
      const response = await axios.get(`${API}/morpho/position/${selectedVault.id}`, getAuthHeaders());
      setMorphoPosition(response.data);
    } catch (error) {
      console.error("Failed to fetch Morpho position:", error);
    }
  };

  const fetchMorphoMarketInfo = async () => {
    try {
      const response = await axios.get(`${API}/morpho/market-info`, getAuthHeaders());
      setMorphoMarketInfo(response.data);
    } catch (error) {
      console.error("Failed to fetch Morpho market info:", error);
    }
  };

  const handleMorphoAction = async (e) => {
    e.preventDefault();
    if (!selectedVault) {
      toast.error("Please select a vault first");
      return;
    }

    setLoading(true);
    try {
      let endpoint = "";
      let requestData = {
        vault_id: selectedVault.id,
        amount: parseFloat(morphoAmount)
      };

      switch (morphoAction) {
        case "supply":
          endpoint = "/morpho/supply-collateral";
          break;
        case "borrow":
          endpoint = "/morpho/borrow";
          break;
        case "repay":
          endpoint = "/morpho/repay";
          break;
        case "withdraw":
          endpoint = "/morpho/withdraw-collateral";
          break;
        default:
          throw new Error("Invalid action");
      }

      const response = await axios.post(`${API}${endpoint}`, requestData, getAuthHeaders());
      
      toast.success(
        `${morphoAction.charAt(0).toUpperCase() + morphoAction.slice(1)} successful! Hash: ${response.data.transaction_hash.substring(0, 10)}...`,
        { duration: 7000 }
      );
      
      setMorphoDialogOpen(false);
      setMorphoAmount("");
      fetchBalance();
      fetchMorphoPosition();
      fetchTransactions();
    } catch (error) {
      const errorMsg = error.response?.data?.detail || `${morphoAction} failed`;
      if (errorMsg.includes("watch") || errorMsg.includes("private key")) {
        toast.error("Cannot transact: This is a watch-only wallet. Create a new wallet to execute transactions.");
      } else {
        toast.error(errorMsg);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleCreateVault = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      // Prepare payload based on import mode
      const payload = importMode 
        ? {
            label: newVault.label,
            private_key: newVault.private_key  // Send private key for import
          }
        : newVault;  // Normal vault creation
      
      await axios.post(`${API}/vaults/create`, payload, getAuthHeaders());
      toast.success(importMode ? "Wallet imported successfully!" : "Vault created successfully!");
      setCreateVaultOpen(false);
      setImportMode(false);
      fetchVaults();
      setNewVault({ label: "", vault_type: "multi-sig", required_signatures: 2, owner_addresses: [""], private_key: "" });
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to create vault");
    } finally {
      setLoading(false);
    }
  };

  const handleSendTransaction = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await axios.post(
        `${API}/vaults/${selectedVault.id}/send`,
        { ...sendTx, vault_id: selectedVault.id },
        getAuthHeaders()
      );
      toast.success(`Transaction sent! Hash: ${response.data.tx_hash.substring(0, 10)}...`);
      setSendTxOpen(false);
      fetchBalance();
      fetchTransactions();
      setSendTx({ to_address: "", amount: "", token: "ETH" });
    } catch (error) {
      const errorMsg = error.response?.data?.detail || "Transaction failed";
      if (errorMsg.includes("watch") || errorMsg.includes("private key")) {
        toast.error("Cannot send: This is a watch-only wallet (imported address). Create a new wallet to send transactions.");
      } else {
        toast.error(errorMsg);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.clear();
    setIsAuthenticated(false);
  };

  const addOwnerAddress = () => {
    setNewVault({ ...newVault, owner_addresses: [...newVault.owner_addresses, ""] });
  };

  const updateOwnerAddress = (index, value) => {
    const updated = [...newVault.owner_addresses];
    updated[index] = value;
    setNewVault({ ...newVault, owner_addresses: updated });
  };

  const formatAddress = (address) => {
    return `${address.substring(0, 6)}...${address.substring(address.length - 4)}`;
  };

  return (
    <div className="min-h-screen p-4 sm:p-6 lg:p-8" style={{ background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)' }}>
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-8" data-testid="dashboard-header">
          <div className="flex items-center gap-4">
            <img 
              src="https://ipfs.io/ipfs/bafkreicuf2opanzlgdcg2r3uh2jkhc64rqo75ddf6fhveuj3etkx2uhazu" 
              alt="Logo" 
              className="w-12 h-12 rounded-full"
              data-testid="dashboard-logo"
              onError={(e) => {e.target.src = 'https://via.placeholder.com/48?text=V'}}
            />
            <div>
              <h1 className="text-3xl font-bold text-white" style={{ fontFamily: 'Space Grotesk' }}>
                Vault Wallet
              </h1>
              <p className="text-gray-400 text-sm">Welcome, {username}</p>
            </div>
          </div>
          <Button onClick={handleLogout} variant="outline" className="border-slate-600 text-white hover:bg-slate-800" data-testid="logout-btn">
            <LogOut className="w-4 h-4 mr-2" />
            Logout
          </Button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Sidebar - Vaults */}
          <div className="lg:col-span-1">
            <Card className="glass-card border-slate-700" data-testid="vaults-card">
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-white">My Vaults</CardTitle>
                <Dialog open={createVaultOpen} onOpenChange={setCreateVaultOpen}>
                  <DialogTrigger asChild>
                    <Button size="sm" className="btn-primary" data-testid="create-vault-btn">
                      <Plus className="w-4 h-4" />
                    </Button>
                  </DialogTrigger>
                  <DialogContent className="bg-slate-900 border-slate-700 text-white">
                    <DialogHeader>
                      <DialogTitle>{importMode ? "Import Existing Wallet" : "Create New Vault"}</DialogTitle>
                      <DialogDescription className="text-gray-400">
                        {importMode 
                          ? "Import your wallet using a private key" 
                          : "Create a new wallet or import an existing one"}
                      </DialogDescription>
                    </DialogHeader>
                    
                    {/* Toggle between Create and Import */}
                    <div className="flex gap-2 mb-4">
                      <Button
                        type="button"
                        onClick={() => setImportMode(false)}
                        className={`flex-1 ${!importMode ? 'bg-blue-600' : 'bg-slate-700'}`}
                        data-testid="create-mode-btn"
                      >
                        Create New
                      </Button>
                      <Button
                        type="button"
                        onClick={() => setImportMode(true)}
                        className={`flex-1 ${importMode ? 'bg-blue-600' : 'bg-slate-700'}`}
                        data-testid="import-mode-btn"
                      >
                        Import Wallet
                      </Button>
                    </div>
                    
                    <form onSubmit={handleCreateVault} className="space-y-4">
                      <div>
                        <Label htmlFor="label" className="text-gray-300">Wallet Label</Label>
                        <Input
                          id="label"
                          value={newVault.label}
                          onChange={(e) => setNewVault({ ...newVault, label: e.target.value })}
                          placeholder={importMode ? "ACS Owner Wallet" : "My Trading Vault"}
                          required
                          className="bg-slate-800 border-slate-600 text-white"
                          data-testid="vault-label-input"
                        />
                      </div>
                      
                      {importMode ? (
                        <>
                          {/* Import Mode - Private Key Input */}
                          <div>
                            <Label htmlFor="private_key" className="text-gray-300">Private Key</Label>
                            <Input
                              id="private_key"
                              type="password"
                              value={newVault.private_key}
                              onChange={(e) => setNewVault({ ...newVault, private_key: e.target.value })}
                              placeholder="0x..."
                              required
                              className="bg-slate-800 border-slate-600 text-white font-mono"
                              data-testid="private-key-input"
                            />
                            <p className="text-xs text-yellow-500 mt-2">
                              ⚠️ Your private key will be encrypted before storage
                            </p>
                          </div>
                          
                          <div className="bg-slate-800/50 p-3 rounded-lg border border-yellow-500/30">
                            <p className="text-xs text-yellow-400 mb-2">🔒 Security Notice:</p>
                            <ul className="text-xs text-gray-400 space-y-1 list-disc list-inside">
                              <li>Private key is encrypted with AES-128</li>
                              <li>Never share your private key with anyone</li>
                              <li>Test with small amounts first</li>
                              <li>Consider using hardware wallet for large amounts</li>
                            </ul>
                          </div>
                        </>
                      ) : (
                        <>
                          {/* Create Mode - Owner Addresses */}
                          <div>
                            <Label className="text-gray-300">Owner Addresses (Optional)</Label>
                            <p className="text-xs text-gray-500 mb-2">Leave empty to generate new wallet</p>
                            {newVault.owner_addresses.map((addr, idx) => (
                              <Input
                                key={idx}
                                value={addr}
                                onChange={(e) => updateOwnerAddress(idx, e.target.value)}
                                placeholder="0x... (optional - for watch-only)"
                                className="bg-slate-800 border-slate-600 text-white mb-2"
                                data-testid={`owner-address-input-${idx}`}
                              />
                            ))}
                            <Button type="button" onClick={addOwnerAddress} size="sm" variant="outline" className="border-slate-600 text-white">
                              Add Owner
                            </Button>
                          </div>
                        </>
                      )}
                      
                      <Button 
                        type="submit" 
                        className="w-full btn-primary" 
                        disabled={loading} 
                        data-testid="create-vault-submit-btn"
                      >
                        {loading 
                          ? (importMode ? "Importing..." : "Creating...") 
                          : (importMode ? "Import Wallet" : "Create Vault")}
                      </Button>
                    </form>
                  </DialogContent>
                </Dialog>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[400px]">
                  {vaults.map((vault) => (
                    <div
                      key={vault.id}
                      onClick={() => setSelectedVault(vault)}
                      className={`p-4 rounded-lg mb-2 cursor-pointer transition ${
                        selectedVault?.id === vault.id
                          ? "wallet-card"
                          : "bg-slate-800/30 hover:bg-slate-800/50"
                      }`}
                      data-testid={`vault-item-${vault.id}`}
                    >
                      <div className="flex items-center gap-3">
                        <Wallet className="w-5 h-5 text-blue-400" />
                        <div className="flex-1">
                          <p className="font-medium text-white">{vault.label}</p>
                          <p className="text-xs text-gray-400">{formatAddress(vault.vault_address)}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </ScrollArea>
              </CardContent>
            </Card>
          </div>

          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {selectedVault && (
              <>
                {/* Balance Card */}
                <Card className="wallet-card" data-testid="balance-card">
                  <CardHeader>
                    <CardTitle className="text-white">Total Balance</CardTitle>
                    <CardDescription className="text-gray-400">{selectedVault.vault_address}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    {balance ? (
                      <div className="space-y-4">
                        <div className="text-center py-6">
                          <h2 className="text-5xl font-bold text-white mb-2" style={{ fontFamily: 'Space Grotesk' }}>
                            ${balance.total_usd.toFixed(2)}
                          </h2>
                          <p className="text-gray-400">Total Portfolio Value</p>
                        </div>
                        
                        <div className="grid grid-cols-2 gap-4">
                          <div className="bg-slate-800/50 p-4 rounded-lg" data-testid="eth-balance">
                            <div className="flex items-center gap-2 mb-2">
                              <DollarSign className="w-4 h-4 text-blue-400" />
                              <span className="text-gray-400 text-sm">Ethereum</span>
                            </div>
                            <p className="text-2xl font-bold text-white">{balance.eth_balance?.toFixed(4) || 0} ETH</p>
                            <p className="text-sm text-gray-400">${balance.eth_usd?.toFixed(2) || 0}</p>
                          </div>
                          
                          <div className="bg-slate-800/50 p-4 rounded-lg" data-testid="acs-balance">
                            <div className="flex items-center gap-2 mb-2">
                              <TrendingUp className="w-4 h-4 text-purple-400" />
                              <span className="text-gray-400 text-sm">ACS Token</span>
                            </div>
                            <p className="text-2xl font-bold text-white">{balance.acs_balance?.toLocaleString() || 0} ACS</p>
                            <p className="text-sm text-green-400 font-semibold">${balance.acs_usd?.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) || 0}</p>
                            {balance.prices?.ETH > 0 && balance.acs_usd > 0 && (
                              <p className="text-xs text-blue-400 mt-1">
                                ≈ {(balance.acs_usd / balance.prices.ETH).toFixed(4)} ETH
                              </p>
                            )}
                          </div>

                          <div className="bg-slate-800/50 p-4 rounded-lg" data-testid="usdc-balance">
                            <div className="flex items-center gap-2 mb-2">
                              <DollarSign className="w-4 h-4 text-green-400" />
                              <span className="text-gray-400 text-sm">USDC</span>
                            </div>
                            <p className="text-2xl font-bold text-white">{balance.balances?.USDC?.toFixed(2) || 0} USDC</p>
                            <p className="text-sm text-gray-400">${balance.usd_values?.USDC?.toFixed(2) || 0}</p>
                          </div>

                          <div className="bg-slate-800/50 p-4 rounded-lg" data-testid="usdt-balance">
                            <div className="flex items-center gap-2 mb-2">
                              <DollarSign className="w-4 h-4 text-teal-400" />
                              <span className="text-gray-400 text-sm">USDT</span>
                            </div>
                            <p className="text-2xl font-bold text-white">{balance.balances?.USDT?.toFixed(2) || 0} USDT</p>
                            <p className="text-sm text-gray-400">${balance.usd_values?.USDT?.toFixed(2) || 0}</p>
                          </div>
                        </div>

                        <div className="flex gap-3 mt-4">
                          <Dialog open={sendTxOpen} onOpenChange={setSendTxOpen}>
                            <DialogTrigger asChild>
                              <Button className="flex-1 btn-primary" data-testid="send-btn">
                                <Send className="w-4 h-4 mr-2" />
                                Send
                              </Button>
                            </DialogTrigger>
                            <DialogContent className="bg-slate-900 border-slate-700 text-white">
                              <DialogHeader>
                                <DialogTitle>Send Transaction</DialogTitle>
                                <DialogDescription className="text-gray-400">
                                  Transfer from: {selectedVault?.label} ({formatAddress(selectedVault?.vault_address || "")})
                                </DialogDescription>
                              </DialogHeader>
                              <form onSubmit={handleSendTransaction} className="space-y-4">
                                <div>
                                  <Label htmlFor="token_select" className="text-gray-300">Select Token</Label>
                                  <select
                                    id="token_select"
                                    value={sendTx.token}
                                    onChange={(e) => setSendTx({ ...sendTx, token: e.target.value })}
                                    className="w-full bg-slate-800 border border-slate-600 text-white rounded-md p-2"
                                    data-testid="send-token-select"
                                  >
                                    <option value="ETH">ETH (Ethereum)</option>
                                    <option value="ACS">ACS (ArtCubeSociety)</option>
                                    <option value="USDC">USDC (USD Coin)</option>
                                    <option value="USDT">USDT (Tether)</option>
                                  </select>
                                </div>
                                <div>
                                  <Label htmlFor="to_address" className="text-gray-300">Recipient Address</Label>
                                  <Input
                                    id="to_address"
                                    value={sendTx.to_address}
                                    onChange={(e) => setSendTx({ ...sendTx, to_address: e.target.value })}
                                    placeholder="0x..."
                                    required
                                    className="bg-slate-800 border-slate-600 text-white"
                                    data-testid="send-to-address-input"
                                  />
                                </div>
                                <div>
                                  <Label htmlFor="amount" className="text-gray-300">Amount ({sendTx.token})</Label>
                                  <Input
                                    id="amount"
                                    type="number"
                                    step="0.0001"
                                    value={sendTx.amount}
                                    onChange={(e) => setSendTx({ ...sendTx, amount: e.target.value })}
                                    placeholder="0.0"
                                    required
                                    className="bg-slate-800 border-slate-600 text-white"
                                    data-testid="send-amount-input"
                                  />
                                  {balance && (
                                    <p className="text-xs text-gray-400 mt-1">
                                      Available: {
                                        sendTx.token === "ETH" ? balance.eth_balance?.toFixed(4) :
                                        sendTx.token === "ACS" ? balance.acs_balance?.toFixed(2) :
                                        sendTx.token === "USDC" ? balance.balances?.USDC?.toFixed(2) :
                                        sendTx.token === "USDT" ? balance.balances?.USDT?.toFixed(2) : 0
                                      } {sendTx.token}
                                    </p>
                                  )}
                                </div>
                                <Button type="submit" className="w-full btn-primary" disabled={loading} data-testid="send-tx-submit-btn">
                                  {loading ? "Sending..." : `Send ${sendTx.token}`}
                                </Button>
                              </form>
                            </DialogContent>
                          </Dialog>
                          
                          <Button variant="outline" className="border-slate-600 text-white hover:bg-slate-800" data-testid="receive-btn">
                            <ArrowDownToLine className="w-4 h-4 mr-2" />
                            Receive
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <p className="text-center text-gray-400">Loading balance...</p>
                    )}
                  </CardContent>
                </Card>

                {/* Tabs for DeFi & Transactions */}
                <Card className="glass-card border-slate-700">
                  <Tabs defaultValue="transactions">
                    <CardHeader>
                      <TabsList className="grid w-full grid-cols-2">
                        <TabsTrigger value="transactions" data-testid="transactions-tab">
                          <History className="w-4 h-4 mr-2" />
                          Transactions
                        </TabsTrigger>
                        <TabsTrigger value="defi" data-testid="defi-tab">
                          <TrendingUp className="w-4 h-4 mr-2" />
                          DeFi Protocols
                        </TabsTrigger>
                      </TabsList>
                    </CardHeader>
                    <CardContent>
                      <TabsContent value="transactions" className="mt-0">
                        <ScrollArea className="h-[300px]">
                          {transactions.length > 0 ? (
                            transactions.map((tx) => (
                              <div
                                key={tx.id}
                                className="flex items-center justify-between p-4 bg-slate-800/30 rounded-lg mb-2"
                                data-testid={`transaction-${tx.id}`}
                              >
                                <div>
                                  <p className="font-medium text-white">{tx.action}</p>
                                  <p className="text-xs text-gray-400">{formatAddress(tx.tx_hash)}</p>
                                </div>
                                <div className="text-right">
                                  <p className="font-medium text-white">{tx.amount} ETH</p>
                                  <Badge variant={tx.status === "pending" ? "outline" : "default"}>
                                    {tx.status}
                                  </Badge>
                                </div>
                              </div>
                            ))
                          ) : (
                            <p className="text-center text-gray-400 py-8">No transactions yet</p>
                          )}
                        </ScrollArea>
                      </TabsContent>
                      
                      <TabsContent value="defi" className="mt-0">
                        <div className="space-y-3">
                          {protocols.map((protocol) => (
                            <div
                              key={protocol.name}
                              className="p-4 bg-slate-800/30 rounded-lg hover:bg-slate-800/50 transition"
                              data-testid={`protocol-${protocol.name.toLowerCase()}`}
                            >
                              <div className="flex items-center justify-between mb-3">
                                <div>
                                  <p className="font-medium text-white">{protocol.name}</p>
                                  <p className="text-xs text-gray-400">{formatAddress(protocol.address)}</p>
                                </div>
                                <Badge variant="outline" className="border-blue-500 text-blue-400">
                                  {protocol.type}
                                </Badge>
                              </div>
                              
                              {(protocol.name === "Aave" || protocol.name === "Compound") && (
                                <div className="flex gap-2 mt-3">
                                  <Button 
                                    size="sm" 
                                    className="flex-1 bg-green-600 hover:bg-green-700 text-white"
                                    onClick={() => {
                                      setDefiAction({ protocol: protocol.name, action: "Lend" });
                                      setDefiDialogOpen(true);
                                    }}
                                    data-testid={`${protocol.name.toLowerCase()}-lend-btn`}
                                  >
                                    <TrendingUp className="w-3 h-3 mr-1" />
                                    Lend
                                  </Button>
                                  <Button 
                                    size="sm" 
                                    className="flex-1 bg-blue-600 hover:bg-blue-700 text-white"
                                    onClick={() => {
                                      setDefiAction({ protocol: protocol.name, action: "Borrow" });
                                      setDefiDialogOpen(true);
                                    }}
                                    data-testid={`${protocol.name.toLowerCase()}-borrow-btn`}
                                  >
                                    <ArrowDownToLine className="w-3 h-3 mr-1" />
                                    Borrow
                                  </Button>
                                </div>
                              )}
                            </div>
                          ))}
                          
                          {/* Morpho Blue Protocol */}
                          <div className="p-4 bg-gradient-to-r from-purple-900/30 to-blue-900/30 rounded-lg border border-purple-500/30 hover:bg-purple-900/40 transition" data-testid="protocol-morpho">
                            <div className="flex items-center justify-between mb-3">
                              <div>
                                <p className="font-medium text-white">Morpho Blue</p>
                                <p className="text-xs text-gray-400">ACS Collateral / USDC Borrowing</p>
                              </div>
                              <Badge variant="outline" className="border-purple-500 text-purple-400">
                                Lending Market
                              </Badge>
                            </div>
                            
                            {/* Morpho Position Info */}
                            {morphoPosition && (
                              <div className="grid grid-cols-2 gap-2 mb-3 text-xs">
                                <div className="bg-slate-800/50 p-2 rounded">
                                  <p className="text-gray-400">Collateral</p>
                                  <p className="text-white font-semibold">{morphoPosition.collateral_formatted.toFixed(2)} ACS</p>
                                </div>
                                <div className="bg-slate-800/50 p-2 rounded">
                                  <p className="text-gray-400">Borrowed</p>
                                  <p className="text-white font-semibold">{morphoPosition.borrow_formatted.toFixed(2)} USDC</p>
                                </div>
                              </div>
                            )}
                            
                            <div className="grid grid-cols-2 gap-2">
                              <Button 
                                size="sm" 
                                className="bg-purple-600 hover:bg-purple-700 text-white"
                                onClick={() => {
                                  setMorphoAction("supply");
                                  setMorphoDialogOpen(true);
                                }}
                                data-testid="morpho-supply-btn"
                              >
                                <Plus className="w-3 h-3 mr-1" />
                                Supply ACS
                              </Button>
                              <Button 
                                size="sm" 
                                className="bg-blue-600 hover:bg-blue-700 text-white"
                                onClick={() => {
                                  setMorphoAction("borrow");
                                  setMorphoDialogOpen(true);
                                }}
                                data-testid="morpho-borrow-btn"
                              >
                                <ArrowDownToLine className="w-3 h-3 mr-1" />
                                Borrow USDC
                              </Button>
                              <Button 
                                size="sm" 
                                className="bg-green-600 hover:bg-green-700 text-white"
                                onClick={() => {
                                  setMorphoAction("repay");
                                  setMorphoDialogOpen(true);
                                }}
                                data-testid="morpho-repay-btn"
                              >
                                <TrendingUp className="w-3 h-3 mr-1" />
                                Repay USDC
                              </Button>
                              <Button 
                                size="sm" 
                                className="bg-orange-600 hover:bg-orange-700 text-white"
                                onClick={() => {
                                  setMorphoAction("withdraw");
                                  setMorphoDialogOpen(true);
                                }}
                                data-testid="morpho-withdraw-btn"
                              >
                                <ArrowDownToLine className="w-3 h-3 mr-1" />
                                Withdraw ACS
                              </Button>
                            </div>
                          </div>
                        </div>
                      </TabsContent>
                    </CardContent>
                  </Tabs>
                </Card>
              </>
            )}
          </div>
        </div>
      </div>

      {/* DeFi Lend/Borrow Dialog */}
      <Dialog open={defiDialogOpen} onOpenChange={setDefiDialogOpen}>
        <DialogContent className="bg-slate-900 border-slate-700 text-white">
          <DialogHeader>
            <DialogTitle>{defiAction.protocol} - {defiAction.action}</DialogTitle>
            <DialogDescription className="text-gray-400">
              {defiAction.action === "Lend" 
                ? `Supply assets to ${defiAction.protocol} to earn interest`
                : `Borrow assets from ${defiAction.protocol} using your collateral`
              }
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={async (e) => {
            e.preventDefault();
            if (!selectedVault) {
              toast.error("Please select a vault first");
              return;
            }
            
            setLoading(true);
            try {
              const response = await axios.post(
                `${API}/defi/transaction`,
                {
                  vault_id: selectedVault.id,
                  protocol: defiAction.protocol,
                  action: defiAction.action,
                  token: defiTx.token,
                  amount: parseFloat(defiTx.amount)
                },
                getAuthHeaders()
              );
              
              toast.success(
                `${defiAction.action} transaction submitted! Hash: ${response.data.tx_hash.substring(0, 10)}...`,
                { duration: 7000 }
              );
              setDefiDialogOpen(false);
              setDefiTx({ token: "USDC", amount: "" });
              fetchBalance();
              fetchTransactions();
            } catch (error) {
              const errorMsg = error.response?.data?.detail || "Transaction failed";
              if (errorMsg.includes("watch") || errorMsg.includes("private key")) {
                toast.error("Cannot transact: This is a watch-only wallet. Create a new wallet to execute transactions.");
              } else {
                toast.error(errorMsg);
              }
            } finally {
              setLoading(false);
            }
          }} className="space-y-4">
            <div>
              <Label htmlFor="defi_token" className="text-gray-300">Select Token</Label>
              <select
                id="defi_token"
                value={defiTx.token}
                onChange={(e) => setDefiTx({ ...defiTx, token: e.target.value })}
                className="w-full bg-slate-800 border border-slate-600 text-white rounded-md p-2"
                data-testid="defi-token-select"
              >
                <option value="ETH">ETH (Ethereum)</option>
                <option value="USDC">USDC (USD Coin)</option>
                <option value="USDT">USDT (Tether)</option>
                <option value="ACS">ACS (ArtCubeSociety)</option>
              </select>
            </div>
            <div>
              <Label htmlFor="defi_amount" className="text-gray-300">Amount</Label>
              <Input
                id="defi_amount"
                type="number"
                step="0.01"
                value={defiTx.amount}
                onChange={(e) => setDefiTx({ ...defiTx, amount: e.target.value })}
                placeholder="0.0"
                required
                className="bg-slate-800 border-slate-600 text-white"
                data-testid="defi-amount-input"
              />
              {balance && (
                <p className="text-xs text-gray-400 mt-1">
                  Available: {
                    defiTx.token === "ETH" ? balance.eth_balance?.toFixed(4) :
                    defiTx.token === "ACS" ? balance.acs_balance?.toFixed(2) :
                    defiTx.token === "USDC" ? balance.balances?.USDC?.toFixed(2) :
                    defiTx.token === "USDT" ? balance.balances?.USDT?.toFixed(2) : 0
                  } {defiTx.token}
                </p>
              )}
            </div>
            <div className="bg-slate-800/50 p-3 rounded-lg">
              <p className="text-sm text-gray-300 mb-1">Protocol: <span className="text-white font-semibold">{defiAction.protocol}</span></p>
              <p className="text-sm text-gray-300">Action: <span className="text-white font-semibold">{defiAction.action}</span></p>
              <p className="text-xs text-gray-500 mt-2">
                {defiAction.action === "Lend" 
                  ? "You will supply tokens and earn interest based on protocol rates"
                  : "You will borrow tokens using your supplied assets as collateral"
                }
              </p>
            </div>
            <Button 
              type="submit" 
              className="w-full btn-primary" 
              disabled={loading}
              data-testid="defi-submit-btn"
            >
              {loading ? "Processing..." : `Execute ${defiAction.action}`}
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Dashboard;
