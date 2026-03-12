"""
GroupPay Telegram Bot — MVP
Requires: python-telegram-bot==20.7, python-dotenv, qrcode[pil], Pillow
"""

import asyncio
import json
import logging
import os
import sqlite3
import sys
import uuid
from datetime import datetime
from io import BytesIO

from dotenv import load_dotenv
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputFile,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
    WebAppInfo,
)
from telegram.constants import ParseMode
from telegram.error import Forbidden, TelegramError
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MINI_APP_URL = os.getenv("MINI_APP_URL", "")
BOT_USERNAME = os.getenv("BOT_USERNAME", "")  # without @, e.g. "GroupPayBot"

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# PayNow QR lives at project root — one level up from this file
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from paynow_qr import PayNowQR  # noqa: E402

DB_PATH = os.path.join(os.path.dirname(__file__), "splitbill.db")

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT,
                first_name  TEXT,
                paynow_number TEXT
            );

            CREATE TABLE IF NOT EXISTS bills (
                bill_id         TEXT PRIMARY KEY,
                group_chat_id   INTEGER,
                payer_id        INTEGER,
                event_name      TEXT,
                total_amount    REAL,
                gst_applied     INTEGER DEFAULT 0,
                group_message_id INTEGER,
                created_at      TEXT,
                is_active       INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS bill_participants (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                bill_id     TEXT,
                user_id     INTEGER,
                username    TEXT,
                amount_owed REAL,
                is_paid     INTEGER DEFAULT 0
            );
        """)


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def short_id() -> str:
    """8-char alphanumeric bill ID."""
    return uuid.uuid4().hex[:8]


def to_base36(n: int) -> str:
    """Encode integer as base-36 string (safe for callback_data)."""
    chars = "0123456789abcdefghijklmnopqrstuvwxyz"
    if n == 0:
        return "0"
    result = ""
    while n:
        result = chars[n % 36] + result
        n //= 36
    return result


def from_base36(s: str) -> int:
    return int(s, 36)


def generate_qr_bytes(paynow_number: str, amount: float, name: str) -> BytesIO:
    """Generate a PayNow QR code image in memory."""
    mobile = paynow_number if paynow_number.startswith("+") else "+65" + paynow_number
    qr_gen = PayNowQR(mobile, amount, name)
    payload = qr_gen.generate_payload()

    import qrcode as qrcode_lib
    qr = qrcode_lib.QRCode(
        error_correction=qrcode_lib.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="purple", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def upsert_user(user_id: int, username: str | None, first_name: str | None) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO users (user_id, username, first_name)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username   = excluded.username,
                first_name = excluded.first_name
            """,
            (user_id, username or "", first_name or ""),
        )


def build_summary(bill_id: str) -> tuple[str, InlineKeyboardMarkup]:
    """Build the group summary message text + inline keyboard."""
    with get_conn() as conn:
        bill = conn.execute("SELECT * FROM bills WHERE bill_id=?", (bill_id,)).fetchone()
        payer = conn.execute("SELECT * FROM users WHERE user_id=?", (bill["payer_id"],)).fetchone()
        participants = conn.execute(
            "SELECT * FROM bill_participants WHERE bill_id=? ORDER BY id", (bill_id,)
        ).fetchall()

    payer_name = payer["first_name"] if payer else "?"
    gst_label = " (incl. GST)" if bill["gst_applied"] else ""
    lines = [
        f"📋 *{bill['event_name']}*",
        f"Paid by: {payer_name}  |  Total: ${bill['total_amount']:.2f}{gst_label}",
        "",
    ]

    buttons = []
    for p in participants:
        handle = f"@{p['username']}" if p["username"] else f"User {p['user_id']}"
        status = "✅ Paid" if p["is_paid"] else "⏳"
        lines.append(f"{handle}  ${p['amount_owed']:.2f}   {status}")
        if not p["is_paid"] and p["user_id"]:
            uid_b36 = to_base36(p["user_id"])
            buttons.append(
                InlineKeyboardButton(
                    f"Get QR 💳 — {handle}",
                    callback_data=f"qr:{bill_id}:{uid_b36}",
                )
            )

    keyboard = []
    # Two buttons per row
    for i in range(0, len(buttons), 2):
        keyboard.append(buttons[i : i + 2])

    return "\n".join(lines), InlineKeyboardMarkup(keyboard) if keyboard else InlineKeyboardMarkup([])


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    upsert_user(user.id, user.username, user.first_name)

    args = context.args  # list of words after /start
    param = args[0] if args else ""

    if param.startswith("grp_"):
        # Deep-link from group — send WebApp keyboard
        raw_chat_id = param  # keep full "grp_XXXX" as start_param for Mini App
        if not MINI_APP_URL:
            await update.message.reply_text("Mini App URL not configured. Ask the admin to set MINI_APP_URL.")
            return

        context.user_data["pending_group"] = param  # store for reference

        keyboard = ReplyKeyboardMarkup(
            [[KeyboardButton("🧾 Open GroupPay", web_app=WebAppInfo(url=MINI_APP_URL))]],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
        await update.message.reply_text(
            "Tap the button below to open GroupPay and fill in the bill details:",
            reply_markup=keyboard,
        )
    else:
        await update.message.reply_text(
            f"👋 Hi {user.first_name}! I'm GroupPay.\n\n"
            "• Use /register to save your PayNow number.\n"
            "• Add me to a group and use /split to create a bill.\n\n"
            "Everyone in the group should DM me /start once so I can send you QR codes.",
        )


async def cmd_register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start PayNow registration flow."""
    if update.effective_chat.type != "private":
        await update.message.reply_text("Please DM me to register your PayNow number.")
        return

    user = update.effective_user
    upsert_user(user.id, user.username, user.first_name)

    args = context.args
    if args:
        await _save_paynow(update, context, args[0])
    else:
        context.user_data["awaiting_paynow"] = True
        await update.message.reply_text(
            "Please send your PayNow mobile number (e.g. 91234567):"
        )


async def _save_paynow(update: Update, context: ContextTypes.DEFAULT_TYPE, number: str) -> None:
    number = number.strip().lstrip("+65").strip()
    if not number.isdigit() or len(number) != 8:
        await update.message.reply_text("Invalid number. Please send an 8-digit Singapore mobile number (e.g. 91234567).")
        return

    user = update.effective_user
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET paynow_number=? WHERE user_id=?",
            (number, user.id),
        )
    context.user_data.pop("awaiting_paynow", None)
    await update.message.reply_text(f"✅ PayNow number {number} saved!")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle plain text messages (used for PayNow registration flow)."""
    if context.user_data.get("awaiting_paynow"):
        await _save_paynow(update, context, update.message.text)


async def cmd_split(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Group command — post deep-link button."""
    if update.effective_chat.type == "private":
        await update.message.reply_text("Use /split in a group chat.")
        return

    user = update.effective_user
    chat = update.effective_chat
    upsert_user(user.id, user.username, user.first_name)

    # Check payer is registered
    with get_conn() as conn:
        row = conn.execute("SELECT paynow_number FROM users WHERE user_id=?", (user.id,)).fetchone()

    if not row or not row["paynow_number"]:
        await update.message.reply_text(
            "⚠️ You need to register your PayNow number first.\n"
            "DM me: /register"
        )
        return

    if not BOT_USERNAME:
        await update.message.reply_text("BOT_USERNAME not configured. Ask the admin.")
        return

    deep_link = f"https://t.me/{BOT_USERNAME}?start=grp_{chat.id}"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 Open GroupPay ↗", url=deep_link)]
    ])
    await update.message.reply_text(
        "💳 *GroupPay*\nTap below to fill in bill details:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard,
    )


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear()
    await update.message.reply_text("Session cleared.", reply_markup=ReplyKeyboardRemove())


# ---------------------------------------------------------------------------
# Mini App data handler
# ---------------------------------------------------------------------------

async def handle_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Receive JSON from the Mini App via sendData()."""
    raw = update.message.web_app_data.data
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        await update.message.reply_text("Invalid data received. Please try again.")
        return

    user = update.effective_user
    group_chat_id_str = data.get("group_chat_id")
    if not group_chat_id_str:
        await update.message.reply_text("Missing group_chat_id. Please try again via /split.")
        return

    try:
        group_chat_id = int(group_chat_id_str)
    except (ValueError, TypeError):
        await update.message.reply_text("Invalid group_chat_id.")
        return

    event_name = data.get("event", "Bill")
    total_amount = float(data.get("total", 0))
    gst_applied = bool(data.get("gst_applied", False))
    participants_raw = data.get("participants", [])

    if not participants_raw:
        await update.message.reply_text("No participants found. Please try again.")
        return

    bill_id = short_id()
    now = datetime.utcnow().isoformat()

    # Resolve usernames → user_ids
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO bills (bill_id, group_chat_id, payer_id, event_name, total_amount, gst_applied, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (bill_id, group_chat_id, user.id, event_name, total_amount, int(gst_applied), now),
        )
        for p in participants_raw:
            uname = p.get("username", "").lstrip("@").lower()
            amount = float(p.get("amount", 0))
            row = conn.execute(
                "SELECT user_id FROM users WHERE lower(username)=?", (uname,)
            ).fetchone()
            uid = row["user_id"] if row else None
            conn.execute(
                "INSERT INTO bill_participants (bill_id, user_id, username, amount_owed) VALUES (?, ?, ?, ?)",
                (bill_id, uid, uname, amount),
            )

    # Build and post group summary
    summary_text, markup = build_summary(bill_id)
    try:
        msg = await context.bot.send_message(
            chat_id=group_chat_id,
            text=summary_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=markup,
        )
        with get_conn() as conn:
            conn.execute(
                "UPDATE bills SET group_message_id=? WHERE bill_id=?",
                (msg.message_id, bill_id),
            )
    except TelegramError as e:
        logger.error("Failed to post to group %s: %s", group_chat_id, e)
        await update.message.reply_text(f"Failed to post to group: {e}")
        return

    # Clean up DM keyboard and confirm
    await update.message.reply_text(
        "✅ Bill posted to the group!",
        reply_markup=ReplyKeyboardRemove(),
    )


# ---------------------------------------------------------------------------
# Callback query handlers
# ---------------------------------------------------------------------------

async def callback_get_qr(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """callback_data: qr:{bill_id}:{uid_b36}"""
    query = update.callback_query
    _, bill_id, uid_b36 = query.data.split(":", 2)
    participant_uid = from_base36(uid_b36)
    clicker_uid = query.from_user.id

    if clicker_uid != participant_uid:
        await query.answer("This QR is not for you 😅", show_alert=True)
        return

    with get_conn() as conn:
        bill = conn.execute("SELECT * FROM bills WHERE bill_id=?", (bill_id,)).fetchone()
        payer = conn.execute("SELECT * FROM users WHERE user_id=?", (bill["payer_id"],)).fetchone()
        part = conn.execute(
            "SELECT * FROM bill_participants WHERE bill_id=? AND user_id=?",
            (bill_id, participant_uid),
        ).fetchone()

    if not bill or not payer or not part:
        await query.answer("Bill not found.", show_alert=True)
        return

    if part["is_paid"]:
        await query.answer("You've already paid! ✅", show_alert=True)
        return

    paynow_number = payer["paynow_number"]
    if not paynow_number:
        await query.answer("Payer has no PayNow number registered.", show_alert=True)
        return

    uid_b36_str = to_base36(participant_uid)
    paid_button = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ I've Paid", callback_data=f"paid:{bill_id}:{uid_b36_str}")]
    ])

    try:
        buf = generate_qr_bytes(paynow_number, part["amount_owed"], payer["first_name"] or "Payer")
        sent = await context.bot.send_photo(
            chat_id=participant_uid,
            photo=InputFile(buf, filename="paynow_qr.png"),
            caption=(
                f"💳 *{bill['event_name']}*\n"
                f"Amount: ${part['amount_owed']:.2f}\n"
                f"Pay to: {payer['first_name']} via PayNow"
            ),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=paid_button,
        )
        # Store sent message id for later edit
        context.bot_data.setdefault("qr_messages", {})[f"{bill_id}:{participant_uid}"] = (
            participant_uid,
            sent.message_id,
        )
        await query.answer("QR sent to your DM! 📱")
    except Forbidden:
        bot_link = f"@{BOT_USERNAME}" if BOT_USERNAME else "the bot"
        await query.answer(
            f"Please start me in DM first: {bot_link}",
            show_alert=True,
        )


async def callback_paid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """callback_data: paid:{bill_id}:{uid_b36}"""
    query = update.callback_query
    _, bill_id, uid_b36 = query.data.split(":", 2)
    participant_uid = from_base36(uid_b36)
    clicker_uid = query.from_user.id

    if clicker_uid != participant_uid:
        await query.answer("This button is not for you 😅", show_alert=True)
        return

    with get_conn() as conn:
        conn.execute(
            "UPDATE bill_participants SET is_paid=1 WHERE bill_id=? AND user_id=?",
            (bill_id, participant_uid),
        )
        bill = conn.execute("SELECT * FROM bills WHERE bill_id=?", (bill_id,)).fetchone()

    if not bill:
        await query.answer("Bill not found.", show_alert=True)
        return

    # Update group message
    summary_text, markup = build_summary(bill_id)
    try:
        await context.bot.edit_message_text(
            chat_id=bill["group_chat_id"],
            message_id=bill["group_message_id"],
            text=summary_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=markup,
        )
    except TelegramError as e:
        logger.warning("Could not edit group message: %s", e)

    # Edit DM QR message
    key = f"{bill_id}:{participant_uid}"
    qr_msg_info = context.bot_data.get("qr_messages", {}).get(key)
    if qr_msg_info:
        dm_chat_id, dm_msg_id = qr_msg_info
        try:
            await context.bot.edit_message_caption(
                chat_id=dm_chat_id,
                message_id=dm_msg_id,
                caption=f"✅ Payment confirmed for *{bill['event_name']}*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([]),
            )
        except TelegramError as e:
            logger.warning("Could not edit DM QR message: %s", e)

    await query.answer("Payment recorded! ✅")


# ---------------------------------------------------------------------------
# Application setup
# ---------------------------------------------------------------------------

def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set in .env")

    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("register", cmd_register))
    app.add_handler(CommandHandler("split", cmd_split))
    app.add_handler(CommandHandler("cancel", cmd_cancel))

    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND, handle_text))

    app.add_handler(CallbackQueryHandler(callback_get_qr, pattern=r"^qr:"))
    app.add_handler(CallbackQueryHandler(callback_paid, pattern=r"^paid:"))

    logger.info("Bot ready. Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
