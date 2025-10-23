# MongoDB Atlas Setup Guide for Vault Wallet

Since Render.com doesn't offer managed MongoDB, you'll need to use MongoDB Atlas (free tier available).

---

## Step 1: Create MongoDB Atlas Account

1. Go to: https://www.mongodb.com/cloud/atlas/register
2. Sign up with email or Google
3. Choose **"Free"** tier (M0 Sandbox)
4. Click **"Create"**

---

## Step 2: Create a Cluster

1. After signup, you'll be prompted to create a cluster
2. Choose:
   - **Cloud Provider**: AWS (recommended)
   - **Region**: Choose closest to your Render deployment region
     - US East (N. Virginia) for US East Render
     - EU West (Ireland) for EU Render
   - **Cluster Tier**: M0 Sandbox (FREE)
   - **Cluster Name**: `vault-wallet-cluster`

3. Click **"Create Cluster"** (takes 3-5 minutes)

---

## Step 3: Create Database User

1. On the left sidebar, click **"Database Access"**
2. Click **"Add New Database User"**
3. Configure:
   - **Authentication Method**: Password
   - **Username**: `vaultwallet_admin`
   - **Password**: Click "Autogenerate Secure Password" or create your own
   - **⚠️ SAVE THIS PASSWORD** - You'll need it for connection string
   - **Database User Privileges**: "Read and write to any database"

4. Click **"Add User"**

---

## Step 4: Whitelist IP Addresses

1. On the left sidebar, click **"Network Access"**
2. Click **"Add IP Address"**
3. Choose:
   - **ALLOW ACCESS FROM ANYWHERE**: `0.0.0.0/0`
   - This allows Render to connect (Render IPs change frequently)
   - ⚠️ This is safe because you have database password authentication

4. Click **"Confirm"**

---

## Step 5: Get Connection String

1. Go back to **"Database"** in left sidebar
2. Click **"Connect"** on your cluster
3. Choose **"Connect your application"**
4. Select:
   - **Driver**: Python
   - **Version**: 3.11 or later

5. Copy the connection string - it looks like:
   ```
   mongodb+srv://vaultwallet_admin:<password>@vault-wallet-cluster.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```

6. **Replace `<password>`** with your actual database password
7. **Add database name** before the `?`:
   ```
   mongodb+srv://vaultwallet_admin:YOUR_PASSWORD@vault-wallet-cluster.xxxxx.mongodb.net/vault_wallet?retryWrites=true&w=majority
   ```

---

## Step 6: Test Connection Locally (Optional)

```bash
# Install MongoDB client
pip install pymongo[srv]

# Test connection
python3 -c "
from pymongo import MongoClient
client = MongoClient('YOUR_CONNECTION_STRING')
db = client.vault_wallet
print('✅ Connected successfully!')
print('Databases:', client.list_database_names())
"
```

---

## Step 7: Add to Render Backend

1. In Render Dashboard, go to your backend service
2. Go to **"Environment"** tab
3. Update **MONGO_URL** environment variable:
   ```
   MONGO_URL=mongodb+srv://vaultwallet_admin:YOUR_PASSWORD@vault-wallet-cluster.xxxxx.mongodb.net/vault_wallet?retryWrites=true&w=majority
   ```

4. Click **"Save Changes"**
5. Backend will automatically redeploy

---

## Step 8: Create Database Indexes (After First Deploy)

After your backend is deployed and running, create indexes for better performance:

1. In MongoDB Atlas, go to **"Browse Collections"**
2. You should see `vault_wallet` database with collections:
   - `users`
   - `user_vaults`
   - `vault_transactions`

3. Create indexes:
   - **users collection**: Index on `email` (unique)
   - **user_vaults collection**: Index on `user_id` and `vault_address`
   - **vault_transactions collection**: Index on `vault_id` and `timestamp`

---

## MongoDB Atlas Free Tier Limits

✅ **What's Included (Free):**
- 512 MB storage
- Shared RAM
- Shared vCPU
- Good for ~5,000-10,000 users
- Automatic backups (7 days retention)

⚠️ **Limitations:**
- Shared cluster (may be slower under heavy load)
- Limited to 100 max connections

💡 **When to Upgrade:**
- More than 5,000 active users
- Need dedicated resources
- Need more storage
- Need more than 100 concurrent connections

**Upgrade Path:**
- M10 Cluster: ~$57/month (2GB RAM, 10GB storage)
- M20 Cluster: ~$117/month (4GB RAM, 20GB storage)

---

## Monitoring Your Database

### Check Usage:
1. Go to Atlas Dashboard
2. Click **"Metrics"** on your cluster
3. Monitor:
   - Storage usage
   - Operations per second
   - Network traffic
   - Connections

### Set Up Alerts:
1. Click **"Alerts"** in left sidebar
2. Set up alerts for:
   - Storage > 80% full
   - High CPU usage
   - Connection limit reached

---

## Backup & Restore

### Automatic Backups (Free Tier):
- ✅ Enabled automatically
- 7 days retention
- Point-in-time restore not available

### Manual Backup:
```bash
# Export specific collection
mongoexport --uri="YOUR_CONNECTION_STRING" --collection=users --out=users_backup.json

# Export entire database
mongodump --uri="YOUR_CONNECTION_STRING" --out=./backup
```

### Restore from Backup:
```bash
# Import collection
mongoimport --uri="YOUR_CONNECTION_STRING" --collection=users --file=users_backup.json

# Restore entire database
mongorestore --uri="YOUR_CONNECTION_STRING" ./backup
```

---

## Security Best Practices

1. ✅ Use strong passwords (20+ characters)
2. ✅ Rotate passwords every 90 days
3. ✅ Enable Multi-Factor Authentication on Atlas account
4. ✅ Use separate database users for different environments (dev/prod)
5. ✅ Monitor access logs regularly
6. ✅ Set up IP whitelisting if using static IPs

---

## Troubleshooting

**Error: "Authentication failed"**
- Check password is correct in connection string
- Verify user has correct permissions
- Ensure user is created in correct cluster

**Error: "Network error"**
- Check IP whitelist includes `0.0.0.0/0`
- Verify cluster is running (not paused)
- Check connection string format

**Error: "Too many connections"**
- Free tier limited to 100 connections
- Check for connection leaks in code
- Consider upgrading to M10 tier

**Slow queries:**
- Create appropriate indexes
- Monitor slow queries in Atlas UI
- Consider upgrading cluster tier

---

## Connection String Format Reference

**Basic Format:**
```
mongodb+srv://username:password@cluster.mongodb.net/database?options
```

**With All Options:**
```
mongodb+srv://username:password@cluster.mongodb.net/vault_wallet?retryWrites=true&w=majority&appName=VaultWallet
```

**Components:**
- `username`: Database user (not Atlas account email)
- `password`: Database user password (URL-encoded if contains special chars)
- `cluster`: Your cluster address
- `database`: Database name (`vault_wallet`)
- `options`: Additional connection options

---

## Need Help?

- **MongoDB Atlas Docs**: https://docs.atlas.mongodb.com
- **MongoDB University**: https://university.mongodb.com (free courses)
- **Community Forums**: https://www.mongodb.com/community/forums

---

## Summary Checklist

Before deploying to Render, ensure:

- [ ] MongoDB Atlas cluster created
- [ ] Database user created with strong password
- [ ] IP whitelist set to `0.0.0.0/0`
- [ ] Connection string copied and password replaced
- [ ] Database name added to connection string (`vault_wallet`)
- [ ] Connection tested locally (optional)
- [ ] Connection string added to Render environment variables
- [ ] Backend deployed and connected successfully

✅ **Once complete, your Render backend will connect to MongoDB Atlas!**
