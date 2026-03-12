import os
import sqlite3
import subprocess
import time
import logging

from telegram import Update, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "8622778264:AAGx9V9JrS8EUdiPUbLqbnA6M7imCODypGg"
ADMIN_ID = 8198378709

logging.basicConfig(level=logging.INFO)

# DB connection
db = sqlite3.connect("users.db", check_same_thread=False)
cursor = db.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY)")
db.commit()

last_video_time = {}

def add_user(user_id):
    cursor.execute("INSERT OR IGNORE INTO users VALUES (?)", (user_id,))
    db.commit()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id)
    await update.message.reply_text(
        f"Salom {user.first_name} 👋\nVideo yuboring — men uni dumaloq video qilib beraman 🎥"
    )


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    await update.message.reply_text(f"Foydalanuvchilar soni: {count}")


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("Xabar yozing.")
        return
    text = " ".join(context.args)
    cursor.execute("SELECT id FROM users")
    users = cursor.fetchall()
    sent = 0
    for user in users:
        try:
            await context.bot.send_message(chat_id=user[0], text=text)
            sent += 1
        except:
            pass
    await update.message.reply_text(f"Yuborildi: {sent}")


async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_user(user_id)

    now = time.time()
    if user_id in last_video_time and now - last_video_time[user_id] < 10:
        await update.message.reply_text("10 sekund kuting.")
        return
    last_video_time[user_id] = now

    await update.message.reply_text("Video qayta ishlanmoqda...")

    video = update.message.video or update.message.document
    file = await context.bot.get_file(video.file_id)

    input_path = f"input_{user_id}.mp4"
    output_path = f"output_{user_id}.mp4"

    await file.download_to_drive(input_path)

    command = [
        "ffmpeg",
        "-i", input_path,
        "-vf", "crop='min(iw,ih)':'min(iw,ih)',scale=360:360",
        "-c:v", "libx264",
        "-preset", "fast",
        "-an",
        "-y",
        output_path
    ]

    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if not os.path.exists(output_path):
        await update.message.reply_text("Video ishlanmadi.")
        return

    with open(output_path, "rb") as v:
        await update.message.reply_video_note(v)

    os.remove(input_path)
    os.remove(output_path)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logging.error(context.error)


app = ApplicationBuilder().token(TOKEN).build()

# Commands
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("stats", stats))
app.add_handler(CommandHandler("broadcast", broadcast))
app.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, handle_video))
app.add_error_handler(error_handler)

# Slash command variantlarini avtomatik ko'rsatish
async def set_commands(app):  # tuzatildi: app argument qo'shildi
    bot = app.bot
    await bot.set_my_commands([
        BotCommand("start", "Botni ishga tushirish"),
        BotCommand("stats", "Foydalanuvchilar sonini ko'rish (admin)"),
        BotCommand("broadcast", "Xabarni barcha foydalanuvchilarga yuborish (admin)")
    ])

app.post_init = set_commands

print("Bot ishga tushdi...")
app.run_polling()