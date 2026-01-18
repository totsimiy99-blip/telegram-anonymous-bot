import telebot
import os
from flask import Flask
from threading import Thread
import time

# Веб-сервер для Koyeb
app = Flask('')

@app.route('/')
def home():
    return "✅ Bot is running!"

@app.route('/health')
def health():
    return "OK", 200

def run():
    port = int(os.environ.get('PORT', 8000))  # ✅ Динамический порт
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True  # ✅ Добавлено для корректной остановки
    t.start()

# Токен бота
TOKEN = os.environ.get('BOT_TOKEN')

if not TOKEN:
    print("❌ ОШИБКА: Токен не найден!")
    exit(1)

bot = telebot.TeleBot(TOKEN)

# База данных
users = {}
waiting = {
    '14-16': [],
    '16-18': [],
    '18-30': []
}

# Цена премиума в Stars
PREMIUM_PRICE_STARS = 50

class User:
    def __init__(self, uid):
        self.id = uid
        self.country = None
        self.city = None
        self.gender = None
        self.age_range = None
        self.search_gender = None
        self.partner = None
        self.ready = False
        self.premium = False
        self.in_queue = False
        self.chats_count = 0

# ===== ПРАВИЛА БОТА =====

RULES = """
📜 *ПРАВИЛА БОТА*

⚠️ *ОБЯЗАТЕЛЬНО К ПРОЧТЕНИЮ:*

1️⃣ Запрещено нарушать законодательство РФ
2️⃣ Запрещены оскорбления и ненормативная лексика
3️⃣ Соблюдайте нормы морали и этики
4️⃣ Уважайте собеседника
5️⃣ Запрещён спам и реклама
6️⃣ Запрещена пропаганда насилия и экстремизма

❌ *ЗА НАРУШЕНИЕ ПРАВИЛ:*
Блокировка без предупреждения

✅ *Нажимая "Принять правила" вы подтверждаете, что:*
• Вам исполнилось 14 лет
• Вы ознакомились с правилами
• Вы обязуетесь их соблюдать

🤝 Приятного общения!
"""

# ===== ФУНКЦИИ =====

def get_main_keyboard():
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🔍 Найти собеседника")
    kb.row("👤 Мой профиль", "❌ Завершить чат")
    kb.row("💎 Премиум", "📊 Статистика")
    return kb

def get_countries():
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.row("🇷🇺 Россия", "🇺🇦 Украина", "🇧🇾 Беларусь")
    kb.row("🇰🇿 Казахстан", "🇺🇿 Узбекистан")
    kb.row("🌍 Другая страна")
    return kb

def get_age_ranges():
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.row("👦 14-16 лет", "👨 16-18 лет", "👨‍💼 18-30 лет")
    return kb

def get_gender_keyboard():
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.row("👨 Мужской", "👩 Женский")
    return kb

def get_search_preferences():
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.row("👨 Парня", "👩 Девушку", "🤝 Без разницы")
    return kb

def parse_age_range(text):
    if "14-16" in text:
        return "14-16"
    elif "16-18" in text:
        return "16-18"
    elif "18-30" in text:
        return "18-30"
    return None

def clean_emoji(text):
    emojis = ["🇷🇺", "🇺🇦", "🇧🇾", "🇰🇿", "🇺🇿", "🌍", "👨", "👩", "👦", "👨‍💼", "🤝"]
    for emoji in emojis:
        text = text.replace(emoji, "")
    return text.strip()

# ===== КОМАНДЫ =====

@bot.message_handler(commands=['start'])
def start(m):
    uid = m.chat.id
    
    if uid not in users:
        users[uid] = User(uid)
        show_rules(m)
    else:
        bot.send_message(uid, 
            "👋 *С возвращением!*\n\n"
            "Используйте меню для навигации 👇",
            parse_mode='Markdown',
            reply_markup=get_main_keyboard())

def show_rules(m):
    uid = m.chat.id
    
    kb = telebot.types.InlineKeyboardMarkup()
    kb.add(telebot.types.InlineKeyboardButton("✅ Принять правила", callback_data="accept_rules"))
    kb.add(telebot.types.InlineKeyboardButton("❌ Отклонить", callback_data="decline_rules"))
    
    bot.send_message(uid, RULES, parse_mode='Markdown', reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data in ['accept_rules', 'decline_rules'])
def handle_rules(call):
    uid = call.message.chat.id
    
    if call.data == 'accept_rules':
        bot.edit_message_text(
            "✅ *Правила приняты!*\n\n"
            "Теперь создайте профиль 👇",
            uid, call.message.message_id,
            parse_mode='Markdown')
        
        time.sleep(1)
        
        bot.send_message(uid, 
            "🎉 *Добро пожаловать в Анонимный Чат!*\n\n"
            "Для начала работы заполните профиль:",
            parse_mode='Markdown')
        
        start_profile(uid)
    else:
        bot.edit_message_text(
            "❌ Вы отклонили правила.\n\n"
            "Без принятия правил использование бота невозможно.\n\n"
            "Для повторной попытки: /start",
            uid, call.message.message_id)

def start_profile(uid):
    msg = bot.send_message(uid, 
        "🌍 *Шаг 1/5: Страна*\n\n"
        "Выберите вашу страну:",
        parse_mode='Markdown',
        reply_markup=get_countries())
    bot.register_next_step_handler(msg, get_country)

@bot.message_handler(commands=['profile'])
def profile_cmd(m):
    uid = m.chat.id
    if uid not in users:
        users[uid] = User(uid)
    
    if users[uid].ready:
        u = users[uid]
        premium_status = "✅ Активен" if u.premium else "❌ Не активен"
        
        kb = telebot.types.InlineKeyboardMarkup()
        kb.add(telebot.types.InlineKeyboardButton("✏️ Изменить профиль", callback_data="edit_profile"))
        
        bot.send_message(uid,
            f"👤 *Ваш профиль:*\n\n"
            f"🌍 Страна: {u.country}\n"
            f"🏙 Город: {u.city}\n"
            f"⚤ Пол: {u.gender}\n"
            f"🎂 Возраст: {u.age_range} лет\n"
            f"💝 Ищу: {u.search_gender}\n"
            f"💬 Диалогов: {u.chats_count}\n"
            f"💎 Премиум: {premium_status}",
            parse_mode='Markdown',
            reply_markup=kb)
    else:
        start_profile(uid)

@bot.callback_query_handler(func=lambda call: call.data == 'edit_profile')
def edit_profile_callback(call):
    uid = call.message.chat.id
    bot.answer_callback_query(call.id, "Начинаем редактирование...")
    start_profile(uid)

def get_country(m):
    uid = m.chat.id
    users[uid].country = clean_emoji(m.text)
    
    msg = bot.send_message(uid, 
        "🏙 *Шаг 2/5: Город*\n\n"
        "Введите название вашего города:",
        parse_mode='Markdown',
        reply_markup=telebot.types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, get_city)

def get_city(m):
    uid = m.chat.id
    users[uid].city = m.text
    
    msg = bot.send_message(uid,
        "⚤ *Шаг 3/5: Ваш пол*\n\n"
        "Выберите ваш пол:",
        parse_mode='Markdown',
        reply_markup=get_gender_keyboard())
    bot.register_next_step_handler(msg, get_gender)

def get_gender(m):
    uid = m.chat.id
    users[uid].gender = clean_emoji(m.text)
    
    msg = bot.send_message(uid,
        "🎂 *Шаг 4/5: Возраст*\n\n"
        "Выберите вашу возрастную группу:",
        parse_mode='Markdown',
        reply_markup=get_age_ranges())
    bot.register_next_step_handler(msg, get_age)

def get_age(m):
    uid = m.chat.id
    age_range = parse_age_range(m.text)
    
    if not age_range:
        msg = bot.send_message(uid, 
            "❌ Пожалуйста, выберите возраст из предложенных вариантов:",
            reply_markup=get_age_ranges())
        bot.register_next_step_handler(msg, get_age)
        return
    
    users[uid].age_range = age_range
    
    msg = bot.send_message(uid,
        "💝 *Шаг 5/5: Предпочтения*\n\n"
        "Кого вы хотите найти?",
        parse_mode='Markdown',
        reply_markup=get_search_preferences())
    bot.register_next_step_handler(msg, get_search_preference)

def get_search_preference(m):
    uid = m.chat.id
    users[uid].search_gender = clean_emoji(m.text)
    users[uid].ready = True
    
    u = users[uid]
    
    bot.send_message(uid,
        f"✅ *Профиль создан!*\n\n"
        f"🌍 Страна: {u.country}\n"
        f"🏙 Город: {u.city}\n"
        f"⚤ Пол: {u.gender}\n"
        f"🎂 Возраст: {u.age_range} лет\n"
        f"💝 Ищу: {u.search_gender}\n\n"
        f"Теперь можно искать собеседника! 🔍",
        parse_mode='Markdown',
        reply_markup=get_main_keyboard())

@bot.message_handler(commands=['find'])
def find_cmd(m):
    find(m)

def find(m):
    uid = m.chat.id
    
    if uid not in users or not users[uid].ready:
        bot.send_message(uid, 
            "⚠️ Сначала заполните профиль!\n\n"
            "Используйте /profile",
            reply_markup=get_main_keyboard())
        return
    
    if users[uid].partner:
        bot.send_message(uid, "⚠️ Вы уже в чате! Используйте /stop для завершения")
        return
    
    if users[uid].in_queue:
        bot.send_message(uid, "⚠️ Вы уже в очереди поиска!")
        return
    
    age_range = users[uid].age_range
    users[uid].in_queue = True
    
    if users[uid].premium:
        waiting[age_range].insert(0, uid)
    else:
        waiting[age_range].append(uid)
    
    queue_count = len(waiting[age_range])
    
    bot.send_message(uid,
        f"🔍 *Поиск собеседника...*\n\n"
        f"🎂 Возраст: {age_range} лет\n"
        f"💝 Ищу: {users[uid].search_gender}\n"
        f"⏳ В очереди: {queue_count} чел.\n\n"
        f"{'⚡ Премиум-приоритет активен' if users[uid].premium else '💡 С премиумом поиск быстрее!'}",
        parse_mode='Markdown')
    
    match_user(uid)

def match_user(uid):
    if uid not in users or not users[uid].in_queue:
        return
    
    age_range = users[uid].age_range
    search_gender = users[uid].search_gender
    my_gender = users[uid].gender
    
    for other_uid in waiting[age_range]:
        if other_uid == uid:
            continue
        
        if other_uid not in users or not users[other_uid].in_queue:
            continue
        
        other_user = users[other_uid]
        match = False
        
        if search_gender == "Без разницы" and other_user.search_gender == "Без разницы":
            match = True
        elif search_gender == "Без разницы":
            if (my_gender == "Мужской" and other_user.search_gender == "Парня") or \
               (my_gender == "Женский" and other_user.search_gender == "Девушку"):
                match = True
        elif other_user.search_gender == "Без разницы":
            if (search_gender == "Парня" and other_user.gender == "Мужской") or \
               (search_gender == "Девушку" and other_user.gender == "Женский"):
                match = True
        elif (search_gender == "Парня" and other_user.gender == "Мужской" and \
              other_user.search_gender == "Девушку" and my_gender == "Женский") or \
             (search_gender == "Девушку" and other_user.gender == "Женский" and \
              other_user.search_gender == "Парня" and my_gender == "Мужской"):
            match = True
        
        if match:
            connect_users(uid, other_uid)
            return

def connect_users(uid1, uid2):
    age_range = users[uid1].age_range
    if uid1 in waiting[age_range]:
        waiting[age_range].remove(uid1)
    if uid2 in waiting[age_range]:
        waiting[age_range].remove(uid2)
    
    users[uid1].partner = uid2
    users[uid2].partner = uid1
    users[uid1].in_queue = False
    users[uid2].in_queue = False
    users[uid1].chats_count += 1
    users[uid2].chats_count += 1
    
    u1 = users[uid1]
    u2 = users[uid2]
    
    info1 = (f"✅ *Собеседник найден!*\n\n"
            f"🌍 {u2.country}, {u2.city}\n"
            f"⚤ Пол: {u2.gender}\n"
            f"🎂 Возраст: {u2.age_range} лет\n\n"
            f"💬 Можете начинать общение!\n\n"
            f"{'📸 Отправка фото доступна!' if u1.premium else '💎 Фото только с премиумом'}\n"
            f"Завершить: /stop")
    
    info2 = (f"✅ *Собеседник найден!*\n\n"
            f"🌍 {u1.country}, {u1.city}\n"
            f"⚤ Пол: {u1.gender}\n"
            f"🎂 Возраст: {u1.age_range} лет\n\n"
            f"💬 Можете начинать общение!\n\n"
            f"{'📸 Отправка фото доступна!' if u2.premium else '💎 Фото только с премиумом'}\n"
            f"Завершить: /stop")
    
    bot.send_message(uid1, info1, parse_mode='Markdown')
    bot.send_message(uid2, info2, parse_mode='Markdown')

@bot.message_handler(commands=['stop'])
def stop_cmd(m):
    stop(m)

def stop(m):
    uid = m.chat.id
    
    if uid in users and users[uid].in_queue:
        age_range = users[uid].age_range
        if uid in waiting[age_range]:
            waiting[age_range].remove(uid)
        users[uid].in_queue = False
        bot.send_message(uid, "❌ Поиск отменён", reply_markup=get_main_keyboard())
        return
    
    if uid not in users or not users[uid].partner:
        bot.send_message(uid, "⚠️ Вы не в чате", reply_markup=get_main_keyboard())
        return
    
    partner = users[uid].partner
    users[uid].partner = None
    users[partner].partner = None
    
    bot.send_message(uid, 
        "👋 *Чат завершён*\n\n"
        "Используйте /find для нового поиска",
        parse_mode='Markdown',
        reply_markup=get_main_keyboard())
    
    bot.send_message(partner,
        "👋 *Собеседник завершил чат*\n\n"
        "Используйте /find для нового поиска",
        parse_mode='Markdown',
        reply_markup=get_main_keyboard())

@bot.message_handler(commands=['premium'])
def premium_cmd(m):
    show_premium(m)

def show_premium(m):
    uid = m.chat.id
    
    if uid in users and users[uid].premium:
        bot.send_message(uid,
            "💎 *У вас есть Премиум!*\n\n"
            "✅ Отправка фотографий\n"
            "✅ Приоритет в поиске\n"
            "✅ Расширенный профиль\n\n"
            "Спасибо за поддержку! ❤️",
            parse_mode='Markdown',
            reply_markup=get_main_keyboard())
    else:
        kb = telebot.types.InlineKeyboardMarkup()
        kb.add(telebot.types.InlineKeyboardButton(
            f"⭐ Купить за {PREMIUM_PRICE_STARS} Stars",
            callback_data="buy_premium"))
        
        bot.send_message(uid,
            f"💎 *ПРЕМИУМ ДОСТУП*\n\n"
            f"✨ *Что вы получите:*\n"
            f"📸 Отправка фотографий собеседнику\n"
            f"🚀 Приоритет в очереди поиска\n"
            f"💬 Расширенный профиль\n"
            f"⚡ Мгновенный поиск\n\n"
            f"💰 Стоимость: *{PREMIUM_PRICE_STARS} Telegram Stars*\n"
            f"(≈ {PREMIUM_PRICE_STARS * 2} рублей)\n\n"
            f"💡 Средства идут на развитие бота!",
            parse_mode='Markdown',
            reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data == 'buy_premium')
def buy_premium_handler(call):
    uid = call.message.chat
