from aiogram import Router, types, Bot
from aiogram.exceptions import TelegramForbiddenError
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, BotCommand, CallbackQuery
from db.models import GameState
from filters import PrivateChatFilter
from keyboards.constants import PRIVATE_COMMANDS, CHAT_COMMANDS
from keyboards.game_keyboards import create_main_game_keyboard, SubscribeCallbackData, create_pagination_keyboard, \
    PaginationCallbackData
from loader import game_dao

router = Router()


@router.message(CommandStart(), PrivateChatFilter())
async def cmd_start(message: types.Message):
    await message.answer('''Привет! 👋
🤖 Enc bot. Чем могу помочь?''')


def split_games_list(games, max_length=4096):
    """Разбивает список игр на логически завершенные части, не превышающие max_length."""
    parts = []
    current_part = []
    current_length = 0

    for game in games:
        game_text = (
            f"🎮 <b>{game.name}</b>\n"
            f"📅 Дата начала: {game.start_date.strftime('%d.%m.%Y %H:%M')}\n"
            f"👥 Количество участников: {game.max_players or 'Не указано'}\n"
        )
        game_link = game.link
        game_id = game.id

        if current_length + len(game_text) > max_length:
            parts.append(current_part)
            current_part = []
            current_length = 0

        current_part.append((game_text, game_link, game_id))
        current_length += len(game_text)

    if current_part:
        parts.append(current_part)

    return parts


@router.message(Command(commands='upcoming'))
async def upcoming_games_command(message: Message):
    all_upcoming_games = await game_dao.get_all(
        state=GameState.UPCOMING.value, is_announcement_sent=True
    )

    if not all_upcoming_games:
        await message.answer("На данный момент нет предстоящих игр.")
        return

    game_parts = split_games_list(all_upcoming_games)

    for part in game_parts:
        for game_text, game_link, game_id in part:
            keyboard = create_main_game_keyboard(game_link, game_id)

            await message.answer(
                game_text,
                disable_web_page_preview=True,
                parse_mode="HTML",
                reply_markup=keyboard
            )


@router.message(Command(commands='active'))
async def active_games_command(message: Message):
    all_upcoming_games = await game_dao.get_all(
        state=GameState.ACTIVE.value
    )

    if not all_upcoming_games:
        await message.answer("На данный момент нет активных игр.")
        return

    game_parts = split_games_list(all_upcoming_games)

    for part in game_parts:
        for game_text, game_link, game_id in part:
            keyboard = create_main_game_keyboard(game_link, game_id)

            await message.answer(
                game_text,
                disable_web_page_preview=True,
                parse_mode="HTML",
                reply_markup=keyboard
            )


@router.message(Command(commands='help'))
async def help_command(message: types.Message):
    if message.chat.type == 'private':
        help_text = "\n".join(f"{command}: {description}" for command, description in PRIVATE_COMMANDS.items())
    elif message.chat.type in ['group', 'supergroup']:
        help_text = "\n".join(f"{command}: {description}" for command, description in CHAT_COMMANDS.items())
    else:
        help_text = "Неизвестный тип чата."

    await message.answer(help_text)


@router.callback_query(SubscribeCallbackData.filter())
async def handle_subscribe_callback(callback_query: CallbackQuery, callback_data: SubscribeCallbackData):
    from __main__ import bot
    game_id = callback_data.game_id
    action = callback_data.action

    user_id = callback_query.from_user.id

    if action == "subscribe":
        # await add_user_to_subscription(game_id, user_id)
        message_text = "Привет! Вы нажали на кнопку для перехода к боту. Для дальнейших действий переходите по ссылке: https://t.me/enc_finder_bot."
        try:
            await bot.send_message(user_id, message_text)
            await bot.answer_callback_query(callback_query.id, text="Мы отправили вам сообщение!")
        except TelegramForbiddenError:
            await bot.answer_callback_query(callback_query.id, text="Мы не смогли отправиль личное сообщение")

        except Exception as e:
            print(f"Ошибка при отправке личного сообщения: {e}")
