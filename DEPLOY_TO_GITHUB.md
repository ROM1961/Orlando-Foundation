# Push Vault Wallet to GitHub

## Step 1: Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `vault-wallet` (or your preferred name)
3. Keep it **Public** (required for Render free tier)
4. **Don't** initialize with README
5. Click "Create repository"

## Step 2: Get Your Code Ready

The code is in `/app` directory with this structure:
```
/app
├── backend/
│   ├── server.py
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── src/
│   ├── package.json
│   └── .env
├── render.yaml
└── README_RENDER_DEPLOYMENT.md
```

## Step 3: Download Your Code

1. In Emergent, click the **"Code diff view"** button (top right)
2. Or use VS Code button to explore files
3. Download all files from `/app` directory to your local computer

## Step 4: Push to GitHub

Open terminal in your downloaded folder and run:

```bash
# Initialize git
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit - Vault Wallet with ACS token integration"

# Add your GitHub repository (replace YOUR_USERNAME and REPO_NAME)
git remote add origin https://github.com/YOUR_USERNAME/vault-wallet.git

# Push to GitHub
git branch -M main
git push -u origin main
```

## Step 5: Go Back to Render

Now that your code is on GitHub, continue with Render deployment!
