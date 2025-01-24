import asyncio
import logging

from aiogram.filters import CommandStart
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Router, types
from apscheduler.triggers.cron import CronTrigger

from db.utils import update_game_states
from filters import PrivateChatFilter
from loader import bot, dp, db, game_dao
from logging_config import bot_logger
from parser.parser import run_parsing
from aiogram.types import CallbackQuery

from utils import check_and_send_messages

router = Router()


@router.callback_query(lambda c: c.data == "go_to_bot")
async def handle_go_to_bot(callback_query: CallbackQuery, bot):
    """Обработка нажатия на кнопку 'Перейти к боту' и отправка личного сообщения"""
    user_id = callback_query.from_user.id  # Получаем id пользователя

    # Текст, который будет отправлен в личку
    message_text = "Привет! Вы нажали на кнопку для перехода к боту. Для дальнейших действий переходите по ссылке: https://t.me/enc_finder_bot."

    try:
        # Отправляем личное сообщение пользователю
        await bot.send_message(user_id, message_text)

        # Подтверждаем нажатие кнопки, чтобы скрыть всплывающее окно
        await bot.answer_callback_query(callback_query.id, text="Мы отправили вам сообщение!")
    except Exception as e:
        print(f"Ошибка при отправке личного сообщения: {e}")


# async def check_and_send_messages(game_dao, bot):
#     """Метод для проверки всех игр в базе данных, чьи start_date наступили в течение 6 часов, и отправки сообщений."""
#
#     date_value = datetime.strptime('2025-01-16', '%Y-%m-%d').date()
#     games = await game_dao.get_all(start_date__lte=date_value)
#     # Отправляем сообщение для каждой игры
#     for game in games:
#         await send_game_message(bot, game)


@router.message(CommandStart(), PrivateChatFilter())
async def cmd_start(message: types.Message):
    await message.answer('''Привет! 👋
🤖 Я бот-магазин по продаже товаров любой категории. Чем могу помочь?''')


async def on_startup(dp):
    """
    Функция запуска бота.
    """
    bot_logger.info("Bot startup initiated")
    dp.include_router(router)
    bot_logger.info("Bot router included successfully")

    scheduler = AsyncIOScheduler()
    # scheduler.add_job(run_parsing, 'interval', hours=24)
    scheduler.add_job(run_parsing, CronTrigger(minute="*", second="0"))
    # scheduler.add_job(check_and_send_messages, CronTrigger(minute="*", second="0"), args=[game_dao, bot])
    # scheduler.add_job(update_game_states, CronTrigger(minute="*", second="0"))
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
