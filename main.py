import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Router, types
from apscheduler.triggers.cron import CronTrigger

from db.utils import update_game_states
from keyboards.game_keyboards import set_main_menu
from loader import bot, dp, db, game_dao
from logging_config import bot_logger
from messages.scheduler_messages import check_and_send_messages
from parser.parser import run_parsing
from handlers.main_handlers import router as main_router

router = Router()


async def on_startup(dp):
    """
    Функция запуска бота.
    """
    bot_logger.info("Bot startup initiated")
    await set_main_menu(bot)

    dp.include_router(router)
    dp.include_router(main_router)
    bot_logger.info("Bot router included successfully")

    scheduler = AsyncIOScheduler()

    # scheduler.add_job(run_parsing, CronTrigger(hour="0,18", minute="0"))
    # scheduler.add_job(check_and_send_messages, CronTrigger(hour="8,12,16,20", minute="0"), args=[game_dao, bot])
    # scheduler.add_job(update_game_states, CronTrigger(minute="0"))

    scheduler.add_job(run_parsing, CronTrigger(minute="15,45"))
    scheduler.add_job(check_and_send_messages, CronTrigger(minute="5,35"), args=[game_dao, bot])
    scheduler.add_job(update_game_states, CronTrigger(minute="20,50"))
    scheduler.start()

    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        bot_logger.info("Bot started successfully")
        asyncio.run(on_startup(dp))
    except KeyboardInterrupt:
        bot_logger.warning("Bot was stopped by KeyboardInterrupt")
    except Exception as e:
        bot_logger.error(f"Unexpected error: {e}")
    finally:
        asyncio.run(db.close())
        bot_logger.info("Database connection closed")
        bot_logger.info("Bot stopped successfully")
