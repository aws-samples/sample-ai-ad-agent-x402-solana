# SET UP

1. First deploy the paid server by navigating into `paid-endpoint-server` and following the instructions below:

# Detailed Setup Guide

This guide provides step-by-step instructions to set up and run the Solana x402 Payment Server.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Setting Up Your Development Environment](#setting-up-your-development-environment)
3. [Getting a Solana Wallet](#getting-a-solana-wallet)
4. [Obtaining Test Funds](#obtaining-test-funds)
5. [Getting API Keys](#getting-api-keys)
6. [Configuring the Server](#configuring-the-server)
7. [Running and Testing](#running-and-testing)
8. [Understanding x402 Payments](#understanding-x402-payments)
9. [Production Deployment](#production-deployment)

---

## 1. System Requirements

### Minimum Requirements

- **Operating System**: Windows 10+, macOS 10.15+, or Linux (Ubuntu 20.04+ recommended)
- **Node.js**: Version 18.0.0 or higher
- **RAM**: 4GB minimum
- **Disk Space**: 500MB for project and dependencies

### Check Your Current Setup

```bash
# Check Node.js version
node --version
# Should output v18.x.x or higher

# Check npm version
npm --version
# Should output 9.x.x or higher
```

### Installing Node.js

If you don't have Node.js or need to upgrade:

**Option A: Using Official Installer**
1. Visit [nodejs.org](https://nodejs.org/)
2. Download the LTS version
3. Run the installer

**Option B: Using nvm (Recommended for developers)**
```bash
# Install nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash

# Install latest LTS
nvm install --lts

# Use it
nvm use --lts
```

---

## 2. Setting Up Your Development Environment

### Clone or Download the Project

```bash
# If using git
git clone <repository-url>
cd solana-x402-server

# Or if you downloaded a zip
unzip solana-x402-server.zip
cd solana-x402-server
```

### Install Dependencies

```bash
npm install
```

This will install:
- Express.js - Web server framework
- x402-express - Payment middleware
- TypeScript - Type-safe JavaScript
- Zod - Runtime validation
- Axios - HTTP client
- dotenv - Environment variable management

### Verify Installation

```bash
# Check if TypeScript is installed
npx tsc --version

# List installed packages
npm list --depth=0
```

---

## 3. Getting a Solana Wallet

You need a Solana wallet to receive payments. Choose one method:

### Method A: Phantom Wallet (Easiest)

1. **Install Browser Extension**
   - Visit [phantom.app](https://phantom.app/)
   - Click "Download"
   - Install for Chrome, Firefox, Brave, or Edge

2. **Create New Wallet**
   - Open Phantom extension
   - Click "Create New Wallet"
   - Save your recovery phrase securely (CRITICAL!)
   - Set a password

3. **Switch to Devnet**
   - Click settings (gear icon)
   - Scroll to "Developer Settings"
   - Toggle "Testnet Mode"
   - Select "Devnet"

4. **Copy Your Address**
   - Click on your address at the top
   - It will copy to clipboard
   - Example format: `5tzFkiKscXHK5ZXCGbXZxdw7gTjjD1mBwuoFbhUvuAi9`

### Method B: Solflare Wallet

1. Install from [solflare.com](https://solflare.com/)
2. Create wallet and save recovery phrase
3. Go to Settings → Network → Select "Devnet"
4. Copy your wallet address

### Method C: Solana CLI (For Advanced Users)


```bash
# Install Solana CLI
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    pkg-config \
    libudev-dev llvm libclang-dev \
    protobuf-compiler libssl-dev

curl --proto '=https' --tlsv1.2 -sSfL https://solana-install.solana.workers.dev | bash
. "$HOME/.cargo/env"
export PATH="/home/sagemaker-user/.local/share/solana/install/active_release/bin:$PATH"

# Generate Solana Account
python generate_keypair.py
```

---

## 4. Create Token and Token Account for Sender and Receiver

Step 1: Create Your Own Test Token
```
# Create a new token (regular SPL token, not Token-2022)
spl-token create-token --decimals 6

# Output will show something like:
# Creating token ABC123...
# Address: ABC123...
# 
# Copy this address!
```
Step 2: Create Token Accounts
```
# Save your token mint address
TOKEN_MINT="7xYourNewToken123456789"  # Replace with actual address from step 1

# Create token account for YOU
spl-token create-account $TOKEN_MINT

# Create token account for RECIPIENT
spl-token create-account $TOKEN_MINT --owner RECEIVER_ADDRESS --fee-payer PATH-TO-KEYPAIR-FILE

# Mint tokens to yourself
spl-token mint $TOKEN_MINT 10000

# Check balance
spl-token balance $TOKEN_MINT
```
---

## 5. Getting API Keys

### OpenWeather API Key

1. **Sign Up**
   - Go to [openweathermap.org](https://openweathermap.org/)
   - Click "Sign Up" (free tier is sufficient)
   - Complete registration

2. **Get API Key**
   - Log in to your account
   - Go to [API Keys](https://home.openweathermap.org/api_keys)
   - Copy your default API key OR generate a new one
   - Example: `<your-openweather-api-key>`

3. **Verify API Key** (Optional but recommended)
   ```bash
   curl "https://api.openweathermap.org/data/2.5/weather?q=London&appid=YOUR_API_KEY"
   ```
   You should get JSON weather data.

---

## 6. Configuring the Server

### Create Environment File

```bash
# Copy the example file
cp .env.example .env
```

### Edit .env File

Open `.env` in your favorite text editor and fill in the values:

```env
# Payment Receiver Solana wallet address (from Step 3)
SELLER_ADDRESS=5tzFkiKscXHK5ZXCGbXZxdw7gTjjD1mBwuoFbhUvuAi9

# Your OpenWeather API key (from Step 5)
OPENWEATHER_API_KEY=<your-openweather-api-key>

# The Token asset ID used for payment currency
PAYMENT_TOKEN_ID=CvArN2zZbDkswQ4g8MZZUNnkJHbHpM5j7isaLfMARGbD  # If you created a new token replace teh value here, or use on of the known token ID (USDC..)

# Solana address private key
SOLANA_PRIVATE_KEY=""  # Your solana address private key

# Facilitator URL (use default or specify custom)
FACILITATOR_URL=https://x402.org/facilitator  # Use this URL
```

### Important Notes

- **SELLER_ADDRESS**: Must be base58 format (NOT `0x...`)
- **OPENWEATHER_API_KEY**: Must be a valid API key
- **Never commit** your `.env` file to version control
- The `.gitignore` file already excludes it

---

## 7. Running and Testing

### Start the Server

**Development Mode (Recommended):**
```bash
npm run dev
```

This uses `tsx` for hot-reloading. Changes to your code will automatically restart the server.

**Production Mode:**
```bash
# Compile TypeScript to JavaScript
npm run build

# Run the compiled code
npm start
```


2. Run the python notebook `agentkit-x402-strands.ipynb` to exeprience the chatbot

To validate tranactions,
1. Prompt the agent for the transaction has
2. copy the hash and paste it in `https://solscan.io/?cluster=devnet`# aws-x402-solana-repo
# aws-x402-solana-repo
# aws-x402-solana-repo
# ai-ad-agent-x402-solana-repo
