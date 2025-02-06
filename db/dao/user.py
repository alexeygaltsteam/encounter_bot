from sqlalchemy import select
from sqlalchemy.orm import joinedload

from db.dao.base import BaseDAO
from db.models import User, GameDate, UserGameSubscription


class UserDAO(BaseDAO):
    __model__ = User

    # async def get_user_subscribed_games(self, telegram_id: int):
    #     async with self.session as session:
    #         result = await session.execute(
    #             select(User)
    #             .filter_by(telegram_id=telegram_id)
    #             .options(joinedload(User.subscribed_games))
    #         )
    #         user = result.scalars().first()
    #         if user:
    #             return user.subscribed_games
    #         return None

    async def get_user_subscribed_games(self, telegram_id: int):
        async with self.session as session:
            result = await session.execute(
                select(GameDate)
                .join(UserGameSubscription, UserGameSubscription.game_id == GameDate.id)
                .join(User, UserGameSubscription.user_id == User.id)
                .filter(User.telegram_id == telegram_id)
            )
            return result.scalars().all()

