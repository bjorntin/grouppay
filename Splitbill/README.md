# GroupPay Telegram Bot - Complete Setup Guide

## 🚀 Quick Start (5 Minutes!)

Transform your prototype into a working Telegram bot.

## 📋 Prerequisites

- Python 3.9+
- Telegram account
- 5 minutes

## Step 1: Get Bot Token from BotFather

1. Open Telegram, search `@BotFather`
2. Send: `/newbot`
3. Name: `GroupPay`
4. Username: `grouppay_yourname_bot`
5. Copy token (like `123456:ABC-DEF...`)

## Step 2: Setup

```bash
# Install
pip install python-telegram-bot==20.7 python-dotenv --break-system-packages

# Configure
echo "TELEGRAM_BOT_TOKEN=your_token_here" > .env
```

## Step 3: Run

```bash
python bot.py
```

## 🎯 What You Get

✅ Full bill splitting
✅ GST calculator (Singapore 10% + 9%)
✅ PayNow QR codes
✅ Privacy (amounts hidden in groups)
✅ Payment verification

## Commands

- `/start` - Begin
- `/split` - Split a bill
- `/help` - Help

## 📱 Test Flow

1. Search your bot in Telegram
2. `/start`
3. `/split`
4. Follow prompts!

The bot handles everything automatically!
