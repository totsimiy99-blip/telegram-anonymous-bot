import telebot
import os
from flask import Flask
from threading import Thread
import time

print("=" * 60)
print("🚀 БОТ ЗАПУСКАЕТСЯ...")
print("=" * 60)

# Проверка токена
TOKEN = os.environ.get('BOT_TOKEN')

if not TOKEN:
    print("❌ ОШИБКА: BOT_TOKEN не найден!")
    exit(1)

print(f"✅ Токен получен: {TOKEN[:15]}...")

# Создаём бота
try:
    bot = telebot.TeleBot(TOKEN)
    print("✅ TeleBot инициализирован")
except Exception as e:
    print(f"❌ Ошибка создания бота: {e}")
    exit(1)

# Flask для health check
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Бот работает!", 200

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    port = int(os.environ.get('PORT', 8000))
    print(f"✅ Flask запускается на порту {port}")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# Команды бота
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, 
        "👋 *Привет! Я работаю!*\n\n"
        "Доступные команды:\n"
        "/start - начать\n"
        "/help - помощь\n"
        "/ping - проверка\n"
        "/stats - статистика",
        parse_mode='Markdown')

@bot.message_handler(commands=['help'])
def help_cmd(message):
    bot.reply_to(message, 
        "ℹ️ *Помощь*\n\n"
        "Это тестовая версия бота.\n"
        "Отправь любое сообщение и я отвечу!",
        parse_mode='Markdown')

@bot.message_handler(commands=['ping'])
def ping(message):
    bot.reply_to(message, "🏓 Понг! Бот работает отлично!")

@bot.message_handler(commands=['stats'])
def stats(message):
    bot.reply_to(message, 
        "📊 *Статистика:*\n\n"
        "✅ Бот онлайн\n"
        "🌍 Сервер: Koyeb (Frankfurt)\n"
        "⚡ Всё работает!",
        parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def echo(message):
    bot.reply_to(message, f"Вы написали: {message.text}")

# Запуск
if __name__ == '__main__':
    print("=" * 60)
    print("🌐 Запуск Flask сервера...")
    keep_alive()
    
    print("✅ Flask запущен!")
    print("🤖 Запуск Telegram polling...")
    print("=" * 60)
    
    try:
        bot.infinity_polling(
            timeout=60,
            long_polling_timeout=60,
            skip_pending=True,
            none_stop=True
        )
    except Exception as e:
        print(f"❌ Ошибка polling: {e}")
        exit(1)
