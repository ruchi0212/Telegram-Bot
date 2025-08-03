import os
import sqlite3
from datetime import datetime
from flask import Flask, request
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ConversationHandler, ContextTypes
)

# Load token and webhook URL
load_dotenv("file.env")
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not BOT_TOKEN or not WEBHOOK_URL:
    raise ValueError("❌ BOT_TOKEN or WEBHOOK_URL not set!")

flask_app = Flask(__name__)
telegram_app = Application.builder().token(BOT_TOKEN).build()

# States
ADDING_TASK, REGISTER = range(2)
DB = "todo_bot.db"

# Database setup
def setup_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY, name TEXT, username TEXT, registered_on TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT,
        task TEXT, created_at TIMESTAMP, updated_at TIMESTAMP, status TEXT DEFAULT 'pending'
    )''')
    conn.commit()
    conn.close()

setup_db()

# DB functions
def get_user(uid):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (uid,))
    r = c.fetchone()
    conn.close()
    return r

def register_user(uid, name, username):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("REPLACE INTO users VALUES (?, ?, ?, ?)", (uid, name, username, datetime.now()))
    conn.commit()
    conn.close()

def add_task(uid, task):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    now = datetime.now()
    c.execute("INSERT INTO tasks (user_id, task, created_at, updated_at) VALUES (?, ?, ?, ?)",
              (uid, task, now, now))
    conn.commit()
    conn.close()

def get_tasks(uid):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id, task, status FROM tasks WHERE user_id = ?", (uid,))
    r = c.fetchall()
    conn.close()
    return r

def complete_task(tid):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE tasks SET status='completed', updated_at=? WHERE id=?",
              (datetime.now(), tid))
    conn.commit()
    conn.close()

# Bot handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    if not get_user(uid):
        await update.message.reply_text("👋 Welcome! Please enter your full name:")
        return REGISTER
    await update.message.reply_text("👋 Welcome back! Use /addtask or /showtask.")
    return ConversationHandler.END

async def save_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    name = update.message.text
    username = update.effective_user.username or "no_username"
    register_user(uid, name, username)
    await update.message.reply_text(f"✅ Registered as {name}. Use /addtask.")
    return ConversationHandler.END

async def begin_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📌 Send task(s) one by one. Use /donetask to stop.")
    return ADDING_TASK

async def store_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    add_task(str(update.effective_user.id), update.message.text)
    await update.message.reply_text("✅ Task added.")
    return ADDING_TASK

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛑 Done adding tasks.")
    return ConversationHandler.END

async def show(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = get_tasks(str(update.effective_user.id))
    if not t:
        await update.message.reply_text("📭 No tasks.")
        return
    msg = "\n".join([f"{i+1}. {task[1]} [{task[2]}]" for i, task in enumerate(t)])
    await update.message.reply_text(f"📝 Your tasks:\n{msg}")

async def complete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        idx = int(context.args[0]) - 1
        t = get_tasks(str(update.effective_user.id))
        complete_task(t[idx][0])
        await update.message.reply_text("✅ Task marked complete.")
    except:
        await update.message.reply_text("⚠️ Error. Usage: /complete [task_number]")

# Add command handlers
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("showtask", show))
telegram_app.add_handler(CommandHandler("complete", complete))

telegram_app.add_handler(ConversationHandler(
    entry_points=[CommandHandler("register", start)],
    states={REGISTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_name)]},
    fallbacks=[]
))

telegram_app.add_handler(ConversationHandler(
    entry_points=[CommandHandler("addtask", begin_task)],
    states={ADDING_TASK: [MessageHandler(filters.TEXT & ~filters.COMMAND, store_task)]},
    fallbacks=[CommandHandler("donetask", done)]
))

# Flask Routes
@flask_app.route("/")
def home():
    return "✅ Telegram To-Do Bot running via webhook."

@flask_app.route("/webhook", methods=["POST"])
async def webhook():
    try:
        data = request.get_json(force=True)
        print("📩 Webhook received:", data)
        update = Update.de_json(data, telegram_app.bot)
        await telegram_app.process_update(update)
        return "OK", 200
    except Exception as e:
        print("❌ Error in webhook:", str(e))
        return "Internal Server Error", 500

# Set the webhook using asyncio (not Flask decorators)
import asyncio

async def set_webhook():
    print("⚙️ Setting Telegram webhook...")
    await telegram_app.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
    print("✅ Webhook successfully set!")

asyncio.run(set_webhook())

