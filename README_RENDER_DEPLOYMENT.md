# Deploy Vault Wallet to Render.com

## Prerequisites
1. Create a free account at [Render.com](https://render.com)
2. Have a MongoDB Atlas account (free tier available at [MongoDB Atlas](https://www.mongodb.com/cloud/atlas))

## Step 1: Set Up MongoDB Atlas

1. Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Create a free cluster
3. Create a database user with password
4. Whitelist all IPs (0.0.0.0/0) in Network Access
5. Get your connection string (looks like: `mongodb+srv://username:password@cluster.mongodb.net/vault_wallet`)

## Step 2: Push Code to GitHub

```bash
# Initialize git repository (if not already done)
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit - Vault Wallet"

# Create repository on GitHub and push
git remote add origin https://github.com/YOUR_USERNAME/vault-wallet.git
git branch -M main
git push -u origin main
```

## Step 3: Deploy Backend to Render

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Configure:
   - **Name**: `vault-wallet-backend`
   - **Region**: Frankfurt (or closest to you)
   - **Branch**: `main`
   - **Root Directory**: `backend`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn server:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free

5. Add Environment Variables:
   ```
   MONGO_URL=mongodb+srv://YOUR_CONNECTION_STRING
   DB_NAME=vault_wallet
   ALCHEMY_API_KEY=OmycSw7kuH59o98EIRZLf
   ETHERSCAN_API_KEY=5PYUYWT9KVPUAPI92G6A2GXYCPKGE2PH86
   ENCRYPTION_KEY=899bdd1d6603b8ad056d17e3fc85eaf2346acc0b1156fb68654d46fff5b72d63
   ACS_TOKEN=0x1769AA7B5B4AAe76B7E6D797B379c21cAE12c46d
   ACS_PRICE_FEED=0x359767f0CE82592eED2F13F19B0252eB539C2A2D
   AAVE_POOL=0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2
   COMPOUND_COMET=0xA17581A9E3356d9A858b789D68B4d866e593aE94
   JWT_SECRET=your-random-secret-key-here
   JWT_ALGORITHM=HS256
   JWT_EXPIRATION_HOURS=24
   CORS_ORIGINS=*
   ```

6. Click "Create Web Service"
7. Wait for deployment (5-10 minutes)
8. Copy your backend URL (e.g., `https://vault-wallet-backend.onrender.com`)

## Step 4: Deploy Frontend to Render

1. Click "New +" → "Web Service"
2. Connect same GitHub repository
3. Configure:
   - **Name**: `vault-wallet-frontend`
   - **Region**: Same as backend
   - **Branch**: `main`
   - **Root Directory**: `frontend`
   - **Runtime**: Node
   - **Build Command**: `yarn install && yarn build`
   - **Start Command**: `yarn global add serve && serve -s build -p $PORT`
   - **Plan**: Free

4. Add Environment Variable:
   ```
   REACT_APP_BACKEND_URL=https://vault-wallet-backend.onrender.com
   ```
   (Use the backend URL from Step 3)

5. Click "Create Web Service"
6. Wait for deployment

## Step 5: Access Your Deployed Wallet

Your Vault Wallet is now live at:
`https://vault-wallet-frontend.onrender.com`

## Important Notes

- **Free Tier Limitations**: Services spin down after 15 minutes of inactivity. First request may take 30-60 seconds.
- **Upgrade**: For production use, upgrade to paid plans ($7/month per service) for always-on services.
- **Custom Domain**: Add custom domain in Render dashboard settings.
- **MongoDB**: Keep your MongoDB connection string secret!

## Troubleshooting

1. **Backend not starting**: Check logs in Render dashboard
2. **Frontend can't connect**: Verify REACT_APP_BACKEND_URL is correct
3. **MongoDB connection failed**: Check connection string and IP whitelist
4. **CORS errors**: Ensure CORS_ORIGINS includes your frontend URL

## Support

- Render Docs: https://render.com/docs
- Render Community: https://community.render.com
