import logging
import random
import asyncio
import datetime

from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram.constants import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# --- CONFIGURATION ---
# Replace with your actual bot token from BotFather
TELEGRAM_BOT_TOKEN = "7927660379:AAGtm-CvAunvvANaaYvzlmRVjjBgJcmEh58" 
# Replace with the ID of the chat where predictions will be sent automatically
TARGET_CHAT_ID = "-1003138310803" 
# --- END CONFIGURATION ---

# Set up logging to see errors
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# This global variable will simulate the game's period/issue number
# We initialize it based on the current date and a starting number
current_period = int(datetime.datetime.now().strftime('%Y%m%d001'))

def generate_prediction():
    """
    This function generates a random 'prediction'.
    THIS IS NOT REAL AI. IT'S PURELY RANDOM FOR ENTERTAINMENT.
    """
    global current_period
    
    # Determine the predicted number (0-9)
    number = random.randint(0, 9)
    
    # Determine the predicted size (Big/Small)
    size = "Big" if number >= 5 else "Small"
    
    # Determine the predicted color based on common game rules
    if number in [1, 3, 7, 9]:
        color = "Green 🟢"
    elif number in [2, 4, 6, 8]:
        color = "Red 🔴"
    elif number == 5:
        color = "Green 🟢 + Violet 🟣"
    else:  # number == 0
        color = "Red 🔴 + Violet 🟣"
        
    # Format the prediction message
    prediction_text = (
        f"🔮 **WinGo 30s Prediction** 🔮\n\n"
        f"📅 **Period:** `{current_period}`\n"
        f"-----------------------------------\n"
        f"💡 **Suggestion:** **{size}** | **{color}**\n"
        f"🔢 **Lucky Number:** `{number}`\n"
        f"-----------------------------------\n\n"
        f"🚨 *Disclaimer: For entertainment purposes only. Results are random and not guaranteed. Play responsibly.*"
    )
    
    # Increment the period for the next round
    current_period += 1
    
    return prediction_text

# Command handler for /start and /help
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcome message and instructions."""
    welcome_text = (
        "👋 **Welcome to the WinGo Predictor Bot!**\n\n"
        "This bot provides *for-fun* predictions for a 30-second lottery game.\n\n"
        "**Commands:**\n"
        "`/predict` - Get a new random prediction instantly.\n"
        "`/help` - Show this message again.\n\n"
        "**Automatic Predictions:**\n"
        "The bot will automatically post a new prediction every 30 seconds to a designated chat.\n\n"
        "🛑 **IMPORTANT DISCLAIMER** 🛑\n"
        "This bot's predictions are **100% random and for entertainment only**. "
        "Do NOT use this for financial decisions. Real lottery games are unpredictable."
    )
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)

# Command handler for /predict
async def predict_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a single, on-demand prediction."""
    logger.info(f"Received /predict command from user {update.effective_user.id}")
    prediction = generate_prediction()
    await update.message.reply_text(prediction, parse_mode=ParseMode.MARKDOWN)

# Function to be called by the scheduler
async def send_scheduled_prediction(bot: Bot):
    """Generates and sends a prediction to the target chat."""
    logger.info(f"Sending scheduled prediction to chat ID {TARGET_CHAT_ID}")
    prediction = generate_prediction()
    try:
        await bot.send_message(
            chat_id=TARGET_CHAT_ID,
            text=prediction,
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"Failed to send message to {TARGET_CHAT_ID}: {e}")
        logger.warning("Please ensure the TARGET_CHAT_ID is correct and the bot is a member of the chat.")

async def main():
    """Main function to set up and run the bot."""
    if TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN" or TARGET_CHAT_ID == "YOUR_TARGET_CHAT_ID":
        logger.error("Please fill in your TELEGRAM_BOT_TOKEN and TARGET_CHAT_ID in the script.")
        return

    # Create the bot application
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", start))
    application.add_handler(CommandHandler("predict", predict_now))

    # --- Scheduler Setup ---
    # This will run the 'send_scheduled_prediction' function every 30 seconds
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        send_scheduled_prediction, 
        'interval', 
        seconds=30, 
        args=[application.bot]
    )
    scheduler.start()
    
    logger.info("Bot started and scheduler is running...")
    
    # Run the bot until you press Ctrl-C
    try:
        await application.run_polling()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
    
if __name__ == '__main__':
    try:
        asyncio.run(main())
    except RuntimeError:
        # This handles a common issue on Windows when stopping the script
        pass

