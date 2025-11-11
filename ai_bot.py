# ai_bot.py

import asyncio, os, re, random, json
from datetime import datetime
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# (အသစ်) Cloudflare ကို ကျော်ဖြတ်ဖို့ `curl_cffi` ကို သုံးပါမယ်
from curl_cffi.requests import Session

# Database module (AI Bot အတွက်) ကို import လုပ်ပါ
try:
    import ai_database as db
except ImportError:
    print("Error: ai_database.py file ကို မတွေ့ပါ။")
    exit()

# --- Environment Variables (AI Bot အတွက်) ---
try:
    # (BotFather မှာ Bot အသစ်တောင်းပြီး Token အသစ် ထည့်ပါ)
    AI_BOT_TOKEN = os.environ.get("AI_BOT_TOKEN") 
    
    # (ကိုကို့ရဲ့ Admin ID)
    OWNER_ID = int(os.environ.get("OWNER_ID"))
    
    # (DB URL ကတော့ Bot တွေအားလုံး အတူတူ သုံးလို့ရပါတယ်)
    MONGO_URL = os.environ.get("MONGO_URL") 
    
    if not all([AI_BOT_TOKEN, OWNER_ID, MONGO_URL]):
        print("Error: AI Bot Environment variables များ (AI_BOT_TOKEN, OWNER_ID, MONGO_URL) မပြည့်စုံပါ။")
        exit()

except Exception as e:
    print(f"Error: Environment variables များ load လုပ်ရာတွင် အမှားဖြစ်နေပါသည်: {e}")
    exit()

# --- Global Settings & Scraper Session ---
DATA_URL = "https://www.bigwingame.bet/data.json" #
scraper_session = Session()
scraper_session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
    "Referer": "https://www.bigwingame.bet/"
})
scraper_session.impersonate = "chrome110" # Cloudflare ကို ကျော်ဖြတ်ရန်

# --- Group Management Handlers ---

async def on_new_chat_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot က Group အသစ်ထဲ ဝင်လာရင် DB ထဲ မှတ်ထားပါ"""
    me = await context.bot.get_me()
    chat = update.effective_chat
    
    if chat.type in ["group", "supergroup"]:
        for new_member in update.message.new_chat_members:
            if new_member.id == me.id:
                print(f"AI Bot joined a new group: {chat.title} (ID: {chat.id})")
                db.add_group(chat.id, chat.title)
                try:
                    await context.bot.send_message(
                        chat_id=chat.id,
                        text=f"👋 မင်္ဂလာပါ! {me.first_name} ပါရှင့်။\n"
                             f"ဒီ Group မှာ Wingo ခန့်မှန်းချက် (Estimate) တွေကို (၁) မိနစ် တစ်ခါ ပို့ပေးပါမယ်။"
                    )
                except Exception as e:
                    print(f"Error sending welcome message to group: {e}")

async def on_left_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot က Group ကနေ ထွက်သွားရင် DB ကနေ ဖြုတ်ပါ"""
    me = await context.bot.get_me()
    chat = update.effective_chat
    
    if chat.type in ["group", "supergroup"]:
        if update.message.left_chat_member.id == me.id:
            print(f"AI Bot left/was kicked from group: (ID: {chat.id})")
            db.remove_group(chat.id)

# --- (အဓိက) Prediction Logic ---

def get_prediction(last_results):
    """Data အဟောင်းတွေကို ကြည့်ပြီး "AI-Estimate" လုပ်မယ့်နေရာ"""
    if len(last_results) < 4:
        return "⏳ Data စုဆောင်းနေပါသည်။" # Data မပြည့်သေး

    active_pattern = db.get_active_pattern() # 1 or 2
    
    # နောက်ဆုံး 4 ခုကို ယူ
    last_4 = last_results[-4:]
    
    # --- (Pattern 1: 3-in-a-row) ---
    if active_pattern == 1:
        if last_4[-3:] == ["small", "small", "small"]:
            return "PREDICT: 🟢 BIG 🟢"
        if last_4[-3:] == ["big", "big", "big"]:
            return "PREDICT: 🔴 SMALL 🔴"
            
    # --- (Pattern 2: Alternating) ---
    elif active_pattern == 2:
        if last_4 == ["small", "big", "small", "big"]:
            return "PREDICT: 🔴 SMALL 🔴"
        if last_4 == ["big", "small", "big", "small"]:
            return "PREDICT: 🟢 BIG 🟢"
            
    # Pattern 1 & 2 မမိရင်၊ နောက်ဆုံးထွက်တာကို ပြောင်းပြန်ခန့်မှန်း
    if last_results[-1] == "small":
        return "PREDICT: 🟢 BIG 🟢"
    else:
        return "PREDICT: 🔴 SMALL 🔴"

# --- (အဓိက) Timer Job (1 MIN WINGO) ---

async def wingo_job(context: ContextTypes.DEFAULT_TYPE):
    """(၁) မိနစ် တစ်ခါ Data လှမ်းယူ၊ ခန့်မှန်း၊ Broadcast ပို့ရန်"""
    
    # (၁) Data လှမ်းယူပါ
    try:
        response = scraper_session.get(DATA_URL, timeout=10) # 10 seconds timeout
        if response.status_code != 200:
            print(f"Error fetching data.json: Status {response.status_code}")
            return
            
        data = response.json()
        
        # (TODO: ကိုကို... data.json ရဲ့ JSON format အမှန်ကို ဒီမှာ ပြင်ပေးဖို့ လိုပါတယ်)
        # (ဘေဘီက ပုံ ကို ကြည့်ပြီး ခန့်မှန်းရေးထားတာပါ)
        latest_result = data.get("latest_issue", {})
        issue_id = latest_result.get("issue_id", "2025111100010660") #
        result_value = latest_result.get("result", "small") #
        
        # (၂) DB ထဲ သိမ်းပါ
        db.add_result(issue_id, result_value)
        
    except Exception as e:
        print(f"Scraping failed: {e}")
        return # Error တက်ရင် ခန့်မှန်းချက် မပို့တော့ဘူး

    # (၃) ခန့်မှန်းချက် တွက်ပါ
    last_results = db.get_last_results(10) # နောက်ဆုံး (၁၀) ခု ယူ
    prediction = get_prediction(last_results)
    
    # (၄) Group တွေအားလုံးကို Broadcast ပို့ပါ
    active_pattern = db.get_active_pattern()
    active_groups = db.get_all_groups()
    
    if not active_groups:
        print("No active groups to broadcast.")
        return

    broadcast_msg = (
        f"--- **1 MIN WINGO** ---\n"
        f"Pattern Set: **{active_pattern}**\n"
        f"Next Issue: **??????**\n\n"
        f"**NEXT RESULT ♻️ {prediction}**"
    )
    
    for group_id in active_groups:
        try:
            await context.bot.send_message(
                chat_id=group_id,
                text=broadcast_msg,
                parse_mode="Markdown"
            )
            await asyncio.sleep(0.1) # Bot မပိတ်မိအောင် ခဏနား
        except Exception as e:
            print(f"Failed to broadcast to group {group_id}: {e}")
            if "forbidden" in str(e).lower():
                db.remove_group(group_id) # Bot ကို ကန်ထုတ်ခံရရင် DB က ဖြုတ်

# --- Admin Commands ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot ကိုစဖွင့်ရင်"""
    await update.message.reply_text(
        "👋 **AI Pattern Bot**\n\n"
        "Game data များကို (၁) မိနစ် တစ်ခါ ခန့်မှန်း ချက် ပို့ပေးပါမည်။\n\n"
        "**Admin Commands:**\n"
        "`/addgroup` - ဤ Group ကို ခန့်မှန်းချက်များ ပို့ရန် (Group Admin များသာ)\n"
        "`/pattern <1 or 2>` - Pattern ပြောင်းရန် (Owner Only)\n"
    )

async def add_group_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot က ခန့်မှန်းချက် ပို့ပေးရမယ့် Group ကို သတ်မှတ်ပါ"""
    chat = update.effective_chat
    user_id = update.effective_user.id

    if chat.type == "private":
        await update.message.reply_text("❌ ဤ command ကို Group တွေထဲမှာပဲ သုံးလို့ရပါတယ်ရှင့်။")
        return
        
    # (Group Admin (ဒါမှမဟုတ်) Owner ဖြစ်မှ ဒီ command သုံးခွင့်ပြုပါ)
    member = await context.bot.get_chat_member(chat.id, user_id)
    if user_id == OWNER_ID or member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]:
        db.add_group(chat.id, chat.title)
        await update.message.reply_text(f"✅ **Group Registered!**\n\nဒီ Group (`{chat.title}`) ကို (၁) မိနစ် တိုင်း ခန့်မှန်းချက် တွေ ပို့ပေးပါတော့မယ်။")
    else:
        await update.message.reply_text("❌ ဤ command ကို Group Admin များသာ အသုံးပြုနိုင်ပါသည်။")

async def pattern_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """(Owner Only) Pattern 1/2 ပြောင်းရန်"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ ဤ command ကို Owner သာ သုံးနိုင်ပါသည်။")
        return
        
    args = context.args
    if len(args) != 1 or args[0] not in ["1", "2"]:
        await update.message.reply_text("❌ Format မှားနေပါပြီ!\n`/pattern 1` သို့မဟုတ် `/pattern 2`")
        return
        
    new_pattern = int(args[0])
    db.set_active_pattern(new_pattern)
    await update.message.reply_text(f"✅ **Pattern Changed!**\n\nBot သည် ယခုအခါ **Pattern {new_pattern}** ကို အသုံးပြုပြီး ခန့်မှန်း ပါမည်။")

# --- Main Function ---

def main():
    print("🤖 AI Pattern Bot စတင်နေပါသည်...")

    application = Application.builder().token(AI_BOT_TOKEN).build() 

    # --- JobQueue (Timer) ကို ဖွင့်ပါ ---
    job_queue = application.job_queue
    # (၁) မိနစ် (60 seconds) တိုင်း (၁) ခါ run မယ်။
    job_queue.run_repeating(wingo_job, interval=60, first=10) # 10 စက္ကန့်မှာ စ run မယ်

    # --- Handlers ---
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("addgroup", add_group_command))
    application.add_handler(CommandHandler("pattern", pattern_command))

    # Group Management
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_new_chat_members))
    application.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, on_left_chat_member))

    print("🚀 AI Bot အဆင်သင့်ဖြစ်ပါပြီ။ (Wingo 1-Min Mode)")
    application.run_polling()

if __name__ == "__main__":
    main()
