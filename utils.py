from datetime import datetime, timedelta
from aiogram.enums import ParseMode
from db.models import GameDate
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from logging_config import bot_logger


async def send_game_message(bot, game: GameDate):
    """Отправка сообщения в чат о начале игры с кнопками"""

    # Формируем текст сообщения
    message = f"""
    <b>Игра:</b> {game.name}
    <b>Начало:</b> {game.start_date.strftime('%d.%m.%Y %H:%M:%S')}
    <b>Автор:</b> {game.author}
    <b>Цена:</b> {game.price}
    <b>Тип игры:</b> {game.game_type}
    """

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ссылка на игру", url=game.link)],
        [InlineKeyboardButton(text="Хочу играть!", callback_data="go_to_bot")]
    ])

    chat_id = '-1002433786707'

    try:
        await bot.send_message(chat_id, message, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    except Exception as e:
        print(f"Ошибка при отправке сообщения: {e}")


from typing import Optional


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
    # Базовый текст сообщения
    message = f"""
    <b>Игра:</b> {game.name}
    <b>Автор:</b> {game.author}
    <b>Цена:</b> {game.price}
    <b>Тип игры:</b> {game.game_type}
    """

    # Добавляем текст в зависимости от типа сообщения
    if message_type == "start":
        message += f"\n<b>Начало:</b> {game.start_date.strftime('%d.%m.%Y %H:%M:%S')}"
    elif message_type == "reschedule_start":
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

    # Клавиатура с кнопками
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ссылка на игру", url=game.link)],
        [InlineKeyboardButton(text="Хочу играть!", callback_data="go_to_bot")]
    ])

    chat_id = '-1002433786707'

    try:
        await bot.send_message(chat_id, message, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    except Exception as e:
        print(f"Ошибка при отправке сообщения: {e}")


async def send_announcement_message(bot, game: GameDate):
    """Отправка сообщения о предстоящей игре (анонс) в чат с кнопками"""
    # Формируем текст сообщения с эмодзи
    announcement_message = f"""
    🚨 <b>Анонс игры:</b> {game.name}
    <b>Начало:</b> {game.start_date.strftime('%d.%m.%Y %H:%M:%S')}
    <b>Автор:</b> {game.author}
    <b>Цена:</b> {game.price}
    <b>Тип игры:</b> {game.game_type}
    """

    # Если анонс уже был отправлен
    if game.is_announcement_sent:
        announcement_message += "\n\n<i>Этот анонс был отправлен ранее.</i>"

    # Клавиатура с кнопками
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ссылка на игру", url=game.link)],
        [InlineKeyboardButton(text="Хочу играть!", callback_data="go_to_bot")]
    ])

    chat_id = '-1002433786707'

    try:
        await bot.send_message(chat_id, announcement_message, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    except Exception as e:
        bot_logger.error(f"Ошибка при отправке анонса для игры {game.id}: {e}")


async def send_start_message(bot, game: GameDate):
    """Отправка сообщения о старте игры в чат с кнопками"""

    # Формируем текст сообщения о старте с эмодзи
    start_message = f"""
    🚀 <b>Игра стартует!</b> {game.name}
    <b>Начало:</b> {game.start_date.strftime('%d.%m.%Y %H:%M:%S')}
    <b>Автор:</b> {game.author}
    <b>Цена:</b> {game.price}
    <b>Тип игры:</b> {game.game_type}
    """

    # Если стартовое сообщение уже было отправлено
    if game.is_start_message_sent:
        start_message += "\n\n<i>Стартовое сообщение уже отправлено ранее.</i>"

    # Клавиатура с кнопками
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ссылка на игру", url=game.link)],
        [InlineKeyboardButton(text="Хочу играть!", callback_data="go_to_bot")]
    ])

    chat_id = '-1002433786707'

    try:
        await bot.send_message(chat_id, start_message, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    except Exception as e:
        bot_logger.error(f"Ошибка при отправке стартового сообщения для игры {game.id}: {e}")


async def send_announcement_messages(game_dao, bot):
    """Отправляем анонсы для игр, у которых не были отправлены анонсы."""

    now = datetime.now()
    five_days_before = now + timedelta(days=5)

    # Получаем игры, для которых не были отправлены анонсы
    games_to_announce = await game_dao.get_all(
        is_announcement_sent=False,
        start_date__lte=five_days_before
    )

    for game in games_to_announce:
        # Отправляем анонс
        if not game.is_announcement_sent:
            await send_announcement_message(bot, game)
            game.is_announcement_sent = True
            bot_logger.info(f"Sent announcement for game {game.id}: {game.name}")

            # Обновляем статус в базе данных
            await game_dao.session.merge(game)
            await game_dao.session.commit()

            bot_logger.info(f"Game {game.id} updated after sending announcement.")


async def send_start_messages(game_dao, bot):
    """Отправляем стартовые сообщения для игр, у которых не были отправлены стартовые сообщения."""

    now = datetime.now()
    twelve_hours_before = now + timedelta(hours=12)

    # Получаем игры, для которых не были отправлены стартовые сообщения
    games_to_start = await game_dao.get_all(
        is_start_message_sent=False,
        start_date__lte=twelve_hours_before
    )

    for game in games_to_start:
        # Отправляем сообщение о старте
        if not game.is_start_message_sent:
            await send_start_message(bot, game)
            game.is_start_message_sent = True
            bot_logger.info(f"Sent start message for game {game.id}: {game.name}")

            # Обновляем статус в базе данных
            await game_dao.session.merge(game)
            await game_dao.session.commit()

            bot_logger.info(f"Game {game.id} updated after sending start message.")


async def check_and_send_messages(game_dao, bot):
    """Основной метод для проверки всех игр и отправки сообщений."""

    await send_announcement_messages(game_dao, bot)
    await send_start_messages(game_dao, bot)
    bot_logger.info("All game messages processed and updated.")
