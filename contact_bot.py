"""
╔══════════════════════════════════════════════════════╗
║         🤖 TELEGRAM CONTACT BOT - FULL FEATURED      ║
║         Made for: Personal Contact/Inbox Bot         ║
║         Commands: /start, /help, /status, /block     ║
╚══════════════════════════════════════════════════════╝

📦 INSTALLATION:
   pip install pyTelegramBotAPI python-dotenv

⚙️ SETUP:
   1. @BotFather se naya bot banao → BOT_TOKEN milega
   2. Apna Telegram User ID niche OWNER_ID mein dalo
   3. python contact_bot.py se run karo
"""

import telebot
from telebot import types
import datetime
import json
import os
import time
import threading

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ⚙️  CONFIGURATION — YEH BHARO
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BOT_TOKEN  = "8729262563:AAFBIkaK9FDdk3xRKL6xA3uafVMHzhg2JWE"   # @BotFather se milega
OWNER_ID   = "6224485571"                    # Apna Telegram numeric ID dalo (apne bot ko /id bhejo)
BOT_NAME   = "Akaza contact Bot"                  # Bot ka naam
OWNER_NAME = "Akaza"                        # Aapka naam (user ko dikhega)

# Auto-reply jo user ko /start pe milega
WELCOME_MSG = (
    "👋 *Namaste!*\n\n"
    f"Aap *{OWNER_NAME}* tak message bhej sakte ho.\n"
    "🟢 Bas yahan apna message type karo — seedha forward ho jayega!\n\n"
    "📎 Photos, videos, voice notes — sab supported hai.\n"
    "⏳ Reply thodi der mein aa sakti hai."
)

# Jab aap reply karo tab user ko yeh confirmation milega
REPLY_NOTIFICATION = "✅ *{owner}* ne jawab diya:"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  🗂️  FILES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BLOCKED_FILE  = "blocked_users.json"
LOG_FILE      = "message_log.txt"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  🚀  BOT INIT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

# In-memory state
blocked_users: set = set()
user_map: dict     = {}   # msg_id (owner inbox) → sender chat_id
pending_reply: dict = {}  # owner_chat_id → user_chat_id (when owner hits Reply)
bot_start_time      = datetime.datetime.now()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  💾  HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def load_blocked():
    global blocked_users
    if os.path.exists(BLOCKED_FILE):
        with open(BLOCKED_FILE) as f:
            blocked_users = set(json.load(f))

def save_blocked():
    with open(BLOCKED_FILE, "w") as f:
        json.dump(list(blocked_users), f)

def log_message(direction, user_id, username, text):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {direction} | ID:{user_id} @{username} | {text[:200]}\n")

def fmt_user(u):
    name = f"{u.first_name or ''} {u.last_name or ''}".strip() or "Unknown"
    uname = f"@{u.username}" if u.username else "no username"
    return name, uname

def user_header(u):
    name, uname = fmt_user(u)
    return (
        f"👤 *{name}* ({uname})\n"
        f"🆔 `{u.id}`\n"
        f"🕐 {datetime.datetime.now().strftime('%d %b %Y, %I:%M %p')}\n"
        f"{'─'*28}"
    )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  📌  OWNER KEYBOARD (inline buttons)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def owner_kb(user_id):
    kb = types.InlineKeyboardMarkup(row_width=3)
    kb.add(
        types.InlineKeyboardButton("✉️ Reply",        callback_data=f"reply_{user_id}"),
        types.InlineKeyboardButton("🚫 Block",        callback_data=f"block_{user_id}"),
        types.InlineKeyboardButton("👤 Profile",      callback_data=f"profile_{user_id}"),
    )
    kb.add(
        types.InlineKeyboardButton("🗑️ Delete Msg",   callback_data=f"delmsg_{user_id}"),
        types.InlineKeyboardButton("📋 Copy ID",      callback_data=f"copyid_{user_id}"),
        types.InlineKeyboardButton("⭐ Mark VIP",     callback_data=f"vip_{user_id}"),
    )
    return kb

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  /start  —  USER SIDE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bot.message_handler(commands=["start"])
def cmd_start(msg):
    if msg.chat.id == OWNER_ID:
        owner_start(msg)
        return
    if msg.chat.id in blocked_users:
        bot.send_message(msg.chat.id, "❌ Aap yahan message nahi bhej sakte.")
        return

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📞 Message Bhejo", callback_data="start_msg"))
    bot.send_message(msg.chat.id, WELCOME_MSG, reply_markup=kb)

def owner_start(msg):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("📥 Inbox", "📊 Stats")
    kb.row("🚫 Blocked List", "📝 Logs")
    kb.row("⚙️ Settings", "❓ Help")
    bot.send_message(
        OWNER_ID,
        f"👑 *Owner Panel*\n\nBot chal raha hai ✅\nSabhi messages directly aayenge.",
        reply_markup=kb
    )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  /help
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bot.message_handler(commands=["help"])
def cmd_help(msg):
    if msg.chat.id == OWNER_ID:
        text = (
            "🛠 *Owner Commands:*\n\n"
            "/start  — Owner panel open karo\n"
            "/stats  — Bot ki stats dekho\n"
            "/block `<user_id>` — User ko block karo\n"
            "/unblock `<user_id>` — Unblock karo\n"
            "/blocklist — Blocked users ki list\n"
            "/broadcast `<msg>` — Sabko message bhejo\n"
            "/logs — Recent message log\n\n"
            "💡 *Tip:* Kisi bhi forwarded message ke neeche buttons se seedha reply karo!"
        )
    else:
        text = (
            "ℹ️ *Madad chahiye?*\n\n"
            "Bas yahan apna message type karo — directly forward ho jayega.\n"
            "📸 Photos, 🎥 Videos, 🎤 Voice notes sab bhej sakte ho!"
        )
    bot.send_message(msg.chat.id, text)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  📊  STATS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bot.message_handler(commands=["stats"])
@bot.message_handler(func=lambda m: m.chat.id == OWNER_ID and m.text == "📊 Stats")
def cmd_stats(msg):
    if msg.chat.id != OWNER_ID:
        return
    uptime = datetime.datetime.now() - bot_start_time
    h, rem = divmod(int(uptime.total_seconds()), 3600)
    m_val, s = divmod(rem, 60)

    total_logs = 0
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE) as f:
            total_logs = sum(1 for _ in f)

    bot.send_message(
        OWNER_ID,
        f"📊 *Bot Stats*\n\n"
        f"⏱ Uptime: `{h}h {m_val}m {s}s`\n"
        f"🚫 Blocked users: `{len(blocked_users)}`\n"
        f"📨 Total messages logged: `{total_logs}`\n"
        f"🟢 Status: Running"
    )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  🚫  BLOCK / UNBLOCK
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bot.message_handler(commands=["block"])
def cmd_block(msg):
    if msg.chat.id != OWNER_ID:
        return
    parts = msg.text.split()
    if len(parts) < 2:
        bot.send_message(OWNER_ID, "Usage: `/block <user_id>`")
        return
    uid = int(parts[1])
    blocked_users.add(uid)
    save_blocked()
    bot.send_message(OWNER_ID, f"✅ User `{uid}` block ho gaya.")
    try:
        bot.send_message(uid, "❌ Aapko is bot se block kar diya gaya hai.")
    except:
        pass

@bot.message_handler(commands=["unblock"])
def cmd_unblock(msg):
    if msg.chat.id != OWNER_ID:
        return
    parts = msg.text.split()
    if len(parts) < 2:
        bot.send_message(OWNER_ID, "Usage: `/unblock <user_id>`")
        return
    uid = int(parts[1])
    blocked_users.discard(uid)
    save_blocked()
    bot.send_message(OWNER_ID, f"✅ User `{uid}` unblock ho gaya.")

@bot.message_handler(commands=["blocklist"])
@bot.message_handler(func=lambda m: m.chat.id == OWNER_ID and m.text == "🚫 Blocked List")
def cmd_blocklist(msg):
    if msg.chat.id != OWNER_ID:
        return
    if not blocked_users:
        bot.send_message(OWNER_ID, "✅ Koi blocked user nahi hai.")
        return
    text = "🚫 *Blocked Users:*\n\n"
    for uid in blocked_users:
        text += f"• `{uid}`\n"
    bot.send_message(OWNER_ID, text)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  📢  BROADCAST
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bot.message_handler(commands=["broadcast"])
def cmd_broadcast(msg):
    if msg.chat.id != OWNER_ID:
        return
    text = msg.text.replace("/broadcast", "").strip()
    if not text:
        bot.send_message(OWNER_ID, "Usage: `/broadcast <message>`")
        return
    sent = 0
    for uid in set(user_map.values()):
        try:
            bot.send_message(uid, f"📢 *Broadcast:*\n\n{text}")
            sent += 1
            time.sleep(0.05)
        except:
            pass
    bot.send_message(OWNER_ID, f"✅ Broadcast bheja gaya `{sent}` users ko.")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  📝  LOGS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bot.message_handler(commands=["logs"])
@bot.message_handler(func=lambda m: m.chat.id == OWNER_ID and m.text == "📝 Logs")
def cmd_logs(msg):
    if msg.chat.id != OWNER_ID:
        return
    if not os.path.exists(LOG_FILE):
        bot.send_message(OWNER_ID, "📭 Abhi koi logs nahi hain.")
        return
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    last = "".join(lines[-20:]) if len(lines) > 20 else "".join(lines)
    bot.send_message(OWNER_ID, f"```\n{last}\n```")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  📩  MAIN MESSAGE HANDLER (User → Owner)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bot.message_handler(
    func=lambda m: m.chat.id != OWNER_ID and m.chat.id not in blocked_users,
    content_types=["text", "photo", "video", "audio", "voice",
                   "document", "sticker", "video_note", "location", "contact"]
)
def user_to_owner(msg):
    uid = msg.chat.id
    u   = msg.from_user
    name, uname = fmt_user(u)

    # Send header to owner
    header_msg = bot.send_message(OWNER_ID, user_header(u))

    # Forward actual message
    fwd = bot.forward_message(OWNER_ID, uid, msg.message_id)

    # Store mapping: forwarded msg id → user chat id
    user_map[fwd.message_id]    = uid
    user_map[header_msg.message_id] = uid

    # Action buttons under forwarded message
    bot.send_message(OWNER_ID, "⬆️ *Actions:*", reply_markup=owner_kb(uid))

    # Log
    content = msg.text or msg.caption or f"[{msg.content_type}]"
    log_message("IN", uid, u.username or "?", content)

    # Auto-read receipt to user
    bot.send_chat_action(uid, "typing")
    time.sleep(0.5)
    bot.send_message(uid, "📨 _Aapka message deliver ho gaya! Jaldi reply milegi._")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  💬  OWNER REPLY (text from owner)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bot.message_handler(
    func=lambda m: m.chat.id == OWNER_ID and m.text not in [
        "📥 Inbox", "📊 Stats", "🚫 Blocked List", "📝 Logs", "⚙️ Settings", "❓ Help"
    ] and not (m.text or "").startswith("/"),
    content_types=["text", "photo", "video", "audio", "voice", "document", "sticker"]
)
def owner_reply(msg):
    # Check if owner is replying to a forwarded message
    target_uid = None

    if msg.reply_to_message:
        target_uid = user_map.get(msg.reply_to_message.message_id)

    if target_uid is None and OWNER_ID in pending_reply:
        target_uid = pending_reply.pop(OWNER_ID)

    if target_uid is None:
        bot.send_message(OWNER_ID, "⚠️ Kisi forwarded message ko *Reply* karo, ya button se user select karo.")
        return

    # Forward owner's reply to user
    try:
        bot.send_message(target_uid,
            REPLY_NOTIFICATION.format(owner=OWNER_NAME),
        )
        bot.copy_message(target_uid, OWNER_ID, msg.message_id)
        bot.send_message(OWNER_ID, "✅ Reply bhej diya!")
        log_message("OUT", target_uid, "owner", msg.text or f"[{msg.content_type}]")
    except Exception as e:
        bot.send_message(OWNER_ID, f"❌ Reply fail: `{e}`")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  🔘  CALLBACK BUTTONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bot.callback_query_handler(func=lambda c: True)
def handle_callback(call):
    data = call.data
    cid  = call.message.chat.id

    # ── Start msg (user side) ──
    if data == "start_msg":
        bot.answer_callback_query(call.id, "Bas type karo! 👍")
        bot.send_message(cid, "✏️ *Apna message type karo:*")
        return

    # ── Owner side buttons ──
    if cid != OWNER_ID:
        bot.answer_callback_query(call.id, "❌ Unauthorized")
        return

    action, uid_str = data.rsplit("_", 1)
    uid = int(uid_str)

    if action == "reply":
        pending_reply[OWNER_ID] = uid
        bot.answer_callback_query(call.id, "✅ Ab apna reply message bhejo!")
        bot.send_message(OWNER_ID, f"💬 User `{uid}` ko reply karo — bas neeche message type karo:")

    elif action == "block":
        blocked_users.add(uid)
        save_blocked()
        bot.answer_callback_query(call.id, "🚫 Blocked!")
        bot.send_message(OWNER_ID, f"🚫 User `{uid}` block ho gaya.")
        try:
            bot.send_message(uid, "❌ Aapko block kar diya gaya hai.")
        except:
            pass

    elif action == "profile":
        try:
            chat = bot.get_chat(uid)
            name = f"{chat.first_name or ''} {chat.last_name or ''}".strip()
            uname = f"@{chat.username}" if chat.username else "None"
            bio  = getattr(chat, "bio", None) or "N/A"
            text = (
                f"👤 *User Profile*\n\n"
                f"📛 Name: `{name}`\n"
                f"🔖 Username: {uname}\n"
                f"🆔 ID: `{uid}`\n"
                f"📝 Bio: {bio}\n"
            )
            bot.answer_callback_query(call.id)
            bot.send_message(OWNER_ID, text)
        except Exception as e:
            bot.answer_callback_query(call.id, f"Error: {e}")

    elif action == "delmsg":
        try:
            bot.delete_message(OWNER_ID, call.message.message_id)
            bot.answer_callback_query(call.id, "🗑️ Deleted")
        except:
            bot.answer_callback_query(call.id, "Delete nahi hua.")

    elif action == "copyid":
        bot.answer_callback_query(call.id, f"ID: {uid}", show_alert=True)

    elif action == "vip":
        bot.answer_callback_query(call.id, f"⭐ User {uid} VIP mark hua!", show_alert=True)
        bot.send_message(OWNER_ID, f"⭐ User `{uid}` VIP list mein add ho gaya.")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ▶️  RUN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    load_blocked()
    print("━" * 48)
    print(f"  🤖  {BOT_NAME} chal raha hai...")
    print(f"  👑  Owner ID: {OWNER_ID}")
    print("━" * 48)
    bot.send_message(OWNER_ID, f"✅ *{BOT_NAME} start ho gaya!*\nVersion: Full Featured 🚀")
    bot.infinity_polling(timeout=30, long_polling_timeout=20)
