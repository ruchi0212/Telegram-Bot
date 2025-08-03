import os
import logging
import asyncio
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ConversationHandler, ContextTypes
)

# Load environment variables from .env
load_dotenv("file.env")

# Fetch bot token from environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Check if the token exists
if not BOT_TOKEN:
    raise ValueError("❌ ERROR: Bot token not found in environment variables.")

print("✅ Bot token loaded successfully!")

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
ADDING_TODO = 1
REGISTRATION = 2

# Database setup
DB_FILE = "todo_bot.db"

def setup_database():
    """Create database tables if they don't exist"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        username TEXT,
        registered_on TIMESTAMP
    )
    ''')
    
    # Create tasks table
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
    
    # Create reminders table
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
    logger.info("Database setup complete")

# Initialize the database
setup_database()

# Database helper functions
def get_user(user_id):
    """Get user from database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def register_user(user_id, name, username):
    """Register a new user"""
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
    """Add a new task for user"""
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
    """Get all tasks for a user"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, task, status, created_at FROM tasks WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    )
    tasks = cursor.fetchall()
    conn.close()
    return tasks

def update_task_status(task_id, status):
    """Update task status"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?",
        (status, now, task_id)
    )
    conn.commit()
    conn.close()

def update_task_text(task_id, new_text):
    """Update task text"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "UPDATE tasks SET task = ?, updated_at = ? WHERE id = ?",
        (new_text, now, task_id)
    )
    conn.commit()
    conn.close()

def delete_task(task_id):
    """Delete a task"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

def delete_all_user_tasks(user_id):
    """Delete all tasks for a user"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def add_reminder(user_id, reminder_text, minutes, task_id=None):
    """Add a reminder"""
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
    """Mark a reminder as completed"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE reminders SET completed = 1 WHERE id = ?", (reminder_id,))
    conn.commit()
    conn.close()

def get_task_history(user_id, days=30):
    """Get task history for analytics"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 
            date(created_at) as day,
            count(*) as task_count,
            sum(case when status = 'completed' then 1 else 0 end) as completed_count
        FROM tasks 
        WHERE user_id = ? AND created_at >= date('now', '-30 day')
        GROUP BY date(created_at)
        ORDER BY day
        """,
        (user_id,)
    )
    history = cursor.fetchall()
    conn.close()
    return history

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user = get_user(user_id)

    if not user:
        await update.message.reply_text("👋 Welcome! Please enter your full name to register:")
        return REGISTRATION  # Directly move to the registration step
    else:
        await update.message.reply_text(
            f"👋 Welcome back, {user[1]}!\n\n"
            "Use /addtask to add a task, /showtask to view tasks, and /deletetask to remove them.\n"
            "For more commands, use /help"
        )

async def process_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    name = update.message.text
    username = update.effective_user.username or "Not provided"

    # Register user in database
    register_user(user_id, name, username)

    await update.message.reply_text(
        f"✅ Registration successful, {name}!\n\n"
        "Use /addtask to add a task, /showtask to view tasks, and /help for all commands."
    )
    return ConversationHandler.END

# Registration command
async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📝 Let's get you registered!\n"
        "Please send your full name:"
    )
    return REGISTRATION

# Handle registration info
async def process_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    name = update.message.text
    username = update.effective_user.username or "Not provided"
    
    # Register user in database
    register_user(user_id, name, username)
    
    await update.message.reply_text(
        f"✅ Registration successful, {name}!\n\n"
        "Use /addtask to add a task, /showtask to view tasks, and /help for all commands."
    )
    return ConversationHandler.END

# /addtask command - Start adding tasks
async def addtask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user = get_user(user_id)
    
    # Check if user is registered
    if not user:
        await update.message.reply_text("⚠️ You need to register first. Please use /register")
        return ConversationHandler.END
    
    await update.message.reply_text("📌 Send me tasks one by one. Type /donetask when finished.")
    return ADDING_TODO

# Handle task addition
async def add_todo_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    task = update.message.text
    
    # Add task to database
    task_id = add_task(user_id, task)
    
    await update.message.reply_text(f"✅ Task added: {task}")
    return ADDING_TODO

# /donetask command - Stop adding tasks
async def donetask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛑 Task entry stopped. Use /showtask to see your tasks.")
    return ConversationHandler.END

# /showtask command - Show all tasks
async def showtask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user = get_user(user_id)
    
    # Check if user is registered
    if not user:
        await update.message.reply_text("⚠️ You need to register first. Please use /register")
        return
    
    # Get tasks from database
    tasks = get_user_tasks(user_id)
    
    if tasks:
        task_list = "\n".join(
            f"{idx+1}. {task[1]} - [{task[2]}]" 
            for idx, task in enumerate(tasks)
        )
        await update.message.reply_text(f"📋 Your tasks:\n{task_list}")
    else:
        await update.message.reply_text("📭 No tasks available.")

# /complete command - Mark a task as completed
async def complete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user = get_user(user_id)
    
    # Check if user is registered
    if not user:
        await update.message.reply_text("⚠️ You need to register first. Please use /register")
        return
    
    # Get task number from command
    args = context.args
    if not args:
        await update.message.reply_text("⚠️ Usage: /complete [task_number]")
        return
    
    try:
        task_index = int(args[0]) - 1
        
        # Get tasks from database
        tasks = get_user_tasks(user_id)
        
        # Check if task exists
        if 0 <= task_index < len(tasks):
            task_id = tasks[task_index][0]
            task_text = tasks[task_index][1]
            
            # Update task status in database
            update_task_status(task_id, "completed")
            
            await update.message.reply_text(f"✅ Marked task as completed: {task_text}")
        else:
            await update.message.reply_text("⚠️ Invalid task number.")
    except ValueError:
        await update.message.reply_text("❌ Please provide a valid task number.")

# /deletetask command - Delete a specific task or all tasks
async def deletetask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user = get_user(user_id)
    
    # Check if user is registered
    if not user:
        await update.message.reply_text("⚠️ You need to register first. Please use /register")
        return
    
    args = context.args
    if not args:
        await update.message.reply_text("⚠️ Usage: /deletetask [task_number] or /deletetask all")
        return

    if args[0].lower() == "all":
        # Delete all tasks from database
        delete_all_user_tasks(user_id)
        await update.message.reply_text("🗑️ All tasks deleted.")
    else:
        try:
            task_index = int(args[0]) - 1
            
            # Get tasks from database
            tasks = get_user_tasks(user_id)
            
            # Check if task exists
            if 0 <= task_index < len(tasks):
                task_id = tasks[task_index][0]
                task_text = tasks[task_index][1]
                
                # Delete task from database
                delete_task(task_id)
                
                await update.message.reply_text(f"🗑️ Deleted task: {task_text}")
            else:
                await update.message.reply_text("⚠️ Invalid task number.")
        except ValueError:
            await update.message.reply_text("❌ Please provide a valid task number.")

# /remind command - Set a reminder
async def remind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user = get_user(user_id)
    
    # Check if user is registered
    if not user:
        await update.message.reply_text("⚠️ You need to register first. Please use /register")
        return
    
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("⚠️ Usage: /remind [minutes] [message]")
        return

    try:
        minutes = int(args[0])
        reminder_text = " ".join(args[1:])
        
        # Add reminder to database
        reminder_id = add_reminder(user_id, reminder_text, minutes)
        
        await update.message.reply_text(
            f"⏳ Reminder set for {minutes} minutes: {reminder_text}"
        )

        # Schedule the reminder
        asyncio.create_task(send_reminder(update, context, reminder_id, minutes, reminder_text))

    except ValueError:
        await update.message.reply_text("❌ Please provide a valid number for minutes.")

# Function to send a reminder after a delay
async def send_reminder(update: Update, context, reminder_id: int, minutes: int, message: str):
    await asyncio.sleep(minutes * 60)  # Convert minutes to seconds
    
    # Mark reminder as completed
    complete_reminder(reminder_id)
    
    # Send the reminder
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"⏰ REMINDER: {message}"
    )

# /history command - Show task history
async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user = get_user(user_id)
    
    # Check if user is registered
    if not user:
        await update.message.reply_text("⚠️ You need to register first. Please use /register")
        return
    
    # Get history from database
    history_data = get_task_history(user_id)
    
    if history_data:
        history_text = "📊 Your task history (last 30 days):\n\n"
        
        for day, total, completed in history_data:
            history_text += f"📅 {day}: {total} tasks ({completed} completed)\n"
        
        await update.message.reply_text(history_text)
    else:
        await update.message.reply_text("📭 No task history available for the last 30 days.")

''' async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user = get_user(user_id)
    
    # Check if user is registered
    if not user:
        await update.message.reply_text("⚠️ You need to register first. Please use /register")
        return
    
    # Get the user's name from the database
    user_name = user[1]  # Index 1 contains the name field from the users table
    
    # Get history from database
    history_data = get_task_history(user_id)
    
    if history_data:
        history_text = f"📊 Task history for {user_name} (last 30 days):\n\n"
        
        for day, total, completed in history_data:
            completion_rate = round((completed / total) * 100) if total > 0 else 0
            history_text += f"📅 {day}: {total} tasks, {completed} completed ({completion_rate}%)\n"
        
        await update.message.reply_text(history_text)
    else:
        await update.message.reply_text(f"📭 No task history available for {user_name} in the last 30 days.")'''

# /help command - Show available commands
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📚 **To-Do Bot Commands**\n\n"
        "/register - Register with the bot\n"
        "/addtask - Start adding tasks\n"
        "/donetask - Finish adding tasks\n"
        "/showtask - View all your tasks\n"
        "/complete [#] - Mark a task as completed\n"
        "/deletetask [#/all] - Delete a specific task or all tasks\n"
        "/remind [min] [msg] - Set a reminder\n"
        "/end - End of Conversation\n"
        "/history - View your task history\n"
        "/help - Show this help message\n\n"
        "🌟 **Tips**:\n"
        "• All your tasks are saved in the database\n"
        "• Your task history is preserved for analytics\n"
        "• You can see your productivity trends with /history"
    )
    await update.message.reply_text(help_text)

# Handle unknown commands
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Sorry, I didn't understand that command.\n"
        "Use /help to see available commands."
    )

# Handle unknown text messages
async def unknown_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❓ I'm not sure what you mean.\n"
        "Use /help to see available commands."
    )
    # /end command - Ends any ongoing conversation
async def end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚫 Conversation ended. See you Again!!!")
    return ConversationHandler.END

# Main function to set up the bot
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Add command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("showtask", showtask))
    app.add_handler(CommandHandler("complete", complete))
    app.add_handler(CommandHandler("deletetask", deletetask))
    app.add_handler(CommandHandler("remind", remind))
    app.add_handler(CommandHandler("history", history))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("end", end))

    # Registration conversation handler
    registration_handler = ConversationHandler(
        entry_points=[CommandHandler("register", register)],
        states={REGISTRATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_registration)]},
        fallbacks=[CommandHandler("start", start),CommandHandler("end", end)],
    )
    app.add_handler(registration_handler)

    # Task addition conversation handler
    task_handler = ConversationHandler(
        entry_points=[CommandHandler("addtask", addtask)],
        states={ADDING_TODO: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_todo_item)]},
        fallbacks=[CommandHandler("donetask", donetask), CommandHandler("end", end)]
    )
    app.add_handler(task_handler)

    # Handle unknown text messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_text))

    # Handle unknown commands
    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    #to end the conversation
    app.add_handler(CommandHandler("end", end))

    logging.info("🚀 Bot is now running...")
    app.run_polling()


if __name__ == "__main__":
    main()