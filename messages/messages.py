from typing import Optional
from datetime import datetime, timedelta
import pytz
from aiogram.enums import ParseMode
from db.models import GameDate
from keyboards.constants import GAME_ANNOUNCEMENT, GAME_START, GAME_DATE_CHANGE
from keyboards.game_keyboards import default_game_keyboard
from logging_config import bot_logger
from settings import settings


# def format_game_message(game: GameDate, header: str) -> str:
#     """Формирует текст сообщения"""
#     return f"""
#     {header} {game.name}
#     <b>Начало:</b> {game.start_date.strftime('%d.%m.%Y %H:%M:%S')}
#     <b>Автор:</b> {game.author}
#     <b>Цена:</b> {game.price}
#     <b>Тип игры:</b> {game.game_type}
#     <b>Количество игроков:</b> {game.max_players}
#     """
def format_game_message(game: GameDate, header: str) -> str:
    """Формирует текст сообщения с информацией об игре"""
    return f"""{header}
<b>🎮 Название:</b> {game.name}
<b>🕒 Начало:</b> {game.start_date.strftime('%d.%m.%Y %H:%M:%S')}
<b>🕒 Конец:</b> {game.end_date.strftime('%d.%m.%Y %H:%M:%S')}
<b>👤 Автор:</b> {game.author}
<b>💰 Цена:</b> {game.price} en usd
<b>🎭 Тип игры:</b> {game.game_type}
<b>👥 Количество игроков:</b> {game.max_players}
"""


async def send_game_message(bot, game, message_type: str):
    """
    Отправляет сообщение о состоянии игры (анонс или старт).

    :param bot: Объект бота
    :param game: Экземпляр GameDate
    :param message_type: Тип сообщения ('announcement' или 'start')
    """
    if message_type == 'announcement':
        header = GAME_ANNOUNCEMENT
    elif message_type == 'start':
        header = GAME_START
    else:
        bot_logger.error(f"Неизвестный тип сообщения: {message_type}")
        return

    message = format_game_message(game, header)
    keyboard = default_game_keyboard(game.link, game.id)

    try:
        await bot.send_message(settings.CHAT_ID, message, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        bot_logger.info(f"Сообщение {message_type} для игры {game.id} успешно отправлено.")
    except Exception as e:
        bot_logger.error(f"Ошибка при отправке сообщения {message_type} для игры {game.id}: {e}")


async def send_announcement_message(bot, game):
    """Отправка анонса игры"""
    await send_game_message(bot, game, 'announcement')


async def send_start_message(bot, game):
    """Отправка сообщения о старте игры"""
    await send_game_message(bot, game, 'start')


async def send_game_message_date_change(
        bot,
        game,
        message_type: str = "start",
        new_start_date: Optional[datetime] = None,
        new_end_date: Optional[datetime] = None
):
    """
    Отправляет сообщение в чат о событии, связанном с игрой.

    :param bot: объект бота для отправки сообщений.
    :param game: объект игры.
    :param message_type: тип сообщения ("start", "reschedule_start", "reschedule_end", "both_reschedule").
    :param new_start_date: новая дата начала игры, если изменена.
    :param new_end_date: новая дата конца игры, если изменена.
    """
    header = GAME_DATE_CHANGE
    message = format_game_message(game, header)

    if message_type == "reschedule_start":
        message += f"""
            ⚠️ Внимание! Дата начала игры изменена.
            <b>Новое начало:</b> {new_start_date.strftime('%d.%m.%Y %H:%M:%S')}
            """
    elif message_type == "reschedule_end":
        message += f"""
            ⚠️ Внимание! Дата окончания игры изменена.
            <b>Новый конец:</b> {new_end_date.strftime('%d.%m.%Y %H:%M:%S')}
            """
    elif message_type == "both_reschedule":
        message += f"""
            ⚠️ Внимание! Изменены даты начала и окончания игры.
            <b>Новое начало:</b> {new_start_date.strftime('%d.%m.%Y %H:%M:%S')}
            <b>Новый конец:</b> {new_end_date.strftime('%d.%m.%Y %H:%M:%S')}
            """

    keyboard = default_game_keyboard(game.link, game.id)

    try:
        await bot.send_message(settings.CHAT_ID, message, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        bot_logger.info(f"Сообщение об изменении дат для игры {game.id} успешно отправлено.")
    except Exception as e:
        bot_logger.error(f"Ошибка при отправке сообщения об изменении дат для игры {game.id}: {e}")


async def send_announcement_messages(game_dao, bot):
    """Отправляем анонсы для игр, у которых не были отправлены анонсы."""

    moscow_tz = pytz.timezone('Europe/Moscow')
    now = datetime.now(moscow_tz).replace(tzinfo=None)

    # now = datetime.now()

    five_days_before = now + timedelta(days=5)

    games_to_announce = await game_dao.get_all(
        is_announcement_sent=False,
        start_date__lte=five_days_before
    )

    for game in games_to_announce:
        if not game.is_announcement_sent:
            await send_announcement_message(bot, game)
            game.is_announcement_sent = True
            bot_logger.info(f"Sent announcement for game {game.id}: {game.name}")

            await game_dao.session.merge(game)
            await game_dao.session.commit()

            bot_logger.info(f"Game {game.id} updated after sending announcement.")


async def send_start_messages(game_dao, bot):
    """Отправляем стартовые сообщения для игр, у которых не были отправлены стартовые сообщения."""

    # now = datetime.now()

    moscow_tz = pytz.timezone('Europe/Moscow')
    now = datetime.now(moscow_tz).replace(tzinfo=None)

    twelve_hours_before = now + timedelta(hours=12)
    games_to_start = await game_dao.get_all(
        is_start_message_sent=False,
        start_date__lte=twelve_hours_before
    )

    for game in games_to_start:
        if not game.is_start_message_sent:
            await send_start_message(bot, game)
            game.is_start_message_sent = True
            bot_logger.info(f"Sent start message for game {game.id}: {game.name}")

            await game_dao.session.merge(game)
            await game_dao.session.commit()

            bot_logger.info(f"Game {game.id} updated after sending start message.")
