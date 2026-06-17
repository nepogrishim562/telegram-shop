# Полный Telegram shop bot (aiogram) — меню, профиль, статистика, покупки (VPN, подписки, Telegram Stars/Premium, CS2 Prime, мануалы),
# подтверждение покупки, кнопка "Назад" везде, админ-команды (orders, deliver, addproduct, addsecret, addmanuals), политики.
# Установка: pip install aiogram python-dotenv
# Запуск: создать файл .env с BOT_TOKEN, ADMIN_IDS (через запятую), OPTIONAL PROVIDER_TOKEN, затем: python bot.py

import os
import json
import uuid
import asyncio
import logging
import sqlite3
from datetime import datetime
from decimal import Decimal
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice

# Load .env manually if python-dotenv is unavailable
ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
if os.path.isfile(ENV_PATH):
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key not in os.environ:
                os.environ[key] = value

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
PROVIDER_TOKEN = os.getenv("PROVIDER_TOKEN", "")  # Telegram Payments provider token
HELP_USERNAME = "@helpingonuser"

if not BOT_TOKEN or not ADMIN_IDS:
    print("Set BOT_TOKEN and ADMIN_IDS env vars.")
    exit(1)

bot = Bot(BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

DATA_FILE = "shop_data.json"
DB_FILE = "shop.db"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

DEFAULT_DATA = {
    "vpn": {
        "title": "🌍 VPN сервера",
        "items": {
            "vpn_uk": {"title": "VPN — England", "price": 5.0, "currency": "USD", "type": "secret",
                       "secrets": ["VPN-UK-KEY-1", "VPN-UK-KEY-2"]},
            "vpn_ch": {"title": "VPN — Switzerland", "price": 5.0, "currency": "USD", "type": "secret",
                       "secrets": ["VPN-CH-KEY-1"]},
            "vpn_se": {"title": "VPN — Sweden", "price": 5.0, "currency": "USD", "type": "secret",
                       "secrets": ["VPN-SE-KEY-1"]},
            "vpn_no": {"title": "VPN — Norway", "price": 5.0, "currency": "USD", "type": "secret",
                       "secrets": ["VPN-NO-KEY-1"]},
            "vpn_us": {"title": "VPN — USA", "price": 5.0, "currency": "USD", "type": "secret",
                       "secrets": ["VPN-US-KEY-1", "VPN-US-KEY-2"]}
        }
    },
    "tg": {
        "title": "⭐ Telegram услуги",
        "items": {
            "tg_star_1": {"title": "Telegram Stars — 1", "price": 1.0, "currency": "XTR", "type": "stars", "stars": 1},
            "tg_star_50": {"title": "Telegram Stars — 50", "price": 50.0, "currency": "XTR", "type": "stars", "stars": 50},
            "tg_premium": {"title": "Telegram Premium — 1 мес", "price": 7.0, "currency": "USD", "type": "premium",
                           "secrets": ["TG-PREMIUM-KEY-1", "TG-PREMIUM-KEY-2"]}
        }
    },
    "subs": {
        "title": "📱 Подписки AI",
        "items": {
            "sub_chatgpt": {"title": "ChatGPT Plus — 1 мес", "price": 20.0, "currency": "USD", "type": "secret",
                            "secrets": ["CHATGPT-KEY-1"]},
            "sub_gemini": {"title": "Gemini Pro — 1 мес", "price": 10.0, "currency": "USD", "type": "secret",
                           "secrets": ["GEMINI-KEY-1"]},
            "sub_claude": {"title": "Claude Pro — 1 мес", "price": 20.0, "currency": "USD", "type": "secret",
                           "secrets": ["CLAUDE-KEY-1"]},
            "sub_grok": {"title": "Grok — 1 мес", "price": 8.0, "currency": "USD", "type": "secret",
                         "secrets": ["GROK-KEY-1"]}
        }
    },
    "cs2": {
        "title": "🎮 CS2 Prime аккаунты",
        "items": {
            "cs2_prime_1": {"title": "CS2 Prime — 1 аккаунт", "price": 15.0, "currency": "USD", "type": "secret",
                            "secrets": ["CS2-PRIME-ACC-1", "CS2-PRIME-ACC-2"]},
            "cs2_prime_bulk": {"title": "CS2 Prime — пакет 5", "price": 60.0, "currency": "USD", "type": "secret",
                               "secrets": ["CS2-BULK-1", "CS2-BULK-2", "CS2-BULK-3", "CS2-BULK-4", "CS2-BULK-5"]}
        }
    },
    "manuals": {
        "title": "📚 Мануалы",
        "items": {
            "manual_ai": {"title": "Мануалы AI", "price": 12.0, "currency": "USD", "type": "manual",
                          "manuals": ["Grok prompts", "Gemini подсказки", "Claude инструкции"],
                          "secrets": ["MANUAL-AI-1", "MANUAL-AI-2"]},
            "manual_security": {"title": "Мануалы безопасности", "price": 15.0, "currency": "USD", "type": "manual",
                                "manuals": ["Настройка VPN", "Анонимный браузинг", "Безопасный доступ"],
                                "secrets": ["MANUAL-SEC-1"]}
        }
    }
}

def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.exception("Failed to load JSON from %s", path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(default, f, ensure_ascii=False, indent=2)
    return default

shop = load_json(DATA_FILE, DEFAULT_DATA)

class OrderStates(StatesGroup):
    waiting_for_username = State()


def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            username TEXT,
            cat TEXT NOT NULL,
            item TEXT NOT NULL,
            price REAL NOT NULL,
            currency TEXT NOT NULL,
            type TEXT NOT NULL,
            status TEXT NOT NULL,
            target_username TEXT,
            secret TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS error_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            level TEXT NOT NULL,
            message TEXT NOT NULL,
            traceback TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def db_connection():
    return sqlite3.connect(DB_FILE)


def save_shop():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(shop, f, ensure_ascii=False, indent=2)


def save_order(order):
    now = datetime.utcnow().isoformat()
    order.setdefault("created_at", now)
    order["updated_at"] = now
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO orders (id, user_id, username, cat, item, price, currency, type, status, target_username, secret, created_at, updated_at) "
            "VALUES (:id, :user_id, :username, :cat, :item, :price, :currency, :type, :status, :target_username, :secret, :created_at, :updated_at)",
            order,
        )
        conn.commit()


def get_order(order_id):
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, user_id, username, cat, item, price, currency, type, status, target_username, secret, created_at, updated_at FROM orders WHERE id = ?", (order_id,))
        row = cursor.fetchone()
    if not row:
        return None
    keys = ["id", "user_id", "username", "cat", "item", "price", "currency", "type", "status", "target_username", "secret", "created_at", "updated_at"]
    return dict(zip(keys, row))


def update_order(order_id, updates):
    order = get_order(order_id)
    if not order:
        return None
    order.update(updates)
    save_order(order)
    return order


def get_user_orders(user_id):
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, user_id, username, cat, item, price, currency, type, status, target_username, secret, created_at, updated_at FROM orders WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        rows = cursor.fetchall()
    keys = ["id", "user_id", "username", "cat", "item", "price", "currency", "type", "status", "target_username", "secret", "created_at", "updated_at"]
    return [dict(zip(keys, row)) for row in rows]


def get_all_orders():
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, user_id, username, cat, item, price, currency, type, status, target_username, secret, created_at, updated_at FROM orders ORDER BY created_at DESC")
        rows = cursor.fetchall()
    keys = ["id", "user_id", "username", "cat", "item", "price", "currency", "type", "status", "target_username", "secret", "created_at", "updated_at"]
    return [dict(zip(keys, row)) for row in rows]


def get_stats():
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*), SUM(price), SUM(CASE WHEN status = 'delivered' THEN 1 ELSE 0 END) FROM orders")
        total, revenue, delivered = cursor.fetchone()
    return total or 0, revenue or 0.0, delivered or 0


def log_error(message, exc_info=None):
    stack = None
    if exc_info:
        if exc_info is True:
            import sys

            exc_info = sys.exc_info()
        try:
            stack = ''.join(logging.Formatter().formatException(exc_info))
        except Exception:
            stack = None
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO error_logs (created_at, level, message, traceback) VALUES (?, ?, ?, ?)",
                (datetime.utcnow().isoformat(), "ERROR", message, stack),
            )
            conn.commit()
    except Exception:
        logger.exception("Could not write error log to database")
    logger.error(message, exc_info=exc_info)


def kb_main():
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    kb.inline_keyboard.append([InlineKeyboardButton(text="📦 Товары", callback_data="menu|catalog")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="👤 Профиль", callback_data="menu|profile")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="📊 Статистика", callback_data="menu|stats")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="📄 Политика конфиденциальности", callback_data="menu|privacy")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="📜 Условия соглашения", callback_data="menu|terms")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="🆘 Помощь", url=f"https://t.me/{HELP_USERNAME.lstrip('@')}")])
    return kb

def mk_buttons(pairs, back_to=None):
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for cb, text in pairs:
        kb.inline_keyboard.append([InlineKeyboardButton(text=text, callback_data=cb)])
    if back_to:
        kb.inline_keyboard.append([InlineKeyboardButton(text="◀ Назад", callback_data=back_to)])
    return kb

def get_item(cat_key, item_key):
    return shop.get(cat_key, {}).get("items", {}).get(item_key)

def get_chat_id(order):
    target = order.get("target_username")
    if target:
        return target
    return order["user_id"]

def send_order_message(chat_id, text):
    return bot.send_message(chat_id, text, parse_mode="Markdown")

def send_invoice_for_order(order, item, chat_id):
    currency = item.get("currency", "USD")
    if currency == "XTR":
        amount = int(item["price"])
    else:
        amount = int(Decimal(str(item["price"])) * 100)
    prices = [LabeledPrice(label=item["title"], amount=amount)]
    return bot.send_invoice(
        chat_id=chat_id,
        title=item["title"],
        description=f"Покупка {item.get('stars', '')} {item['title']}".strip(),
        payload=order["id"],
        provider_token=PROVIDER_TOKEN,
        currency=currency,
        prices=prices,
        start_parameter=order["id"]
    )

PRIVACY_TEXT = (
    "Политика конфиденциальности\n\n"
    "1. Сбор данных\n"
    "Мы собираем минимальные данные: Telegram ID, имя/никнейм пользователя для обработки заказов.\n\n"
    "2. Использование данных\n"
    "Данные используются только для выполнения заказов, доставки и уведомлений администраторов.\n\n"
    "3. Хранение данных\n"
    "Данные хранятся локально в файлах shop_data.json и shop.db. По запросу администратора данные могут быть удалены.\n\n"
    "4. Передача третьим лицам\n"
    "Мы не передаем персональные данные третьим лицам без вашего согласия, кроме случаев, предусмотренных законом.\n\n"
    "5. Контакты\n"
    "По вопросам конфиденциальности обращайтесь к администраторам бота."
)

TERMS_TEXT = (
    "Условия соглашения\n\n"
    "1. Общие положения\n"
    "Использование бота означает согласие с настоящими условиями. Товары предоставляются «как есть».\n\n"
    "2. Оплата и доставка\n"
    "Оплата производится по инструкциям в боте. Выдача товара осуществляется после подтверждения оплаты администратором.\n\n"
    "3. Возвраты\n"
    "Возвраты и спорные вопросы решаются через администрацию и зависят от конкретного случая.\n\n"
    "4. Ответственность\n"
    "Администрация не несет ответственности за последствия использования приобретенных товаров.\n\n"
    "5. Обновления\n"
    "Условия могут быть изменены. Текущая версия доступна в боте."
)

@dp.message(Command("start", "help"))
async def cmd_start(msg: types.Message):
    text = (
        f"👋 Привет, {msg.from_user.full_name}!\n\n"
        "Добро пожаловать в магазин. Выберите раздел в меню.\n\n"
        f"🆘 Помощь: {HELP_USERNAME}"
    )
    await msg.reply(text, reply_markup=kb_main())

@dp.callback_query(lambda c: c.data and c.data.startswith("menu|"))
async def cb_menu(call: types.CallbackQuery):
    _, action = call.data.split("|", 1)
    if action == "catalog":
        kb = InlineKeyboardMarkup(inline_keyboard=[])
        for cat_key, cat in shop.items():
            kb.inline_keyboard.append([InlineKeyboardButton(text=cat.get("title", cat_key), callback_data=f"cat|{cat_key}")])
        kb.inline_keyboard.append([InlineKeyboardButton(text="◀ Назад", callback_data="menu|main")])
        await call.message.edit_text("📦 Категории:", reply_markup=kb)
    elif action == "profile":
        uid = call.from_user.id
        user_orders = get_user_orders(uid)
        lines = [
            f"👤 Профиль: @{call.from_user.username or call.from_user.id}",
            f"Всего заказов: {len(user_orders)}",
            ""
        ]
        if user_orders:
            for o in user_orders[:10]:
                lines.append(f"- `{o.get('id')}` {o.get('cat')}/{o.get('item')} • {o.get('status')}")
        else:
            lines.append("Пока нет заказов.")
        await call.message.edit_text("\n".join(lines), reply_markup=mk_buttons([("menu|main", "Главное меню")]))
    elif action == "stats":
        total_orders, revenue, delivered = get_stats()
        lines = [
            "📊 Статистика:",
            f"Всего заказов: {total_orders}",
            f"Оплачено (сумма): {revenue}",
            f"Выдано: {delivered}"
        ]
        await call.message.edit_text("\n".join(lines), reply_markup=mk_buttons([("menu|main", "Главное меню")]))
    elif action == "privacy":
        await call.message.edit_text(PRIVACY_TEXT, reply_markup=mk_buttons([("menu|main", "Главное меню")]))
    elif action == "terms":
        await call.message.edit_text(TERMS_TEXT, reply_markup=mk_buttons([("menu|main", "Главное меню")]))
    elif action == "main":
        await call.message.edit_text("Главное меню:", reply_markup=kb_main())
    await call.answer()

@dp.message(Command("catalog"))
async def cmd_catalog(msg: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for cat_key, cat in shop.items():
        kb.inline_keyboard.append([InlineKeyboardButton(text=cat.get("title", cat_key), callback_data=f"cat|{cat_key}")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="◀ Назад", callback_data="menu|main")])
    await msg.answer("📦 Категории:", reply_markup=kb)

@dp.callback_query(lambda c: c.data and c.data.startswith("cat|"))
async def cb_catalog(call: types.CallbackQuery):
    _, cat_key = call.data.split("|", 1)
    cat = shop.get(cat_key)
    if not cat:
        await call.answer("Категория не найдена", show_alert=True)
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for item_key, item in cat["items"].items():
        title = f"{item['title']} — {item['price']}{item.get('currency','')}"
        kb.inline_keyboard.append([InlineKeyboardButton(text=title, callback_data=f"item|{cat_key}|{item_key}")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="◀ Назад", callback_data="menu|catalog")])
    await call.message.edit_text(f"📂 Категория: {cat.get('title')}", reply_markup=kb)
    await call.answer()

@dp.callback_query(lambda c: c.data and c.data.startswith("item|"))
async def cb_item(call: types.CallbackQuery):
    _, cat_key, item_key = call.data.split("|", 2)
    item = get_item(cat_key, item_key)
    if not item:
        await call.answer("Товар не найден", show_alert=True)
        return
    stock = "∞" if item.get("type") not in ["secret", "manual"] else len(item.get("secrets", []))
    text = f"📄 {item['title']}\n💰 Цена: {item['price']}{item.get('currency','')}\n📦 В наличии: {stock}"
    if item.get("type") == "manual":
        manuals = item.get("manuals", [])
        if manuals:
            text += "\n\n📚 Список мануалов:\n" + "\n".join(f"- {name}" for name in manuals)
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    kb.inline_keyboard.append([InlineKeyboardButton(text="✅ Купить", callback_data=f"confirm_buy|{cat_key}|{item_key}")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="◀ Назад", callback_data=f"cat|{cat_key}")])
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()

@dp.callback_query(lambda c: c.data and c.data.startswith("confirm_buy|"))
async def cb_confirm_buy(call: types.CallbackQuery):
    _, cat_key, item_key = call.data.split("|", 2)
    item = get_item(cat_key, item_key)
    if not item:
        await call.answer("Товар не найден", show_alert=True)
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    kb.inline_keyboard.append([InlineKeyboardButton(text="Да, купить", callback_data=f"buy|{cat_key}|{item_key}")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="Отмена", callback_data=f"cat|{cat_key}")])
    await call.message.edit_text(
        f"Вы уверены, что хотите купить?\n\n{item['title']} — {item['price']}{item.get('currency','')}",
        reply_markup=kb
    )
    await call.answer()

@dp.callback_query(lambda c: c.data and c.data.startswith("buy|"))
async def cb_buy(call: types.CallbackQuery, state: FSMContext):
    user = call.from_user
    _, cat_key, item_key = call.data.split("|", 2)
    item = get_item(cat_key, item_key)
    if not item:
        await call.answer("Ошибка", show_alert=True)
        return

    order_id = str(uuid.uuid4())[:8]
    order = {
        "id": order_id,
        "user_id": user.id,
        "username": user.username or "",
        "cat": cat_key,
        "item": item_key,
        "price": item["price"],
        "currency": item.get("currency", "USD"),
        "type": item.get("type", "secret"),
        "status": "pending",
        "target_username": "",
        "secret": None,
    }
    try:
        save_order(order)
    except Exception:
        log_error("Failed to save new order", exc_info=True)
        await call.answer("Ошибка при создании заказа. Попробуйте позже.", show_alert=True)
        return

    if order["type"] in ["stars", "premium"]:
        order["status"] = "waiting_username"
        save_order(order)
        await state.set_state(OrderStates.waiting_for_username)
        await state.update_data(order_id=order_id)
        await call.message.answer(
            "Введите @username пользователя, которому нужно доставить товар.\n"
            "Внимание: проверьте username: возврата не делается при неверном username."
        )
        await call.answer("Введите имя пользователя для доставки.", show_alert=True)
        return

    pay_instructions = (
        f"🧾 Заказ: `{order_id}`\n"
        f"📦 Товар: {item['title']}\n"
        f"💵 Сумма: {item['price']}{item.get('currency','')}\n\n"
        "Оплатите через ваш метод (карта/Qiwi/crypto). После оплаты нажмите «Оплатил(а)'."
    )
    kb = mk_buttons([(f"paid|{order_id}", "Оплатил(а)")], back_to="menu|main")
    await call.message.answer(pay_instructions, reply_markup=kb, parse_mode="Markdown")
    await call.answer("Создан заказ. Следуйте инструкциям для оплаты.", show_alert=True)

    for aid in ADMIN_IDS:
        try:
            await bot.send_message(
                aid,
                f"🆕 Новый заказ `{order_id}` от @{order['username'] or order['user_id']}\n"
                f"📦 {item['title']}\n"
                f"💰 {order['price']}{order['currency']}"
            )
        except Exception:
            log_error(f"Failed to notify admin {aid} about order {order_id}", exc_info=True)

@dp.message(StateFilter(OrderStates.waiting_for_username), lambda message: message.content_type == types.ContentType.TEXT)
async def handle_target_username(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    order_id = data.get("order_id")
    if not order_id:
        await msg.reply("Не удалось найти заказ. Попробуйте снова.")
        await state.set_state(None)
        await state.set_data({})
        return

    order = get_order(order_id)
    if not order:
        await msg.reply("Заказ не найден.")
        await state.set_state(None)
        await state.set_data({})
        return

    username = msg.text.strip()
    if not username.startswith("@") or len(username) < 2:
        await msg.reply("Введите действительный @username. Пример: @username")
        return

    username = username.lstrip("@")
    order["target_username"] = username
    order["status"] = "pending"
    save_order(order)
    await state.set_state(None)
    await state.set_data({})

    item = get_item(order["cat"], order["item"])
    if not item:
        await msg.answer("Товар не найден в каталоге.")
        return

    if order["type"] in ["stars", "premium"] and PROVIDER_TOKEN:
        try:
            await send_invoice_for_order(order, item, msg.from_user.id)
            await msg.answer("Инвойс отправлен. Оплатите через Telegram.")
        except Exception as e:
            order["status"] = "error"
            save_order(order)
            log_error(f"Failed to create invoice for order {order_id}", exc_info=True)
            await msg.answer(f"Ошибка создания платежа: {e}")
            return
    else:
        pay_instructions = (
            f"🧾 Заказ: `{order_id}`\n"
            f"📦 Товар: {item['title']}\n"
            f"💵 Сумма: {item['price']}{item.get('currency','')}\n"
            f"👤 Доставить: `{username}`\n\n"
            "Оплатите через ваш метод (карта/Qiwi/crypto). После оплаты нажмите «Оплатил(а)».\n"
            "Возврат не делается при неверном username."
        )
        kb = mk_buttons([(f"paid|{order_id}", "Оплатил(а)")], back_to="menu|main")
        await msg.answer(pay_instructions, reply_markup=kb, parse_mode="Markdown")

    for aid in ADMIN_IDS:
        try:
            await bot.send_message(
                aid,
                f"🆕 Новый заказ `{order_id}` от @{order['username'] or order['user_id']}\n"
                f"📦 {item['title']}\n"
                f"💰 {order['price']}{order['currency']}\n"
                f"👤 Доставить: {order['target_username']}"
            )
        except Exception:
            log_error(f"Failed to notify admin {aid} about order {order_id}", exc_info=True)

@dp.pre_checkout_query(lambda q: True)
async def process_pre_checkout_query(pre_checkout_q: types.PreCheckoutQuery):
    try:
        await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)
    except Exception:
        pass

@dp.message(lambda message: message.content_type == types.ContentType.SUCCESSFUL_PAYMENT)
async def process_payment(msg: types.Message):
    payload = msg.successful_payment.invoice_payload
    order = get_order(payload)
    if not order:
        await msg.reply("Заказ не найден")
        return
    order["status"] = "paid"
    save_order(order)
    item = get_item(order["cat"], order["item"])
    if item and order["type"] == "stars":
        await msg.answer(f"✅ Спасибо за покупку! Вы получили {item.get('stars',1)} Telegram Stars (заказ `{payload}`).")
    for aid in ADMIN_IDS:
        try:
            await bot.send_message(
                aid,
                f"✅ Платеж получен\nЗаказ: `{payload}`\nПользователь: @{order.get('username')}\n"
                f"Товар: {item['title'] if item else order.get('item')}\n"
                f"Статус: {order['status']}\n"
                f"Используйте /deliver {payload} если требуется выдача."
            )
        except Exception:
            log_error(f"Failed to notify admin {aid} about payment for order {payload}", exc_info=True)

@dp.callback_query(lambda c: c.data and c.data.startswith("paid|"))
async def cb_paid(call: types.CallbackQuery):
    _, order_id = call.data.split("|", 1)
    order = get_order(order_id)
    if not order:
        await call.answer("Заказ не найден", show_alert=True)
        return
    if order["status"] in ["paid", "delivered"]:
        await call.answer("Заказ уже помечен как оплаченный.", show_alert=True)
        return
    order = update_order(order_id, {"status": "paid"})
    if not order:
        await call.answer("Не удалось обновить заказ.", show_alert=True)
        return
    item = get_item(order["cat"], order["item"])
    for aid in ADMIN_IDS:
        try:
            await bot.send_message(
                aid,
                f"✅ Оплата подтверждена для заказа `{order_id}`.\n"
                f"Пользователь: @{order.get('username')}\n"
                f"Товар: {item['title'] if item else order.get('item')}\n"
                f"Доставить: {order.get('target_username') or order.get('username')}"
            )
        except Exception:
            log_error(f"Failed to notify admin {aid} about paid order {order_id}", exc_info=True)
    await call.answer("Оплата помечена как оплаченная. Ожидайте выдачи.", show_alert=True)

@dp.message(Command("orders"))
async def cmd_orders(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        await msg.reply("❌ Доступ только администраторам.")
        return
    all_orders = get_all_orders()
    if not all_orders:
        await msg.reply("📭 Нет заказов.")
        return
    lines = [
        f"{o.get('id')}: {o.get('cat')}/{o.get('item')} @{o.get('username')} • {o.get('status')} • {o.get('target_username','')}"
        for o in all_orders[:20]
    ]
    await msg.reply(f"📄 Последние {len(lines)} заказов из {len(all_orders)}:\n" + "\n".join(lines))

@dp.message(Command("errors"))
async def cmd_errors(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        await msg.reply("❌ Доступ только администраторам.")
        return
    parts = msg.text.split(maxsplit=1)
    full = len(parts) > 1 and parts[1].strip().lower() == "full"
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, created_at, message, traceback FROM error_logs ORDER BY id DESC LIMIT 20"
        )
        rows = cursor.fetchall()
    if not rows:
        await msg.reply("✅ Ошибок не найдено.")
        return
    messages = []
    for log_id, created_at, message_text, traceback_text in rows:
        if full and traceback_text:
            messages.append(f"{log_id} {created_at}\n{message_text}\n{traceback_text}")
        else:
            snippet = message_text.replace("\n", " ")
            if traceback_text:
                trace_line = traceback_text.splitlines()[0]
                messages.append(f"{log_id} {created_at}: {snippet} — {trace_line}")
            else:
                messages.append(f"{log_id} {created_at}: {snippet}")
    await msg.reply("\n\n".join(messages))

@dp.message(Command("deliver"))
async def cmd_deliver(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        await msg.reply("❌ Только админам.")
        return
    parts = msg.text.split()
    if len(parts) < 2:
        await msg.reply("Использование: /deliver <order_id>")
        return
    oid = parts[1]
    order = get_order(oid)
    if not order:
        await msg.reply("❌ Заказ не найден.")
        return
    item = get_item(order["cat"], order["item"])
    if not item:
        await msg.reply("❌ Товар не найден в каталоге.")
        return
    if item.get("type") in ["secret", "manual", "premium"]:
        if not item.get("secrets"):
            await msg.reply("❌ Нет секретов в наличии. Добавьте через /addsecret или выдайте вручную.")
            return
        secret = item["secrets"].pop(0)
        save_shop()
        target = get_chat_id(order)
        try:
            await send_order_message(
                target,
                f"🎉 Ваш заказ `{oid}` выполнен!\n📦 {item['title']}\n🔑 Данные:\n`{secret}`"
            )
            order = update_order(oid, {"status": "delivered", "secret": secret})
            await msg.reply(f"✅ Выдано {oid} -> {secret}")
        except Exception as e:
            log_error(f"Failed to deliver order {oid} to user", exc_info=True)
            await msg.reply(f"⚠️ Не удалось отправить пользователю: {e}\nЗаказ остался в статусе {order.get('status') if order else 'unknown'}.")
    else:
        order = update_order(oid, {"status": "delivered"})
        target = get_chat_id(order)
        try:
            await send_order_message(target, f"🎉 Ваш заказ `{oid}` выполнен!\n📦 {item['title']}")
        except Exception:
            log_error(f"Failed to send delivery confirmation for order {oid}", exc_info=True)
        await msg.reply(f"✅ Заказ {oid} помечен как выданный.")

@dp.message(Command("addproduct"))
async def cmd_addproduct(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        await msg.reply("❌ Только админам.")
        return
    parts = msg.text.split(maxsplit=6)
    if len(parts) < 7:
        await msg.reply("Использование: /addproduct <категория> <item_key> <type> <price> <currency> <title>")
        return
    _, cat, item_key, item_type, price, currency, title = parts
    try:
        price = float(price)
    except ValueError:
        await msg.reply("Цена должна быть числом.")
        return
    if cat not in shop:
        shop[cat] = {"title": cat.capitalize(), "items": {}}
    new_item = {"title": title, "price": price, "currency": currency, "type": item_type}
    if item_type in ["secret", "premium", "manual"]:
        new_item["secrets"] = []
    if item_type == "manual":
        new_item["manuals"] = []
    if item_type == "stars":
        new_item["stars"] = int(price)
    shop[cat]["items"][item_key] = new_item
    save_shop()
    await msg.reply(f"✅ Товар {item_key} добавлен в категорию {cat}.")

@dp.message(Command("addsecret"))
async def cmd_addsecret(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        await msg.reply("❌ Только админам.")
        return
    parts = msg.text.split(maxsplit=3)
    if len(parts) < 4:
        await msg.reply("Использование: /addsecret <категория> <item_key> <secret>")
        return
    _, cat, item_key, secret = parts
    item = get_item(cat, item_key)
    if not item:
        await msg.reply("❌ Товар не найден.")
        return
    item.setdefault("secrets", []).append(secret)
    save_shop()
    await msg.reply("✅ Секрет добавлен.")

@dp.message(Command("addmanuals"))
async def cmd_addmanuals(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        await msg.reply("❌ Только админам.")
        return
    parts = msg.text.split(maxsplit=3)
    if len(parts) < 4:
        await msg.reply("Использование: /addmanuals <категория> <item_key> <manual1;manual2;...>")
        return
    _, cat, item_key, manuals_text = parts
    item = get_item(cat, item_key)
    if not item or item.get("type") != "manual":
        await msg.reply("❌ Мануал не найден или товар не является типом manual.")
        return
    manuals = [x.strip() for x in manuals_text.split(";") if x.strip()]
    item.setdefault("manuals", []).extend(manuals)
    save_shop()
    await msg.reply("✅ Названия мануалов добавлены.")

@dp.message(Command("ping"))
async def cmd_ping(msg: types.Message):
    await msg.reply("pong")

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    init_db()
    asyncio.run(main())