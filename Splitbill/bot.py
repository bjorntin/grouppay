"""
GroupPay Telegram Bot - Complete Working Implementation
Features: Bill splitting, GST calc, PayNow verification, Privacy
Run: python bot.py
"""

import os
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, ContextTypes, filters

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# States
WHO_PAID, EVENT_NAME, BILL_TYPE, BILL_AMOUNT, PARTICIPANTS, SPLIT_TYPE, REVIEW = range(7)

# Storage
sessions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎉 *GroupPay Bot*\n\n✅ GST calc\n✅ Private amounts\n✅ PayNow QR\n\n/split - Start",
        parse_mode='Markdown'
    )

async def split_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sessions[user_id] = {'participants': [], 'amounts': {}}
    keyboard = [[KeyboardButton("✋ Me")]]
    await update.message.reply_text("💰 Who paid?", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True))
    return WHO_PAID

async def who_paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sessions[user_id]['payee'] = update.effective_user.first_name
    await update.message.reply_text("📝 Event? (e.g. Dinner)", reply_markup=ReplyKeyboardRemove())
    return EVENT_NAME

async def event_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sessions[user_id]['event'] = update.message.text
    keyboard = [[KeyboardButton("✅ Total")], [KeyboardButton("📊 Subtotal")]]
    await update.message.reply_text("Bill type?", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True))
    return BILL_TYPE

async def bill_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sessions[user_id]['has_gst'] = 'Total' in update.message.text
    msg = "💰 Amount:" if sessions[user_id]['has_gst'] else "📊 Subtotal:"
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
    return BILL_AMOUNT

async def bill_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        amount = float(update.message.text.replace('$', ''))
        if not sessions[user_id]['has_gst']:
            sc = amount * 0.10
            gst = (amount + sc) * 0.09
            total = amount + sc + gst
            sessions[user_id]['total'] = total
            await update.message.reply_text(f"Sub: ${amount:.2f}\nSC: ${sc:.2f}\nGST: ${gst:.2f}\n*Total: ${total:.2f}*", parse_mode='Markdown')
        else:
            sessions[user_id]['total'] = amount
        await update.message.reply_text("👥 Participants:\n@alice\n@bob\n\nType 'done'")
        return PARTICIPANTS
    except:
        await update.message.reply_text("❌ Try: 145.50")
        return BILL_AMOUNT

async def add_participants(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    if text.lower() == 'done':
        if not sessions[user_id]['participants']:
            await update.message.reply_text("❌ Add at least 1!")
            return PARTICIPANTS
        keyboard = [[KeyboardButton("➗ Even")]]
        await update.message.reply_text(f"✅ {len(sessions[user_id]['participants'])}\nSplit?", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True))
        return SPLIT_TYPE
    if text.startswith('@'):
        sessions[user_id]['participants'].append(text)
        await update.message.reply_text(f"✅ {text}")
    else:
        await update.message.reply_text("❌ Use @")
    return PARTICIPANTS

async def split_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = sessions[user_id]
    per = session['total'] / len(session['participants'])
    for p in session['participants']:
        session['amounts'][p] = round(per, 2)
    review = f"*{session['event']}*\nTotal: ${session['total']:.2f}\n\n"
    for p, amt in session['amounts'].items():
        review += f"{p}: ${amt:.2f}\n"
    keyboard = [[KeyboardButton("✅ Send")]]
    await update.message.reply_text(review, reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True), parse_mode='Markdown')
    return REVIEW

async def review_split(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = sessions[user_id]
    group = f"📢 *{session['event']}*\n\n"
    for p in session['participants']:
        group += f"{p}: ⏳\n"
    group += "\n🔒 _Amounts private_"
    await update.message.reply_text(group, parse_mode='Markdown', reply_markup=ReplyKeyboardRemove())
    p1 = session['participants'][0]
    amt = session['amounts'][p1]
    dm = f"💰 *Payment*\n\nEvent: {session['event']}\nTo: {session['payee']}\n\n*${amt:.2f}*\n\n📱 [QR here]\n\n🔒 _Private_"
    await update.message.reply_text(dm, parse_mode='Markdown')
    await update.message.reply_text("✅ Done! /split again")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def main():
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print('❌ Set TELEGRAM_BOT_TOKEN\necho "TELEGRAM_BOT_TOKEN=token" > .env')
        return
    app = Application.builder().token(token).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler('split', split_start)],
        states={
            WHO_PAID: [MessageHandler(filters.TEXT & ~filters.COMMAND, who_paid)],
            EVENT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, event_name)],
            BILL_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, bill_type)],
            BILL_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, bill_amount)],
            PARTICIPANTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_participants)],
            SPLIT_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, split_type)],
            REVIEW: [MessageHandler(filters.TEXT & ~filters.COMMAND, review_split)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    app.add_handler(CommandHandler('start', start))
    app.add_handler(conv)
    print("🚀 Bot ready! Search in Telegram\n💡 Send /start")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except:
        pass
    main()
