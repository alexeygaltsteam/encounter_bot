import asyncio
from datetime import datetime

from loader import bot, dp, db, game_dao


async def check_and_send_messages(game_dao, bot):
    """Метод для проверки всех игр в базе данных, чьи start_date наступили в течение 6 часов, и отправки сообщений."""
    games = await game_dao.get_all()
    # date_value = datetime.strptime('2025-01-16', '%Y-%m-%d').date()
    # results = await game_dao.get_all(start_date__lte=date_value)
    # print(results)
    game = games[0]
    game.name = "asd"
    print(game.id)
    print(game)
    game = await game_dao.session.merge(game)
    await game_dao.session.commit()


    # Отправляем сообщение для каждой игры
    # for game in games:
    #     await send_game_message(bot, game)


if __name__ == "__main__":
    asyncio.run(check_and_send_messages(game_dao=game_dao, bot=bot))
