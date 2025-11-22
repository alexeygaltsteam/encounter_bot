from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta
import pytz
from aiogram.enums import ParseMode
from aiogram.types import FSInputFile

from db.models import GameDate
from keyboards.constants import GAME_ANNOUNCEMENT, GAME_START, GAME_DATE_CHANGE
from keyboards.game_keyboards import default_game_keyboard
from logging_config import bot_logger
from settings import  CHATS_ID


def get_user_facing_link(link: str) -> str:
    """Заменяет .encounter.cx на .en.cx для отображения пользователю."""
    if not link:
        return link
    return link.replace('.encounter.cx', '.en.cx')


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
    players = "Один игрок" if game.game_type == "single" else (
        game.max_players if game.max_players > 0 else "Не указано")
    try:
        price = game.price.split(' ')[0] if game.price.split(' ')[0] != '0' else "Не указано"
    except Exception:
        price = "Не указано"

    return f"""{header}
<b>🎮 <a href='{get_user_facing_link(game.link)}'>{game.name}</a></b>\n"
<b>🕒 Начало:</b> {game.start_date.strftime('%d.%m.%Y %H:%M:%S')}
<b>🕒 Конец:</b> {game.end_date.strftime('%d.%m.%Y %H:%M:%S') if game.end_date else "Отсутствует"}
<b>📝 Автор(ы):</b> {game.author}
<b>🌐 Домен:</b> {game.domain}
<b>💰 Взнос:</b> {price}
<b>🎭 Тип игры:</b> {'Одиночная' if game.game_type == 'single' else 'Командная'}
<b>👥 Ограничение игроков:</b> {players}
"""


def format_annonsed_game_message(game: GameDate, header: str) -> str:
    """Формирует текст сообщения с информацией об игре"""
    players = "Один игрок" if game.game_type == "single" else (
        game.max_players if game.max_players > 0 else "Не указано")
    return f"""{header}
<b>🎮 <a href='{get_user_facing_link(game.link)}'>{game.name}</a></b>\n"
<b>📅 Начало:</b> {game.start_date.strftime('%d.%m.%Y %H:%M:%S')}
<b>📆 Конец:</b> {game.end_date.strftime('%d.%m.%Y %H:%M:%S') if game.end_date else "Отсутствует"}
<b>📝 Автор(ы):</b> {game.author}
<b>🌐 Домен:</b> {game.domain}
<b>👥 Ограничение игроков:</b> {players}
"""


def format_game_message_with_change(game: GameDate, header: str) -> str:
    """Формирует текст сообщения с информацией об игре"""
    return f"""{header}
<b>🎮 <a href='{get_user_facing_link(game.link)}'>{game.name}</a></b>\n"
<b>📝 Автор(ы):</b> {game.author}
<b>🌐 Домен:</b> {game.domain}
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

    message = format_annonsed_game_message(game, header)
    keyboard = default_game_keyboard(get_user_facing_link(game.link), game.id)

    try:
        # await bot.send_message(settings.CHAT_ID, message, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        file_name = str(game.id) + '.' + game.image.split('.')[-1] if game.image else None
        photo_path = Path(f"images/{file_name}").resolve()

        if not photo_path.exists() or not photo_path.is_file():
            bot_logger.info(f"❌ Файл {photo_path} не найден. Используем изображение по умолчанию.")
            photo_path = Path("images/DEFAULT.jpg").resolve()

        for chat in CHATS_ID:
            await bot.send_photo(
                chat_id=chat,
                photo=FSInputFile(str(photo_path)),
                caption=message,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
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
        new_end_date: Optional[datetime] = None,
        old_start_date: Optional[datetime] = None,
        old_end_date: Optional[datetime] = None,
):
    """
    Отправляет сообщение в чат о событии, связанном с игрой.

    :param bot: объект бота для отправки сообщений.
    :param game: объект игры.
    :param message_type: тип сообщения ("start", "reschedule_start", "reschedule_end", "both_reschedule").
    :param new_start_date: новая дата начала игры, если изменена.
    :param new_end_date: новая дата конца игры, если изменена.
    :param old_end_date: старая дата конца  игры.
    :param old_start_date: старая дата начала игры.
    """
    header = GAME_DATE_CHANGE
    message = format_game_message_with_change(game, header)

    # if message_type == "reschedule_start":
    #     message += f"""
    #         ⚠️ Внимание! Дата начала игры изменена.
    #         <b>Предыдущая дата начала:</b> {old_start_date.strftime('%d.%m.%Y %H:%M:%S')}
    #         <b>Новое начало:</b> {new_start_date.strftime('%d.%m.%Y %H:%M:%S')}
    #         """
    # elif message_type == "reschedule_end":
    #     message += f"""
    #         ⚠️ Внимание! Дата окончания игры изменена.
    #         <b>Предыдущая дата конца:</b> {old_end_date.strftime('%d.%m.%Y %H:%M:%S')}
    #         <b>Новый конец:</b> {new_end_date.strftime('%d.%m.%Y %H:%M:%S')}
    #         """
    # elif message_type == "both_reschedule":
    #     message += f"""
    #         ⚠️ Внимание! Изменены даты начала и окончания игры.
    #         <b>Предыдущая дата начала:</b> {old_start_date.strftime('%d.%m.%Y %H:%M:%S')}
    #         <b>Предыдущая дата конца:</b> {old_end_date.strftime('%d.%m.%Y %H:%M:%S')}
    #
    #         <b>Новое начало:</b> {new_start_date.strftime('%d.%m.%Y %H:%M:%S')}
    #         <b>Новый конец:</b> {new_end_date.strftime('%d.%m.%Y %H:%M:%S')}
    #         """
    if message_type == "reschedule_start":
        old_start_str = old_start_date.strftime('%d.%m.%Y %H:%M:%S') if old_start_date else "не указана"
        new_start_str = new_start_date.strftime('%d.%m.%Y %H:%M:%S') if new_start_date else "не указана"
        message += f"""
            <i>⚠️ Внимание! Дата начала игры изменена.</i>
            ├ <b>Предыдущая дата начала:</b> {old_start_str}
            └ 🟢 <b>Новое начало:</b> {new_start_str}
        """
    elif message_type == "reschedule_end":
        old_end_str = old_end_date.strftime('%d.%m.%Y %H:%M:%S') if old_end_date else "не указана"
        new_end_str = new_end_date.strftime('%d.%m.%Y %H:%M:%S') if new_end_date else "не указана"
        message += f"""
            <i>⚠️ Внимание! Дата окончания игры изменена.</i>
            ├ <b>Предыдущая дата конца:</b> {old_end_str}
            └ 🟢 <b>Новый конец:</b> {new_end_str}
        """
    elif message_type == "both_reschedule":
        old_start_str = old_start_date.strftime('%d.%m.%Y %H:%M:%S') if old_start_date else "не указана"
        old_end_str = old_end_date.strftime('%d.%m.%Y %H:%M:%S') if old_end_date else "не указана"
        new_start_str = new_start_date.strftime('%d.%m.%Y %H:%M:%S') if new_start_date else "не указана"
        new_end_str = new_end_date.strftime('%d.%m.%Y %H:%M:%S') if new_end_date else "не указана"
        message += f"""
            <i>⚠️ Внимание! Изменены даты начала и окончания игры.</i>
            ├ <b>Предыдущая дата начала:</b> {old_start_str}
            ├ <b>Предыдущая дата конца:</b> {old_end_str}

            └ 🟢 <b>Новое начало:</b> {new_start_str}
            └ 🟢 <b>Новый конец:</b> {new_end_str}
        """

    keyboard = default_game_keyboard(get_user_facing_link(game.link), game.id)

    try:
        # await bot.send_message(settings.CHAT_ID, message, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        file_name = str(game.id) + '.' + game.image.split('.')[-1] if game.image else None
        photo_path = Path(f"images/{file_name}").resolve()

        if not photo_path.exists() or not photo_path.is_file():
            bot_logger.info(f"❌ Файл {photo_path} не найден. Используем изображение по умолчанию.")
            photo_path = Path("images/DEFAULT.jpg").resolve()

        for chat in CHATS_ID:
            await bot.send_photo(
                chat_id=chat,
                photo=FSInputFile(str(photo_path)),
                caption=message,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
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
