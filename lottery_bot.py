import logging
import random
import asyncio
import datetime

from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram.constants import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# --- CONFIGURATION (ဒီနေရာမှာ သင့်အချက်အလက်တွေဖြည့်ပါ) ---
# BotFather ကရလာတဲ့ သင့်ရဲ့ Bot Token ကိုထည့်ပါ
TELEGRAM_BOT_TOKEN = "7927660379:AAGtm-CvAunvvANaaYvzlmRVjjBgJcmEh58" 
# Bot က message တွေ အလိုအလျောက်ပంపမယ့် Chat ID ကိုထည့်ပါ
TARGET_CHAT_ID = "-1003124904293" 
# --- END CONFIGURATION ---

# Error တွေကို ကြည့်ရှုနိုင်ရန် Logging ပြုလုပ်ခြင်း
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ဂိမ်းရဲ့ အကြိမ်ရေ (Period) ကို မှတ်သားရန်
current_period = int(datetime.datetime.now().strftime('%Y%m%d001'))

def generate_prediction():
    """
    ဤ function သည် ကျပန်း 'ခန့်မှန်းချက်' တစ်ခုကို ဖန်တီးပေးသည်။
    ၎င်းသည် AI အစစ်မဟုတ်ဘဲ ဖျော်ဖြေရေးအတွက်သာဖြစ်ပါသည်။
    """
    global current_period
    
    # ခန့်မှန်းဂဏန်း (0-9) ကို ကျပန်းရွေးခြင်း
    number = random.randint(0, 9)
    
    # အကြီး/အသေး ခန့်မှန်းခြင်း
    size_en = "Big" if number >= 5 else "Small"
    size_mm = "အကြီး" if size_en == "Big" else "အသေး"
    
    # အရောင်ခန့်မှန်းခြင်း
    if number in [1, 3, 7, 9]:
        color_mm = "အစိမ်း 🟢"
    elif number in [2, 4, 6, 8]:
        color_mm = "အနီ 🔴"
    elif number == 5:
        color_mm = "အစိမ်း 🟢 + ခရမ်း 🟣"
    else:  # number == 0
        color_mm = "အနီ 🔴 + ခရမ်း 🟣"
        
    # ပေးပို့မည့် message ကို မြန်မာလိုပြင်ဆင်ခြင်း
    prediction_text = (
        f"🔮 **WinGo 30s ခန့်မှန်းချက်** 🔮\n\n"
        f"📅 **အကြိမ်ရေ:** `{current_period}`\n"
        f"-----------------------------------\n"
        f"💡 **အကြံပြုချက်:** **{size_mm}** | **{color_mm}**\n"
        f"🔢 **ကံကောင်းစေမယ့်ဂဏန်း:** `{number}`\n"
        f"-----------------------------------\n\n"
        f"🚨 *သတိပေးချက်: ဤခန့်မှန်းချက်သည် ဖျော်ဖြေရေးအတွက်သာဖြစ်သည်။ ရလဒ်များမှာ ကျပန်းဖြစ်ပြီး အာမ မခံပါ။ တာဝန်ယူမှုဖြင့်သာ ကစားပါ။*"
    )
    
    # နောက်တစ်ကြိမ်အတွက် အကြိမ်ရေကို တစ်ခုတိုးခြင်း
    current_period += 1
    
    return prediction_text

# /start နှင့် /help command များအတွက် handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ကြိုဆိုခြင်းနှင့် လမ်းညွှန်ချက် message ပို့ခြင်း"""
    welcome_text = (
        "👋 **WinGo ခန့်မှန်းချက်ပေး Bot မှ ကြိုဆိုပါတယ်။**\n\n"
        "ဤ Bot သည် စက္ကန့် ၃၀ ဂိမ်းအတွက် **ဖျော်ဖြေရေး** ခန့်မှန်းချက်များကို ထုတ်ပေးပါသည်။\n\n"
        "**Commands များ:**\n"
        "`/predict` - ခန့်မှန်းချက်အသစ်တစ်ခု ချက်ချင်းရယူရန်။\n"
        "`/help` - ဤလမ်းညွှန်ကို ထပ်မံကြည့်ရှုရန်။\n\n"
        "**အလိုအလျောက် ခန့်မှန်းချက်များ:**\n"
        "Bot သည် သတ်မှတ်ထားသော chat သို့ စက္ကန့် ၃၀ တိုင်း ခန့်မှန်းချက်အသစ်များ အလိုအလျောက် ပို့ပေးပါမည်။\n\n"
        "🛑 **အရေးကြီးသတိပေးချက်** 🛑\n"
        "ဤ Bot ၏ ခန့်မှန်းချက်များသည် **၁၀၀% ကျပန်းဖြစ်ပြီး ဖျော်ဖြေရေးအတွက်သာ** ဖြစ်သည်။ "
        "တကယ့်ငွေကြေးဖြင့် လောင်းကစားရန် လုံးဝအသုံးမပြုပါနှင့်။"
    )
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)

# /predict command အတွက် handler
async def predict_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """တောင်းဆိုချိန်တွင် ခန့်မှန်းချက်တစ်ခုပို့ပေးခြင်း"""
    logger.info(f"User {update.effective_user.id} ထံမှ /predict command ရရှိသည်")
    prediction = generate_prediction()
    await update.message.reply_text(prediction, parse_mode=ParseMode.MARKDOWN)

# အချိန်ဇယား (Scheduler) မှ ခေါ်သုံးမည့် function
async def send_scheduled_prediction(bot: Bot):
    """သတ်မှတ်ထားသော chat သို့ အလိုအလျောက် message ပို့ခြင်း"""
    logger.info(f"Chat ID {TARGET_CHAT_ID} သို့ အလိုအလျောက် message ပို့နေသည်")
    prediction = generate_prediction()
    try:
        await bot.send_message(
            chat_id=TARGET_CHAT_ID,
            text=prediction,
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"Chat ID {TARGET_CHAT_ID} သို့ message ပို့ရာတွင် error ဖြစ်ပွားနေသည်: {e}")

async def main():
    """Bot ကို စတင်လည်ပတ်စေရန် main function"""
    if TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN" or TARGET_CHAT_ID == "YOUR_TARGET_CHAT_ID":
        logger.error("ကျေးဇူးပြု၍ သင့် TELEGRAM_BOT_TOKEN နှင့် TARGET_CHAT_ID ကို code ထဲတွင် ဖြည့်စွက်ပါ")
        return

    # Bot application ကို တည်ဆောက်ခြင်း
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Command handlers များကို ထည့်သွင်းခြင်း
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", start))
    application.add_handler(CommandHandler("predict", predict_now))

    # --- Scheduler ကိုတည်ဆောက်ခြင်း ---
    # စက္ကန့် ၃၀ တိုင်း 'send_scheduled_prediction' function ကို ခေါ်ခိုင်းပါမည်
    scheduler = AsyncIOScheduler(timezone="Asia/Yangon")
    scheduler.add_job(
        send_scheduled_prediction, 
        'interval', 
        seconds=30, 
        args=[application.bot]
    )
    scheduler.start()
    
    logger.info("Bot စတင်လည်ပတ်နေပြီးဖြစ်သည်...")
    
    # Bot ကို Ctrl-C မနှိပ်မချင်း အလုပ်လုပ်စေခြင်း
    await application.run_polling()
    
if __name__ == '__main__':
    asyncio.run(main())

