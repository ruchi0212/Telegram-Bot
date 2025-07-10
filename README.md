# 📝 Telegram To-Do List Bot with Reminders

A fully functional **Telegram chatbot** built in Python that helps users manage their **to-do tasks**, set **reminders**, and **track productivity**. This bot features **user registration**, **persistent task storage**, and **task history analytics** using SQLite.

---

## 🚀 Features

✅ User registration system  
✅ Add, view, complete, and delete tasks  
✅ Set timed reminders  
✅ View task history over the past 30 days  
✅ Stores data in a local SQLite database  
✅ Personalized user experience via Telegram chat  
✅ Modular Python structure and environment variable support  

---

## 🧠 Technologies Used

| Category       | Tech/Library                    |
|----------------|---------------------------------|
| Programming    | Python 3.10+                    |
| Bot Framework  | python-telegram-bot (v20+)      |
| Database       | SQLite                          |
| Environment    | python-dotenv                   |
| Platform       | Telegram Bot API                |

---

## 📁 Project Structure

\`\`\`bash
├── botfinal.py         # Main Telegram bot logic
├── database.py         # Optional separate DB file (unused in main bot)
├── file.env            # Contains Telegram bot token
├── todo_bot.db         # SQLite database storing users, tasks, and reminders
└── README.md           # Project documentation
\`\`\`

---

## 🔑 .env Setup

Create a `.env` file in your project root directory to store your Telegram bot token:

\`\`\`env
BOT_TOKEN = your_telegram_bot_token
\`\`\`

---

## ⚙️ Installation & Running the Bot

1. **Clone the repository:**

\`\`\`bash
git clone https://github.com/your-username/telegram-todo-bot.git
cd telegram-todo-bot
\`\`\`

2. **Install dependencies:**

\`\`\`bash
pip install -r requirements.txt
\`\`\`

> If \`requirements.txt\` doesn't exist, install manually:
\`\`\`bash
pip install python-telegram-bot python-dotenv
\`\`\`

3. **Set your environment variables in \`file.env\`.**

4. **Run the bot:**

\`\`\`bash
python botfinal.py
\`\`\`

> You should see: \`✅ Bot token loaded successfully!\` and \`🚀 Bot is now running...\`

---

## 💬 Telegram Bot Commands

| Command            | Description                                     |
|--------------------|-------------------------------------------------|
| \`/start\`           | Start the bot or return to welcome screen       |
| \`/register\`        | Register with the bot                           |
| \`/addtask\`         | Start adding tasks                              |
| \`/donetask\`        | Stop adding tasks                               |
| \`/showtask\`        | Show your current task list                     |
| \`/complete [n]\`    | Mark task #n as completed                       |
| \`/deletetask [n]\`  | Delete task #n or all tasks with \`/deletetask all\` |
| \`/remind [min] msg\`| Set a reminder after given minutes              |
| \`/history\`         | View task completion history for last 30 days   |
| \`/help\`            | View all available commands                     |
| \`/end\`             | End any ongoing conversation                    |

---

## 🗃️ Database Tables

The bot creates and uses a local \`todo_bot.db\` SQLite database with 3 tables:

### 1. \`users\`
Stores registered users.
- \`user_id\`, \`name\`, \`username\`, \`registered_on\`

### 2. \`tasks\`
Stores individual user tasks.
- \`id\`, \`user_id\`, \`task\`, \`created_at\`, \`updated_at\`, \`status\`

### 3. \`reminders\`
Stores reminders set by users.
- \`id\`, \`user_id\`, \`task_id\`, \`reminder_text\`, \`reminder_time\`, \`created_at\`, \`completed\`

---

## 📊 Productivity History

The \`/history\` command gives a summary of:
- Tasks added per day
- Number of tasks completed
- Completion rate over the last 30 days

---

## 🧪 Future Improvements (Suggestions)

- Deploy on cloud using webhook + Flask
- Add support for recurring reminders
- Allow editing of tasks
- Export tasks to CSV
- Push notifications via email

---

## 👩‍💻 Developed By

**Ruchi Pagar** & **Siddhi Lokhande**  
Final-Year Computer Engineering Students  
🔗 [Ruchi’s LinkedIn](https://www.linkedin.com/in/ruchipagar)

---

## 🛡️ Disclaimer

This bot is for educational purposes. Use responsibly and ensure you don’t expose your Telegram bot token publicly.