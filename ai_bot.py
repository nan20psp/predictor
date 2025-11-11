# ai_bot_selenium.py

import asyncio, os, re, random, json
from datetime import datetime
from telegram import Update, Bot, ChatMember
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# (အသစ်) Selenium imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# Database module (AI Bot အတွက်) ကို import လုပ်ပါ
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
DATA_URL = "https://www.bigwingame.bet/#/home/index" # .json မဟုတ်တော့ဘဲ Website ပင်မကို ဝင်ရပါမယ်

# --- Selenium Setup (Render/Server အတွက်) ---
def setup_selenium_driver():
    """Render ပေါ်မှာ Chrome Browser run ဖို့ ပြင်ဆင်ပါ။"""
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless") # Browser မမြင်ရဘဲ run မယ်
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    # (Render မှာ ChromeDriver ကို အလိုအလျောက် install လုပ်ဖို့)
    from webdriver_manager.chrome import ChromeDriverManager
    # (Service object အသစ်ကို သုံးမှ Render မှာ အဆင်ပြေပါမယ်)
    from selenium.webdriver.chrome.service import Service as ChromeService
    
    try:
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
        return driver
    except Exception as e:
        print(f"!!! CRITICAL: Selenium Driver စတင်လို့ မရပါ !!!")
        print(f"Error: {e}")
        print("Render မှာ Chrome Buildpack ထည့်သွင်းပြီးပြီလား စစ်ဆေးပါ။")
        return None

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
        return "⏳ Data စုဆောင်းနေပါသည်။" 

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

# --- (အဓိက) Timer Job (Selenium [Response 76] ဖြင့်) ---
async def wingo_job(context: ContextTypes.DEFAULT_TYPE):
    print(f"Running Selenium Wingo Job... (Time: {datetime.now()})")
    
    driver = None
    try:
        # (၁) Selenium Browser ကို ဖွင့်ပါ
        driver = setup_selenium_driver()
        if not driver:
            raise Exception("Selenium Driver ဖွင့်လို့မရပါ။")
            
        driver.get(DATA_URL)
        
        # (TODO: ကိုကို... Website က "1 MIN WINGO" tab ကို အရင် နှိပ်ရရင် အဲ့ဒီ code ထပ်ထည့်ရပါမယ်)
        # ဥပမာ: driver.find_element(By.XPATH, "//*[contains(text(), '1 Min Wingo')]").click()
        
        # (၂) Data တွေကို Browser ကနေ ခိုးယူ (Scrape) ပါ
        
        # (TODO: ကိုကို... ဒီ `CSS_SELECTOR` က အရေးကြီးဆုံးပါ။)
        # ဘေဘီက ပုံ ကို ကြည့်ပြီး မှန်းရေးထားတာပါ)
        # ဥပမာ: HTML က <div class="issue-id">2025111100010660</div>
        # ဥပမာ: HTML က <div class="result-value">SMALL</div>
        
        # (၁၀) စက္ကန့် အထိ စောင့်
        wait = WebDriverWait(driver, 10) 
        
        # (ဒီ Selector တွေကို F12 (Inspect) နဲ့ ရှာပြီး အမှန် ပြန်ထည့်ပေးပါ)
        latest_issue_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.issue-id")))
        latest_result_element = driver.find_element(By.CSS_SELECTOR, "div.result-value")
        
        issue_id = latest_issue_element.text
        result_value = latest_result_element.text
        
        # (Browser ကို ချက်ချင်း ပိတ်ပါ)
        driver.quit()

        if not issue_id or not result_value:
            raise Exception("Scraping လုပ်လို့ရတဲ့ Data က အလွတ် ဖြစ်နေပါတယ်။ (Selector မှားနိုင်)")

        # (၃) DB ထဲ သိမ်းပါ
        db.add_result(issue_id, result_value)
        
    except Exception as e:
        print(f"Selenium Scraping failed: {e}")
        if driver:
            driver.quit() # Error တက်ရင် Browser ကို ပိတ်ပါ
        return # Error တက်ရင် ခန့်မှန်းချက် မပို့တော့ဘူး

    # (၄) ခန့်မှန်းချက် တွက်ပါ
    last_results = db.get_last_results(10) 
    prediction = get_prediction(last_results)
    
    # (၅) Group တွေအားလုံးကို Broadcast ပို့ပါ
    active_pattern = db.get_active_pattern()
    active_groups = db.get_all_groups()
    
    if not active_groups:
        print("No active groups to broadcast.")
        return

    broadcast_msg = (
        f"--- **1 MIN WINGO** ---\n"
        f"Pattern Set: **{active_pattern}**\n"
        f"Last Result: `{issue_id}` -> **{result_value.upper()}**\n\n"
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
    print("🤖 AI Pattern Bot (Selenium Mode) စတင်နေပါသည်...")

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
