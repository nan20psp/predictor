# lottery_bot.py
import asyncio, sqlite3, io, os
import pandas as pd
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = "7927660379:AAEsm1s4sdi60OozbA-QiJDEJJvw5d0a9_M"   # BotFather က ယူထားတဲ့ token
TARGET_CHAT_ID = -1003124904293                   # Group / User chat_id ထည့်လို့ရတယ်
PRED_INTERVAL = 30
SUM_THRESHOLD = 150
DB_PATH = "lottery.sqlite"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS draws (
        id INTEGER PRIMARY KEY,
        draw_time TEXT,
        n1 INT, n2 INT, n3 INT, n4 INT, n5 INT, n6 INT
    )""")
    conn.commit()
    conn.close()

def insert_csv(df):
    conn = sqlite3.connect(DB_PATH)
    df.to_sql("draws", conn, if_exists="append", index=False)
    conn.commit()
    conn.close()

def get_history():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM draws", conn)
    conn.close()
    return df

def heuristic_predict(df):
    if df.empty:
        import random
        return "Random => " + ("Big" if random.random() > 0.5 else "Small")
    s = df[["n1","n2","n3","n4","n5","n6"]].sum(axis=1)
    label = "Big" if s.iloc[-1] > SUM_THRESHOLD else "Small"
    return f"{label} (sum={s.iloc[-1]})"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Lottery Predictor Bot\n/predict ခန့်မှန်းချက်\n/upload CSV upload\n/stats အချိုးအစား")

async def predict(update: Update, context: ContextTypes.DEFAULT_TYPE):
    df = get_history()
    result = heuristic_predict(df)
    await update.message.reply_text(f"Prediction: {result}")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    df = get_history()
    if df.empty:
        await update.message.reply_text("မရှိသေးပါ")
        return
    s = df[["n1","n2","n3","n4","n5","n6"]].sum(axis=1)
    big = (s > SUM_THRESHOLD).sum()
    small = (s <= SUM_THRESHOLD).sum()
    await update.message.reply_text(f"Total: {len(df)}\nBig: {big}\nSmall: {small}")

async def upload_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    f = await doc.get_file()
    bio = io.BytesIO()
    await f.download(out=bio)
    bio.seek(0)
    df = pd.read_csv(bio)
    insert_csv(df)
    await update.message.reply_text(f"CSV {len(df)} rows ထည့်ပြီးပါပြီ")

async def periodic(app):
    await asyncio.sleep(2)
    while True:
        df = get_history()
        result = heuristic_predict(df)
        if TARGET_CHAT_ID:
            await app.bot.send_message(chat_id=int(TARGET_CHAT_ID), text=f"Periodic: {result}")
        else:
            print("Periodic:", result)
        await asyncio.sleep(PRED_INTERVAL)

def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("predict", predict))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(MessageHandler(filters.Document.FileExtension("csv"), upload_file))

    async def run():
        asyncio.create_task(periodic(app))
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        await app.idle()

    asyncio.run(run())

if __name__ == "__main__":
    main()
