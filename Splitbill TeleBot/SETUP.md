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

Open a terminal in your project folder and run:

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/grouppay.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your GitHub username.

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

---

## Part 3: Configure the Bot

### Step 9 — Create the `.env` file

In `Splitbill TeleBot/`, create a file named exactly `.env`:

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

## Part 4: First-Time Setup (Bill Payer Only)

Only the person who paid the bill needs to do this once.

### Step 12 — The bill payer: Register PayNow

1. DM the bot: `/register`
2. Bot asks for your PayNow number
3. Reply with your 8-digit Singapore mobile number, e.g. `91234567`
4. Bot replies: `✅ PayNow number 91234567 saved!`

> **Everyone else (participants) does NOT need to do anything in advance.**
> No pre-registration, no `/start`, no DM required.

---

## Part 5: Using GroupPay

### Step 13 — Add the bot to your group

1. Open your group chat
2. Tap the group name → **Add Members**
3. Search for your bot → Add it

### Step 14 — Create a bill split

1. **In the group**, type `/split`
2. Bot posts a message with a **📱 Open GroupPay ↗** button
3. Tap it — Telegram opens a DM with the bot

   > **Why DM?** Telegram only allows Mini Apps to submit form data back to the bot
   > from a private chat. This is a Telegram platform limitation — the bill form
   > itself opens normally, and results are posted back to the group automatically.

4. Bot sends a **🧾 Open GroupPay** keyboard button — tap it
5. The Mini App opens in Telegram

### Step 15 — Fill in the bill

The Mini App has 4 screens:

1. **Bill Details** — enter event name, subtotal, toggle GST+SC if applicable
2. **Split type** — Equal or Custom amounts
3. **Participants** — add each person by their Telegram @username (without @)
4. **Review** — confirm everything → tap **✅ Confirm & Send**

### Step 16 — QR codes appear in the group

After submitting, the group receives **two types of messages**:

1. **Summary board** — shows everyone's name, amount owed, and payment status (⏳ / ✅)
2. **One whisper message per participant** — e.g.:
   ```
   🔒 @alice — $25.50 for Dinner at Saizeriya
   Tap View QR to get your PayNow QR code.
   Tap I've Paid after you've transferred.
   [👁 View QR & Pay 💳]  [✅ I've Paid]
   ```

### Step 17 — Each participant pays

Each person's whisper message has two buttons:

- **👁 View QR & Pay 💳** — opens a private Mini App overlay showing their PayNow QR code.
  Scan it with any Singapore banking app (PayLah!, PayNow, DBS, POSB, etc.) and transfer.
  The QR is generated on the spot and visible only to the person who taps it.

- **✅ I've Paid** — tap this after transferring. The bot verifies you're the right person
  (matched by your Telegram @username or user ID). Once confirmed:
  - Your whisper message updates to ✅ and buttons are removed
  - The summary board updates to show ✅ for your name

> **No pre-registration needed.** Participants just tap the buttons directly.
> They do not need to have messaged the bot before.

---

## Quick Reference

| Who | Does what | Where |
|-----|-----------|-------|
| Bill payer | `/register` | DM the bot (once) |
| Bill payer | `/split` | Group chat |
| Bill payer | Fill in bill form | Mini App (via DM link) |
| Each participant | Tap "View QR" | Group whisper message |
| Each participant | Scan QR, pay | Banking app |
| Each participant | Tap "I've Paid" | Group whisper message |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Bot doesn't see `/split` in group | Check `/setprivacy → Disable` in BotFather (Step 3) |
| "Bot URL not configured" | Check `MINI_APP_URL` in `.env` ends with `/` |
| Mini App opens blank | Wait a few min for GitHub Pages to deploy; check the URL works in a browser |
| QR screen shows "QR data missing" | Tap the "View QR" button again; the URL may have been truncated |
| "This button is not for you 😅" | You tapped someone else's I've Paid button |
| `pip install` fails | Make sure Python 3.9+ is installed: `python --version` |
| `.env` not loading | Make sure the file is named `.env` (not `env.txt` or `.env.txt`) |
