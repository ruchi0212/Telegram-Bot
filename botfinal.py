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

# === Load environment variables ===
load_dotenv("file.env")
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not BOT_TOKEN or not WEBHOOK_URL:
    raise ValueError("❌ BOT_TOKEN or WEBHOOK_URL not set!")

# === Flask app ===
flask_app = Flask(__name__)

# === Telegram Bot App ===
telegram_app = Application.builder().token(BOT_TOKEN).build()

# === Conversation States ===
ADDING_TODO = 1
REGISTRATION = 2

# === Database ===
DB_FILE = "todo_bot.db"

def setup_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            username TEXT,
            registered_on TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            task TEXT NOT NULL,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            task_id INTEGER,
            reminder_text TEXT NOT NULL,
            reminder_time INTEGER NOT NULL,
            created_at TIMESTAMP,
            completed BOOLEAN DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (task_id) REFERENCES tasks (id)
        )
    ''')
    conn.commit()
    conn.close()

setup_database()

# === Database helpers ===
def get_user(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def register_user(user_id, name, username):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT OR REPLACE INTO users (user_id, name, username, registered_on) VALUES (?, ?, ?, ?)",
        (user_id, name, username, now)
    )
    conn.commit()
    conn.close()

def add_task(user_id, task_text):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO tasks (user_id, task, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (user_id, task_text, now, now)
    )
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return task_id

def get_user_tasks(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, task, status, created_at FROM tasks WHERE user_id = ?", (user_id,))
    tasks = cursor.fetchall()
    conn.close()
    return tasks

def update_task_status(task_id, status):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?", (status, now, task_id))
    conn.commit()
    conn.close()

def delete_task(task_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

def delete_all_user_tasks(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def add_reminder(user_id, reminder_text, minutes, task_id=None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO reminders (user_id, task_id, reminder_text, reminder_time, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, task_id, reminder_text, minutes, now)
    )
    reminder_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return reminder_id

def complete_reminder(reminder_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE reminders SET completed = 1 WHERE id = ?", (reminder_id,))
    conn.commit()
    conn.close()

def get_task_history(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        """SELECT date(created_at), count(*), sum(CASE WHEN status='completed' THEN 1 ELSE 0 END)
           FROM tasks WHERE user_id = ? AND created_at >= date('now', '-30 day')
           GROUP BY date(created_at) ORDER BY date(created_at)""", (user_id,))
    history = cursor.fetchall()
    conn.close()
    return history

# === Bot Command Handlers ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("👋 Welcome! Please enter your full name to register:")
        return REGISTRATION
    await update.message.reply_text("👋 Welcome back! Use /help for commands.")
    return ConversationHandler.END

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📝 Please enter your full name:")
    return REGISTRATION

async def process_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    name = update.message.text
    username = update.effective_user.username or "Not provided"
    register_user(user_id, name, username)
    await update.message.reply_text(f"✅ Welcome {name}! Use /addtask to begin.")
    return ConversationHandler.END

async def addtask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📌 Send your task. Use /donetask when done.")
    return ADDING_TODO

async def add_todo_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    task = update.message.text
    add_task(user_id, task)
    await update.message.reply_text("✅ Task added.")
    return ADDING_TODO

async def donetask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👍 Task entry ended.")
    return ConversationHandler.END

async def showtask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    tasks = get_user_tasks(user_id)
    if tasks:
        msg = "\n".join([f"{i+1}. {t[1]} [{t[2]}]" for i, t in enumerate(tasks)])
        await update.message.reply_text(f"📋 Your tasks:\n{msg}")
    else:
        await update.message.reply_text("📭 No tasks found.")

async def complete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    tasks = get_user_tasks(user_id)
    try:
        index = int(context.args[0]) - 1
        task_id = tasks[index][0]
        update_task_status(task_id, "completed")
        await update.message.reply_text("✅ Task marked complete.")
    except:
        await update.message.reply_text("⚠️ Invalid task number.")

async def deletetask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    args = context.args
    if args and args[0] == "all":
        delete_all_user_tasks(user_id)
        await update.message.reply_text("🗑️ All tasks deleted.")
    elif args:
        tasks = get_user_tasks(user_id)
        try:
            index = int(args[0]) - 1
            task_id = tasks[index][0]
            delete_task(task_id)
            await update.message.reply_text("🗑️ Task deleted.")
        except:
            await update.message.reply_text("⚠️ Invalid task number.")
    else:
        await update.message.reply_text("⚠️ Usage: /deletetask [task# or all]")

async def remind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: /remind [minutes] [message]")
        return
    try:
        minutes = int(args[0])
        message = " ".join(args[1:])
        reminder_id = add_reminder(user_id, message, minutes)
        asyncio.create_task(send_reminder(update, context, reminder_id, minutes, message))
        await update.message.reply_text(f"⏳ Reminder set for {minutes} minutes.")
    except:
        await update.message.reply_text("⚠️ Invalid minutes.")

async def send_reminder(update: Update, context, reminder_id, minutes, message):
    await asyncio.sleep(minutes * 60)
    complete_reminder(reminder_id)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"🔔 Reminder: {message}")

async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = get_task_history(user_id)
    if not data:
        await update.message.reply_text("📭 No history available.")
        return
    msg = "📊 Task History:\n\n"
    for day, total, completed in data:
        msg += f"📅 {day}: {total} tasks ({completed} completed)\n"
    await update.message.reply_text(msg)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""
📚 Commands:
• /start - Start or login
• /register - Register new user
• /addtask - Add a new task
• /donetask - End task addition
• /showtask - Show tasks
• /complete [n] - Mark task as complete
• /deletetask [n/all] - Delete task(s)
• /remind [min] msg - Set reminder
• /history - Show task history
""")

# === Telegram App Routing ===
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("register", register))
telegram_app.add_handler(CommandHandler("addtask", addtask))
telegram_app.add_handler(CommandHandler("donetask", donetask))
telegram_app.add_handler(CommandHandler("showtask", showtask))
telegram_app.add_handler(CommandHandler("complete", complete))
telegram_app.add_handler(CommandHandler("deletetask", deletetask))
telegram_app.add_handler(CommandHandler("remind", remind))
telegram_app.add_handler(CommandHandler("history", history))
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

# === Webhook Endpoints ===
@flask_app.route("/", methods=["GET"])
def home():
    return "✅ Telegram To-Do Bot running via webhook."

@flask_app.route("/webhook", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    await telegram_app.process_update(update)
    return "OK", 200

@flask_app.before_first_request
def set_webhook():
    telegram_app.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")

# === Run the Flask app ===
if __name__ == "__main__":
    flask_app.run(host="0.0.0.0", port=5000)
