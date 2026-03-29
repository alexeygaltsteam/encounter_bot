from aiogram import Router, types, F
from pathlib import Path
from aiogram.exceptions import TelegramForbiddenError
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, FSInputFile
from db.models import GameState
from db.utils import ensure_user_registered, get_players_and_teams_count
from filters import PrivateChatFilter
from keyboards.constants import PRIVATE_COMMANDS, CHAT_COMMANDS, NOT_NICKNAME, START_MESSAGE
from keyboards.game_keyboards import create_main_game_keyboard, SubscribeCallbackData, create_team_finder_keyboard, \
    GameRoleCallbackData, SubscribeFromChannelCallbackData, create_dynamic_game_keyboard, \
    create_team_search_menu_keyboard, create_only_link_keyboard
from loader import game_dao, user_dao, user_subs_dao, user_role_dao
from logging_config import bot_logger
from messages.messages import format_game_message

router = Router()


def escape_html(text: str) -> str:
    """Экранирует HTML спецсимволы для безопасной вставки в HTML."""
    if not text:
        return text
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def get_user_facing_link(link: str) -> str:
    """Заменяет .encounter.cx на .en.cx для отображения пользователю."""
    if not link:
        return link
    return link.replace('.encounter.cx', '.en.cx')


@router.message(CommandStart(), PrivateChatFilter())
async def cmd_start(message: types.Message):
    if not message.from_user.username:
        await message.answer(NOT_NICKNAME)
        return

    user = await user_dao.get(telegram_id=message.from_user.id)

    if not user:
        user = await user_dao.create(
            telegram_id=message.from_user.id,
            nickname=message.from_user.username or f"User_{message.from_user.id}"
        )

    await message.answer(START_MESSAGE, parse_mode="HTML", )


def split_games_list(games, max_length=4096):
    """Разбивает список игр на логически завершенные части, не превышающие max_length."""
    parts = []
    current_part = []
    current_length = 0

    for game in games:
        players = "Один игрок" if game.game_type == "single" else (
            game.max_players if game.max_players > 0 else "Не указано")
        user_link = get_user_facing_link(game.link)
        game_text = (
            f"<b>🎮 <a href='{user_link}'>{escape_html(game.name)}</a></b>\n"
            f"<b>📅 Начало:</b> {game.start_date.strftime('%d.%m.%Y %H:%M')}\n"
            f"<b>📅 Конец:</b> {game.end_date.strftime('%d.%m.%Y %H:%M') if game.end_date else 'Отсутствует'}\n"
            f"<b>📝 Автор(ы):</b> {escape_html(game.author)}\n"
            f"<b>🌐 Домен:</b> {escape_html(game.domain)}\n"
            # f"👥 <b>Ограничение игроков</b>: {game.max_players if game.max_players > 0 else 'Не указано'}\n"
            f"👥 <b>Ограничение игроков</b>: {players}\n"
        )
        game_link = user_link
        game_id = game.id
        image_url = game.image

        if current_length + len(game_text) > max_length:
            parts.append(current_part)
            current_part = []
            current_length = 0

        current_part.append((game_text, game_link, game_id, image_url))
        current_length += len(game_text)

    if current_part:
        parts.append(current_part)

    return parts


@router.message(Command(commands='upcoming'), PrivateChatFilter())
@ensure_user_registered(user_dao)
async def upcoming_games_command(message: Message):
    user_id = message.from_user.id

    all_upcoming_games = await game_dao.get_all(
        state=GameState.UPCOMING.value, is_announcement_sent=True, order_by="start_date",
    )

    if not all_upcoming_games:
        await message.answer("На данный момент нет предстоящих игр.")
        return

    game_parts = split_games_list(all_upcoming_games)

    for part in game_parts:
        for game_text, game_link, game_id, image_url in part:
            # keyboard = create_main_game_keyboard(game_link, game_id)
            #
            # await message.answer(
            #     game_text,
            #     disable_web_page_preview=True,
            #     parse_mode="HTML",
            #     reply_markup=keyboard
            # )
            is_subscribed = await user_subs_dao.is_user_subscribed(user_id=user_id, game_id=game_id)
            keyboard = create_dynamic_game_keyboard(game_link, game_id, is_subscribed)

            # await message.answer(
            #     game_text,
            #     disable_web_page_preview=True,
            #     parse_mode="HTML",
            #     reply_markup=keyboard
            # )
            # if image_url:
            #     file_name = image_url.split("/")[-1]
            #     photo_path = Path(f"images/{file_name}").resolve()
            # else:
            #     photo_path = Path(f"images/DEFAULT.jpg").resolve()
            # await message.answer_photo(
            #     photo=FSInputFile(photo_path),
            #     caption=game_text,
            #     parse_mode="HTML",
            #     reply_markup=keyboard
            # )
            # file_name = image_url.split("/")[-1] if image_url else None
            file_name = str(game_id) + '.' + image_url.split('.')[-1] if image_url else None
            photo_path = Path(f"images/{file_name}").resolve()
            if not photo_path.exists() or not photo_path.is_file():
                bot_logger.info(
                    f"❌ Файл {photo_path} не найден. Используем изображение по умолчанию. "
                    f"Игра ID={game_id}, ссылка: {game_link}"
                )
                photo_path = Path("images/DEFAULT.jpg").resolve()

            await message.answer_photo(
                photo=FSInputFile(str(photo_path)),
                caption=game_text,
                parse_mode="HTML",
                reply_markup=keyboard
            )


@router.message(Command(commands='active'), PrivateChatFilter())
@ensure_user_registered(user_dao)
async def active_games_command(message: Message):
    user_id = message.from_user.id

    all_upcoming_games = await game_dao.get_all(
        state=GameState.ACTIVE.value, order_by="end_date"
    )

    if not all_upcoming_games:
        await message.answer("На данный момент нет активных игр.")
        return

    game_parts = split_games_list(all_upcoming_games)
    for part in game_parts:
        for game_text, game_link, game_id, image_url in part:
            is_subscribed = await user_subs_dao.is_user_subscribed(user_id=user_id, game_id=game_id)
            keyboard = create_dynamic_game_keyboard(game_link, game_id, is_subscribed)

            # await message.answer(
            #     game_text,
            #     disable_web_page_preview=True,
            #     parse_mode="HTML",
            #     reply_markup=keyboard
            # )
            # file_name = image_url.split("/")[-1] if image_url else None
            file_name = str(game_id) + '.' + image_url.split('.')[-1] if image_url else None
            photo_path = Path(f"images/{file_name}").resolve()
            if not photo_path.exists() or not photo_path.is_file():
                bot_logger.info(
                    f"❌ Файл {photo_path} не найден. Используем изображение по умолчанию. "
                    f"Игра ID={game_id}, ссылка: {game_link}"
                )
                photo_path = Path("images/DEFAULT.jpg").resolve()

            await message.answer_photo(
                photo=FSInputFile(str(photo_path)),
                caption=game_text,
                parse_mode="HTML",
                reply_markup=keyboard
            )


@router.message(Command(commands='help'))
@ensure_user_registered(user_dao)
async def help_command(message: types.Message):
    if message.chat.type == 'private':
        help_text = "\n".join(f"{command} {description}" for command, description in PRIVATE_COMMANDS.items())
    elif message.chat.type in ['group', 'supergroup']:
        help_text = "\n".join(f"{command} {description}" for command, description in CHAT_COMMANDS.items())
    else:
        help_text = "Неизвестный тип чата."

    await message.answer(f"<b>📜 Доступные команды:</b>\n\n{help_text}", parse_mode="HTML")


@router.callback_query(SubscribeCallbackData.filter())
async def handle_subscribe_callback(callback_query: CallbackQuery, callback_data: SubscribeCallbackData):
    from __main__ import bot
    game_id = callback_data.game_id
    action = callback_data.action
    user_id = callback_query.from_user.id

    message = ''

    if action == "subscribe":
        message = await user_subs_dao.add_user_to_subscription(game_id=game_id, user_id=user_id)

        is_subscribed = True
        new_keyboard = create_dynamic_game_keyboard(
            link=callback_query.message.reply_markup.inline_keyboard[0][0].url,
            game_id=game_id,
            is_subscribed=is_subscribed
        )

        try:
            await bot.edit_message_reply_markup(
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                reply_markup=new_keyboard
            )
        except Exception as e:
            bot_logger.error(f"Ошибка при обновлении кнопки подписки для игры {game_id}: {e}")

    if action == "unsubscribe":
        message = await user_subs_dao.remove_user_from_subscription(user_id=user_id, game_id=game_id)

        # try:
        #     await bot.answer_callback_query(callback_query.id, text=f"Вы успешно отписались от игры {game_id}!")
        # except Exception as e:
        #     print(f"Ошибка при отправке сплывающего сообщения: {e}")
        game = await game_dao.get(id=game_id)
        message_text = f"Вы отписались от игры <b>{game.name}</b>."
        try:
            await bot.send_message(user_id, message_text, parse_mode="HTML")
            await bot.delete_message(chat_id=callback_query.message.chat.id,
                                     message_id=callback_query.message.message_id)
        except Exception as e:
            bot_logger.error(f"Ошибка при удалении/отправке сообщения после отписки от игры {game_id}: {e}")

    try:
        await bot.answer_callback_query(callback_query.id, text=message)
    except Exception as e:
        bot_logger.error(f"Ошибка при ответе на callback для игры {game_id}: {e}")


@router.message(Command(commands='subs'), PrivateChatFilter())
@ensure_user_registered(user_dao)
async def subs_command(message: types.Message):
    games = await user_dao.get_user_subscribed_games(telegram_id=message.from_user.id)

    if not games:
        await message.answer("Вы не подписаны ни на одну игру.")
        return

    for game in games:
        header = "🔎 <b>Поиск игроков и команд!</b>"
        text = format_game_message(game, header)
        keyboard = create_team_finder_keyboard(game.id, get_user_facing_link(game.link))
        image_url = game.image

        # file_name = image_url.split("/")[-1] if image_url else None
        file_name = str(game.id) + '.' + image_url.split('.')[-1] if image_url else None
        photo_path = Path(f"images/{file_name}").resolve()
        if not photo_path.exists() or not photo_path.is_file():
            bot_logger.info(
                f"❌ Файл {photo_path} не найден. Используем изображение по умолчанию. "
                f"Игра ID={game.id}, ссылка: {game.link}"
            )
            photo_path = Path("images/DEFAULT.jpg").resolve()

        await message.answer_photo(
            photo=FSInputFile(str(photo_path)),
            caption=text,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        #
        # await message.answer(
        #     text,
        #     disable_web_page_preview=True,
        #     parse_mode="HTML",
        #     reply_markup=keyboard
        # )


@router.callback_query(GameRoleCallbackData.filter(F.action == "open_team_search"))
async def open_team_search(callback_query: CallbackQuery, callback_data: GameRoleCallbackData):
    """Обрабатывает нажатие на кнопку 'Поиск сокомандника' и меняет клавиатуру"""
    game_id = callback_data.game_id
    user_id = callback_query.from_user.id
    game = await game_dao.get(id=game_id)
    if not game:
        return f"Упс {game_id} уже не существует."

    counts = await get_players_and_teams_count(game_id)
    players_count = counts["players"]
    teams_count = counts["teams"]

    is_searching = await user_role_dao.is_user_searching(user_id=user_id, game_id=game_id)
    new_keyboard = create_team_search_menu_keyboard(game_id, is_searching=is_searching, players_count=players_count,
                                                    teams_count=teams_count)

    await callback_query.message.edit_reply_markup(reply_markup=new_keyboard)


@router.callback_query(GameRoleCallbackData.filter(F.action == "back_to_main"))
async def back_to_main(callback_query: CallbackQuery, callback_data: GameRoleCallbackData):
    """Обрабатывает кнопку 'Назад' и возвращает основную клавиатуру"""
    game_id = callback_data.game_id
    game = await game_dao.get(id=game_id)
    if not game:
        return f"Упс {game_id} уже не существует."
    new_keyboard = create_team_finder_keyboard(game_id, get_user_facing_link(game.link))

    await callback_query.message.edit_reply_markup(reply_markup=new_keyboard)


@router.callback_query(GameRoleCallbackData.filter())
async def handle_game_role_callback(callback_query: CallbackQuery, callback_data: GameRoleCallbackData):
    from __main__ import bot
    game_id = callback_data.game_id
    action = callback_data.action
    user_id = callback_query.from_user.id
    game = await game_dao.get(id=game_id)
    if not game:
        return f"Упс {game_id} уже не существует."

    if action == "cancel_search":
        user = await user_dao.get(telegram_id=user_id)
        user_role = await user_role_dao.get(user_id=user.id, game_id=game_id)
        if user_role:
            await user_role_dao.delete(user_id=user.id, game_id=game_id)

        response_text = "Вы успешно отписались от поиска."

        counts = await get_players_and_teams_count(game_id)
        players_count = counts["players"]
        teams_count = counts["teams"]
        new_keyboard = create_team_search_menu_keyboard(game_id, is_searching=False, players_count=players_count,
                                                        teams_count=teams_count)

        try:
            await bot.answer_callback_query(callback_query.id, text=response_text)
            await bot.edit_message_reply_markup(chat_id=callback_query.message.chat.id,
                                                message_id=callback_query.message.message_id,
                                                reply_markup=new_keyboard)
        except Exception as e:
            bot_logger.error(f"Ошибка при обработке отмены поиска для игры {game_id}: {e}")
        return

    role = "Команда" if action == "find_player" else "Игрок"
    await user_role_dao.add_user_role(user_id=user_id, game_id=game_id, role=role)

    opposite_role = "Команда" if role == "Игрок" else "Игрок"
    matched_users = await user_role_dao.get_opposite_role_users(game_id, opposite_role)
    # message = f'<b><a href="{game.link}">Игра : «{game.name}»</a></b>\n'
    message = ''
    user_list = "\n".join([f"@{nickname}" for nickname in matched_users])
    if matched_users:
        if role == "Команда":
            message += f"👥 <b>Доступные игроки</b>:\n{user_list}"
        else:
            message += f"👑 <b>Доступные капитаны</b>:\n{user_list}"
    else:
        message += f"😔 Ты первый!\n Пока нет доступных сокомандников к игре \n«<b>{game.name}</b>»"

    if role == "Игрок":
        response_text = "Теперь вы ищете команду."
    else:
        response_text = "Теперь вы ищете игроков."

    counts = await get_players_and_teams_count(game_id)
    players_count = counts["players"]
    teams_count = counts["teams"]

    new_keyboard = create_team_search_menu_keyboard(game_id, is_searching=True, players_count=players_count,
                                                    teams_count=teams_count)
    link_keyboard = create_only_link_keyboard(get_user_facing_link(game.link))

    try:
        await bot.answer_callback_query(callback_query.id, text=response_text)
        await bot.send_message(chat_id=callback_query.message.chat.id, text=message, reply_markup=link_keyboard,
                               parse_mode="HTML")
        await bot.edit_message_reply_markup(chat_id=callback_query.message.chat.id,
                                            message_id=callback_query.message.message_id,
                                            reply_markup=new_keyboard)
    except Exception as e:
        bot_logger.error(f"Ошибка при отправке сообщений/клавиатур для игры {game_id}: {e}")


@router.callback_query(SubscribeFromChannelCallbackData.filter())
async def handle_subscribe_from_channel_callback(callback_query: CallbackQuery,
                                                 callback_data: SubscribeFromChannelCallbackData):
    from __main__ import bot
    game_id = callback_data.game_id
    action = callback_data.action
    user_id = callback_query.from_user.id

    if not callback_query.from_user.username:
        await callback_query.answer(NOT_NICKNAME)
        return

    user = await user_dao.get(telegram_id=user_id)

    if not user:
        await user_dao.create(
            telegram_id=user_id,
            nickname=callback_query.from_user.username or f"User_{callback_query.from_user.id}"
        )

    if action == "subscribe_channel":
        await user_subs_dao.add_user_to_subscription(game_id=game_id, user_id=user_id)
        game = await game_dao.get(id=game_id)
        message_text = f"Привет! Вы подписались на игру <b>{game.name}</b>. Для просмотра подписок использвуйте /subs"
        try:
            await bot.send_message(user_id, message_text, parse_mode="HTML")
            await bot.answer_callback_query(callback_query.id, text="Мы отправили вам сообщение!")
        except TelegramForbiddenError:
            await bot.answer_callback_query(callback_query.id, text="Мы не смогли отправить личное сообщение. Напишите боту в личные сообщения.")
        except Exception as e:
            bot_logger.error(f"Ошибка при отправке личного сообщения о подписке на игру {game_id}: {e}")


@router.callback_query(F.data == "show_subscriptions")
async def show_user_subscriptions(callback_query: CallbackQuery):
    await callback_query.message.answer("📋 Ваши подписки: /subs")
    await callback_query.answer()


@router.message(Command(commands='actives'), PrivateChatFilter())
@ensure_user_registered(user_dao)
async def short_actives_games_command(message: Message):
    all_upcoming_games = await game_dao.get_all(
        state=GameState.ACTIVE.value, order_by="end_date"
    )
    if not all_upcoming_games:
        await message.answer("На данный момент нет активных игр.")
        return
    games_list = []

    for index, game in enumerate(all_upcoming_games, start=1):
        game_link = get_user_facing_link(game.link) if game.link else "#"
        game_end_date = game.end_date.strftime('%d.%m.%Y %H:%M') if game.end_date else "Не указана"

        game_name_with_link = f'<a href="{game_link}">{escape_html(game.name)}</a>'
        players = "Один игрок" if game.game_type == "single" else (
            game.max_players if game.max_players > 0 else "Не указано")
        game_info = f"""
<b>{index}. {game_name_with_link}</b>
<i>Игроков:</i> {players}
<i>Автор:</i> {escape_html(game.author)}
<i>Дата окончания:</i> {game_end_date}
"""
        games_list.append(game_info)
    max_message_length = 4096
    current_message = ""

    for game in games_list:
        if len(current_message) + len(game) + 1 > max_message_length:
            await message.answer(current_message, parse_mode="HTML")
            current_message = game
        else:
            current_message += game
    if current_message:
        await message.answer(current_message, parse_mode="HTML", disable_web_page_preview=True)
