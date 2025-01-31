from logging_config import bot_logger
from messages.messages import send_announcement_messages, send_start_messages


async def check_and_send_messages(game_dao, bot):
    """Основной метод для проверки всех игр и отправки сообщений."""

    await send_announcement_messages(game_dao, bot)
    await send_start_messages(game_dao, bot)
    bot_logger.info("All game messages processed and updated.")