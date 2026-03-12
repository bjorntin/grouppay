# GroupPay Telegram Bot - Complete Guide

## ⚡ 5-Minute Setup

### 1. Get Bot Token
- Open Telegram → Search `@BotFather`
- Send `/newbot`
- Name: GroupPay
- Username: `grouppay_yourname_bot`
- Copy token

### 2. Install
```bash
cd telegram-bot
pip install -r requirements.txt --break-system-packages
echo "TELEGRAM_BOT_TOKEN=your_token" > .env
```

### 3. Run
```bash
python bot.py
```

### 4. Test
- Search bot in Telegram
- Send `/start`
- Send `/split`

## ✨ Features
✅ Bill splitting
✅ GST calc (10% + 9%)
✅ Private amounts
✅ Group privacy
✅ PayNow ready

## 🚀 Deploy to Cloud

### Render.com (Free)
1. Push to GitHub
2. render.com → New Background Worker
3. Add `TELEGRAM_BOT_TOKEN`
4. Deploy!

### Railway.app
1. railway.app
2. Deploy from GitHub
3. Add token variable
4. Done!

## 📝 Bot Commands
- `/start` - Welcome
- `/split` - New split
- `/cancel` - Cancel

## 🎯 User Flow
```
/split → Who paid → Event → Amount → 
GST calc → Participants → Split → 
✅ Group announcement (no amounts) +
📱 Private DMs with QR codes
```

All working and tested! 🚀
