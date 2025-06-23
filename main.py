import telebot
import os
import json
from telebot.types import Message, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = "8104357530:AAFJUcAoAsMqdfATENXb93yqupPT5X2QOpg"
OWNER_ID = 580123456  # Replace with your Telegram ID
DATA_FOLDER = "data"
FILES_FOLDER = "files"
USER_DATA_FILE = os.path.join(DATA_FOLDER, "users.json")
THEME_DEFAULT = "light"

if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)
if not os.path.exists(FILES_FOLDER):
    os.makedirs(FILES_FOLDER)
if not os.path.exists(USER_DATA_FILE):
    with open(USER_DATA_FILE, "w") as f:
        json.dump({}, f)

bot = telebot.TeleBot(BOT_TOKEN)

def load_users():
    with open(USER_DATA_FILE, "r") as f:
        return json.load(f)

def save_users(data):
    with open(USER_DATA_FILE, "w") as f:
        json.dump(data, f)

def get_user(uid):
    users = load_users()
    return users.get(str(uid), {})

def is_logged_in(uid):
    return str(uid) in load_users()

def is_verified(uid, field):
    return get_user(uid).get(field, False)

@bot.message_handler(commands=['start'])
def start(message):
    uid = str(message.from_user.id)
    users = load_users()
    if uid in users:
        send_home(message)
    else:
        bot.send_message(message.chat.id, "🔐 প্রথমবার ব্যবহারের জন্য একটি পাসওয়ার্ড লিখুন:")

@bot.message_handler(commands=['setpass'])
def setpass(message):
    if message.from_user.id != OWNER_ID:
        return bot.reply_to(message, "❌ অনুমতি নেই।")
    parts = message.text.split(maxsplit=1)
    if len(parts) != 2:
        return bot.reply_to(message, "🛡️ উদাহরণ: /setpass mypassword")
    with open(os.path.join(DATA_FOLDER, "password.txt"), "w") as f:
        f.write(parts[1].strip())
    bot.reply_to(message, "✅ পাসওয়ার্ড সেট হয়েছে।")

@bot.message_handler(commands=['logout'])
def logout(message):
    uid = str(message.from_user.id)
    users = load_users()
    if uid in users:
        del users[uid]
        save_users(users)
        bot.reply_to(message, "🚪 লগআউট সম্পন্ন হয়েছে।")

@bot.message_handler(commands=['theme'])
def theme(message):
    if not is_logged_in(message.from_user.id):
        return bot.reply_to(message, "🔐 আগে লগইন করুন।")
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🌞 Light", callback_data="theme:light"),
        InlineKeyboardButton("🌙 Dark", callback_data="theme:dark")
    )
    bot.send_message(message.chat.id, "🎨 থিম নির্বাচন করুন:", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("theme:"))
def set_theme(call):
    theme = call.data.split(":")[1]
    uid = str(call.from_user.id)
    users = load_users()
    if uid not in users:
        users[uid] = {}
    users[uid]["theme"] = theme
    save_users(users)
    bot.edit_message_text(f"✅ থিম সেট হয়েছে: {theme.upper()}", call.message.chat.id, call.message.message_id)
    send_home(call.message)

def send_home(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📤 Upload", "📂 My Files")
    markup.row("✏️ Rename", "🗑️ Delete")
    bot.send_message(message.chat.id, "🏠 হোমে স্বাগতম!", reply_markup=markup)

@bot.message_handler(func=lambda msg: True, content_types=['text', 'document'])
def handle_all(message):
    uid = str(message.from_user.id)
    users = load_users()

    # Not logged in yet
    if not is_logged_in(uid):
        pwfile = os.path.join(DATA_FOLDER, "password.txt")
        if os.path.exists(pwfile):
            with open(pwfile) as f:
                if message.text.strip() == f.read().strip():
                    users[uid] = {"theme": THEME_DEFAULT}
                    save_users(users)
                    return bot.send_message(message.chat.id, "✅ লগইন সফল!
/start দিয়ে শুরু করুন।")
        return bot.send_message(message.chat.id, "❌ ভুল পাসওয়ার্ড।")

    # Handle commands
    text = message.text
    if text == "📤 Upload":
        bot.send_message(message.chat.id, "📎 শুধু ফাইল পাঠান, চাইলে ক্যাপশন দিয়ে ক্যাটাগরি দিন।")
    elif text == "📂 My Files":
        if not is_verified(uid, "auth_files"):
            return ask_auth(message, "auth_files", "📂 My Files")
        return show_files(message)
    elif text == "✏️ Rename":
        if not is_verified(uid, "auth_rename"):
            return ask_auth(message, "auth_rename", "✏️ Rename")
        return bot.send_message(message.chat.id, "✏️ উদাহরণ: /rename old.txt new.txt")
    elif text == "🗑️ Delete":
        if not is_verified(uid, "auth_delete"):
            return ask_auth(message, "auth_delete", "🗑️ Delete")
        return bot.send_message(message.chat.id, "🗑️ উদাহরণ: /delete filename.txt")
    elif text.startswith("/rename"):
        if not is_verified(uid, "auth_rename"):
            return ask_auth(message, "auth_rename", "/rename")
        parts = text.split(maxsplit=2)
        if len(parts) == 3:
            rename_file(message, parts[1], parts[2])
    elif text.startswith("/delete"):
        if not is_verified(uid, "auth_delete"):
            return ask_auth(message, "auth_delete", "/delete")
        delete_file(message, text.split(maxsplit=1)[1])
    elif message.document:
        save_doc(message)

def ask_auth(message, field, cmd):
    bot.send_message(message.chat.id, f"🔐 {cmd} ব্যবহারের জন্য আবার পাসওয়ার্ড দিন:")
    bot.register_next_step_handler(message, check_subpass, field, cmd)

def check_subpass(message, field, cmd):
    uid = str(message.from_user.id)
    pwfile = os.path.join(DATA_FOLDER, "password.txt")
    if os.path.exists(pwfile):
        with open(pwfile) as f:
            if message.text.strip() == f.read().strip():
                users = load_users()
                if uid not in users:
                    users[uid] = {}
                users[uid][field] = True
                save_users(users)
                bot.send_message(message.chat.id, f"✅ অনুমতি দেওয়া হয়েছে: {cmd}")
                return
    bot.send_message(message.chat.id, "❌ ভুল পাসওয়ার্ড।")

def save_doc(message):
    category = message.caption.strip() if message.caption else "uncategorized"
    path = os.path.join(FILES_FOLDER, category)
    os.makedirs(path, exist_ok=True)
    file_path = os.path.join(path, message.document.file_name)
    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    with open(file_path, "wb") as f:
        f.write(downloaded_file)
    bot.reply_to(message, f"✅ ফাইল আপলোড হয়েছে: {message.document.file_name}")

def show_files(message):
    reply = ""
    for cat in os.listdir(FILES_FOLDER):
        files = os.listdir(os.path.join(FILES_FOLDER, cat))
        if files:
            reply += f"
📁 {cat}:
" + "\n".join(f"• {f}" for f in files)
    if reply:
        bot.send_message(message.chat.id, reply)
    else:
        bot.send_message(message.chat.id, "📂 কোনো ফাইল নেই।")

def rename_file(message, old, new):
    for root, _, files in os.walk(FILES_FOLDER):
        if old in files:
            os.rename(os.path.join(root, old), os.path.join(root, new))
            bot.reply_to(message, "✅ রিনেম সফল")
            return
    bot.reply_to(message, "❌ ফাইল পাওয়া যায়নি।")

def delete_file(message, filename):
    for root, _, files in os.walk(FILES_FOLDER):
        if filename in files:
            os.remove(os.path.join(root, filename))
            bot.reply_to(message, "🗑️ ফাইল ডিলিট করা হয়েছে।")
            return
    bot.reply_to(message, "❌ ফাইল খুঁজে পাওয়া যায়নি।")

bot.infinity_polling()
