# GroupPay — Telegram Mini App Bot

Split bills in group chats with a proper UI. Sends PayNow QR codes privately.

---

## Setup

### 1. BotFather

1. `/newbot` → get your bot token
2. `/setprivacy` → select your bot → **Disable** (so bot sees group messages)
3. Note your bot's username (without `@`)

### 2. GitHub Pages (Mini App hosting)

Telegram Mini Apps require HTTPS. GitHub Pages is free.

1. Push this project to a GitHub repo
2. Repo **Settings → Pages → Source**: Deploy from branch → `main`, folder `/root`
3. Wait ~1 min → your URL: `https://<username>.github.io/<repo>/`
4. Your Mini App URL will be: `https://<username>.github.io/<repo>/frontend/`

### 3. Install dependencies

```bash
cd "Splitbill TeleBot"
pip install -r requirements.txt
```

### 4. Configure environment

Create a `.env` file in `Splitbill TeleBot/`:

```
TELEGRAM_BOT_TOKEN=123456:ABCdef...
MINI_APP_URL=https://yourusername.github.io/yourrepo/frontend/
BOT_USERNAME=YourBotName
```

> `BOT_USERNAME` — your bot's username **without** the `@`.

### 5. Run the bot

```bash
python bot.py
```

You should see: `Bot ready. Press Ctrl+C to stop.`

---

## First-time user flow

1. **Everyone** in the group: DM the bot `/start`
   - This lets the bot send you QR codes later (Telegram requires you to have started a bot before it can DM you)

2. **The person paying**: DM the bot `/register`
   - Bot asks for your PayNow mobile number (8 digits, e.g. `91234567`)

---

## Usage

1. In a group chat: `/split`
2. Tap **📱 Open GroupPay ↗** → bot DMs you
3. Tap **🧾 Open GroupPay** in the DM → Mini App opens
4. Fill in:
   - Event name
   - Total amount
   - GST/SC toggle (adds 10% SC + 9% GST on SC-inclusive amount)
   - Split type: Equal or Custom
   - Add participants by @username
5. Review → **Confirm & Send**
6. Bot posts summary to the group with "Get QR" buttons
7. Each participant taps their **Get QR 💳** button → QR arrives in DM
8. Pay via PayNow, then tap **✅ I've Paid** → group message updates

---

## Architecture

```
Group chat          DM with bot              Mini App (GitHub Pages)
──────────          ───────────              ──────────────────────
/split
Bot posts link ──► /start grp_{chat_id}
                   Bot sends WebApp button
                   User taps ──────────────► Bill form UI
                   web_app_data ◄────────── Submit (sendData)
Bot posts summary ◄─────────────────────────
  + "Get QR" buttons
Participant taps ──► Bot sends QR to DM
                   "I've Paid" ────────────► Group message updated
```

**Why DM for Mini App:** `sendData()` only works in private chats (Telegram limitation). The `/split` command posts a deep link that opens a DM where the WebApp keyboard button works.

---

## Database

SQLite file `splitbill.db` is auto-created on first run. Tables:

- `users` — user_id, username, first_name, paynow_number
- `bills` — bill metadata + group message ID for editing
- `bill_participants` — per-person amounts and payment status

---

## File structure

```
Splitbill TeleBot/
├── bot.py              # Telegram bot backend
├── requirements.txt
├── README.md
├── splitbill.db        # Auto-created
└── frontend/
    ├── index.html      # Mini App (4 screens)
    ├── style.css
    └── app.js
```

`paynow_qr.py` at the project root is imported automatically.
