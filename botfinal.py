import telebot
from flask import Flask, request
import database
import os

API_TOKEN = os.getenv('API_TOKEN')
bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Welcome to your To-Do Bot!")

@bot.message_handler(func=lambda m: True)
def handle_message(message):
    bot.reply_to(message, f"Got your message: {message.text}")

@app.route('/' + API_TOKEN, methods=['POST'])
def receive_update():
    update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
    bot.process_new_updates([update])
    return "OK", 200

@app.route('/')
def index():
    bot.remove_webhook()
    webhook_url = f"https://your-app-name.onrender.com/{API_TOKEN}"
    bot.set_webhook(url=webhook_url)
    return "Webhook is set!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)