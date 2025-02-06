from sqlalchemy import select

from db.dao.base import BaseDAO
from db.models import UserGameSubscription, UserGameRole, User


class UserGameSubscriptionDAO(BaseDAO):
    __model__ = UserGameSubscription

    async def add_user_to_subscription(self, user_id: int, game_id: int):
        existing_user = await self.session.execute(
            select(User).filter_by(telegram_id=user_id)
        )
        user = existing_user.scalars().first()
        existing_subscription = await self.get(user_id=user.id, game_id=game_id)

        if existing_subscription:
            return f"Вы уже подписаны на игру {game_id}."
        
        await self.create(user_id=user.id, game_id=game_id)
        return f"Вы успешно подписались на игру {game_id}."

    async def remove_user_from_subscription(self, user_id: int, game_id: int):
        """Удаляет подписку пользователя на игру"""
        existing_user = await self.session.execute(
            select(User).filter_by(telegram_id=user_id)
        )
        user = existing_user.scalars().first()

        existing_subscription = await self.get(user_id=user.id, game_id=game_id)
        if not existing_subscription:
            return f"Вы не подписаны на игру {game_id}."

        await self.delete(user_id=user.id, game_id=game_id)
        return f"Вы успешно отписались от игры {game_id}."


class UserGameRoleDAO(BaseDAO):
    __model__ = UserGameRole

    async def add_user_role(self, user_id: int, game_id: int, role: str):
        """Добавляет или обновляет роль пользователя в игре"""
        existing_user = await self.session.execute(
            select(User).filter_by(telegram_id=user_id)
        )
        user = existing_user.scalars().first()

        if not user:
            return "Ошибка: Пользователь не найден."

        existing_role = await self.get(user_id=user.id, game_id=game_id)

        if existing_role:
            existing_role.role = role
            await self.session.commit()
            return
        await self.create(user_id=user.id, game_id=game_id, role=role)
        return

    async def get_opposite_role_users(self, game_id: int, opposite_role: str):
        """Возвращает список пользователей с противоположной ролью"""
        async with self.session as session:
            result = await session.execute(
                select(User.nickname)
                .join(UserGameRole, User.id == UserGameRole.user_id)
                .filter(UserGameRole.game_id == game_id, UserGameRole.role == opposite_role)
            )
            return [row[0] for row in result.fetchall()]
