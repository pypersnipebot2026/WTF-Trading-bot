import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

from bot import create_bot, setup_handlers, setup_middlewares
from core.config import settings
from utils.logger import setup_logging

# Load environment variables
load_dotenv()

async def main():
    # Setup logging
    setup_logging(level=settings.LOG_LEVEL)

    logger = logging.getLogger("WTF_TRADING_BOT")
    logger.info("Starting WTF Trading Bot...")

    # Initialize bot, dispatcher and all dependencies
    bot, dp = await create_bot()

    # Setup middlewares (logging, throttling, auth, etc.)
    setup_middlewares(dp)

    # Register all handlers (commands, callbacks, messages)
    setup_handlers(dp)

    # Start polling
    try:
        logger.info("Bot polling started")
        await dp.start_polling(
            bot,
            allowed_updates=["message", "callback_query"],
            drop_pending_updates=True
        )
    except Exception as e:
        logger.critical("Critical error in polling loop", exc_info=True)
    finally:
        logger.info("Bot is shutting down...")
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
