from datetime import datetime

from sqlalchemy import delete

from db.dao import GameDateDAO
from db.models import GameState, UserGameSubscription, UserGameRole
from loader import db, user_role_dao, user_subs_dao
from logging_config import bot_logger
import pytz
from functools import wraps
from aiogram import types

game_dao = GameDateDAO(db.async_session)


async def update_game_states():
    """
    Обновляет статусы игр в зависимости от текущего времени.
    """
    bot_logger.info("Starting the game state update process.")
    try:

        games = await game_dao.get_all()
        updated_counts = {GameState.UPCOMING: 0, GameState.ACTIVE: 0, GameState.COMPLETED: 0}

        moscow_tz = pytz.timezone('Europe/Moscow')
        now = datetime.now(moscow_tz).replace(tzinfo=None)

        async with game_dao.session_factory() as session:
            for game in games:
                # Не трогаем игры, которые уже завершены парсером
                if game.state == GameState.COMPLETED.value:
                    continue

                game_start_date = game.start_date.replace(tzinfo=None)

                if game_start_date > now:
                    new_state = GameState.UPCOMING
                elif game_start_date <= now and (game.end_date is None or game.end_date.replace(tzinfo=None) > now):
                    new_state = GameState.ACTIVE
                else:
                    new_state = GameState.COMPLETED

                if game.state != new_state.value:
                    # Определяем причину смены статуса
                    if new_state == GameState.UPCOMING:
                        reason = f"start_date ({game_start_date}) > now ({now})"
                    elif new_state == GameState.ACTIVE:
                        if game.end_date is None:
                            reason = f"start_date ({game_start_date}) <= now ({now}), end_date=None"
                        else:
                            reason = f"start_date ({game_start_date}) <= now ({now}), end_date ({game.end_date.replace(tzinfo=None)}) > now"
                    else:  # COMPLETED
                        reason = f"start_date ({game_start_date}) <= now ({now}), end_date ({game.end_date.replace(tzinfo=None) if game.end_date else 'None'}) <= now"

                    bot_logger.info(
                        f"Updating game {game.id} from {game.state} to {new_state}. "
                        f"Причина: {reason}. Ссылка: https://{game.domain}/GameDetails.aspx?gid={game.id}"
                    )
                    game.state = new_state.value
                    await session.merge(game)
                    updated_counts[new_state] += 1

            await session.commit()
        bot_logger.info(
            "Game state update process completed successfully. "
            f"Changed: UPCOMING={updated_counts[GameState.UPCOMING]}, "
            f"ACTIVE={updated_counts[GameState.ACTIVE]}, "
            f"COMPLETED={updated_counts[GameState.COMPLETED]}"
        )
    except Exception as e:
        bot_logger.error(f"Error during game state update: {e}")


def ensure_user_registered(user_dao):
    """ Декоратор для проверки, зарегистрирован ли пользователь. """

    def decorator(handler):
        @wraps(handler)
        async def wrapper(message: types.Message, *args, **kwargs):
            user = await user_dao.get(telegram_id=message.from_user.id)
            if not user:
                await message.answer("❌ Для начала работы нажмите /start")
                return
            return await handler(message, *args, **kwargs)

        return wrapper

    return decorator


async def get_players_and_teams_count(game_id: int) -> dict:
    """Возвращает количество доступных игроков и команд для игры."""
    players_count = await user_role_dao.get_opposite_role_users_count(game_id, "Игрок")
    teams_count = await user_role_dao.get_opposite_role_users_count(game_id, "Команда")

    return {
        "players": players_count,
        "teams": teams_count
    }
