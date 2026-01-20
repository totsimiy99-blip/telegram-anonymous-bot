import telebot
import os
import requests
from flask import Flask
from threading import Thread
import time
from sqlalchemy import create_engine, Column, BigInteger, String, Boolean, Integer, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

print("=" * 60)
print("🤖 Анонимный чат-бот запускается...")
print("=" * 60)

# Flask для health check
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Анонимный чат-бот работает!", 200

@app.route('/health')
def health():
    try:
        bot_info = bot.get_me()
        db_status = "✅" if db_session else "❌"
        return f"✅ @{bot_info.username} | DB: {db_status}", 200
    except Exception as e:
        return f"⚠️ Error: {e}", 503

def run_flask():
    port = int(os.environ.get('PORT', 8000))
    print(f"✅ Flask сервер на порту {port}")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

def auto_ping():
    """Автопинг Flask каждые 5 минут"""
    SERVICE_URL = os.environ.get('SERVICE_URL', '')
    
    while True:
        try:
            time.sleep(300)  # 5 минут
            if SERVICE_URL:
                requests.get(SERVICE_URL + '/health', timeout=10)
                print("🏓 HTTP пинг выполнен")
        except Exception as e:
            print(f"⚠️ Ошибка HTTP пинга: {e}")

def keep_bot_active():
    """Отправка пинга себе каждые 5 минут"""
    ADMIN_ID = 5426463183
    
    while True:
        try:
            time.sleep(300)  # 5 минут
            try:
                bot.send_message(ADMIN_ID, "🏓", disable_notification=True)
                print("🏓 Telegram пинг отправлен")
            except Exception as e:
                print(f"⚠️ Ошибка Telegram пинга: {e}")
        except:
            pass

def start_auto_services():
    """Запуск всех фоновых сервисов"""
    t1 = Thread(target=auto_ping)
    t1.daemon = True
    t1.start()
    
    t2 = Thread(target=keep_bot_active)
    t2.daemon = True
    t2.start()

# Токен бота
TOKEN = os.environ.get('BOT_TOKEN')

if not TOKEN:
    print("❌ ОШИБКА: BOT_TOKEN не найден!")
    exit(1)

print(f"✅ Токен получен: {TOKEN[:15]}...")

# Подключение к БД
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    print(f"✅ DATABASE_URL получена: {DATABASE_URL[:50]}...")
    try:
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        Base = declarative_base()
        
        # Модель таблицы users
        class UserDB(Base):
            __tablename__ = 'users'
            
            id = Column(BigInteger, primary_key=True)
            country = Column(String(100))
            city = Column(String(100))
            gender = Column(String(20))
            age_range = Column(String(20))
            search_gender = Column(String(50))
            premium = Column(Boolean, default=False)
            chats_count = Column(Integer, default=0)
            created_at = Column(DateTime, default=datetime.now)
            updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
        
        # Создание таблиц
        Base.metadata.create_all(engine)
        
        # Сессия
        SessionLocal = sessionmaker(bind=engine)
        db_session = SessionLocal()
        
        print("✅ База данных подключена!")
        print("🗄️ Таблица users создана/проверена")
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        db_session = None
else:
    print("⚠️ DATABASE_URL не найдена, работаем без БД")
    db_session = None

bot = telebot.TeleBot(TOKEN)

# База данных (в памяти для текущей сессии)
users = {}
waiting = {
    '14-16': [],
    '16-18': [],
    '18-30': []
}

# Функции работы с БД
def save_user_to_db(user):
    """Сохранить пользователя в БД"""
    if not db_session:
        return
    
    try:
        db_user = db_session.query(UserDB).filter_by(id=user.id).first()
        
        if db_user:
            # Обновление
            db_user.country = user.country
            db_user.city = user.city
            db_user.gender = user.gender
            db_user.age_range = user.age_range
            db_user.search_gender = user.search_gender
            db_user.premium = user.premium
            db_user.chats_count = user.chats_count
            db_user.updated_at = datetime.now()
        else:
            # Создание
            db_user = UserDB(
                id=user.id,
                country=user.country,
                city=user.city,
                gender=user.gender,
                age_range=user.age_range,
                search_gender=user.search_gender,
                premium=user.premium,
                chats_count=user.chats_count
            )
            db_session.add(db_user)
        
        db_session.commit()
        print(f"💾 Пользователь {user.id} сохранён в БД")
    except Exception as e:
        print(f"❌ Ошибка сохранения в БД: {e}")
        db_session.rollback()

def load_user_from_db(uid):
    """Загрузить пользователя из БД"""
    if not db_session:
        return None
    
    try:
        db_user = db_session.query(UserDB).filter_by(id=uid).first()
        if db_user:
            print(f"📂 Пользователь {uid} загружен из БД")
            return db_user
        return None
    except Exception as e:
        print(f"❌ Ошибка загрузки из БД: {e}")
        return None

def get_db_stats():
    """Получить статистику из БД"""
    if not db_session:
        return None
    
    try:
        total = db_session.query(UserDB).count()
        premium = db_session.query(UserDB).filter_by(premium=True).count()
        total_chats = db_session.query(func.sum(UserDB.chats_count)).scalar() or 0
        
        return {
            'total': total,
            'premium': premium,
            'total_chats': total_chats // 2
        }
    except Exception as e:
        print(f"❌ Ошибка получения статистики: {e}")
        return None

# Цена премиума
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
        
        # Попытка загрузить из БД
        db_user = load_user_from_db(uid)
        if db_user:
            self.country = db_user.country
            self.city = db_user.city
            self.gender = db_user.gender
            self.age_range = db_user.age_range
            self.search_gender = db_user.search_gender
            self.premium = db_user.premium
            self.chats_count = db_user.chats_count
            self.ready = True if self.country else False

# Правила
RULES = """
📜 *ПРАВИЛА БОТА*

⚠️ *ОБЯЗАТЕЛЬНО К ПРОЧТЕНИЮ:*

1️⃣ Запрещено нарушать законодательство РФ
2️⃣ Запрещены оскорбления и мат
3️⃣ Соблюдайте нормы морали
4️⃣ Уважайте собеседника
5️⃣ Запрещён спам
6️⃣ Запрещена пропаганда насилия

❌ *ЗА НАРУШЕНИЕ:* Блокировка

✅ *Нажимая "Принять" вы подтверждаете:*
• Вам есть 14 лет
• Вы ознакомились с правилами
• Обязуетесь их соблюдать
"""

# Клавиатуры
def get_main_keyboard():
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🔍 Найти собеседника")
    kb.row("👤 Профиль", "❌ Завершить чат")
    kb.row("💎 Премиум", "📊 Статистика")
    return kb

def get_countries():
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.row("🇷🇺 Россия", "🇺🇦 Украина", "🇧🇾 Беларусь")
    kb.row("🇰🇿 Казахстан", "🇺🇿 Узбекистан")
    kb.row("🌍 Другая")
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

# Команда /start
@bot.message_handler(commands=['start'])
def start(m):
    uid = m.chat.id
    
    if uid not in users:
        users[uid] = User(uid)
    
    if users[uid].ready:
        bot.send_message(uid, 
            "👋 *С возвращением!*\n\n"
            "Используйте меню 👇",
            parse_mode='Markdown',
            reply_markup=get_main_keyboard())
    else:
        show_rules(m)

def show_rules(m):
    uid = m.chat.id
    kb = telebot.types.InlineKeyboardMarkup()
    kb.add(telebot.types.InlineKeyboardButton("✅ Принять", callback_data="accept_rules"))
    kb.add(telebot.types.InlineKeyboardButton("❌ Отклонить", callback_data="decline_rules"))
    bot.send_message(uid, RULES, parse_mode='Markdown', reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data in ['accept_rules', 'decline_rules'])
def handle_rules(call):
    uid = call.message.chat.id
    
    if call.data == 'accept_rules':
        bot.edit_message_text(
            "✅ *Правила приняты!*\n\nТеперь создайте профиль 👇",
            uid, call.message.message_id, parse_mode='Markdown')
        time.sleep(1)
        bot.send_message(uid, "🎉 *Добро пожаловать!*\n\nЗаполните профиль:", parse_mode='Markdown')
        start_profile(uid)
    else:
        bot.edit_message_text(
            "❌ Вы отклонили правила.\n\nДля повторной попытки: /start",
            uid, call.message.message_id)

def start_profile(uid):
    msg = bot.send_message(uid, 
        "🌍 *Шаг 1/5: Страна*\n\nВыберите страну:",
        parse_mode='Markdown', reply_markup=get_countries())
    bot.register_next_step_handler(msg, get_country)

def get_country(m):
    uid = m.chat.id
    users[uid].country = clean_emoji(m.text)
    msg = bot.send_message(uid, 
        "🏙 *Шаг 2/5: Город*\n\nВведите город:",
        parse_mode='Markdown',
        reply_markup=telebot.types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, get_city)

def get_city(m):
    uid = m.chat.id
    users[uid].city = m.text
    msg = bot.send_message(uid, "⚤ *Шаг 3/5: Пол*\n\nВыберите пол:",
        parse_mode='Markdown', reply_markup=get_gender_keyboard())
    bot.register_next_step_handler(msg, get_gender)

def get_gender(m):
    uid = m.chat.id
    users[uid].gender = clean_emoji(m.text)
    msg = bot.send_message(uid, "🎂 *Шаг 4/5: Возраст*\n\nВыберите группу:",
        parse_mode='Markdown', reply_markup=get_age_ranges())
    bot.register_next_step_handler(msg, get_age)

def get_age(m):
    uid = m.chat.id
    age_range = parse_age_range(m.text)
    
    if not age_range:
        msg = bot.send_message(uid, "❌ Выберите из вариантов:",
            reply_markup=get_age_ranges())
        bot.register_next_step_handler(msg, get_age)
        return
    
    users[uid].age_range = age_range
    msg = bot.send_message(uid, "💝 *Шаг 5/5: Предпочтения*\n\nКого ищете?",
        parse_mode='Markdown', reply_markup=get_search_preferences())
    bot.register_next_step_handler(msg, get_search_preference)

def get_search_preference(m):
    uid = m.chat.id
    users[uid].search_gender = clean_emoji(m.text)
    users[uid].ready = True
    
    # Сохранить в БД
    save_user_to_db(users[uid])
    
    u = users[uid]
    bot.send_message(uid,
        f"✅ *Профиль создан!*\n\n"
        f"🌍 {u.country}, {u.city}\n"
        f"⚤ {u.gender}\n"
        f"🎂 {u.age_range} лет\n"
        f"💝 Ищу: {u.search_gender}\n\n"
        f"{'💾 Сохранено в БД ✅' if db_session else ''}\n"
        f"Теперь можно искать! 🔍",
        parse_mode='Markdown', reply_markup=get_main_keyboard())

# Профиль
@bot.message_handler(commands=['profile'])
def profile_cmd(m):
    uid = m.chat.id
    if uid not in users:
        users[uid] = User(uid)
    
    if users[uid].ready:
        u = users[uid]
        premium = "✅" if u.premium else "❌"
        
        kb = telebot.types.InlineKeyboardMarkup()
        kb.add(telebot.types.InlineKeyboardButton("✏️ Изменить", callback_data="edit_profile"))
        
        bot.send_message(uid,
            f"👤 *Профиль:*\n\n"
            f"🌍 {u.country}, {u.city}\n"
            f"⚤ {u.gender}\n"
            f"🎂 {u.age_range} лет\n"
            f"💝 Ищу: {u.search_gender}\n"
            f"💬 Диалогов: {u.chats_count}\n"
            f"💎 Премиум: {premium}",
            parse_mode='Markdown', reply_markup=kb)
    else:
        start_profile(uid)

@bot.callback_query_handler(func=lambda call: call.data == 'edit_profile')
def edit_profile(call):
    bot.answer_callback_query(call.id, "Начинаем...")
    start_profile(call.message.chat.id)

# Поиск
@bot.message_handler(commands=['find'])
def find_cmd(m):
    find(m)

def find(m):
    uid = m.chat.id
    
    if uid not in users or not users[uid].ready:
        bot.send_message(uid, "⚠️ Заполните профиль!\n\n/profile",
            reply_markup=get_main_keyboard())
        return
    
    if users[uid].partner:
        bot.send_message(uid, "⚠️ Вы уже в чате! /stop для завершения")
        return
    
    if users[uid].in_queue:
        bot.send_message(uid, "⚠️ Вы уже в очереди!")
        return
    
    age_range = users[uid].age_range
    users[uid].in_queue = True
    
    if users[uid].premium:
        waiting[age_range].insert(0, uid)
    else:
        waiting[age_range].append(uid)
    
    queue_count = len(waiting[age_range])
    
    bot.send_message(uid,
        f"🔍 *Поиск...*\n\n"
        f"🎂 {age_range} лет\n"
        f"💝 {users[uid].search_gender}\n"
        f"⏳ В очереди: {queue_count}\n\n"
        f"{'⚡ Премиум-приоритет' if users[uid].premium else '💡 С премиумом быстрее!'}",
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
	    # Сохранить в БД
    save_user_to_db(users[uid1])
    save_user_to_db(users[uid2])
    
    u1 = users[uid1]
    u2 = users[uid2]
    
    info1 = (f"✅ *Собеседник найден!*\n\n"
            f"🌍 {u2.country}, {u2.city}\n"
            f"⚤ {u2.gender}\n"
            f"🎂 {u2.age_range} лет\n\n"
            f"{'📸 Фото доступны' if u1.premium else '💎 Фото с премиумом'}\n"
            f"/stop - завершить")
    
    info2 = (f"✅ *Собеседник найден!*\n\n"
            f"🌍 {u1.country}, {u1.city}\n"
            f"⚤ {u1.gender}\n"
            f"🎂 {u1.age_range} лет\n\n"
            f"{'📸 Фото доступны' if u2.premium else '💎 Фото с премиумом'}\n"
            f"/stop - завершить")
    
    bot.send_message(uid1, info1, parse_mode='Markdown')
    bot.send_message(uid2, info2, parse_mode='Markdown')

# Остановка чата
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
    
    bot.send_message(uid, "👋 *Чат завершён*\n\n/find для нового",
        parse_mode='Markdown', reply_markup=get_main_keyboard())
    bot.send_message(partner, "👋 *Собеседник завершил чат*\n\n/find для нового",
        parse_mode='Markdown', reply_markup=get_main_keyboard())

# Премиум
@bot.message_handler(commands=['premium'])
def premium_cmd(m):
    show_premium(m)

def show_premium(m):
    uid = m.chat.id
    
    if uid not in users:
        users[uid] = User(uid)
    
    if users[uid].premium:
        bot.send_message(uid,
            "💎 *У вас Премиум!*\n\n"
            "✅ Фото\n✅ Приоритет\n✅ Расширенный профиль",
            parse_mode='Markdown', reply_markup=get_main_keyboard())
    else:
        kb = telebot.types.InlineKeyboardMarkup()
        kb.add(telebot.types.InlineKeyboardButton(
            f"⭐ Купить {PREMIUM_PRICE_STARS} Stars",
            callback_data="buy_premium"))
        
        bot.send_message(uid,
            f"💎 *ПРЕМИУМ*\n\n"
            f"✨ Что получите:\n"
            f"📸 Отправка фото\n"
            f"🚀 Приоритет в поиске\n"
            f"💬 Расширенный профиль\n\n"
            f"💰 {PREMIUM_PRICE_STARS} Stars (≈{PREMIUM_PRICE_STARS*2}₽)",
            parse_mode='Markdown', reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data == 'buy_premium')
def buy_premium(call):
    uid = call.message.chat.id
    prices = [telebot.types.LabeledPrice(label="Премиум", amount=PREMIUM_PRICE_STARS)]
    
    try:
        bot.send_invoice(
            uid,
            title="💎 Премиум доступ",
            description="📸 Фото | 🚀 Приоритет | 💬 Профиль",
            invoice_payload="premium",
            provider_token="",
            currency="XTR",
            prices=prices,
            start_parameter="premium")
        bot.answer_callback_query(call.id, "✅ Счёт создан!")
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Ошибка: {e}", show_alert=True)

@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def successful_payment(message):
    uid = message.chat.id
    if uid in users:
        users[uid].premium = True
        
        # Сохранить в БД
        save_user_to_db(users[uid])
        
        bot.send_message(uid,
            "🎉 *Премиум активирован!*\n\n"
            "✅ Теперь можете:\n"
            "📸 Отправлять фото\n"
            "🚀 Приоритет в поиске\n\n"
            f"{'💾 Сохранено в БД ✅' if db_session else ''}\n"
            "Спасибо! ❤️",
            parse_mode='Markdown', reply_markup=get_main_keyboard())

# Статистика
@bot.message_handler(commands=['stats'])
def stats(m):
    # Статистика из памяти
    in_chat = sum(1 for u in users.values() if u.partner)
    in_queue = sum(1 for u in users.values() if u.in_queue)
    
    # Статистика из БД
    db_stats = get_db_stats()
    
    if db_stats:
        bot.send_message(m.chat.id,
            f"📊 *Статистика:*\n\n"
            f"👥 Всего пользователей: {db_stats['total']}\n"
            f"💬 Сейчас в чате: {in_chat}\n"
            f"🔍 В поиске: {in_queue}\n"
            f"💎 Премиум: {db_stats['premium']}\n"
            f"📈 Всего диалогов: {db_stats['total_chats']}\n\n"
            f"🗄️ Данные из БД ✅",
            parse_mode='Markdown')
    else:
        total_users = len(users)
        premium_users = sum(1 for u in users.values() if u.premium)
        total_chats = sum(u.chats_count for u in users.values()) // 2
        
        bot.send_message(m.chat.id,
            f"📊 *Статистика:*\n\n"
            f"👥 Пользователей: {total_users}\n"
            f"💬 В чате: {in_chat}\n"
            f"🔍 В поиске: {in_queue}\n"
            f"💎 Премиум: {premium_users}\n"
            f"📈 Всего диалогов: {total_chats}",
            parse_mode='Markdown')

# Команда для админа - выдать себе премиум
ADMIN_ID = 5426463183

@bot.message_handler(commands=['givepremium'])
def give_premium(m):
    uid = m.chat.id
    
    if uid == ADMIN_ID:
        if uid in users:
            users[uid].premium = True
            save_user_to_db(users[uid])
            
            bot.send_message(uid,
                "✅ *Премиум активирован бесплатно!*\n\n"
                "💎 Теперь доступно:\n"
                "📸 Отправка фото\n"
                "🚀 Приоритет в поиске\n\n"
                f"{'💾 Сохранено в БД ✅' if db_session else ''}",
                parse_mode='Markdown',
                reply_markup=get_main_keyboard())
        else:
            bot.send_message(uid, "❌ Сначала создайте профиль: /start")
    else:
        bot.send_message(uid, "⛔ Команда только для админа")

# Команда для получения своего ID
@bot.message_handler(commands=['myid'])
def my_id(m):
    bot.send_message(m.chat.id,
        f"🆔 *Ваш Telegram ID:*\n\n`{m.chat.id}`\n\n"
        f"_Скопируйте это число для настройки админа_",
        parse_mode='Markdown')

# Пересылка сообщений
@bot.message_handler(content_types=['text'])
def handle_text(m):
    uid = m.chat.id
    
    # Кнопки меню
    if m.text == "🔍 Найти собеседника":
        find(m)
        return
    elif m.text == "👤 Профиль":
        profile_cmd(m)
        return
    elif m.text == "❌ Завершить чат":
        stop(m)
        return
    elif m.text == "💎 Премиум":
        show_premium(m)
        return
    elif m.text == "📊 Статистика":
        stats(m)
        return
    
    # Пересылка в чате
    if uid in users and users[uid].partner:
        partner = users[uid].partner
        try:
            bot.send_message(partner, m.text)
        except:
            bot.send_message(uid, "❌ Ошибка отправки")
    else:
        bot.send_message(uid, 
            "💡 Используйте меню или команды:\n"
            "/find - найти собеседника\n"
            "/profile - профиль\n"
            "/premium - премиум\n"
            "/myid - узнать свой ID",
            reply_markup=get_main_keyboard())

# Пересылка фото
@bot.message_handler(content_types=['photo'])
def handle_photo(m):
    uid = m.chat.id
    
    if uid not in users or not users[uid].partner:
        bot.send_message(uid, "⚠️ Сначала найдите собеседника! /find")
        return
    
    if not users[uid].premium:
        bot.send_message(uid, 
            "🔒 *Отправка фото доступна только с премиумом!*\n\n"
            "Получите премиум: /premium",
            parse_mode='Markdown')
        return
    
    partner = users[uid].partner
    try:
        bot.send_photo(partner, m.photo[-1].file_id, caption="📸 Фото от собеседника")
        bot.send_message(uid, "✅ Фото отправлено!")
    except Exception as e:
        bot.send_message(uid, f"❌ Ошибка: {e}")

# Пересылка стикеров
@bot.message_handler(content_types=['sticker'])
def handle_sticker(m):
    uid = m.chat.id
    
    if uid in users and users[uid].partner:
        partner = users[uid].partner
        try:
            bot.send_sticker(partner, m.sticker.file_id)
        except:
            bot.send_message(uid, "❌ Ошибка отправки")
    else:
        bot.send_message(uid, "⚠️ Сначала /find")

# Пересылка голосовых
@bot.message_handler(content_types=['voice'])
def handle_voice(m):
    uid = m.chat.id
    
    if uid in users and users[uid].partner:
        partner = users[uid].partner
        try:
            bot.send_voice(partner, m.voice.file_id)
        except:
            bot.send_message(uid, "❌ Ошибка отправки")
    else:
        bot.send_message(uid, "⚠️ Сначала /find")

# Запуск
if __name__ == '__main__':
    print("=" * 60)
    print("🌐 Запуск Flask...")
    keep_alive()
    start_auto_services()
    print("🏓 Автопинг HTTP + Telegram запущен!")
    
    if db_session:
        print("💎 Премиум: Telegram Stars")
        print("🗄️ База данных: ✅ Подключена")
    else:
        print("💎 Премиум: Telegram Stars")
        print("🗄️ База данных: ⚠️ Отключена")
    
    print("🤖 Запуск Telegram polling...")
    print("=" * 60)
    
    try:
        bot.infinity_polling(
            timeout=60,
            long_polling_timeout=60,
            skip_pending=True,
            none_stop=True
        )
    except KeyboardInterrupt:
        print("\n❌ Остановлено пользователем")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if db_session:
            try:
                db_session.close()
                print("🗄️ Соединение с БД закрыто")
            except:
                pass
