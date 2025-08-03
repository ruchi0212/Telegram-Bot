import os
import sqlite3
import asyncio
from datetime import datetime
from flask import Flask, request
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ConversationHandler, ContextTypes
)

# Load secrets
load_dotenv("file.env")
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not BOT_TOKEN or not WEBHOOK_URL:
    raise ValueError("❌ BOT_TOKEN or WEBHOOK_URL not set!")

# Flask + Telegram app setup
flask_app = Flask(__name__)
telegram_app = Application.builder().token(BOT_TOKEN).build()

# Conversation states
ADDING_TODO, REGISTRATION = range(2)
DB_FILE = "todo_bot.db"

# ---------- Database Setup ----------
def setup_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        name TEXT,
        username TEXT,
        registered_on TIMESTAMP)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        task TEXT,
        created_at TIMESTAMP,
        updated_at TIMESTAMP,
        status TEXT DEFAULT 'pending')''')
    conn.commit()
    conn.close()

setup_database()

# ---------- DB Helpers ----------
def get_user(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result

def register_user(user_id, name, username):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    now = datetime.now()
    cursor.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?)", (user_id, name, username, now))
    conn.commit()
    conn.close()

def add_task(user_id, task):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    now = datetime.now()
    cursor.execute("INSERT INTO tasks (user_id, task, created_at, updated_at) VALUES (?, ?, ?, ?)",
                   (user_id, task, now, now))
    conn.commit()
    conn.close()

def get_user_tasks(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, task, status FROM tasks WHERE user_id = ?", (user_id,))
    result = cursor.fetchall()
    conn.close()
    return result

def update_task_status(task_id, status):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    now = datetime.now()
    cursor.execute("UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?", (status, now, task_id))
    conn.commit()
    conn.close()

# ---------- Bot Handlers ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("👋 Welcome! Please enter your full name to register:")
        return REGISTRATION
    await update.message.reply_text("👋 Welcome back! Use /addtask or /showtask.")
    return ConversationHandler.END

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📝 Please enter your full name:")
    return REGISTRATION

async def process_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    name = update.message.text
    username = update.effective_user.username or "not_provided"
    register_user(user_id, name, username)
    await update.message.reply_text(f"✅ Registered as {name}. Use /addtask to begin.")
    return ConversationHandler.END

async def addtask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📌 Send your task messages one by one. Use /donetask to finish.")
    return ADDING_TODO

async def add_todo_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    task = update.message.text
    add_task(user_id, task)
    await update.message.reply_text("✅ Task added.")
    return ADDING_TODO

async def donetask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛑 Task entry stopped.")
    return ConversationHandler.END

async def showtask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    tasks = get_user_tasks(user_id)
    if not tasks:
        await update.message.reply_text("📭 No tasks found.")
        return
    message = "\n".join([f"{i+1}. {t[1]} [{t[2]}]" for i, t in enumerate(tasks)])
    await update.message.reply_text(f"🗂️ Your tasks:\n{message}")

async def complete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    tasks = get_user_tasks(user_id)
    try:
        index = int(context.args[0]) - 1
        task_id = tasks[index][0]
        update_task_status(task_id, "completed")
        await update.message.reply_text("✅ Task marked as completed.")
    except:
        await update.message.reply_text("⚠️ Invalid task number.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""
📚 Commands:
/start - Start the bot
/register - Register as a user
/addtask - Start adding tasks
/donetask - Stop task input
/showtask - View your tasks
/complete [n] - Mark task n as completed
/help - View this help message
""")

# ---------- Handlers Registration ----------
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("showtask", showtask))
telegram_app.add_handler(CommandHandler("complete", complete))
telegram_app.add_handler(CommandHandler("help", help_command))

telegram_app.add_handler(ConversationHandler(
    entry_points=[CommandHandler("register", register)],
    states={REGISTRATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_registration)]},
    fallbacks=[]
))

telegram_app.add_handler(ConversationHandler(
    entry_points=[CommandHandler("addtask", addtask)],
    states={ADDING_TODO: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_todo_item)]},
    fallbacks=[CommandHandler("donetask", donetask)]
))

# ---------- Webhook Routes ----------
@flask_app.route("/", methods=["GET"])
def index():
    return "✅ Telegram To-Do Bot running via webhook."

@flask_app.route("/webhook", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    await telegram_app.process_update(update)
    return "OK", 200

@flask_app.before_request
def set_webhook():
    telegram_app.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")

# ---------- Start App ----------
if __name__ == "__main__":
    flask_app.run(host="0.0.0.0", port=5000)
