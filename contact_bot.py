import telebot
from telebot import types
import datetime
import json
import os
import time

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ⚙️  CONFIGURATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BOT_TOKEN  = "8729262563:AAFBIkaK9FDdk3xRKL6xA3uafVMHzhg2JWE"
OWNER_ID   = 6224485571          # ✅ INTEGER — quotes nahi!
BOT_NAME   = "Akaza Contact Bot"
OWNER_NAME = "Akaza"

WELCOME_MSG = (
    "👋 *Namaste!*\n\n"
    f"Aap *{OWNER_NAME}* tak message bhej sakte ho.\n"
    "🟢 Bas yahan apna message type karo — seedha forward ho jayega!\n\n"
    "📎 Photos, videos, voice notes — sab supported hai.\n"
    "⏳ Reply thodi der mein aa sakti hai."
)

REPLY_NOTIFICATION = "✅ *{owner}* ne jawab diya:"

BLOCKED_FILE = "blocked_users.json"
LOG_FILE     = "message_log.txt"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  🚀  BOT INIT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

blocked_users: set  = set()
user_map: dict      = {}
pending_reply: dict = {}
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
    name  = f"{u.first_name or ''} {u.last_name or ''}".strip() or "Unknown"
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

def owner_kb(user_id):
    kb = types.InlineKeyboardMarkup(row_width=3)
    kb.add(
        types.InlineKeyboardButton("✉️ Reply",    callback_data=f"reply_{user_id}"),
        types.InlineKeyboardButton("🚫 Block",    callback_data=f"block_{user_id}"),
        types.InlineKeyboardButton("👤 Profile",  callback_data=f"profile_{user_id}"),
    )
    kb.add(
        types.InlineKeyboardButton("🗑️ Delete",   callback_data=f"delmsg_{user_id}"),
        types.InlineKeyboardButton("📋 Copy ID",  callback_data=f"copyid_{user_id}"),
        types.InlineKeyboardButton("⭐ VIP",      callback_data=f"vip_{user_id}"),
    )
    return kb

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  /start
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bot.message_handler(commands=["start"])
def cmd_start(msg):
    if msg.chat.id == OWNER_ID:
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row("📊 Stats", "🚫 Blocked List")
        kb.row("📝 Logs", "❓ Help")
        bot.send_message(OWNER_ID,
            f"👑 *Owner Panel Active!*\n\nBot chal raha hai ✅\nSabhi messages directly aayenge.",
            reply_markup=kb)
        return

    if msg.chat.id in blocked_users:
        bot.send_message(msg.chat.id, "❌ Aap yahan message nahi bhej sakte.")
        return

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📞 Message Bhejo", callback_data="start_msg"))
    bot.send_message(msg.chat.id, WELCOME_MSG, reply_markup=kb)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  /help
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bot.message_handler(commands=["help"])
def cmd_help(msg):
    if msg.chat.id == OWNER_ID:
        bot.send_message(OWNER_ID,
            "🛠 *Owner Commands:*\n\n"
            "/stats — Bot stats\n"
            "/block `<id>` — Block user\n"
            "/unblock `<id>` — Unblock user\n"
            "/blocklist — Blocked list\n"
            "/broadcast `<msg>` — Sabko bhejo\n"
            "/logs — Recent logs\n\n"
            "💡 Forwarded message pe Reply karo — seedha user tak jayega!"
        )
    else:
        bot.send_message(msg.chat.id,
            "ℹ️ Bas apna message type karo — directly forward ho jayega!\n"
            "📸 Photos, 🎥 Videos, 🎤 Voice — sab supported."
        )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  /stats
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bot.message_handler(commands=["stats"])
@bot.message_handler(func=lambda m: m.chat.id == OWNER_ID and m.text == "📊 Stats")
def cmd_stats(msg):
    if msg.chat.id != OWNER_ID:
        return
    uptime = datetime.datetime.now() - bot_start_time
    h, rem = divmod(int(uptime.total_seconds()), 3600)
    mv, s  = divmod(rem, 60)
    logs   = sum(1 for _ in open(LOG_FILE)) if os.path.exists(LOG_FILE) else 0
    bot.send_message(OWNER_ID,
        f"📊 *Stats*\n\n"
        f"⏱ Uptime: `{h}h {mv}m {s}s`\n"
        f"🚫 Blocked: `{len(blocked_users)}`\n"
        f"📨 Messages logged: `{logs}`\n"
        f"🟢 Status: Running"
    )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  BLOCK / UNBLOCK / BLOCKLIST
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bot.message_handler(commands=["block"])
def cmd_block(msg):
    if msg.chat.id != OWNER_ID:
        return
    parts = msg.text.split()
    if len(parts) < 2:
        bot.send_message(OWNER_ID, "Usage: `/block <user_id>`"); return
    uid = int(parts[1])
    blocked_users.add(uid); save_blocked()
    bot.send_message(OWNER_ID, f"✅ `{uid}` block ho gaya.")
    try: bot.send_message(uid, "❌ Aapko block kar diya gaya.")
    except: pass

@bot.message_handler(commands=["unblock"])
def cmd_unblock(msg):
    if msg.chat.id != OWNER_ID:
        return
    parts = msg.text.split()
    if len(parts) < 2:
        bot.send_message(OWNER_ID, "Usage: `/unblock <user_id>`"); return
    uid = int(parts[1])
    blocked_users.discard(uid); save_blocked()
    bot.send_message(OWNER_ID, f"✅ `{uid}` unblock ho gaya.")

@bot.message_handler(commands=["blocklist"])
@bot.message_handler(func=lambda m: m.chat.id == OWNER_ID and m.text == "🚫 Blocked List")
def cmd_blocklist(msg):
    if msg.chat.id != OWNER_ID:
        return
    if not blocked_users:
        bot.send_message(OWNER_ID, "✅ Koi blocked user nahi."); return
    bot.send_message(OWNER_ID, "🚫 *Blocked:*\n\n" + "\n".join(f"• `{u}`" for u in blocked_users))

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  /broadcast
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bot.message_handler(commands=["broadcast"])
def cmd_broadcast(msg):
    if msg.chat.id != OWNER_ID:
        return
    text = msg.text.replace("/broadcast", "").strip()
    if not text:
        bot.send_message(OWNER_ID, "Usage: `/broadcast <msg>`"); return
    sent = 0
    for uid in set(user_map.values()):
        try: bot.send_message(uid, f"📢 *Broadcast:*\n\n{text}"); sent += 1; time.sleep(0.05)
        except: pass
    bot.send_message(OWNER_ID, f"✅ `{sent}` users ko bheja.")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  /logs
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bot.message_handler(commands=["logs"])
@bot.message_handler(func=lambda m: m.chat.id == OWNER_ID and m.text == "📝 Logs")
def cmd_logs(msg):
    if msg.chat.id != OWNER_ID:
        return
    if not os.path.exists(LOG_FILE):
        bot.send_message(OWNER_ID, "📭 Koi logs nahi."); return
    with open(LOG_FILE, encoding="utf-8") as f:
        lines = f.readlines()
    last = "".join(lines[-20:])
    bot.send_message(OWNER_ID, f"```\n{last}\n```")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  📩  USER → OWNER  (main forwarder)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bot.message_handler(
    func=lambda m: m.chat.id != OWNER_ID and m.chat.id not in blocked_users,
    content_types=["text","photo","video","audio","voice",
                   "document","sticker","video_note","location","contact"]
)
def user_to_owner(msg):
    uid = msg.chat.id
    u   = msg.from_user

    # Header
    hdr = bot.send_message(OWNER_ID, user_header(u))
    # Forward
    fwd = bot.forward_message(OWNER_ID, uid, msg.message_id)
    # Action buttons
    bot.send_message(OWNER_ID, "⬆️ *Actions:*", reply_markup=owner_kb(uid))

    # Save mapping
    user_map[fwd.message_id] = uid
    user_map[hdr.message_id] = uid

    # Log
    content = msg.text or msg.caption or f"[{msg.content_type}]"
    log_message("IN", uid, u.username or "?", content)

    # Delivery receipt to user
    bot.send_chat_action(uid, "typing")
    time.sleep(0.5)
    bot.send_message(uid, "📨 _Message deliver ho gaya! Jaldi reply milegi._")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  💬  OWNER → USER  (reply)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bot.message_handler(
    func=lambda m: m.chat.id == OWNER_ID
        and m.text not in ["📊 Stats","🚫 Blocked List","📝 Logs","❓ Help"]
        and not (m.text or "").startswith("/"),
    content_types=["text","photo","video","audio","voice","document","sticker"]
)
def owner_reply(msg):
    target_uid = None

    if msg.reply_to_message:
        target_uid = user_map.get(msg.reply_to_message.message_id)

    if target_uid is None:
        target_uid = pending_reply.pop(OWNER_ID, None)

    if target_uid is None:
        bot.send_message(OWNER_ID,
            "⚠️ Kisi forwarded message ko *Reply* karo ya pehle ✉️ Reply button dabao.")
        return

    try:
        bot.send_message(target_uid, REPLY_NOTIFICATION.format(owner=OWNER_NAME))
        bot.copy_message(target_uid, OWNER_ID, msg.message_id)
        bot.send_message(OWNER_ID, "✅ Reply bhej diya!")
        log_message("OUT", target_uid, "owner", msg.text or f"[{msg.content_type}]")
    except Exception as e:
        bot.send_message(OWNER_ID, f"❌ Reply fail: `{e}`")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  🔘  CALLBACKS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bot.callback_query_handler(func=lambda c: True)
def handle_callback(call):
    data = call.data
    cid  = call.message.chat.id

    if data == "start_msg":
        bot.answer_callback_query(call.id, "Type karo! 👍")
        bot.send_message(cid, "✏️ *Apna message type karo:*")
        return

    if cid != OWNER_ID:
        bot.answer_callback_query(call.id, "❌ Unauthorized")
        return

    action, uid_str = data.rsplit("_", 1)
    uid = int(uid_str)

    if action == "reply":
        pending_reply[OWNER_ID] = uid
        bot.answer_callback_query(call.id, "Ab neeche reply type karo!")
        bot.send_message(OWNER_ID, f"💬 User `{uid}` ko reply karo — neeche type karo:")

    elif action == "block":
        blocked_users.add(uid); save_blocked()
        bot.answer_callback_query(call.id, "🚫 Blocked!")
        bot.send_message(OWNER_ID, f"🚫 User `{uid}` block ho gaya.")
        try: bot.send_message(uid, "❌ Aapko block kar diya gaya.")
        except: pass

    elif action == "profile":
        try:
            chat  = bot.get_chat(uid)
            name  = f"{chat.first_name or ''} {chat.last_name or ''}".strip()
            uname = f"@{chat.username}" if chat.username else "None"
            bio   = getattr(chat, "bio", None) or "N/A"
            bot.answer_callback_query(call.id)
            bot.send_message(OWNER_ID,
                f"👤 *Profile*\n\n📛 `{name}`\n🔖 {uname}\n🆔 `{uid}`\n📝 {bio}")
        except Exception as e:
            bot.answer_callback_query(call.id, f"Error: {e}", show_alert=True)

    elif action == "delmsg":
        try:
            bot.delete_message(OWNER_ID, call.message.message_id)
            bot.answer_callback_query(call.id, "🗑️ Deleted!")
        except:
            bot.answer_callback_query(call.id, "Delete nahi hua.")

    elif action == "copyid":
        bot.answer_callback_query(call.id, f"ID: {uid}", show_alert=True)

    elif action == "vip":
        bot.answer_callback_query(call.id, f"⭐ VIP mark ho gaya!", show_alert=True)
        bot.send_message(OWNER_ID, f"⭐ User `{uid}` VIP list mein add.")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ▶️  RUN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    load_blocked()
    print("━" * 40)
    print(f"  🤖  {BOT_NAME} starting...")
    print(f"  👑  Owner ID: {OWNER_ID}  (type: {type(OWNER_ID).__name__})")
    print("━" * 40)
    bot.send_message(OWNER_ID, f"✅ *{BOT_NAME} start ho gaya!* 🚀")
    bot.infinity_polling(timeout=30, long_polling_timeout=20)
