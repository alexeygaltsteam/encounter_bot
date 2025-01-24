from datetime import datetime
from db.dao import GameDateDAO
from db.models import GameState
from loader import db
from logging_config import bot_logger

game_dao = GameDateDAO(db.async_session)


async def update_game_states():
    """
    Обновляет статусы игр в зависимости от текущего времени.
    """
    bot_logger.info("Starting the game state update process.")
    try:

        games = await game_dao.get_all()

        now = datetime.now().replace(tzinfo=None)

        for game in games:
            game_start_date = game.start_date.replace(tzinfo=None)

            if game_start_date > now:
                new_state = GameState.UPCOMING
            elif game_start_date <= now and (game.end_date is None or game.end_date.replace(tzinfo=None) > now):
                new_state = GameState.ACTIVE
            else:
                new_state = GameState.COMPLETED

            if game.state != new_state.value:
                bot_logger.info(f"Updating game {game.id} from {game.state} to {new_state}.")
                game.state = new_state.value
                await game_dao.session.merge(game)

            if game.state != new_state.value:
                bot_logger.info(f"Updating game {game.id} from {game.state} to {new_state}.")
                game.state = new_state.value
                await game_dao.session.merge(game)

        await game_dao.session.commit()
        await game_dao.session.close()
        bot_logger.info("Game state update process completed successfully.")
    except Exception as e:
        bot_logger.error(f"Error during game state update: {e}")
