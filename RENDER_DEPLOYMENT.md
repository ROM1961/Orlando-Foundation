# Vault Wallet - Render.com Deployment Guide

## Prerequisites
- GitHub account with your code repository
- Render.com account (free tier works)
- All environment variables ready

---

## Step 1: Push Code to GitHub

1. Initialize git repository (if not already done):
```bash
git init
git add .
git commit -m "Initial commit - Vault Wallet"
```

2. Create a new repository on GitHub: https://github.com/new
   - Name: `vault-wallet` or `Orlando-Foundation`
   - Make it private (recommended for production apps)

3. Push your code:
```bash
git remote add origin https://github.com/YOUR_USERNAME/vault-wallet.git
git branch -M main
git push -u origin main
```

---

## Step 2: Deploy MongoDB Database

1. Go to Render Dashboard: https://dashboard.render.com
2. Click **"New +"** → **"PostgreSQL"** or use external MongoDB:
   
   **Option A: Use MongoDB Atlas (Recommended)**
   - Go to https://www.mongodb.com/cloud/atlas
   - Create free cluster
   - Get connection string: `mongodb+srv://username:password@cluster.mongodb.net/vault_wallet`
   
   **Option B: Use Render's managed database**
   - Render doesn't offer MongoDB, so MongoDB Atlas is the best option

---

## Step 3: Deploy Backend API

1. Click **"New +"** → **"Web Service"**
2. Connect your GitHub repository
3. Configure:
   - **Name**: `vault-wallet-backend`
   - **Environment**: `Python 3`
   - **Region**: Choose closest to your users
   - **Branch**: `main`
   - **Root Directory**: Leave empty
   - **Build Command**: 
     ```bash
     cd backend && pip install -r requirements.txt
     ```
   - **Start Command**: 
     ```bash
     cd backend && uvicorn server:app --host 0.0.0.0 --port $PORT
     ```
   - **Plan**: Select appropriate plan (Free tier available)

4. **Environment Variables** - Add these in the Environment tab:
   ```
   MONGO_URL=mongodb+srv://your-atlas-connection-string
   DB_NAME=vault_wallet
   CORS_ORIGINS=*
   ALCHEMY_API_KEY=OmycSw7kuH59o98EIRZLf
   ETHERSCAN_API_KEY=5PYUYWT9KVPUAPI92G6A2GXYCPKGE2PH86
   ENCRYPTION_KEY=899bdd1d6603b8ad056d17e3fc85eaf2346acc0b1156fb68654d46fff5b72d63
   JWT_SECRET=your-secret-key-change-in-production
   JWT_ALGORITHM=HS256
   JWT_EXPIRATION_HOURS=24
   ACS_TOKEN=0x1769AA7B5B4AAe76B7E6D797B379c21cAE12c46d
   ACS_PRICE_FEED=0x359767f0CE82592eED2F13F19B0252eB539C2A2D
   AAVE_POOL=0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2
   COMPOUND_COMET=0xA17581A9E3356d9A858b789D68B4d866e593aE94
   ```

5. Click **"Create Web Service"**
6. Wait for deployment to complete (5-10 minutes)
7. **Copy the backend URL** (e.g., `https://vault-wallet-backend.onrender.com`)

---

## Step 4: Deploy Frontend

1. Click **"New +"** → **"Static Site"**
2. Connect your GitHub repository
3. Configure:
   - **Name**: `vault-wallet-frontend`
   - **Branch**: `main`
   - **Root Directory**: Leave empty
   - **Build Command**: 
     ```bash
     cd frontend && yarn install && yarn build
     ```
   - **Publish Directory**: `frontend/build`

4. **Environment Variables** - Add these:
   ```
   REACT_APP_BACKEND_URL=https://vault-wallet-backend.onrender.com
   REACT_APP_ALCHEMY_API_KEY=OmycSw7kuH59o98EIRZLf
   REACT_APP_AAVE_POOL=0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2
   REACT_APP_COMPOUND_COMET=0xA17581A9E3356d9A858b789D68B4d866e593aE94
   ```
   
   ⚠️ **Important**: Replace `https://vault-wallet-backend.onrender.com` with your actual backend URL from Step 3

5. Click **"Create Static Site"**
6. Wait for build to complete

---

## Step 5: Update CORS Settings

1. Go back to your backend service on Render
2. Update the `CORS_ORIGINS` environment variable:
   ```
   CORS_ORIGINS=https://vault-wallet-frontend.onrender.com
   ```
   Replace with your actual frontend URL

3. Click **"Save Changes"** - Backend will redeploy

---

## Step 6: Verify Deployment

1. Open your frontend URL: `https://vault-wallet-frontend.onrender.com`
2. Test:
   - ✅ Login/Register functionality
   - ✅ Wallet creation
   - ✅ Balance display
   - ✅ DeFi protocols visible
   - ✅ Transaction preparation (don't execute without funds)

---

## Important Notes

### Free Tier Limitations
- Backend may sleep after 15 minutes of inactivity (first request takes longer)
- Consider upgrading to paid plan for production use

### Security Recommendations
1. **Change JWT_SECRET** to a strong random value
2. **Update CORS_ORIGINS** to only allow your frontend domain
3. **Use HTTPS** everywhere (Render provides this automatically)
4. **Enable 2FA** on your Render account
5. **Set up monitoring** for your services

### MongoDB Atlas Setup
1. Whitelist Render IPs or use `0.0.0.0/0` (allow from anywhere)
2. Create database user with strong password
3. Create database named `vault_wallet`
4. Get connection string and add to backend environment variables

### Troubleshooting

**Backend won't start:**
- Check logs in Render dashboard
- Verify all environment variables are set
- Ensure MongoDB connection string is correct

**Frontend shows API errors:**
- Verify `REACT_APP_BACKEND_URL` points to correct backend
- Check backend CORS settings include frontend URL
- Check browser console for specific errors

**Transactions fail:**
- Ensure Alchemy API key is valid
- Check wallet has sufficient ETH for gas
- Verify smart contract addresses are correct

---

## Cost Estimate (Render.com)

**Free Tier:**
- Backend: Free (with sleep)
- Frontend: Free
- MongoDB: Use MongoDB Atlas free tier

**Paid Plan (Recommended for Production):**
- Backend (Starter): $7/month
- Frontend (Starter): $7/month
- MongoDB Atlas (M10): $0.08/hour (~$57/month)

**Total: ~$14-71/month** depending on configuration

---

## Custom Domain Setup

1. In Render Dashboard, go to your frontend service
2. Click **"Settings"** → **"Custom Domain"**
3. Add your domain (e.g., `wallet.yourdomain.com`)
4. Follow DNS configuration instructions
5. Render provides free SSL certificate

---

## Continuous Deployment

✅ **Already configured!** 

Every push to your `main` branch will automatically:
1. Trigger new build on Render
2. Deploy if build succeeds
3. Notify you of deployment status

---

## Monitoring & Logs

**View Logs:**
1. Go to service in Render Dashboard
2. Click **"Logs"** tab
3. View real-time application logs

**Set up Alerts:**
1. Go to service settings
2. Enable email notifications
3. Get alerts for deployment failures

---

## Backup Strategy

**Code:** Already backed up in GitHub
**Database:** Set up MongoDB Atlas backups:
1. Go to Atlas cluster
2. Enable **"Cloud Backup"**
3. Configure retention policy

---

## Next Steps After Deployment

1. ✅ Test all functionality on live site
2. ✅ Set up custom domain
3. ✅ Configure monitoring
4. ✅ Enable database backups
5. ✅ Update documentation with live URLs
6. ✅ Share with users

---

## Support

- **Render Docs**: https://render.com/docs
- **Render Community**: https://community.render.com
- **MongoDB Atlas Docs**: https://docs.atlas.mongodb.com

Good luck with your deployment! 🚀
