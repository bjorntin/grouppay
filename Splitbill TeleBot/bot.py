"""
GroupPay Telegram Bot — MVP
Requires: python-telegram-bot==20.7, python-dotenv, qrcode[pil], Pillow
"""

import base64
import json
import logging
import os
import sqlite3
import sys
import uuid
from datetime import datetime
from urllib.parse import urlencode

from dotenv import load_dotenv
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
    WebAppInfo,
)
from telegram.constants import ParseMode
from telegram.error import TelegramError
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
BOT_USERNAME = os.getenv("BOT_USERNAME", "")

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

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
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                bill_id            TEXT,
                user_id            INTEGER,
                username           TEXT,
                amount_owed        REAL,
                is_paid            INTEGER DEFAULT 0,
                whisper_message_id INTEGER
            );
        """)
        # Migrate existing tables: add whisper_message_id if missing
        try:
            conn.execute("ALTER TABLE bill_participants ADD COLUMN whisper_message_id INTEGER")
        except sqlite3.OperationalError:
            pass  # Column already exists


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def short_id() -> str:
    return uuid.uuid4().hex[:8]


def build_qr_url(paynow_number: str, amount: float, event_name: str, payer_name: str) -> str | None:
    """
    Generate Mini App URL with PayNow QR data embedded as query params.
    The Mini App reads these params and renders the QR client-side — no DM needed.
    """
    if not MINI_APP_URL:
        return None
    mobile = paynow_number if paynow_number.startswith("+") else "+65" + paynow_number
    try:
        payload = PayNowQR(mobile, amount, payer_name).generate_payload()
    except Exception as exc:
        logger.warning("PayNow payload generation failed: %s", exc)
        return None
    # Base64url-encode the payload (URL-safe, no padding)
    encoded = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
    params = urlencode({
        "mode": "qr",
        "p": encoded,
        "a": f"{amount:.2f}",
        "e": event_name[:40],
        "n": (payer_name or "Payer")[:20],
    })
    base = MINI_APP_URL.rstrip("/") + "/"
    return f"{base}?{params}"


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
    """Build the group summary message (text only, no inline buttons)."""
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
    for p in participants:
        handle = f"@{p['username']}" if p["username"] else f"User {p['id']}"
        status = "✅ Paid" if p["is_paid"] else "⏳"
        lines.append(f"{handle}  ${p['amount_owed']:.2f}   {status}")

    return "\n".join(lines), InlineKeyboardMarkup([])


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    upsert_user(user.id, user.username, user.first_name)

    param = (context.args or [""])[0]

    if param.startswith("grp_"):
        # Deep-link from /split in group — open the Mini App bill form
        if not MINI_APP_URL:
            await update.message.reply_text("Mini App URL not configured. Ask the admin to set MINI_APP_URL.")
            return
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
            "• Add me to a group and use /split to create a bill.\n"
        )


async def cmd_register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
        await update.message.reply_text("Please send your PayNow mobile number (e.g. 91234567):")


async def _save_paynow(update: Update, context: ContextTypes.DEFAULT_TYPE, number: str) -> None:
    number = number.strip().lstrip("+65").strip()
    if not number.isdigit() or len(number) != 8:
        await update.message.reply_text(
            "Invalid number. Please send an 8-digit Singapore mobile number (e.g. 91234567)."
        )
        return
    user = update.effective_user
    with get_conn() as conn:
        conn.execute("UPDATE users SET paynow_number=? WHERE user_id=?", (number, user.id))
    context.user_data.pop("awaiting_paynow", None)
    await update.message.reply_text(f"✅ PayNow number {number} saved!")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get("awaiting_paynow"):
        await _save_paynow(update, context, update.message.text)


async def cmd_split(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.type == "private":
        await update.message.reply_text("Use /split in a group chat.")
        return

    user = update.effective_user
    chat = update.effective_chat
    upsert_user(user.id, user.username, user.first_name)

    with get_conn() as conn:
        row = conn.execute("SELECT paynow_number FROM users WHERE user_id=?", (user.id,)).fetchone()

    if not row or not row["paynow_number"]:
        await update.message.reply_text(
            "⚠️ You need to register your PayNow number first.\nDM me: /register"
        )
        return

    if not BOT_USERNAME:
        await update.message.reply_text("BOT_USERNAME not configured. Ask the admin.")
        return

    deep_link = f"https://t.me/{BOT_USERNAME}?start=grp_{chat.id}"
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("📱 Open GroupPay ↗", url=deep_link)]])
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

    # Save bill + participants to DB
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

    # Post group summary (status board, no buttons)
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
        logger.error("Failed to post summary to group %s: %s", group_chat_id, e)
        await update.message.reply_text(f"Failed to post to group: {e}")
        return

    # Post per-participant whisper QR messages in the group
    with get_conn() as conn:
        payer_row = conn.execute("SELECT * FROM users WHERE user_id=?", (user.id,)).fetchone()
        participants_db = conn.execute(
            "SELECT * FROM bill_participants WHERE bill_id=? ORDER BY id", (bill_id,)
        ).fetchall()

    if payer_row and payer_row["paynow_number"]:
        for part in participants_db:
            handle = f"@{part['username']}" if part["username"] else f"User {part['id']}"
            qr_url = build_qr_url(
                payer_row["paynow_number"],
                part["amount_owed"],
                event_name,
                payer_row["first_name"] or "Payer",
            )

            buttons: list[list[InlineKeyboardButton]] = []
            if qr_url:
                # url= button works in group chats and opens the Mini App in Telegram's in-app browser.
                # Only the person who taps it sees the QR — it opens as a private overlay.
                buttons.append([InlineKeyboardButton("👁  View QR & Pay 💳", url=qr_url)])
            # paid: callback — only the right person can confirm (verified by user_id or username)
            buttons.append([InlineKeyboardButton("✅  I've Paid", callback_data=f"paid:{bill_id}:{part['id']}")])

            try:
                whisper_msg = await context.bot.send_message(
                    chat_id=group_chat_id,
                    text=(
                        f"🔒 {handle} — *${part['amount_owed']:.2f}* for _{event_name}_\n"
                        f"Tap *View QR* to get your PayNow QR code.\n"
                        f"Tap *I've Paid* after you've transferred."
                    ),
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup(buttons),
                )
                with get_conn() as conn:
                    conn.execute(
                        "UPDATE bill_participants SET whisper_message_id=? WHERE id=?",
                        (whisper_msg.message_id, part["id"]),
                    )
            except TelegramError as e:
                logger.warning("Failed to post whisper for %s: %s", handle, e)

    await update.message.reply_text("✅ Bill posted to the group!", reply_markup=ReplyKeyboardRemove())


# ---------------------------------------------------------------------------
# Callback query handlers
# ---------------------------------------------------------------------------

async def callback_paid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    callback_data: paid:{bill_id}:{row_id}
    Verifies the clicker is the right person (by user_id or @username).
    No pre-registration required — username match works for anyone in the group.
    """
    query = update.callback_query
    parts = query.data.split(":", 2)
    if len(parts) != 3:
        await query.answer("Invalid button.", show_alert=True)
        return
    _, bill_id, row_id_str = parts
    try:
        row_id = int(row_id_str)
    except ValueError:
        await query.answer("This button is outdated. Please recreate the bill.", show_alert=True)
        return

    with get_conn() as conn:
        part = conn.execute("SELECT * FROM bill_participants WHERE id=?", (row_id,)).fetchone()

    if not part:
        await query.answer("Participant not found.", show_alert=True)
        return

    # Allow match by user_id (if known) or by @username (no prior /start needed)
    clicker_uid = query.from_user.id
    clicker_uname = (query.from_user.username or "").lower()
    is_match = (
        (part["user_id"] and clicker_uid == part["user_id"]) or
        (part["username"] and clicker_uname == part["username"].lower())
    )
    if not is_match:
        await query.answer("This button is not for you 😅", show_alert=True)
        return

    if part["is_paid"]:
        await query.answer("Already marked as paid! ✅", show_alert=True)
        return

    with get_conn() as conn:
        conn.execute("UPDATE bill_participants SET is_paid=1 WHERE id=?", (row_id,))
        bill = conn.execute("SELECT * FROM bills WHERE bill_id=?", (bill_id,)).fetchone()

    if not bill:
        await query.answer("Bill not found.", show_alert=True)
        return

    # Update the group summary board
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
        logger.warning("Could not update group summary: %s", e)

    # Edit the whisper message to show confirmed and remove buttons
    if part["whisper_message_id"]:
        handle = f"@{part['username']}" if part["username"] else "You"
        try:
            await context.bot.edit_message_text(
                chat_id=bill["group_chat_id"],
                message_id=part["whisper_message_id"],
                text=f"✅ {handle} paid *${part['amount_owed']:.2f}* for _{bill['event_name']}_",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([]),
            )
        except TelegramError as e:
            logger.warning("Could not edit whisper message: %s", e)

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

    app.add_handler(CallbackQueryHandler(callback_paid, pattern=r"^paid:"))

    logger.info("Bot ready. Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
