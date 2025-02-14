from aiogram import Bot
from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand, BotCommandScopeAllPrivateChats, \
    BotCommandScopeDefault
# from handlers.callbacks import SubscribeCallbackData
from keyboards.constants import MAIN_COMMANDS, CHAT_COMMANDS


class SubscribeCallbackData(CallbackData, prefix="subscribe"):
    game_id: int
    action: str


class SubscribeFromChannelCallbackData(CallbackData, prefix="subscribe_channel"):
    game_id: int
    action: str


class GameRoleCallbackData(CallbackData, prefix="game_role"):
    game_id: int
    action: str


class PaginationCallbackData(CallbackData, prefix="pagination"):
    action: str
    page: int


def default_game_keyboard(link: str, game_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ссылка на игру", url=link)],
        [InlineKeyboardButton(text="Хочу играть!",
                              callback_data=SubscribeFromChannelCallbackData(game_id=game_id,
                                                                             action="subscribe_channel").pack())]
    ])


def create_main_game_keyboard(link: str, game_id: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру с кнопками"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ссылка на игру", url=link)],
        [InlineKeyboardButton(text="Хочу играть!",
                              callback_data=SubscribeCallbackData(game_id=game_id, action="subscribe").pack())],
    ])


def create_dynamic_game_keyboard(link: str, game_id: int, is_subscribed: bool) -> InlineKeyboardMarkup:
    """Создает клавиатуру с кнопками, учитывая подписку"""
    if is_subscribed:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Ссылка на игру", url=link)],
            [InlineKeyboardButton(text="В подписках ✅", callback_data="show_subscriptions")]
        ])
    else:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Ссылка на игру", url=link)],
            [InlineKeyboardButton(text="Хочу играть!",
                                  callback_data=SubscribeCallbackData(game_id=game_id, action="subscribe").pack())]
        ])


async def set_main_menu(bot: Bot) -> None:
    main_menu_commands = [BotCommand(
        command=command,
        description=description
    ) for command, description in MAIN_COMMANDS.items()]
    channel_menu_commands = [BotCommand(
        command=command,
        description=description
    ) for command, description in CHAT_COMMANDS.items()]

    # await bot.set_my_commands(main_menu_commands)
    await bot.set_my_commands(main_menu_commands, scope=BotCommandScopeAllPrivateChats())
    await bot.set_my_commands(channel_menu_commands, scope=BotCommandScopeDefault())


def create_pagination_keyboard(page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Создаёт клавиатуру с кнопками пагинации"""

    buttons = []
    # Кнопка "Назад"
    if page > 1:
        buttons.append(
            InlineKeyboardButton(text="Назад",
                                 callback_data=PaginationCallbackData(page=page - 1, action="back").pack())
        )

    # Кнопка "Вперед"
    if page < total_pages:
        buttons.append(
            InlineKeyboardButton(text="Вперед",
                                 callback_data=PaginationCallbackData(page=page + 1, action="forward").pack())
        )

    keyboard = InlineKeyboardMarkup(row_width=2, inline_keyboard=[buttons])

    return keyboard


def create_team_finder_keyboard(game_id: int, link: str) -> InlineKeyboardMarkup:
    """Создает клавиатуру с кнопками 'Найти игрока' и 'Найти команду'"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ссылка на игру", url=link)],
        [InlineKeyboardButton(text="Поиск сокомандника",
                              callback_data=GameRoleCallbackData(game_id=game_id, action="open_team_search").pack())],
        # [InlineKeyboardButton(text="Найти игрока",
        #                       callback_data=GameRoleCallbackData(game_id=game_id, action="find_player").pack())],
        # [InlineKeyboardButton(text="Найти команду",
        #                       callback_data=GameRoleCallbackData(game_id=game_id, action="find_team").pack())],
        [InlineKeyboardButton(text="❌ Отписаться от игры",
                              callback_data=SubscribeCallbackData(game_id=game_id, action="unsubscribe").pack())]
    ])


# def create_team_search_menu_keyboard(game_id: int) -> InlineKeyboardMarkup:
#     """Создает клавиатуру для поиска сокомандника"""
#     return InlineKeyboardMarkup(inline_keyboard=[
#         [InlineKeyboardButton(text="Найти игрока",
#                               callback_data=GameRoleCallbackData(game_id=game_id, action="find_player").pack())],
#         [InlineKeyboardButton(text="Найти команду",
#                               callback_data=GameRoleCallbackData(game_id=game_id, action="find_team").pack())],
#         [InlineKeyboardButton(text="❌ Отписаться от поиска",
#                               callback_data=GameRoleCallbackData(game_id=game_id, action="cancel_search").pack())],
#         [InlineKeyboardButton(text="⬅️ Назад",
#                               callback_data=GameRoleCallbackData(game_id=game_id, action="back_to_main").pack())]
#     ])

def create_team_search_menu_keyboard(game_id: int, is_searching: bool, players_count: int,
                                     teams_count: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру для поиска сокомандника, включая кнопку отписки только если пользователь ищет"""
    keyboard = [
        [InlineKeyboardButton(text=f"Найти игрока ({players_count})",
                              callback_data=GameRoleCallbackData(game_id=game_id, action="find_player").pack())],
        [InlineKeyboardButton(text=f"Найти команду ({teams_count})",
                              callback_data=GameRoleCallbackData(game_id=game_id, action="find_team").pack())],
        [InlineKeyboardButton(text="⬅️ Назад",
                              callback_data=GameRoleCallbackData(game_id=game_id, action="back_to_main").pack())]
    ]

    # Если пользователь ищет, добавляем кнопку "Отписаться от поиска"
    if is_searching:
        keyboard.insert(2, [InlineKeyboardButton(text="❌ Отписаться от поиска",
                                                 callback_data=GameRoleCallbackData(game_id=game_id,
                                                                                    action="cancel_search").pack())])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)
