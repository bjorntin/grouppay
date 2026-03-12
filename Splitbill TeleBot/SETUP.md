# GroupPay — Complete Setup Guide

---

## Part 1: Create the Telegram Bot

### Step 1 — Open BotFather

1. Open Telegram (desktop or mobile)
2. In the search bar, search for **`@BotFather`** (blue checkmark, official)
3. Tap/click it → tap **Start**

### Step 2 — Create your bot

Type this command in the BotFather chat:
```
/newbot
```

BotFather will ask two questions:

1. **"What's the name of your bot?"**
   — This is the display name users see, e.g. `GroupPay`

2. **"What username would you like?"**
   — Must end in `bot`, e.g. `GroupPaySplitBot`
   — Must be globally unique — try a few if it's taken

BotFather replies with:
```
Done! Your bot token is:
123456789:ABCdefGHIjklMNOpqrSTUvwxYZ
```
TOKEN I GOT: 8616935012:AAEp1raouLovkij5BgddL2PB6Uc8kZuAHts

**Copy and save this token — you'll need it soon.**

### Step 3 — Disable privacy mode (required for groups)

Still in BotFather, type:
```
/setprivacy
```
- Select your bot from the list
- Select **Disable**

This allows the bot to see messages in group chats.

---

## Part 2: Host the Mini App on GitHub Pages

Telegram Mini Apps **must** be served over HTTPS. GitHub Pages gives you a free permanent HTTPS URL.

### Step 4 — Create a GitHub account (if you don't have one)

Go to [github.com](https://github.com) → Sign up (free).

### Step 5 — Create a new repository

1. Click the **+** icon (top right) → **New repository**
2. Name it something like `grouppay` (lowercase)
3. Set visibility to **Public** (required for free GitHub Pages)
4. Click **Create repository**

### Step 6 — Push your project to GitHub

Open a terminal in your project folder (`E:/Y3S2/CS206/Project`) and run:

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/grouppay.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your GitHub username and `grouppay` with your repo name.

### Step 7 — Enable GitHub Pages

1. Go to your repo on GitHub
2. Click **Settings** (top tab) → **Pages** (left sidebar)
3. Under **Source**, select:
   - Branch: `main`
   - Folder: `/ (root)`
4. Click **Save**
5. Wait about 1–2 minutes
6. GitHub shows your URL: `https://YOUR_USERNAME.github.io/grouppay/`

Your Mini App URL is:
```
https://YOUR_USERNAME.github.io/grouppay/frontend/
```

### Step 8 — Register the Mini App with BotFather

Back in the BotFather chat, type:
```
/newapp
```
- Select your bot
- **Title**: `GroupPay`
- **Description**: `Split bills with friends`
- **Photo**: Skip by sending any small image (or `/skip` if prompted)
- **GIF**: `/skip`
- **URL**: paste your GitHub Pages URL, e.g.:
  ```
  https://YOUR_USERNAME.github.io/grouppay/frontend/
  ```
- **Short name**: `grouppay`

This step isn't strictly required for the bot to work, but it formally registers the Mini App with Telegram.
https://t.me/GroupPaySplitBot/grouppay
---

## Part 3: Configure the Bot

### Step 9 — Create the `.env` file

In `Splitbill TeleBot/`, create a file named exactly `.env` (no filename, just the extension):

```
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxYZ
MINI_APP_URL=https://YOUR_USERNAME.github.io/grouppay/frontend/
BOT_USERNAME=GroupPaySplitBot
```

- `TELEGRAM_BOT_TOKEN` — from Step 2
- `MINI_APP_URL` — your GitHub Pages URL from Step 7 (with trailing `/`)
- `BOT_USERNAME` — your bot's username **without** the `@`

### Step 10 — Install Python dependencies

Open a terminal in `Splitbill TeleBot/`:

```bash
cd "Splitbill TeleBot"
pip install -r requirements.txt
```

If `pip` isn't found, try `pip3` or `python -m pip`.

This installs:
- `python-telegram-bot` — the bot framework
- `python-dotenv` — reads your `.env` file
- `qrcode` + `Pillow` — generates the PayNow QR images

### Step 11 — Run the bot

```bash
python bot.py
```

You should see:
```
2026-03-12 12:00:00 [INFO] Bot ready. Press Ctrl+C to stop.
```

The bot is now live. **Keep this terminal open** — closing it stops the bot.

---

## Part 4: First-Time User Setup

Every person who wants to use GroupPay needs to do this **once**:

### Step 12 — Everyone: Start the bot in DM

In Telegram, search for your bot (e.g. `@GroupPaySplitBot`) → tap **Start**.

This is required so the bot can DM you later (Telegram blocks unsolicited DMs).

### Step 13 — The bill payer: Register PayNow

The person who paid the bill (and wants to receive money) must register:

1. DM the bot: `/register`
2. Bot asks for your PayNow number
3. Reply with your 8-digit Singapore mobile number, e.g. `91234567`
4. Bot replies: `✅ PayNow number 91234567 saved!`

---

## Part 5: Using GroupPay

### Step 14 — Add the bot to your group

1. Open your group chat
2. Tap the group name → **Add Members**
3. Search for your bot → Add it

### Step 15 — Create a bill split

1. **In the group**, type `/split`
2. Bot posts a message with a **📱 Open GroupPay ↗** button
3. Tap it — Telegram opens a DM with the bot
4. Bot sends a **🧾 Open GroupPay** keyboard button — tap it
5. The Mini App opens in Telegram

### Step 16 — Fill in the bill

The Mini App has 4 screens:

1. **Bill Details** — enter event name, subtotal, toggle GST+SC if applicable
2. **Split type** — Equal (everyone pays the same) or Custom (specify each person's amount)
3. **Participants** — add each person by their Telegram @username (without @)
4. **Review** — confirm everything looks right → tap **✅ Confirm & Send**

### Step 17 — Participants get their QR codes

After submitting:
- The group receives a summary showing everyone's amount and payment status (⏳)
- Each participant taps their **Get QR 💳** button
- The bot sends them a PayNow QR code in DM
- They scan it with their banking app and pay
- They tap **✅ I've Paid** in the DM
- The group message updates to show ✅ for that person

---

## Quick Reference

| Who | Does what | Where |
|-----|-----------|-------|
| Everyone | `/start` | DM the bot |
| Bill payer | `/register` | DM the bot |
| Bill payer | `/split` | Group chat |
| Each participant | Tap "Get QR 💳" | Group chat |
| Each participant | Tap "I've Paid" | DM from bot |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Bot doesn't see `/split` in group | Check `/setprivacy → Disable` in BotFather (Step 3) |
| "Bot URL not configured" | Check `MINI_APP_URL` in `.env` ends with `/` |
| Mini App opens blank | Wait a few min for GitHub Pages to deploy; check the URL works in a browser |
| "Please start me in DM" error | That participant needs to do Step 12 |
| `pip install` fails | Make sure Python 3.9+ is installed: `python --version` |
| `.env` not loading | Make sure the file is named `.env` (not `env.txt` or `.env.txt`) |
