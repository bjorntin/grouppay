#!/bin/bash
# GroupPay Telegram Bot - Quick Setup Script

echo "🚀 GroupPay Bot Setup"
echo "===================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Install it first."
    exit 1
fi

echo "✅ Python found"

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt --break-system-packages

# Check for .env
if [ ! -f .env ]; then
    echo ""
    echo "⚠️  No .env file found!"
    echo "📝 Create .env file with your bot token:"
    echo ""
    echo "1. Open Telegram, search @BotFather"
    echo "2. Send: /newbot"
    echo "3. Follow instructions"
    echo "4. Copy the token"
    echo "5. Run: echo 'TELEGRAM_BOT_TOKEN=your_token' > .env"
    echo ""
    exit 1
fi

echo "✅ .env file found"
echo ""
echo "🎉 Setup complete!"
echo ""
echo "To start the bot, run:"
echo "  python3 bot.py"
echo ""
