import sqlite3
import re
import base64
import random
import string
import time
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ================= CONFIG =================
API_ID = 19731848
API_HASH = "c9833f83810d4d3eacaa23373fb417db"
BOT_TOKEN = "8753327006:AAFND8qAmKN6o0VMyRjFLIvq9VLM4pUzX8I"
ADMINS = [1106857285]
RESULTS_PER_PAGE = 8
DB_FILE = "files.db"
WATERMARK_FILE = "watermark.txt"
PREFIX = "@ZlixOfficial"
BOT_USERNAME = "LordVT3Bot"  # without @
# ==========================================

def connect():
    return sqlite3.connect(DB_FILE, check_same_thread=False)


# ================= AUTO DELETE =================
async def auto_delete(msg, seconds=60):
    await asyncio.sleep(seconds)
    try:
        await msg.delete()
    except:
        pass


# ================= USERS =================
def add_user(user_id):
    conn = connect()
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)", (user_id,))
    conn.commit()
    conn.close()


def total_users():
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    count = cur.fetchone()[0]
    conn.close()
    return count


# ================= LOGS =================
def log_search(user_id, query):
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO logs(user_id,query,date) VALUES(?,?,?)",
        (user_id, query, int(time.time()))
    )
    conn.commit()
    conn.close()


def log_file(user_id, file_id):
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO logs(user_id,file_id,date) VALUES(?,?,?)",
        (user_id, file_id, int(time.time()))
    )
    conn.commit()
    conn.close()


# ================= SHORT LINKS =================
def generate_code():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))


def save_link(code, file_id):
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO links(code,file_id) VALUES(?,?)",
        (code, file_id)
    )
    conn.commit()
    conn.close()


def get_link(code):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT file_id FROM links WHERE code=?", (code,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


# ================= SEARCH =================
def search_files(keyword, limit, offset):
    conn = connect()
    cur = conn.cursor()

    keyword = re.sub(r"[^\w\s]", " ", keyword)
    keyword = re.sub(r"\s+", " ", keyword).strip()

    cur.execute("""
    SELECT files.id, files.file_name
    FROM files_fts
    JOIN files ON files_fts.rowid = files.id
    WHERE files_fts MATCH ?
    ORDER BY files.id DESC
    LIMIT ? OFFSET ?
    """, (keyword, limit, offset))

    rows = cur.fetchall()
    conn.close()
    return rows


def get_file(fid):
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT file_id,file_name,chat_id,message_id FROM files WHERE id=?",
        (fid,)
    )
    row = cur.fetchone()
    conn.close()
    return row


# ================= BOT =================
app = Client("ZLIX_FINAL_UI", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


def build_results(keyword, page, user):

    offset = page * RESULTS_PER_PAGE
    files = search_files(keyword, RESULTS_PER_PAGE, offset)

    if not files:
        return None

    buttons = []

    for fid, name in files:

        row = [
            InlineKeyboardButton(name[:40], callback_data=f"file_{fid}")
        ]

        # 🔐 ADMIN ONLY LINK
        if user and user.id in ADMINS:
            code = generate_code()
            save_link(code, fid)
            link = f"https://t.me/{BOT_USERNAME}?start=zlix_{code}"

            row.append(
                InlineKeyboardButton("🔗", url=link)
            )

        buttons.append(row)

    nav = []

    if page > 0:
        nav.append(
            InlineKeyboardButton("⬅️", callback_data=f"page_{keyword}_{page-1}")
        )

    if len(files) == RESULTS_PER_PAGE:
        nav.append(
            InlineKeyboardButton("➡️", callback_data=f"page_{keyword}_{page+1}")
        )

    if nav:
        buttons.append(nav)

    return InlineKeyboardMarkup(buttons)


# ================= START =================
@app.on_message(filters.command("start"))
async def start(client, message):

    add_user(message.from_user.id)

    args = message.text.split()

    # 🔗 DEEP LINK HANDLER
    if len(args) > 1:
        data = args[1]

        if data.startswith("zlix_"):
            fid = get_link(data.split("_")[1])
        else:
            try:
                fid = int(base64.b64decode(data).decode())
            except:
                fid = None

        if not fid:
            await message.reply("❌ Invalid link")
            return

        file = get_file(fid)

        if file:
            file_id, name, chat_id, msg_id = file
            #deep link sticker
            await client.send_sticker(
                message.chat.id,
                "CAACAgIAAxkBAAIBbGnJhTIFHudklVsWUAaZHXPFHfxJAAJNBwACRvusBP2GZcNkayxTHgQ"
            )
            #small delay
            await asyncio.sleep(0.5)

            await client.copy_message(
                message.chat.id,
                chat_id,
                msg_id
            )

            log_file(message.from_user.id, fid)

        return

    # 🎨 NORMAL START UI
    await client.send_sticker(
        message.chat.id,
        "CAACAgIAAxkBAAIBVWnJgUUPm8ktI4_7A_p9UGBSFS4uAAI-BwACRvusBK9cOl7BGYj2HgQYOUR_STICKER_ID"
    )

    msg = await message.reply(
        "✨ **Welcome to ZLIX Bot** ✨\n\n"
        "🎬 Search movies instantly\n"
        "⚡ Fast • Clean • Smart\n\n"
        "🔍 Example:\n"
        "`avengers 2019`"
    )

    await auto_delete(msg, 60)


# ================= SEARCH =================
@app.on_message(filters.private & filters.text & ~filters.regex(r"^/"))
async def search(client, message):

    add_user(message.from_user.id)

    keyword = message.text.strip()
    log_search(message.from_user.id, keyword)

    try:
        await message.delete()
    except:
        pass

    loading = await client.send_message(
        message.chat.id,
        "⏳ Searching..."
    )

    await asyncio.sleep(1)

    kb = build_results(keyword, 0, message.from_user)

    await loading.delete()

    if not kb:
        msg = await client.send_message(
            message.chat.id,
            "❌ No results found"
        )
        await auto_delete(msg, 20)
        return

    msg = await client.send_message(
        message.chat.id,
        f"🔎 **{keyword}**",
        reply_markup=kb
    )

    await auto_delete(msg, 120)


# ================= PAGINATION =================
@app.on_callback_query(filters.regex("^page_"))
async def pagination(client, query):

    _, keyword, page = query.data.split("_")

    kb = build_results(keyword, int(page), query.from_user)

    if kb:
        await query.message.edit_reply_markup(kb)


# ================= FILE SEND =================
@app.on_callback_query(filters.regex("^file_"))
async def send_file(client, query):

    fid = int(query.data.split("_")[1])

    file = get_file(fid)

    if not file:
        await query.answer("❌ Missing", show_alert=True)
        return

    file_id, name, chat_id, msg_id = file

    await query.answer("📥 Sending...")

    await client.copy_message(
        query.message.chat.id,
        chat_id,
        msg_id
    )

    log_file(query.from_user.id, fid)

#@app.on_message(filters.sticker)
#async def get_sticker(client, message):
#    print(message.sticker.file_id)

# ================= ADMIN =================
@app.on_message(filters.command("stats"))
async def stats(client, message):

    if message.from_user.id not in ADMINS:
        return

    conn = connect()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM files")
    files = cur.fetchone()[0]

    users = total_users()

    await message.reply(
        f"📊 Files: {files}\n👥 Users: {users}"
    )


@app.on_message(filters.command("broadcast"))
async def broadcast(client, message):

    if message.from_user.id not in ADMINS:
        return

    if len(message.text.split()) < 2:
        await message.reply("Usage: /broadcast message")
        return

    text = message.text.split(None, 1)[1]

    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users")

    sent = 0

    for (uid,) in cur.fetchall():
        try:
            await client.send_message(uid, text)
            sent += 1
        except:
            pass

    await message.reply(f"✅ Sent to {sent} users")


print("🔥 ZLIX FINAL UI BOT RUNNING")
app.run()
