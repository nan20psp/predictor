# ai_bot_api.py (ပြင်ဆင်ပြီး)

import asyncio, os, re, random, json
from datetime import datetime
from telegram import Update, Bot, ChatMember
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

import requests 

try:
    import ai_database as db
except ImportError:
    print("Error: ai_database.py file ကို မတွေ့ပါ။")
    exit()

# --- Environment Variables (AI Bot အတွက်) ---
try:
    AI_BOT_TOKEN = os.environ.get("AI_BOT_TOKEN") 
    OWNER_ID = int(os.environ.get("OWNER_ID"))
    MONGO_URL = os.environ.get("MONGO_URL") 
    
    if not all([AI_BOT_TOKEN, OWNER_ID, MONGO_URL]):
        print("Error: AI Bot Environment variables များ (AI_BOT_TOKEN, OWNER_ID, MONGO_URL) မပြည့်စုံပါ။")
        exit()

except Exception as e:
    print(f"Error: Environment variables များ load လုပ်ရာတွင် အမှားဖြစ်နေပါသည်: {e}")
    exit()

# --- Global Settings ---
DATA_API_URL = "https://api.bigwinqaz.com/api/webapi/GetNoaverageEmerdList" #
API_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
    "Referer": "https://www.bigwingame.bet/" 
}


# --- Group Management (မပြောင်းပါ) ---
async def on_new_chat_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    me = await context.bot.get_me()
    chat = update.effective_chat
    if chat.type in ["group", "supergroup"]:
        for new_member in update.message.new_chat_members:
            if new_member.id == me.id:
                print(f"AI Bot joined a new group: {chat.title} (ID: {chat.id})")
                db.add_group(chat.id, chat.title)
                try:
                    await context.bot.send_message(chat_id=chat.id, text=f"👋 မင်္ဂလာပါ! {me.first_name} ပါရှင့်။\nဒီ Group မှာ Wingo ခန့်မှန်းချက် တွေ ပို့ပေးပါမယ်။")
                except: pass

async def on_left_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    me = await context.bot.get_me()
    chat = update.effective_chat
    if chat.type in ["group", "supergroup"]:
        if update.message.left_chat_member.id == me.id:
            print(f"AI Bot left/was kicked from group: (ID: {chat.id})")
            db.remove_group(chat.id)

# --- (အဓိက) Prediction Logic (မပြောင်းပါ) ---
def get_prediction(last_results):
    if len(last_results) < 4:
        return "⏳ Data စုဆောင်းနေပါသည်။" #

    active_pattern = db.get_active_pattern() 
    last_4 = last_results[-4:]
    
    if active_pattern == 1:
        if last_4[-3:] == ["small", "small", "small"]: return "PREDICT: 🟢 BIG 🟢"
        if last_4[-3:] == ["big", "big", "big"]: return "PREDICT: 🔴 SMALL 🔴"
            
    elif active_pattern == 2:
        if last_4 == ["small", "big", "small", "big"]: return "PREDICT: 🔴 SMALL 🔴"
        if last_4 == ["big", "small", "big", "small"]: return "PREDICT: 🟢 BIG 🟢"
            
    if last_results[-1] == "small":
        return "PREDICT: 🟢 BIG 🟢"
    else:
        return "PREDICT: 🔴 SMALL 🔴"

# --- (အဓိက) Timer Job (Requests ဖြင့်) ---
async def wingo_job(context: ContextTypes.DEFAULT_TYPE):
    """(၁) မိနစ် တစ်ခါ Data လှမ်းယူ၊ ခန့်မှန်း၊ Broadcast ပို့ရန်"""
    
    print(f"Running API Request Job... (Time: {datetime.now()})")
    
    latest_issue_id = ""
    latest_result_val = ""
    latest_result_num = ""
    
    # (၁) Data လှမ်းယူပါ (Selenium မလိုတော့ပါ)
    try:
        # --- (ပြင်ဆင်ပြီး) GET အစား POST ကို သုံးပါ ---
        response = requests.post(DATA_API_URL, headers=API_HEADERS, timeout=10)
        
        if response.status_code == 405:
            print(f"CRITICAL ERROR: API method ကို Server က လက်မခံပါ။ (405 Method Not Allowed)")
            return
        if response.status_code != 200:
            print(f"Error fetching API: Status {response.status_code}")
            return
            
        data = response.json()
        
        # --- (JSON Logic - Response 157) ---
        if data.get("code") != 0 or "data" not in data or "list" not in data["data"]:
            raise Exception(f"API Response 'data' or 'list' key မတွေ့ပါ။ Msg: {data.get('msg')}")
            
        if not data["data"]["list"]:
            raise Exception("API Response 'list' is empty.")
            
        latest_result_obj = data["data"]["list"][0] # List ထဲက ပထမဆုံး (နောက်ဆုံး) result ကို ယူ
        
        latest_issue_id = latest_result_obj.get("issueNumber") #
        latest_result_num_str = latest_result_obj.get("number") # "6"

        if not latest_issue_id or not latest_result_num_str:
             raise Exception("API Response ထဲမှာ 'issueNumber' or 'number' မတွေ့ပါ။")
        
        try:
            num = int(latest_result_num_str)
            if 0 <= num <= 4:
                latest_result_val = "small"
            elif 5 <= num <= 9:
                latest_result_val = "big"
            else:
                latest_result_val = "unknown" # (Violet/Special case)
        except Exception:
             raise Exception(f"Result 'number' ({latest_result_num_str}) က 'BIG'/'SMALL' တွက်လို့မရပါ။")
        # --- (JSON Logic ပြီး) ---

        # (၂) DB ထဲ သိမ်းပါ
        db.add_result(latest_issue_id, latest_result_val, latest_result_num_str)
        
    except requests.exceptions.RequestException as e:
        print(f"API Request (Network/Timeout) failed: {e}")
        return
    except Exception as e:
        print(f"API Data Processing failed: {e}")
        return # Error တက်ရင် ခန့်မှန်းချက် မပို့တော့ဘူး

    # (၃) ခန့်မှန်းချက် တွက်ပါ
    last_results = db.get_last_results(10) 
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
        f"Last Result: `{latest_issue_id}` -> **{latest_result_val.upper()} ({latest_result_num_str})**\n\n"
        f"**NEXT RESULT ♻️ {prediction}**"
    )
    
    for group_id in active_groups:
        try:
            await context.bot.send_message(
                chat_id=group_id,
                text=broadcast_msg,
                parse_mode="Markdown"
            )
            await asyncio.sleep(0.1)
        except Exception as e:
            print(f"Failed to broadcast to group {group_id}: {e}")
            if "forbidden" in str(e).lower():
                db.remove_group(group_id)

# --- Admin Commands (မပြောင်းပါ) ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 **AI Pattern Bot**\n\n"
        "Game data များကို (၁) မိနစ် တစ်ခါ ခန့်မှန်း ချက် ပို့ပေးပါမည်။\n\n"
        "**Admin Commands:**\n"
        "`/addgroup` - ဤ Group ကို ခန့်မှန်းချက်များ ပို့ရန် (Group Admin များသာ)\n"
        "`/pattern <1 or 2>` - Pattern ပြောင်းရန် (Owner Only)\n"
    )

async def add_group_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user_id = update.effective_user.id

    if chat.type == "private":
        await update.message.reply_text("❌ ဤ command ကို Group တွေထဲမှာပဲ သုံးလို့ရပါတယ်ရှင့်။")
        return
        
    member = await context.bot.get_chat_member(chat.id, user_id)
    if user_id == OWNER_ID or member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]:
        db.add_group(chat.id, chat.title)
        await update.message.reply_text(f"✅ **Group Registered!**\n\nဒီ Group (`{chat.title}`) ကို (၁) မိနစ် တိုင်း ခန့်မှန်းချက် တွေ ပို့ပေးပါတော့မယ်။")
    else:
        await update.message.reply_text("❌ ဤ command ကို Group Admin များသာ အသုံးပြုနိုင်ပါသည်။")

async def pattern_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    print("🤖 AI Pattern Bot (API Mode) စတင်နေပါသည်...")

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
